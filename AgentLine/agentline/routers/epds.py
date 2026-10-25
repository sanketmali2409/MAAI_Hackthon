"""
AgentLine — EPDS Screening Router

Runs Edinburgh Postnatal Depression Scale screening on top of a voice call.
Answers are captured one at a time (as the agent asks each question) and the
score is computed in code — never by the LLM — then banded into low / medium /
high risk. Answering question 10 affirmatively raises a self-harm flag for
immediate human escalation.
"""

import logging
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Body, Depends, HTTPException

from agentline import bolna, epds
from agentline.auth_middleware import get_current_account
from agentline.database import get_db
from agentline.escalation import create_escalation, escalate_from_result
from agentline.models.epds import (
    EpdsAnswerIn,
    EpdsCallCreate,
    EpdsScoreRequest,
    EpdsSessionCreate,
    EpdsSessionOut,
    EscalationCreate,
    EscalationUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/epds", tags=["EPDS"])


async def _load_answers(db, session_id: str) -> dict[int, int]:
    rows = await db.fetch(
        "SELECT question_no, answer FROM epds_responses WHERE session_id = $1",
        session_id,
    )
    return {r["question_no"]: r["answer"] for r in rows}


async def _record_one(db, session_id: str, question_no: int, answer: int) -> None:
    """Validate scoring then upsert one answer (idempotent per question)."""
    score = epds.score_answer(question_no, answer)  # raises ValueError on bad input
    await db.execute(
        """INSERT INTO epds_responses (session_id, question_no, answer, score)
           VALUES ($1,$2,$3,$4)
           ON CONFLICT (session_id, question_no)
           DO UPDATE SET answer = EXCLUDED.answer, score = EXCLUDED.score,
                         created_at = now()""",
        session_id,
        question_no,
        answer,
        score,
    )


async def _get_session(db, session_id: str, account_id: str) -> dict:
    row = await db.fetchrow(
        "SELECT * FROM epds_sessions WHERE id = $1 AND account_id = $2",
        session_id,
        account_id,
    )
    if not row:
        raise HTTPException(404, "EPDS session not found.")
    return dict(row)


async def _finalize(db, session_id: str) -> dict:
    """Recompute the score from stored answers, persist band/flag/status, and
    raise clinician escalations for self-harm / high-risk results."""
    answers = await _load_answers(db, session_id)
    result = epds.compute(answers)
    status = "completed" if result["complete"] else "in_progress"
    completed_at = datetime.now(timezone.utc) if result["complete"] else None
    row = await db.fetchrow(
        """UPDATE epds_sessions
           SET total_score = $2, risk_band = $3, self_harm_flag = $4,
               status = $5, completed_at = $6
           WHERE id = $1
           RETURNING *""",
        session_id,
        result["total_score"],
        result["risk_band"],
        result["self_harm_flag"],
        status,
        completed_at,
    )
    escalations = await escalate_from_result(db, dict(row), result)
    result["escalations"] = [e["id"] for e in escalations]
    return result


async def _create_and_trigger(
    db,
    account_id: str,
    *,
    mother_id: str | None,
    phone: str,
    name: str | None,
    language: str,
    agent_id: str | None,
) -> tuple[str, str | None, dict]:
    """Create an in_progress session and place the Bolna call for it.

    Returns (session_id, execution_id, bolna_response). Marks the session
    'failed' and re-raises BolnaError if the call cannot be placed.
    """
    session_id = f"eps_{secrets.token_urlsafe(12)}"
    now = datetime.now(timezone.utc)
    await db.execute(
        """INSERT INTO epds_sessions
           (id, account_id, agent_id, mother_id, subject_name, subject_phone,
            language, status, self_harm_flag, created_at)
           VALUES ($1,$2,$3,$4,$5,$6,$7,'in_progress',false,$8)""",
        session_id,
        account_id,
        agent_id,
        mother_id,
        name,
        phone,
        language,
        now,
    )
    try:
        call = await bolna.trigger_call(
            recipient_phone_number=phone,
            session_id=session_id,
            agent_id=agent_id,
            user_data={"language": language, "subject_name": name or ""},
        )
    except bolna.BolnaError:
        await db.execute(
            "UPDATE epds_sessions SET status = 'failed' WHERE id = $1", session_id
        )
        raise
    execution_id = call.get("execution_id")
    await db.execute(
        "UPDATE epds_sessions SET call_id = $2, bolna_execution_id = $2 WHERE id = $1",
        session_id,
        execution_id,
    )
    return session_id, execution_id, call


@router.get("/questionnaire", operation_id="get_epds_questionnaire")
async def get_questionnaire(language: str | None = None):
    """
    Get the 10 EPDS questions and answer options.

    Pass ?language=hi (or en, pa) to receive a single language; omit it to get
    every language. Use this to drive the agent's conversation, one question at
    a time. Answer indices (0-3) returned here map to POST .../answers.
    """
    return {"questions": epds.questionnaire(language)}


@router.post("/score", operation_id="score_epds")
async def score_epds(body: EpdsScoreRequest):
    """
    Score a full or partial set of EPDS answers without saving anything.

    Stateless helper for quick scoring or testing. Each answer is the option
    index (0-3) in display order; reverse-scored items are handled in code.
    Returns the total (0-30), risk band, and self-harm flag.
    """
    answers: dict[int, int] = {}
    for a in body.answers:
        answers[a.question_no] = a.answer
    try:
        return epds.compute(answers)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/sessions", response_model=EpdsSessionOut, operation_id="create_epds_session")
async def create_session(
    body: EpdsSessionCreate,
    account=Depends(get_current_account),
    db=Depends(get_db),
):
    """
    Start a new EPDS screening session for one mother.

    Create this when a screening call begins, then post each answer as the
    agent collects it. The session tracks the running score, risk band, and
    self-harm flag until all 10 questions are answered.
    """
    session_id = f"eps_{secrets.token_urlsafe(12)}"
    now = datetime.now(timezone.utc)
    await db.execute(
        """INSERT INTO epds_sessions
           (id, account_id, agent_id, call_id, mother_id, subject_name, subject_phone,
            language, status, self_harm_flag, created_at)
           VALUES ($1,$2,$3,$4,$5,$6,$7,$8,'in_progress',false,$9)""",
        session_id,
        account["id"],
        body.agent_id,
        body.call_id,
        body.mother_id,
        body.subject_name,
        body.subject_phone,
        body.language,
        now,
    )
    row = await _get_session(db, session_id, account["id"])
    return EpdsSessionOut(**row)


@router.post("/calls", operation_id="start_epds_call")
async def start_call(
    body: EpdsCallCreate,
    account=Depends(get_current_account),
    db=Depends(get_db),
):
    """
    Start an outbound EPDS screening call via Bolna.

    Creates a screening session, then asks Bolna to call the mother in her
    language. The session_id is handed to Bolna as a dynamic variable so its
    in-call tools can post each answer back here. Pass mother_id to call a
    registered mother (active consent is required) or subject_phone for a
    one-off call. Returns the session and Bolna's execution id.
    """
    mother_id = body.mother_id
    phone = body.subject_phone
    name = body.subject_name
    language = body.language

    if mother_id:
        mother = await db.fetchrow(
            "SELECT * FROM mothers WHERE id = $1 AND account_id = $2",
            mother_id,
            account["id"],
        )
        if not mother:
            raise HTTPException(404, "Mother not found.")
        consent = await db.fetchrow(
            """SELECT * FROM consent WHERE mother_id = $1
               ORDER BY recorded_at DESC LIMIT 1""",
            mother_id,
        )
        if not (consent and consent["consented"] and consent["revoked_at"] is None):
            raise HTTPException(403, "Mother has no active consent for screening calls.")
        phone = phone or mother["phone"]
        name = name or mother["name"]
        language = body.language or mother["language"]

    if not phone:
        raise HTTPException(400, "subject_phone is required when mother_id is not given.")

    try:
        session_id, execution_id, call = await _create_and_trigger(
            db,
            account_id=account["id"],
            mother_id=mother_id,
            phone=phone,
            name=name,
            language=language,
            agent_id=body.agent_id,
        )
    except bolna.BolnaError as e:
        raise HTTPException(502, f"Failed to start Bolna call: {e}")

    session = await _get_session(db, session_id, account["id"])
    return {"session": session, "execution_id": execution_id, "bolna": call}


@router.post("/calls/run-due", operation_id="run_due_epds_calls")
async def run_due_calls(
    limit: int = 50,
    account=Depends(get_current_account),
    db=Depends(get_db),
):
    """
    Place screening calls for every mother who is due right now.

    Picks active mothers whose next_call_at has passed, skips any without
    active consent, triggers a Bolna call for the rest, and advances each
    caller's next_call_at by her cadence (daily / weekly). Intended to be hit
    by a cron. Returns a per-mother breakdown.
    """
    now = datetime.now(timezone.utc)
    due = await db.fetch(
        """SELECT * FROM mothers
           WHERE account_id = $1 AND active = true
             AND next_call_at IS NOT NULL AND next_call_at <= $2
           ORDER BY next_call_at ASC
           LIMIT $3""",
        account["id"],
        now,
        limit,
    )

    results: list[dict] = []
    called = skipped = failed = 0
    for m in due:
        mother = dict(m)
        consent = await db.fetchrow(
            """SELECT * FROM consent WHERE mother_id = $1
               ORDER BY recorded_at DESC LIMIT 1""",
            mother["id"],
        )
        if not (consent and consent["consented"] and consent["revoked_at"] is None):
            skipped += 1
            results.append({"mother_id": mother["id"], "status": "skipped_no_consent"})
            continue

        try:
            session_id, execution_id, _ = await _create_and_trigger(
                db,
                account_id=account["id"],
                mother_id=mother["id"],
                phone=mother["phone"],
                name=mother["name"],
                language=mother["language"],
                agent_id=None,
            )
        except bolna.BolnaError as e:
            failed += 1
            results.append(
                {"mother_id": mother["id"], "status": "call_failed", "error": str(e)}
            )
            continue

        delta = timedelta(days=1 if mother["call_cadence"] == "daily" else 7)
        await db.execute(
            "UPDATE mothers SET next_call_at = $2 WHERE id = $1",
            mother["id"],
            now + delta,
        )
        called += 1
        results.append(
            {
                "mother_id": mother["id"],
                "status": "called",
                "session_id": session_id,
                "execution_id": execution_id,
            }
        )

    return {
        "due": len(due),
        "called": called,
        "skipped": skipped,
        "failed": failed,
        "results": results,
    }


@router.get("/sessions", operation_id="list_epds_sessions")
async def list_sessions(
    account=Depends(get_current_account),
    db=Depends(get_db),
):
    """
    List EPDS screening sessions for your account, newest first.

    Returns each session with its current score, risk band, and self-harm
    flag — the backbone of a clinician triage view.
    """
    rows = await db.fetch(
        "SELECT * FROM epds_sessions WHERE account_id = $1 ORDER BY created_at DESC",
        account["id"],
    )
    return [dict(r) for r in rows]


@router.get("/sessions/{session_id}", operation_id="get_epds_session")
async def get_session(
    session_id: str,
    account=Depends(get_current_account),
    db=Depends(get_db),
):
    """
    Get one EPDS session with its answers and computed score.

    Returns the session record plus every recorded answer and a live
    recomputation of the total, risk band, and self-harm flag.
    """
    session = await _get_session(db, session_id, account["id"])
    answers = await _load_answers(db, session_id)
    result = epds.compute(answers)
    return {"session": session, "result": result, "answers": answers}


@router.post("/sessions/{session_id}/answers", operation_id="record_epds_answer")
async def record_answer(
    session_id: str,
    body: EpdsScoreRequest,
    account=Depends(get_current_account),
    db=Depends(get_db),
):
    """
    Record one or more EPDS answers for a session.

    This is the webhook target the agent hits as it collects each answer.
    Answers are idempotent per question (re-posting overwrites). Once all 10
    are in, the session is finalized automatically with its risk band.
    """
    session = await _get_session(db, session_id, account["id"])
    if session["status"] == "completed":
        raise HTTPException(409, "Session already completed.")
    if not body.answers:
        raise HTTPException(400, "No answers provided.")

    for a in body.answers:
        # Validate scoring before persisting so a bad index never lands in the DB.
        try:
            await _record_one(db, session_id, a.question_no, a.answer)
        except ValueError as e:
            raise HTTPException(400, str(e))

    result = await _finalize(db, session_id)
    if result["self_harm_flag"]:
        logger.warning("EPDS self-harm flag raised on session %s — escalate.", session_id)
    return result


@router.post("/sessions/{session_id}/answer", operation_id="record_epds_answer_single")
async def record_single_answer(
    session_id: str,
    body: EpdsAnswerIn,
    account=Depends(get_current_account),
    db=Depends(get_db),
):
    """
    Record a single EPDS answer (question_no + answer).

    Flat single-answer variant the Bolna voice agent calls once per question as
    the conversation progresses — easier to map than the batch endpoint. Same
    idempotent upsert and auto-finalize behavior.
    """
    session = await _get_session(db, session_id, account["id"])
    if session["status"] == "completed":
        raise HTTPException(409, "Session already completed.")
    try:
        await _record_one(db, session_id, body.question_no, body.answer)
    except ValueError as e:
        raise HTTPException(400, str(e))

    result = await _finalize(db, session_id)
    if result["self_harm_flag"]:
        logger.warning("EPDS self-harm flag raised on session %s — escalate.", session_id)
    return result


@router.post("/sessions/{session_id}/finalize", operation_id="finalize_epds_session")
async def finalize_session(
    session_id: str,
    account=Depends(get_current_account),
    db=Depends(get_db),
):
    """
    Force-finalize a session from the answers collected so far.

    Normally a session finalizes itself once all 10 answers are in. Call this
    to score an incomplete session (e.g. the mother ended the call early);
    the risk band is only set when all 10 questions are answered.
    """
    await _get_session(db, session_id, account["id"])
    return await _finalize(db, session_id)


@router.post("/sessions/{session_id}/escalate", operation_id="escalate_epds_session")
async def escalate_session(
    session_id: str,
    body: EscalationCreate,
    account=Depends(get_current_account),
    db=Depends(get_db),
):
    """
    Raise a clinician escalation for a session.

    The agent calls this when the mother reports self-harm, harm to the baby,
    or psychosis mid-call — regardless of the running score. Escalations are
    de-duplicated per (session, reason), so repeat calls return the existing
    record instead of raising a duplicate.
    """
    session = await _get_session(db, session_id, account["id"])
    esc = await create_escalation(
        db,
        account_id=account["id"],
        reason=body.reason,
        session_id=session_id,
        mother_id=session.get("mother_id"),
        risk_band=session.get("risk_band"),
        total_score=session.get("total_score"),
        notes=body.notes,
    )
    return esc


@router.get("/escalations", operation_id="list_escalations")
async def list_escalations(
    status: str | None = None,
    account=Depends(get_current_account),
    db=Depends(get_db),
):
    """
    List clinician escalations for your account, newest first.

    Pass ?status=open (or acknowledged, resolved) to filter the triage queue.
    """
    if status:
        rows = await db.fetch(
            """SELECT * FROM escalations
               WHERE account_id = $1 AND status = $2
               ORDER BY created_at DESC""",
            account["id"],
            status,
        )
    else:
        rows = await db.fetch(
            "SELECT * FROM escalations WHERE account_id = $1 ORDER BY created_at DESC",
            account["id"],
        )
    return [dict(r) for r in rows]


@router.patch("/escalations/{escalation_id}", operation_id="update_escalation")
async def update_escalation(
    escalation_id: str,
    body: EscalationUpdate,
    account=Depends(get_current_account),
    db=Depends(get_db),
):
    """
    Update an escalation's status or notes (acknowledge / resolve).

    Setting status to 'acknowledged' or 'resolved' stamps the matching
    timestamp so a clinician can track follow-up.
    """
    existing = await db.fetchrow(
        "SELECT * FROM escalations WHERE id = $1 AND account_id = $2",
        escalation_id,
        account["id"],
    )
    if not existing:
        raise HTTPException(404, "Escalation not found.")

    now = datetime.now(timezone.utc)
    status = body.status if body.status is not None else existing["status"]
    notes = body.notes if body.notes is not None else existing["notes"]
    acknowledged_at = existing["acknowledged_at"]
    resolved_at = existing["resolved_at"]
    if body.status == "acknowledged" and acknowledged_at is None:
        acknowledged_at = now
    if body.status == "resolved":
        resolved_at = now
        if acknowledged_at is None:
            acknowledged_at = now

    row = await db.fetchrow(
        """UPDATE escalations
           SET status = $2, notes = $3, acknowledged_at = $4, resolved_at = $5
           WHERE id = $1
           RETURNING *""",
        escalation_id,
        status,
        notes,
        acknowledged_at,
        resolved_at,
    )
    return dict(row)


def _extract(payload: dict, *keys):
    """Return the first present, non-null value among top-level or nested keys."""
    for k in keys:
        if k in payload and payload[k] is not None:
            return payload[k]
    return None


@router.post("/calls/webhook", operation_id="bolna_call_webhook")
async def bolna_call_webhook(
    payload: dict = Body(...),
    db=Depends(get_db),
):
    """
    Receive Bolna's post-call webhook (transcript + call metadata).

    Unauthenticated: Bolna cannot send our API key, so the call is matched to a
    session via the session_id we handed Bolna as a dynamic variable (echoed
    back in user_data) or by its execution id. Stores the transcript and
    re-finalizes the session so the score/escalations reflect the full call.
    """
    user_data = payload.get("user_data") or payload.get("context_details") or {}
    session_id = (
        _extract(user_data, "session_id")
        or _extract(payload, "session_id")
    )
    execution_id = _extract(payload, "execution_id", "id")

    if session_id:
        row = await db.fetchrow("SELECT * FROM epds_sessions WHERE id = $1", session_id)
    elif execution_id:
        row = await db.fetchrow(
            "SELECT * FROM epds_sessions WHERE bolna_execution_id = $1", execution_id
        )
    else:
        raise HTTPException(400, "No session_id or execution_id in webhook payload.")

    if not row:
        logger.warning("Bolna webhook for unknown session/execution (%s/%s)", session_id, execution_id)
        raise HTTPException(404, "No matching EPDS session.")

    session = dict(row)
    transcript = _extract(payload, "transcript")
    if isinstance(transcript, (list, dict)):
        import json as _json
        transcript = _json.dumps(transcript, ensure_ascii=False)

    await db.execute(
        "UPDATE epds_sessions SET transcript = COALESCE($2, transcript) WHERE id = $1",
        session["id"],
        transcript,
    )

    result = await _finalize(db, session["id"])
    logger.info(
        "Bolna webhook processed session=%s (complete=%s, band=%s, escalations=%s)",
        session["id"], result["complete"], result["risk_band"], result["escalations"],
    )
    return {"session_id": session["id"], "result": result}
