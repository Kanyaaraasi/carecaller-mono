"""Questionnaire response models — the 14 health questions and captured answers."""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel


class QuestionStatus(str, Enum):
    """Lifecycle of a single question within a call."""

    PENDING = "pending"
    ASKING = "asking"
    ANSWERED = "answered"
    SKIPPED = "skipped"


class Question(BaseModel):
    """A single health check-in question definition (static, does not change per call)."""

    index: int
    text: str
    expected_type: Literal["free_text", "numeric", "yes_no", "yes_no_detail"]

    @classmethod
    def all_questions(cls) -> list[Question]:
        """Return the 14 TrimRX health check-in questions."""
        return [
            cls(index=0, text="How have you been feeling overall?", expected_type="free_text"),
            cls(index=1, text="What's your current weight in pounds?", expected_type="numeric"),
            cls(index=2, text="What's your height in feet and inches?", expected_type="numeric"),
            cls(
                index=3,
                text="How much weight have you lost this past month in pounds?",
                expected_type="numeric",
            ),
            cls(
                index=4,
                text="Any side effects from your medication this month?",
                expected_type="yes_no_detail",
            ),
            cls(
                index=5,
                text="Satisfied with your rate of weight loss?",
                expected_type="yes_no",
            ),
            cls(index=6, text="What's your goal weight in pounds?", expected_type="numeric"),
            cls(
                index=7,
                text="Any requests about your dosage?",
                expected_type="yes_no_detail",
            ),
            cls(
                index=8,
                text="Have you started any new medications or supplements since last month?",
                expected_type="yes_no_detail",
            ),
            cls(
                index=9,
                text="Do you have any new medical conditions since your last check-in?",
                expected_type="yes_no_detail",
            ),
            cls(index=10, text="Any new allergies?", expected_type="yes_no_detail"),
            cls(
                index=11,
                text="Any surgeries since your last check-in?",
                expected_type="yes_no_detail",
            ),
            cls(
                index=12,
                text="Any questions for your doctor?",
                expected_type="yes_no_detail",
            ),
            cls(
                index=13,
                text="Has your shipping address changed?",
                expected_type="yes_no_detail",
            ),
        ]


class QuestionResponse(BaseModel):
    """Live state of one question during a call. Updated as the patient answers.

    Consumed by: prompts/system_prompt.py to track progress,
                 worker.py to publish response_captured events.
    """

    question_index: int
    question: str
    raw_answer: str = ""
    normalized_answer: str = ""
    status: QuestionStatus = QuestionStatus.PENDING
    confidence: float = 0.0

    @classmethod
    def from_questions(cls, questions: list[Question]) -> list[QuestionResponse]:
        """Initialize a response list from the question definitions (all PENDING)."""
        return [
            cls(question_index=q.index, question=q.text) for q in questions
        ]


class CapturedResponse(BaseModel):
    """Return type for the response capture handler interface.

    Used by: handlers/response_capture.py → ResponseCaptureHandler.extract_response()
    Consumed by: worker.py to update the corresponding QuestionResponse in CallState.
    """

    question_index: int
    raw_answer: str
    normalized_answer: str
    confidence: float
    needs_clarification: bool = False


class TranscriptTurn(BaseModel):
    """A single conversation turn (one utterance by agent or patient).

    Accumulated in CallState.transcript. Published to the UI via LiveKit Data Channels.
    """

    role: Literal["agent", "user"]
    message: str
    timestamp: float
