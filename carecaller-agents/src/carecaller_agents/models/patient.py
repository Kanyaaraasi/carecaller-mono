"""Patient context model — the profile for the patient being called."""

from __future__ import annotations

from pydantic import BaseModel


class PatientContext(BaseModel):
    """Patient information loaded from room metadata at call start.

    Consumed by: prompts/system_prompt.py to personalize the agent greeting
    and medication references (e.g. "Hi Maria, your Tirzepatide 2.5mg refill").
    """

    id: str
    name: str
    date_of_birth: str
    medication: str
    dosage: str
    pharmacy: str
    phone: str
