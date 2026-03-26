"""Call state machine — the session scratchpad that tracks where we are in the call.

This is the single source of truth for call progress. Every module reads from it:
- prompts/system_prompt.py reads phase + responses to build the LLM prompt
- worker.py reads phase to decide pipeline behavior and publish events
- handlers read it to make decisions about edge cases and escalation
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from carecaller_agents.models.call import CallConfig, CallOutcome, CallPhase
from carecaller_agents.models.responses import (
    Question,
    QuestionResponse,
    QuestionStatus,
    TranscriptTurn,
)

if TYPE_CHECKING:
    from carecaller_agents.models.patient import PatientContext

logger = logging.getLogger(__name__)

# Maps exit phases to their corresponding outcome
_PHASE_TO_OUTCOME: dict[CallPhase, CallOutcome] = {
    CallPhase.COMPLETED: CallOutcome.COMPLETED,
    CallPhase.WRONG_NUMBER: CallOutcome.WRONG_NUMBER,
    CallPhase.OPTED_OUT: CallOutcome.OPTED_OUT,
    CallPhase.SCHEDULED: CallOutcome.SCHEDULED,
    CallPhase.ESCALATED: CallOutcome.ESCALATED,
    CallPhase.INCOMPLETE: CallOutcome.INCOMPLETE,
    CallPhase.VOICEMAIL: CallOutcome.VOICEMAIL,
}

# Valid forward transitions for the happy path
_HAPPY_PATH: list[CallPhase] = [
    CallPhase.IDLE,
    CallPhase.GREETING,
    CallPhase.IDENTITY_CONFIRM,
    CallPhase.REFILL_INTEREST,
    CallPhase.AVAILABILITY_CHECK,
    CallPhase.QUESTIONNAIRE,
    CallPhase.CLOSING,
    CallPhase.COMPLETED,
]


class CallState:
    """Mutable session state for a single call. Created once per call in worker.py."""

    def __init__(self, patient: PatientContext, config: CallConfig | None = None) -> None:
        self.patient = patient
        self.config = config or CallConfig()
        self.phase = CallPhase.IDLE
        self.current_question_index: int = 0
        self.outcome: CallOutcome | None = None
        self.transcript: list[TranscriptTurn] = []
        self.started_at: float = time.time()
        self._pending_escalation: bool = False

        # Initialize all 14 question responses as PENDING
        questions = Question.all_questions()
        self.responses: list[QuestionResponse] = QuestionResponse.from_questions(questions)

    @property
    def elapsed_seconds(self) -> float:
        """Seconds since the call started."""
        return time.time() - self.started_at

    @property
    def is_terminal(self) -> bool:
        """True if the call has ended (no more transitions possible)."""
        return self.phase.is_terminal

    @property
    def answered_count(self) -> int:
        """Number of questions that have been answered."""
        return sum(1 for r in self.responses if r.status == QuestionStatus.ANSWERED)

    @property
    def completeness(self) -> float:
        """Fraction of questions answered (0.0 to 1.0)."""
        total = len(self.responses)
        return self.answered_count / total if total > 0 else 0.0

    def advance_phase(self) -> CallPhase:
        """Move to the next phase in the happy path.

        During QUESTIONNAIRE phase, this advances the question index instead.
        Returns the new phase.
        """
        if self.is_terminal:
            logger.warning("Cannot advance from terminal phase %s", self.phase)
            return self.phase

        if self.phase == CallPhase.QUESTIONNAIRE:
            return self._advance_question()

        # Move forward along the happy path
        try:
            current_idx = _HAPPY_PATH.index(self.phase)
            self.phase = _HAPPY_PATH[current_idx + 1]
        except (ValueError, IndexError):
            logger.warning("Cannot advance from phase %s", self.phase)
            return self.phase

        logger.info("Phase advanced to %s", self.phase)

        # If entering questionnaire, mark the first question as ASKING
        if self.phase == CallPhase.QUESTIONNAIRE:
            self.responses[0].status = QuestionStatus.ASKING

        return self.phase

    def _advance_question(self) -> CallPhase:
        """Move to the next question, or to CLOSING if all questions are done."""
        # Mark current as answered if it was being asked
        if self.current_question_index < len(self.responses):
            current = self.responses[self.current_question_index]
            if current.status == QuestionStatus.ASKING:
                current.status = QuestionStatus.ANSWERED

        self.current_question_index += 1

        # All questions done?
        if self.current_question_index >= len(self.responses):
            # Check for pending escalation (flagged as "after_questions")
            if self._pending_escalation:
                return self.set_outcome(CallOutcome.ESCALATED)
            self.phase = CallPhase.CLOSING
            logger.info("All questions answered, moving to CLOSING")
            return self.phase

        # Mark the next question as ASKING
        self.responses[self.current_question_index].status = QuestionStatus.ASKING
        logger.info(
            "Advanced to question %d/%d",
            self.current_question_index + 1,
            len(self.responses),
        )
        return self.phase

    def set_outcome(self, outcome: CallOutcome) -> CallPhase:
        """Transition to a terminal exit state.

        Can be called from any phase to end the call with the given outcome.
        """
        self.outcome = outcome

        # Find the matching terminal phase
        for phase, phase_outcome in _PHASE_TO_OUTCOME.items():
            if phase_outcome == outcome:
                self.phase = phase
                break

        logger.info("Call ended with outcome %s (phase: %s)", outcome, self.phase)
        return self.phase

    def flag_pending_escalation(self) -> None:
        """Flag that escalation is needed but should happen after questions complete."""
        self._pending_escalation = True
        logger.info("Escalation flagged — will trigger after questionnaire completes")

    def record_answer(
        self,
        question_index: int,
        raw_answer: str,
        normalized_answer: str = "",
        confidence: float = 1.0,
    ) -> None:
        """Record a patient's answer to a specific question."""
        if question_index < 0 or question_index >= len(self.responses):
            logger.warning("Invalid question index: %d", question_index)
            return

        response = self.responses[question_index]
        response.raw_answer = raw_answer
        response.normalized_answer = normalized_answer or raw_answer
        response.status = QuestionStatus.ANSWERED
        response.confidence = confidence

        logger.info(
            "Recorded answer for Q%d: %s",
            question_index + 1,
            normalized_answer or raw_answer,
        )

    def add_transcript_turn(self, role: str, message: str) -> TranscriptTurn:
        """Append a turn to the conversation transcript."""
        turn = TranscriptTurn(
            role=role,  # type: ignore[arg-type]
            message=message,
            timestamp=self.elapsed_seconds,
        )
        self.transcript.append(turn)
        return turn
