"""Response extraction interface — contract for the response agent team.

FILE STATUS: INTERFACE ONLY (Protocol stub)
IMPLEMENTER: Response agent team
CALLED FROM: worker.py — after STT finalizes a patient utterance during questionnaire phase

The pipeline calls extract_response() to turn natural language ("I'm at 233 pounds")
into a structured answer (normalized_answer="233"). The response agent team provides
the concrete implementation.

MODELS USED:
    Input:  models/responses.py → Question, TranscriptTurn
    Output: models/responses.py → CapturedResponse

IMPLEMENTATION APPROACHES (for response agent team):
    1. LLM function-calling — ask the LLM to extract the answer as a structured tool call
    2. Secondary LLM pass — separate extraction prompt after the conversational response
    3. Regex + heuristics — for numeric answers (weight, height), pattern matching
    4. Hybrid — regex for numeric fields, LLM for free-text fields
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from carecaller_agents.models.responses import CapturedResponse, Question, TranscriptTurn


@runtime_checkable
class ResponseCaptureHandler(Protocol):
    """Interface for extracting structured answers from patient speech."""

    async def extract_response(
        self,
        question: Question,
        patient_utterance: str,
        conversation_context: list[TranscriptTurn],
    ) -> CapturedResponse:
        """Extract a structured answer from the patient's natural language response.

        Args:
            question: The question that was just asked.
            patient_utterance: What the patient said (final STT transcript).
            conversation_context: Full conversation so far (for disambiguation).

        Returns:
            CapturedResponse with raw_answer, normalized_answer, confidence,
            and needs_clarification flag.
        """
        ...


class DefaultResponseCapture:
    """Passthrough implementation — captures the raw utterance without normalization.

    Use this as a fallback until the response agent team provides their implementation.
    Passes the verbatim STT transcript as both raw and normalized answer.
    """

    async def extract_response(
        self,
        question: Question,
        patient_utterance: str,
        conversation_context: list[TranscriptTurn],
    ) -> CapturedResponse:
        return CapturedResponse(
            question_index=question.index,
            raw_answer=patient_utterance,
            normalized_answer=patient_utterance,
            confidence=0.5,
            needs_clarification=False,
        )
