"""Pydantic request/response models — matches carecaller-ui/src/lib/api/types.ts exactly."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


# --- Patients ---

class PatientOut(BaseModel):
    id: str
    name: str
    date_of_birth: str
    medication: str
    pharmacy: str
    phone: str


class PatientsListOut(BaseModel):
    patients: list[PatientOut]


# --- Questions ---

class QuestionOut(BaseModel):
    index: int
    text: str


class QuestionsListOut(BaseModel):
    questions: list[QuestionOut]


# --- Call Lifecycle ---

class CallConfigIn(BaseModel):
    tone: Literal["friendly", "neutral", "formal"] = "friendly"
    speed: float = 1.0
    auto_greet: bool = True
    skip_answered: bool = True


class StartCallIn(BaseModel):
    patient_id: str
    call_id: str | None = None
    config: CallConfigIn = CallConfigIn()


class StartCallOut(BaseModel):
    call_id: str
    status: str
    greeting_message: str


class SendMessageIn(BaseModel):
    call_id: str
    message: str
    timestamp: float = 0.0


class QuestionResponseOut(BaseModel):
    question_index: int
    question: str
    answer: str | None
    status: str


class SendMessageOut(BaseModel):
    agent_message: str
    captured_response: QuestionResponseOut | None
    current_question_index: int
    call_status: str


class TranscriptMessageOut(BaseModel):
    id: str
    role: str
    text: str
    timestamp: float


class GetResponsesOut(BaseModel):
    call_id: str
    responses: list[QuestionResponseOut]
    completeness: float
    transcript: list[TranscriptMessageOut]
    outcome: str | None
    duration_seconds: float | None


class EndCallIn(BaseModel):
    call_id: str
    reason: str = "completed"


class EndCallOut(BaseModel):
    call_id: str
    outcome: str
    duration_seconds: float
    responses: list[QuestionResponseOut]
    completeness: float
    transcript: list[TranscriptMessageOut]


# --- Voice Call (Phase 5) ---

class StartVoiceCallIn(BaseModel):
    patient_id: str
    call_id: str | None = None
    config: CallConfigIn = CallConfigIn()


class StartVoiceCallOut(BaseModel):
    call_id: str
    livekit_url: str
    livekit_token: str
    status: str


class VoiceCapturedResponse(BaseModel):
    question_index: int
    raw_answer: str
    normalized_answer: str
    confidence: float = 1.0


class VoiceEventIn(BaseModel):
    """Webhook payload POSTed by the voice agent when the call ends."""
    event: Literal["call_completed"]
    call_id: str
    outcome: str
    completeness: float
    responses: list[VoiceCapturedResponse]
    transcript: list[TranscriptMessageOut]


class VoiceEventOut(BaseModel):
    status: str
    call_id: str
