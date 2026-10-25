"""
AgentLine — MAAI clinician escalation.

Creates an escalation record when a screening is high risk or raises a
self-harm flag, and (if configured) POSTs it to a clinician webhook so a human
can follow up. Escalations are de-duplicated per (session, reason) so repeated
scoring of the same call does not spam the clinician.
"""

import logging
import secrets
from datetime import datetime, timezone

import httpx

from agentline.config import settings

logger = logging.getLogger(__name__)


async def _notify(payload: dict) -> bool:
    url = settings.CLINICIAN_WEBHOOK_URL
    if not url:
        return False
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
        return True
    except Exception as exc:
        logger.warning("Clinician webhook POST failed: %s", exc)
        return False


async def create_escalation(
    db,
    account_id: str,
    reason: str,
    session_id: str | None = None,
    mother_id: str | None = None,
    risk_band: str | None = None,
    total_score: int | None = None,
    notes: str | None = None,
) -> dict | None:
    """Create a de-duplicated escalation and attempt clinician notification.

    Returns the escalation row, or the existing one if (session, reason) already
    escalated. ``reason`` is typically 'self_harm', 'high_risk', or 'manual'.
    """
    if session_id:
        existing = await db.fetchrow(
            "SELECT * FROM escalations WHERE session_id = $1 AND reason = $2",
            session_id,
            reason,
        )
        if existing:
            return dict(existing)

    escalation_id = f"esc_{secrets.token_urlsafe(12)}"
    now = datetime.now(timezone.utc)
    notified = await _notify(
        {
            "escalation_id": escalation_id,
            "reason": reason,
            "session_id": session_id,
            "mother_id": mother_id,
            "risk_band": risk_band,
            "total_score": total_score,
            "created_at": now.isoformat(),
        }
    )
    row = await db.fetchrow(
        """INSERT INTO escalations
           (id, account_id, session_id, mother_id, reason, risk_band,
            total_score, status, notified, notes, created_at)
           VALUES ($1,$2,$3,$4,$5,$6,$7,'open',$8,$9,$10)
           RETURNING *""",
        escalation_id,
        account_id,
        session_id,
        mother_id,
        reason,
        risk_band,
        total_score,
        notified,
        notes,
        now,
    )
    logger.warning(
        "Escalation %s created (reason=%s, session=%s, notified=%s)",
        escalation_id, reason, session_id, notified,
    )
    return dict(row)


async def escalate_from_result(db, session: dict, result: dict) -> list[dict]:
    """Given an EPDS session row and a computed result, raise the right
    escalations: self-harm as soon as it is detected, high risk once complete."""
    created: list[dict] = []
    common = dict(
        db=db,
        account_id=session["account_id"],
        session_id=session["id"],
        mother_id=session.get("mother_id"),
        risk_band=result.get("risk_band"),
        total_score=result.get("total_score"),
    )
    if result.get("self_harm_flag"):
        esc = await create_escalation(reason="self_harm", **common)
        if esc:
            created.append(esc)
    if result.get("complete") and result.get("risk_band") == "high":
        esc = await create_escalation(reason="high_risk", **common)
        if esc:
            created.append(esc)
    return created
