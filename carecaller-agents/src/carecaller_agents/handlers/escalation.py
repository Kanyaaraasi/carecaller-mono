"""Escalation detection interface — contract for the response agent team.

FILE STATUS: INTERFACE ONLY (Protocol stub)
IMPLEMENTER: Response agent team
CALLED FROM: worker.py — evaluated after each patient utterance

The pipeline calls should_escalate() to determine if the call needs human intervention.
The response agent team provides the concrete implementation.

MODELS USED:
    Input:  models/responses.py → TranscriptTurn
            handlers/call_state.py → CallState
    Output: models/call.py → EscalationResult

ESCALATION TRIGGERS (from transcript_samples.json analysis):
    - Patient explicitly asks to speak to a person/doctor
    - Medical emergency indicators
    - Patient distress or anger
    - Questions the agent cannot safely answer
    - Typically happens AFTER questionnaire when patient has persistent medical concerns
      (e.g., "I really want to talk to someone about my nausea")
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from carecaller_agents.models.call import EscalationResult
from carecaller_agents.models.responses import TranscriptTurn

if TYPE_CHECKING:
    from carecaller_agents.handlers.call_state import CallState


@runtime_checkable
class EscalationHandler(Protocol):
    """Interface for detecting when a call needs human intervention."""

    async def should_escalate(
        self,
        patient_utterance: str,
        conversation_context: list[TranscriptTurn],
        call_state: CallState,
    ) -> EscalationResult:
        """Analyze whether this call needs to be escalated to a human agent.

        Args:
            patient_utterance: What the patient just said.
            conversation_context: Full conversation history.
            call_state: Current call state (phase, responses, patient context).

        Returns:
            EscalationResult with should_escalate, reason, and urgency.
        """
        ...


class DefaultEscalationHandler:
    """No-op implementation — never escalates.

    Use this as a fallback until the response agent team provides their implementation.
    """

    async def should_escalate(
        self,
        patient_utterance: str,
        conversation_context: list[TranscriptTurn],
        call_state: CallState,
    ) -> EscalationResult:
        return EscalationResult(should_escalate=False)
