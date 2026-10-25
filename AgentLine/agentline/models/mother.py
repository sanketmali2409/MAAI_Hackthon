"""
AgentLine — Mother & Consent Pydantic schemas (MAAI)
"""

from datetime import date, datetime

from pydantic import BaseModel, Field


class MotherCreate(BaseModel):
    name: str | None = Field(default=None, description="Mother's name")
    phone: str = Field(description="Phone number in E.164 format, e.g. +919000000001")
    language: str = Field(default="hi", description="Preferred language code: hi, en, pa")
    registered_by: str | None = Field(default=None, description="ASHA worker or hospital that registered her")
    delivery_date: date | None = Field(default=None, description="Delivery date (for postpartum scheduling)")
    call_cadence: str = Field(default="weekly", description="Check-in cadence: daily or weekly")
    next_call_at: datetime | None = Field(default=None, description="When the next screening call is due")
    notes: str | None = Field(default=None, description="Free-text notes")


class MotherUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    language: str | None = None
    registered_by: str | None = None
    delivery_date: date | None = None
    call_cadence: str | None = None
    next_call_at: datetime | None = None
    active: bool | None = None
    notes: str | None = None


class ConsentCreate(BaseModel):
    consented: bool = Field(description="True if the mother consents to screening calls")
    scope: str = Field(default="screening_calls", description="What the consent covers")
    method: str | None = Field(default=None, description="How consent was taken: asha_form, verbal, sms")
