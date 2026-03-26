"""Dynamic system prompt builder — assembles templates based on current call state."""

from __future__ import annotations

from typing import TYPE_CHECKING

from carecaller_agents.models.call import CallConfig, CallPhase
from carecaller_agents.models.responses import QuestionResponse, QuestionStatus
from carecaller_agents.prompts.templates import (
    CLOSING_PHASE,
    EDGE_CASE_RULES,
    OFF_SCRIPT_RULES,
    OPENING_PHASE,
    PERSONA_BASE,
    QUESTIONNAIRE_PHASE,
)

if TYPE_CHECKING:
    from carecaller_agents.models.patient import PatientContext


def build_system_prompt(
    *,
    phase: CallPhase,
    patient: PatientContext,
    config: CallConfig,
    responses: list[QuestionResponse],
    current_question_index: int,
) -> str:
    """Build the full system prompt for the LLM based on current call state.

    Called before every LLM invocation to give it fresh context about
    where we are in the call and what's been captured so far.
    """
    parts: list[str] = []

    # --- Always include persona ---
    parts.append(
        PERSONA_BASE.format(
            agent_name=config.agent_name,
            tone=config.tone,
        )
    )

    # --- Phase-specific instructions ---
    if phase in (
        CallPhase.IDLE,
        CallPhase.GREETING,
        CallPhase.IDENTITY_CONFIRM,
        CallPhase.REFILL_INTEREST,
        CallPhase.AVAILABILITY_CHECK,
    ):
        parts.append(
            OPENING_PHASE.format(
                agent_name=config.agent_name,
                patient_name=patient.name,
                medication=patient.medication,
                dosage=patient.dosage,
            )
        )

    elif phase == CallPhase.QUESTIONNAIRE:
        answered_summary = _format_answered(responses)
        remaining_summary = _format_remaining(responses, current_question_index)
        current_q = (
            responses[current_question_index].question
            if current_question_index < len(responses)
            else "N/A"
        )
        answered_count = sum(1 for r in responses if r.status == QuestionStatus.ANSWERED)

        parts.append(
            QUESTIONNAIRE_PHASE.format(
                answered_count=answered_count,
                current_index=current_question_index + 1,
                current_question=current_q,
                answered_summary=answered_summary or "None yet.",
                remaining_summary=remaining_summary or "None — this is the last question.",
            )
        )

    elif phase == CallPhase.CLOSING:
        parts.append(CLOSING_PHASE)

    # --- Always include edge case + off-script rules ---
    parts.append(
        EDGE_CASE_RULES.format(patient_name=patient.name)
    )
    parts.append(OFF_SCRIPT_RULES)

    return "\n\n".join(parts)


def _format_answered(responses: list[QuestionResponse]) -> str:
    """Format already-answered questions as context for the LLM."""
    lines: list[str] = []
    for r in responses:
        if r.status == QuestionStatus.ANSWERED:
            answer = r.normalized_answer or r.raw_answer
            lines.append(f'  Q{r.question_index + 1}: {r.question} -> "{answer}"')
    return "\n".join(lines)


def _format_remaining(responses: list[QuestionResponse], current_index: int) -> str:
    """Format remaining questions (after current) for the LLM."""
    lines: list[str] = []
    for r in responses:
        if r.question_index > current_index and r.status == QuestionStatus.PENDING:
            lines.append(f"  Q{r.question_index + 1}: {r.question}")
    return "\n".join(lines)
