"""Call lifecycle models: phases, outcomes, configuration, and handler result types."""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel


class CallPhase(str, Enum):
    """Finite states the call can be in. The state machine transitions between these."""

    IDLE = "idle"
    GREETING = "greeting"
    IDENTITY_CONFIRM = "identity_confirm"
    REFILL_INTEREST = "refill_interest"
    AVAILABILITY_CHECK = "availability_check"
    QUESTIONNAIRE = "questionnaire"
    CLOSING = "closing"
    COMPLETED = "completed"

    # --- Exit states (reachable from any phase) ---
    WRONG_NUMBER = "wrong_number"
    OPTED_OUT = "opted_out"
    SCHEDULED = "scheduled"
    ESCALATED = "escalated"
    INCOMPLETE = "incomplete"
    VOICEMAIL = "voicemail"

    @property
    def is_terminal(self) -> bool:
        """Return True if this phase represents a final call state."""
        return self in _TERMINAL_PHASES


_TERMINAL_PHASES: frozenset[CallPhase] = frozenset(
    {
        CallPhase.COMPLETED,
        CallPhase.WRONG_NUMBER,
        CallPhase.OPTED_OUT,
        CallPhase.SCHEDULED,
        CallPhase.ESCALATED,
        CallPhase.INCOMPLETE,
        CallPhase.VOICEMAIL,
    }
)


class CallOutcome(str, Enum):
    """How the call ended — reported back to the API."""

    COMPLETED = "completed"
    INCOMPLETE = "incomplete"
    OPTED_OUT = "opted_out"
    SCHEDULED = "scheduled"
    ESCALATED = "escalated"
    WRONG_NUMBER = "wrong_number"
    VOICEMAIL = "voicemail"


class CallConfig(BaseModel):
    """Per-call configuration sent by the UI when starting a call."""

    tone: Literal["friendly", "neutral", "formal"] = "friendly"
    speed: float = 1.0
    auto_greet: bool = True
    agent_name: str = "Jessica"


class EscalationResult(BaseModel):
    """Return type for the escalation handler interface.

    Used by: handlers/escalation.py → EscalationHandler.should_escalate()
    Consumed by: worker.py to decide whether to transition to ESCALATED phase.
    """

    should_escalate: bool
    reason: str = ""
    urgency: Literal["immediate", "after_questions"] = "after_questions"


class EdgeCaseResult(BaseModel):
    """Return type for the edge-case handler interface.

    Used by: handlers/edge_cases.py → EdgeCaseHandler.detect_edge_case()
    Consumed by: worker.py to transition to the appropriate exit phase.
    """

    case_type: Literal["wrong_number", "opted_out", "scheduled", "voicemail"]
    confidence: float
    suggested_response: str = ""
