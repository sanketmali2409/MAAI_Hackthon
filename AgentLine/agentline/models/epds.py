"""
AgentLine — EPDS Pydantic schemas
"""

from datetime import datetime

from pydantic import BaseModel, Field


class EpdsAnswerIn(BaseModel):
    question_no: int = Field(ge=1, le=10, description="EPDS question number, 1-10")
    answer: int = Field(ge=0, le=3, description="Index (0-3) of the chosen option in display order")


class EpdsScoreRequest(BaseModel):
    answers: list[EpdsAnswerIn] = Field(description="One entry per answered question (1-10)")


class EscalationCreate(BaseModel):
    reason: str = Field(default="manual", description="Why: self_harm, high_risk, or manual")
    notes: str | None = Field(default=None, description="Optional context for the clinician")


class EscalationUpdate(BaseModel):
    status: str | None = Field(default=None, description="open, acknowledged, or resolved")
    notes: str | None = Field(default=None, description="Clinician follow-up notes")


class EpdsSessionCreate(BaseModel):
    subject_name: str | None = Field(default=None, description="Name of the mother being screened")
    subject_phone: str | None = Field(default=None, description="Mother's phone number in E.164 format")
    language: str = Field(default="hi", description="Language code for the questionnaire, e.g. 'hi', 'en', 'pa'")
    agent_id: str | None = Field(default=None, description="Voice agent that ran the screening call")
    call_id: str | None = Field(default=None, description="Call this screening belongs to")
    mother_id: str | None = Field(default=None, description="Registered mother this screening is for")


class EpdsCallCreate(BaseModel):
    mother_id: str | None = Field(default=None, description="Registered mother to call; her phone/language/consent are used")
    subject_phone: str | None = Field(default=None, description="Phone to call in E.164 if no mother_id is given")
    subject_name: str | None = Field(default=None, description="Name to greet, when calling an unregistered subject")
    language: str = Field(default="hi", description="Language code for the screening call")
    agent_id: str | None = Field(default=None, description="Override the default Bolna agent id for this call")


class EpdsSessionOut(BaseModel):
    id: str
    account_id: str
    agent_id: str | None = None
    call_id: str | None = None
    mother_id: str | None = None
    subject_name: str | None = None
    subject_phone: str | None = None
    language: str
    status: str = Field(description="in_progress or completed")
    total_score: int | None = None
    risk_band: str | None = Field(default=None, description="low, medium, or high")
    self_harm_flag: bool = False
    created_at: datetime
    completed_at: datetime | None = None
