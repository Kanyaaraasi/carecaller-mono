"""Data access for calls, call responses, and call transcripts."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from db.entities import Call, CallResponse, CallTranscript

from carecaller_agents.models.responses import Question


async def create_call(
    session: AsyncSession,
    call_id: str,
    patient_id: str,
    config_tone: str = "friendly",
    config_speed: float = 1.0,
) -> Call:
    """Insert a new call record and 14 empty response rows."""
    call = Call(
        id=call_id,
        patient_id=patient_id,
        config_tone=config_tone,
        config_speed=config_speed,
    )
    session.add(call)

    questions = Question.all_questions()
    for q in questions:
        session.add(CallResponse(
            call_id=call_id,
            question_index=q.index,
            question_text=q.text,
            status="pending",
        ))

    await session.flush()
    return call


async def get_call(session: AsyncSession, call_id: str) -> Call | None:
    """Return a call by ID."""
    result = await session.execute(
        select(Call).where(Call.id == call_id)
    )
    return result.scalar_one_or_none()


async def get_responses(session: AsyncSession, call_id: str) -> list[CallResponse]:
    """Return all 14 response rows for a call, ordered by question index."""
    result = await session.execute(
        select(CallResponse)
        .where(CallResponse.call_id == call_id)
        .order_by(CallResponse.question_index)
    )
    return list(result.scalars().all())


async def update_response(
    session: AsyncSession,
    call_id: str,
    question_index: int,
    raw_answer: str,
    normalized_answer: str,
    status: str = "answered",
    confidence: float = 1.0,
) -> None:
    """Update a single response row with the patient's answer."""
    await session.execute(
        update(CallResponse)
        .where(
            CallResponse.call_id == call_id,
            CallResponse.question_index == question_index,
        )
        .values(
            raw_answer=raw_answer,
            normalized_answer=normalized_answer,
            status=status,
            confidence=confidence,
        )
    )


async def mark_question_asking(
    session: AsyncSession,
    call_id: str,
    question_index: int,
) -> None:
    """Mark a question as currently being asked."""
    await session.execute(
        update(CallResponse)
        .where(
            CallResponse.call_id == call_id,
            CallResponse.question_index == question_index,
        )
        .values(status="asking")
    )


async def get_transcript(session: AsyncSession, call_id: str) -> list[CallTranscript]:
    """Return the full transcript for a call, ordered by timestamp."""
    result = await session.execute(
        select(CallTranscript)
        .where(CallTranscript.call_id == call_id)
        .order_by(CallTranscript.timestamp)
    )
    return list(result.scalars().all())


async def add_transcript_turn(
    session: AsyncSession,
    call_id: str,
    role: str,
    message: str,
    timestamp: float,
) -> CallTranscript:
    """Append a turn to the call transcript."""
    turn = CallTranscript(
        call_id=call_id,
        role=role,
        message=message,
        timestamp=timestamp,
    )
    session.add(turn)
    await session.flush()
    return turn


async def end_call(
    session: AsyncSession,
    call_id: str,
    outcome: str,
    completeness: float,
    notes: str = "",
) -> None:
    """Mark a call as ended with outcome and duration."""
    now = datetime.now().isoformat()
    call = await get_call(session, call_id)
    if call is None:
        return

    started = datetime.fromisoformat(call.started_at)
    duration = (datetime.now() - started).total_seconds()

    await session.execute(
        update(Call)
        .where(Call.id == call_id)
        .values(
            outcome=outcome,
            ended_at=now,
            duration_secs=duration,
            completeness=completeness,
            notes=notes,
        )
    )
