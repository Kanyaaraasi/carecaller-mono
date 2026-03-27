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


import re


# Patterns that indicate the user is NOT answering the question
_NON_ANSWER_PATTERNS = re.compile(
    r"^("
    r"(what|huh|sorry|excuse me|pardon|come again|say that again)"
    r"|what do you mean"
    r"|can you (repeat|explain|clarify|say)"
    r"|i don'?t (understand|know what|get)"
    r"|repeat that"
    r"|what was (that|the question)"
    r"|i'?m sorry\??"
    r")[\s?.!]*$",
    re.IGNORECASE,
)

# Very short utterances that are likely not substantive answers
_MIN_ANSWER_LENGTH = 3  # characters, excluding whitespace


class DefaultResponseCapture:
    """Response capture with non-answer detection.

    Detects clarification requests, questions, and non-answers so the agent
    can re-ask instead of blindly advancing to the next question.
    """

    async def extract_response(
        self,
        question: Question,
        patient_utterance: str,
        conversation_context: list[TranscriptTurn],
    ) -> CapturedResponse:
        text = patient_utterance.strip()
        needs_clarification = False
        confidence = 0.5

        # Check for non-answer patterns
        if _NON_ANSWER_PATTERNS.match(text):
            needs_clarification = True
            confidence = 0.1

        # Very short non-word utterances
        elif len(text) < _MIN_ANSWER_LENGTH:
            needs_clarification = True
            confidence = 0.1

        # Utterance is a question (ends with ?) and short — likely asking for clarification
        elif text.endswith("?") and len(text.split()) < 8:
            needs_clarification = True
            confidence = 0.2

        return CapturedResponse(
            question_index=question.index,
            raw_answer=patient_utterance,
            normalized_answer=patient_utterance,
            confidence=confidence,
            needs_clarification=needs_clarification,
        )
