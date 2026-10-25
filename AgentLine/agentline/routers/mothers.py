"""
AgentLine — Mothers & Consent Router (MAAI)

Registration of mothers (by an ASHA worker or hospital) and their consent to
receive screening calls. Consent is an append-only audit trail; the latest
non-revoked record decides eligibility, which the call scheduler relies on.
"""

import logging
import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from agentline.auth_middleware import get_current_account
from agentline.database import get_db
from agentline.models.mother import ConsentCreate, MotherCreate, MotherUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/mothers", tags=["Mothers"])


async def _latest_consent(db, mother_id: str) -> dict | None:
    row = await db.fetchrow(
        """SELECT * FROM consent WHERE mother_id = $1
           ORDER BY recorded_at DESC LIMIT 1""",
        mother_id,
    )
    return dict(row) if row else None


def _has_active_consent(consent: dict | None) -> bool:
    return bool(consent and consent["consented"] and consent["revoked_at"] is None)


async def _get_mother(db, mother_id: str, account_id: str) -> dict:
    row = await db.fetchrow(
        "SELECT * FROM mothers WHERE id = $1 AND account_id = $2",
        mother_id,
        account_id,
    )
    if not row:
        raise HTTPException(404, "Mother not found.")
    return dict(row)


@router.post("", operation_id="register_mother")
async def register_mother(
    body: MotherCreate,
    account=Depends(get_current_account),
    db=Depends(get_db),
):
    """
    Register a mother for maternal wellbeing screening.

    Typically called from the ASHA/hospital intake form. Record consent
    separately via POST /v1/mothers/{id}/consent before any call is placed.
    """
    mother_id = f"mom_{secrets.token_urlsafe(12)}"
    now = datetime.now(timezone.utc)
    await db.execute(
        """INSERT INTO mothers
           (id, account_id, name, phone, language, registered_by,
            delivery_date, call_cadence, next_call_at, active, notes, created_at)
           VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,true,$10,$11)""",
        mother_id,
        account["id"],
        body.name,
        body.phone,
        body.language,
        body.registered_by,
        body.delivery_date,
        body.call_cadence,
        body.next_call_at,
        body.notes,
        now,
    )
    return await _get_mother(db, mother_id, account["id"])


@router.get("", operation_id="list_mothers")
async def list_mothers(
    account=Depends(get_current_account),
    db=Depends(get_db),
):
    """List registered mothers for your account, newest first."""
    rows = await db.fetch(
        "SELECT * FROM mothers WHERE account_id = $1 ORDER BY created_at DESC",
        account["id"],
    )
    return [dict(r) for r in rows]


@router.get("/{mother_id}", operation_id="get_mother")
async def get_mother(
    mother_id: str,
    account=Depends(get_current_account),
    db=Depends(get_db),
):
    """Get one mother with her latest consent status and screening history."""
    mother = await _get_mother(db, mother_id, account["id"])
    consent = await _latest_consent(db, mother_id)
    sessions = await db.fetch(
        """SELECT id, status, total_score, risk_band, self_harm_flag, created_at, completed_at
           FROM epds_sessions WHERE mother_id = $1 ORDER BY created_at DESC""",
        mother_id,
    )
    return {
        "mother": mother,
        "consent": consent,
        "has_active_consent": _has_active_consent(consent),
        "sessions": [dict(s) for s in sessions],
    }


@router.patch("/{mother_id}", operation_id="update_mother")
async def update_mother(
    mother_id: str,
    body: MotherUpdate,
    account=Depends(get_current_account),
    db=Depends(get_db),
):
    """Update a mother's details (phone, language, cadence, next call, active)."""
    await _get_mother(db, mother_id, account["id"])
    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(400, "No fields to update.")

    set_clauses = []
    values = []
    for i, (field, value) in enumerate(updates.items(), start=1):
        set_clauses.append(f"{field} = ${i}")
        values.append(value)
    values.append(mother_id)
    values.append(account["id"])
    query = f"""UPDATE mothers SET {', '.join(set_clauses)}
                WHERE id = ${len(values) - 1} AND account_id = ${len(values)}
                RETURNING *"""
    row = await db.fetchrow(query, *values)
    return dict(row)


@router.delete("/{mother_id}", operation_id="delete_mother")
async def delete_mother(
    mother_id: str,
    account=Depends(get_current_account),
    db=Depends(get_db),
):
    """Delete a mother and her consent records. Screening sessions are kept but detached."""
    await _get_mother(db, mother_id, account["id"])
    await db.execute("UPDATE epds_sessions SET mother_id = NULL WHERE mother_id = $1", mother_id)
    await db.execute("DELETE FROM mothers WHERE id = $1", mother_id)
    return {"deleted": True, "mother_id": mother_id}


@router.post("/{mother_id}/consent", operation_id="record_consent")
async def record_consent(
    mother_id: str,
    body: ConsentCreate,
    account=Depends(get_current_account),
    db=Depends(get_db),
):
    """
    Record (or withdraw) a mother's consent to screening calls.

    Append-only: each call adds a new record. Posting consented=false withdraws
    consent, which stops the scheduler from calling her.
    """
    await _get_mother(db, mother_id, account["id"])
    consent_id = f"con_{secrets.token_urlsafe(12)}"
    now = datetime.now(timezone.utc)
    revoked_at = None if body.consented else now
    await db.execute(
        """INSERT INTO consent
           (id, mother_id, account_id, consented, scope, method, recorded_at, revoked_at)
           VALUES ($1,$2,$3,$4,$5,$6,$7,$8)""",
        consent_id,
        mother_id,
        account["id"],
        body.consented,
        body.scope,
        body.method,
        now,
        revoked_at,
    )
    consent = await _latest_consent(db, mother_id)
    return {"consent": consent, "has_active_consent": _has_active_consent(consent)}


@router.get("/{mother_id}/consent", operation_id="list_consent")
async def list_consent(
    mother_id: str,
    account=Depends(get_current_account),
    db=Depends(get_db),
):
    """Get a mother's full consent history, newest first."""
    await _get_mother(db, mother_id, account["id"])
    rows = await db.fetch(
        "SELECT * FROM consent WHERE mother_id = $1 ORDER BY recorded_at DESC",
        mother_id,
    )
    return [dict(r) for r in rows]
