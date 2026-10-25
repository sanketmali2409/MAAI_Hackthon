"""
AgentLine — Bolna voice platform client (MAAI).

Bolna owns the voice + telephony for screening calls (Indian-language STT/TTS,
Plivo/Sarvam under the hood). We trigger an outbound call and hand Bolna the
session_id as a dynamic variable so its in-call function calls can POST each
EPDS answer back to us. Scoring and escalation stay in our backend — Bolna
never computes a score.
"""

import logging

import httpx

from agentline.config import settings

logger = logging.getLogger(__name__)


class BolnaError(RuntimeError):
    """Raised when Bolna rejects a call-trigger request."""


async def trigger_call(
    recipient_phone_number: str,
    session_id: str,
    agent_id: str | None = None,
    user_data: dict | None = None,
) -> dict:
    """Place an outbound screening call via Bolna.

    ``session_id`` is passed as a dynamic variable so Bolna's in-call tools can
    reach the right EPDS session. Returns Bolna's JSON (includes ``execution_id``).
    Raises :class:`BolnaError` if the platform is not configured or rejects us.
    """
    if not settings.BOLNA_API_KEY:
        raise BolnaError("BOLNA_API_KEY is not configured.")
    agent = agent_id or settings.BOLNA_AGENT_ID
    if not agent:
        raise BolnaError("No Bolna agent id (set BOLNA_AGENT_ID or pass agent_id).")

    payload: dict = {
        "agent_id": agent,
        "recipient_phone_number": recipient_phone_number,
        "user_data": {"session_id": session_id, **(user_data or {})},
    }
    if settings.BOLNA_FROM_NUMBER:
        payload["from_number"] = settings.BOLNA_FROM_NUMBER

    url = f"{settings.BOLNA_BASE_URL.rstrip('/')}/call"
    headers = {"Authorization": f"Bearer {settings.BOLNA_API_KEY}"}
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as exc:
        body = exc.response.text[:500]
        logger.error("Bolna call trigger failed (%s): %s", exc.response.status_code, body)
        raise BolnaError(f"Bolna returned {exc.response.status_code}: {body}") from exc
    except Exception as exc:
        logger.error("Bolna call trigger error: %s", exc)
        raise BolnaError(str(exc)) from exc

    logger.info(
        "Bolna call triggered (session=%s, execution=%s)",
        session_id,
        data.get("execution_id"),
    )
    return data
