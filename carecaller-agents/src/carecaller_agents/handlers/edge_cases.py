"""Edge case detection interface — contract for the response agent team.

FILE STATUS: INTERFACE ONLY (Protocol stub)
IMPLEMENTER: Response agent team
CALLED FROM: worker.py — first check after every patient utterance (BEFORE response capture)

The pipeline calls detect_edge_case() before processing the utterance as a questionnaire
answer. If an edge case is detected, the pipeline skips response capture and transitions
the state machine to the appropriate exit state.

MODELS USED:
    Input:  handlers/call_state.py → CallState
    Output: models/call.py → EdgeCaseResult

EDGE CASES (from transcript_samples.json analysis):
    - wrong_number: "No, this isn't {name}" / "wrong number" (duration ~22s)
    - opted_out: "I'm not interested" / "I'm busy" + declines check-in (duration ~25s)
    - scheduled: "Can you call me back later?" + agrees to callback time (duration ~45s)
    - voicemail: No human response after opening turns (duration ~20-25s, handled by VAD timeout)

PRIORITY: Edge case detection runs BEFORE response capture on each turn.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from carecaller_agents.models.call import EdgeCaseResult

if TYPE_CHECKING:
    from carecaller_agents.handlers.call_state import CallState


@runtime_checkable
class EdgeCaseHandler(Protocol):
    """Interface for detecting non-happy-path scenarios that change the call flow."""

    async def detect_edge_case(
        self,
        patient_utterance: str,
        call_state: CallState,
    ) -> EdgeCaseResult | None:
        """Check if the patient's response indicates an edge case.

        Args:
            patient_utterance: What the patient just said.
            call_state: Current call state (phase, patient context).

        Returns:
            None if no edge case detected, otherwise EdgeCaseResult with
            case_type, confidence, and optional suggested_response.
        """
        ...


class DefaultEdgeCaseHandler:
    """No-op implementation — never detects edge cases.

    Use this as a fallback until the response agent team provides their implementation.
    The LLM will still handle edge cases via prompt instructions (EDGE_CASE_RULES),
    but won't trigger explicit state machine transitions.
    """

    async def detect_edge_case(
        self,
        patient_utterance: str,
        call_state: CallState,
    ) -> EdgeCaseResult | None:
        return None
