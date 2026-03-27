"""Builds LLM prompt context from database — patient profile + health history.

Queries the patient record and latest health snapshot, then formats them
into a structured context block that gets injected into the system prompt.
This gives the LLM *memory* of the patient across calls.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from db.entities import Call, HealthSnapshot, Patient
from repositories import call_repo, patient_repo


async def build_patient_context(session: AsyncSession, patient_id: str) -> str:
    """Query DB for patient + latest snapshot → return formatted context string."""
    patient = await patient_repo.get_by_id(session, patient_id)
    if patient is None:
        raise ValueError(f"Patient {patient_id} not found")

    snapshot = await patient_repo.get_latest_snapshot(session, patient_id)
    last_call = await _get_last_completed_call(session, patient_id)

    lines = [
        "PATIENT CONTEXT (from database):",
        f"  Name: {patient.name}",
        f"  Date of birth: {patient.dob}",
        f"  Medication: {patient.medication}, {patient.dosage}",
        f"  Pharmacy: {patient.pharmacy}",
    ]

    if last_call:
        days_ago = _days_since(last_call.started_at)
        lines.append(f"  Last check-in: {last_call.started_at[:10]} ({days_ago} days ago)")
        lines.append(f"  Previous call outcome: {last_call.outcome} ({_format_completeness(last_call.completeness)})")
    else:
        lines.append("  Last check-in: None — this is the first call")

    if snapshot:
        lines.append("")
        lines.append("  LAST KNOWN HEALTH STATE:")
        if snapshot.weight_lbs is not None:
            weight_str = f"{snapshot.weight_lbs:.0f} lbs"
            if snapshot.goal_weight_lbs is not None:
                weight_str += f" (goal: {snapshot.goal_weight_lbs:.0f} lbs)"
            lines.append(f"    Weight: {weight_str}")
        if snapshot.height:
            lines.append(f"    Height: {snapshot.height}")
        if snapshot.weight_lost_lbs is not None:
            lines.append(f"    Weight lost last month: {snapshot.weight_lost_lbs:.0f} lbs")
        if snapshot.side_effects:
            lines.append(f"    Side effects: {snapshot.side_effects}")
        if snapshot.allergies:
            lines.append(f"    Allergies: {snapshot.allergies}")
        if snapshot.new_conditions:
            lines.append(f"    Conditions: {snapshot.new_conditions}")
        if snapshot.new_medications:
            lines.append(f"    Other medications: {snapshot.new_medications}")
        if snapshot.surgeries and snapshot.surgeries.lower() not in ("no", "no surgeries", "no surgeries."):
            lines.append(f"    Recent surgeries: {snapshot.surgeries}")

    lines.append("")
    lines.append(
        "Use this context to personalize the conversation. Reference prior answers "
        "when relevant (e.g., \"Last time you mentioned no side effects — has that changed?\")."
    )

    return "\n".join(lines)


async def _get_last_completed_call(session: AsyncSession, patient_id: str) -> Call | None:
    """Return the most recent call for this patient (any outcome)."""
    from sqlalchemy import select

    result = await session.execute(
        select(Call)
        .where(Call.patient_id == patient_id, Call.outcome.isnot(None))
        .order_by(Call.started_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


def _days_since(iso_datetime: str) -> int:
    """Calculate days between an ISO datetime string and today."""
    try:
        dt = datetime.fromisoformat(iso_datetime)
        return (datetime.now() - dt).days
    except (ValueError, TypeError):
        return 0


def _format_completeness(completeness: float) -> str:
    """Format completeness as 'X/14 questions answered'."""
    answered = round(completeness * 14)
    return f"{answered}/14 questions answered"
