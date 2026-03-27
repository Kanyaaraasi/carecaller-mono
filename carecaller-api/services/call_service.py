"""Call lifecycle service — orchestrates repos, FSM, LLM, and context builder.

This is the single entry point for call business logic. Routers call this,
never the repos or LLM directly.
"""

from __future__ import annotations

import logging
import time

from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from db.entities import Call, CallResponse, HealthSnapshot
from repositories import call_repo, patient_repo
from services.context_builder import build_patient_context
from services.livekit_service import create_voice_room, generate_participant_token

from carecaller_agents.handlers.call_state import CallState
from carecaller_agents.models.call import CallConfig, CallOutcome, CallPhase
from carecaller_agents.models.patient import PatientContext
from carecaller_agents.models.responses import Question
from carecaller_agents.prompts.system_prompt import build_system_prompt

logger = logging.getLogger("carecaller-api.call_service")

# In-memory call state machines — keyed by call_id.
# The FSM lives in memory for fast turn-by-turn access; the DB is the
# persistent record. If the server restarts mid-call, the call is lost
# (acceptable for a hackathon — production would reconstruct from DB).
_active_states: dict[str, CallState] = {}

_llm_client: AsyncOpenAI | None = None


def _get_llm() -> AsyncOpenAI:
    global _llm_client
    if _llm_client is None:
        settings = get_settings()
        _llm_client = AsyncOpenAI(
            api_key=settings.groq_api_key,
            base_url=settings.groq_base_url,
        )
    return _llm_client


async def start_call(
    session: AsyncSession,
    call_id: str,
    patient_id: str,
    tone: str = "friendly",
    speed: float = 1.0,
) -> tuple[Call, str]:
    """Start a new call. Returns (call_record, greeting_message).

    1. Load patient from DB
    2. Create call + 14 empty responses in DB
    3. Initialize FSM in memory
    4. Generate greeting
    5. Persist greeting to transcript
    """
    patient = await patient_repo.get_by_id(session, patient_id)
    if patient is None:
        raise ValueError(f"Patient {patient_id} not found")

    call = await call_repo.create_call(
        session, call_id, patient_id, config_tone=tone, config_speed=speed,
    )

    # Mark Q0 as "asking"
    await call_repo.mark_question_asking(session, call_id, 0)

    settings = get_settings()
    config = CallConfig(tone=tone, agent_name=settings.agent_name)

    patient_ctx = PatientContext(
        id=patient.id,
        name=patient.name,
        date_of_birth=patient.dob,
        medication=patient.medication,
        dosage=patient.dosage,
        pharmacy=patient.pharmacy,
        phone=patient.phone,
    )
    state = CallState(patient=patient_ctx, config=config)
    state.phase = CallPhase.GREETING

    greeting = (
        f"Thanks for calling CareCaller. This is {config.agent_name}. "
        f"Am I speaking with {patient.name}?"
    )
    state.add_transcript_turn("agent", greeting)

    await call_repo.add_transcript_turn(session, call_id, "agent", greeting, 0.0)
    await session.commit()

    _active_states[call_id] = state
    logger.info("Started call %s for patient %s", call_id, patient.name)
    return call, greeting


async def process_message(
    session: AsyncSession,
    call_id: str,
    user_message: str,
    timestamp: float = 0.0,
) -> tuple[str, dict | None, int, str]:
    """Process a user message. Returns (agent_response, captured_response, current_q_index, ui_status).

    1. Record user turn in DB + FSM
    2. Capture response if in questionnaire phase
    3. Advance FSM
    4. Build enriched prompt from DB context + FSM state
    5. Call Groq LLM
    6. Record agent turn in DB + FSM
    7. Return result
    """
    state = _active_states.get(call_id)
    if state is None:
        raise ValueError(f"No active call session: {call_id}")

    # Record user turn
    state.add_transcript_turn("user", user_message)
    await call_repo.add_transcript_turn(session, call_id, "user", user_message, timestamp)

    # Capture response if in questionnaire phase
    captured = None
    if state.phase == CallPhase.QUESTIONNAIRE:
        q_index = state.current_question_index
        questions = Question.all_questions()
        current_q = questions[q_index]

        state.record_answer(q_index, user_message, user_message)
        await call_repo.update_response(
            session, call_id, q_index,
            raw_answer=user_message,
            normalized_answer=user_message,
        )

        captured = {
            "question_index": q_index,
            "question": current_q.text,
            "answer": user_message,
            "status": "answered",
        }

    # Advance state
    if not state.is_terminal:
        state.advance_phase()

    # If entering questionnaire, mark current question as asking
    if state.phase == CallPhase.QUESTIONNAIRE:
        await call_repo.mark_question_asking(session, call_id, state.current_question_index)

    # Build LLM prompt with DB context
    patient_context = await build_patient_context(session, state.patient.id)
    system_prompt = build_system_prompt(
        phase=state.phase,
        patient=state.patient,
        config=state.config,
        responses=state.responses,
        current_question_index=state.current_question_index,
    )
    full_prompt = f"{system_prompt}\n\n{patient_context}"

    # Build message history
    messages: list[dict[str, str]] = [{"role": "system", "content": full_prompt}]
    for turn in state.transcript:
        role = "assistant" if turn.role == "agent" else "user"
        messages.append({"role": role, "content": turn.message})

    # Call Groq LLM
    settings = get_settings()
    llm = _get_llm()
    response = await llm.chat.completions.create(
        model=settings.groq_model,
        messages=messages,
        temperature=settings.llm_temperature,
        max_tokens=300,
    )
    agent_response = response.choices[0].message.content or ""

    # Record agent turn
    state.add_transcript_turn("agent", agent_response)
    await call_repo.add_transcript_turn(session, call_id, "agent", agent_response, timestamp)

    # Update completeness in DB
    call = await call_repo.get_call(session, call_id)
    if call:
        from sqlalchemy import update as sql_update
        from db.entities import Call as CallEntity
        await session.execute(
            sql_update(CallEntity)
            .where(CallEntity.id == call_id)
            .values(completeness=state.completeness)
        )

    await session.commit()

    # Map FSM phase to UI status
    ui_status = _phase_to_ui_status(state)

    return agent_response, captured, state.current_question_index, ui_status


async def end_call(
    session: AsyncSession,
    call_id: str,
    reason: str,
) -> Call:
    """End a call. Persists outcome, creates health snapshot if completed.

    Returns the updated call record.
    """
    state = _active_states.get(call_id)

    # Map reason to outcome
    outcome_map = {
        "completed": "completed",
        "incomplete": "incomplete",
        "opted_out": "opted_out",
        "escalated": "escalated",
        "wrong_number": "wrong_number",
    }
    outcome = outcome_map.get(reason, "incomplete")
    completeness = state.completeness if state else 0.0

    await call_repo.end_call(session, call_id, outcome, completeness)

    # If completed, create a new health snapshot from captured responses
    if outcome == "completed" and state:
        await _create_snapshot_from_call(session, call_id, state)

    await session.commit()

    # Clean up in-memory state
    _active_states.pop(call_id, None)

    call = await call_repo.get_call(session, call_id)
    logger.info("Ended call %s with outcome %s", call_id, outcome)
    return call


async def get_call_state(
    session: AsyncSession,
    call_id: str,
) -> tuple[Call | None, list[CallResponse], list, float | None]:
    """Load full call state from DB for the responses endpoint.

    Returns (call, responses, transcript, duration_seconds).
    """
    call = await call_repo.get_call(session, call_id)
    if call is None:
        return None, [], [], None

    responses = await call_repo.get_responses(session, call_id)
    transcript = await call_repo.get_transcript(session, call_id)

    duration = None
    if call.duration_secs is not None:
        duration = call.duration_secs
    elif call.started_at:
        from datetime import datetime
        started = datetime.fromisoformat(call.started_at)
        duration = (datetime.now() - started).total_seconds()

    return call, responses, transcript, duration


async def start_voice_call(
    session: AsyncSession,
    call_id: str,
    patient_id: str,
    tone: str = "friendly",
    speed: float = 1.0,
) -> tuple[str, str, str]:
    """Start a voice call via LiveKit. Returns (call_id, livekit_url, livekit_token).

    1. Create call + 14 empty responses in DB (same as text call)
    2. Create LiveKit room with DB-enriched patient metadata
    3. Generate participant token for the frontend
    """
    patient = await patient_repo.get_by_id(session, patient_id)
    if patient is None:
        raise ValueError(f"Patient {patient_id} not found")

    await call_repo.create_call(
        session, call_id, patient_id, config_tone=tone, config_speed=speed,
    )
    await session.commit()

    # Create LiveKit room with enriched metadata
    room_name = await create_voice_room(session, call_id, patient_id)

    # Generate token for the frontend participant
    settings = get_settings()
    token = generate_participant_token(
        room_name=room_name,
        identity=f"user-{call_id}",
        name=patient.name,
    )

    logger.info("Started voice call %s for patient %s (room: %s)", call_id, patient.name, room_name)
    return call_id, settings.livekit_url, token


async def persist_voice_results(
    session: AsyncSession,
    call_id: str,
    outcome: str,
    completeness: float,
    responses: list[dict],
    transcript: list[dict],
) -> None:
    """Persist voice call results POSTed by the agent worker.

    Called from the /api/call/:id/voice-event webhook. The agent drives the
    call FSM independently — this just writes the final state to DB.
    """
    call = await call_repo.get_call(session, call_id)
    if call is None:
        raise ValueError(f"Call {call_id} not found")

    # Skip if already persisted (idempotent — UI and agent may both call this)
    existing_transcript = await call_repo.get_transcript(session, call_id)
    if len(existing_transcript) > 0:
        logger.info("Voice results already persisted for call %s — skipping", call_id)
        return

    # Persist each captured response
    for r in responses:
        await call_repo.update_response(
            session,
            call_id,
            question_index=r["question_index"],
            raw_answer=r["raw_answer"],
            normalized_answer=r["normalized_answer"],
            status="answered",
            confidence=r.get("confidence", 1.0),
        )

    # Persist transcript
    for t in transcript:
        await call_repo.add_transcript_turn(
            session, call_id, role=t["role"], message=t["text"], timestamp=t["timestamp"],
        )

    # End the call
    await call_repo.end_call(session, call_id, outcome, completeness)

    # Create health snapshot if completed
    if outcome == "completed":
        await _create_voice_snapshot(session, call_id, call.patient_id, responses)

    await session.commit()
    logger.info("Persisted voice results for call %s (outcome=%s)", call_id, outcome)


async def _create_voice_snapshot(
    session: AsyncSession,
    call_id: str,
    patient_id: str,
    responses: list[dict],
) -> None:
    """Create a HealthSnapshot from voice call captured responses."""
    snapshot = HealthSnapshot(patient_id=patient_id, source_call_id=call_id)

    for r in responses:
        answer = r.get("normalized_answer") or r.get("raw_answer", "")
        if not answer:
            continue
        q_idx = r["question_index"]
        match q_idx:
            case 1:
                try:
                    snapshot.weight_lbs = float("".join(c for c in answer if c.isdigit() or c == "."))
                except ValueError:
                    pass
            case 2:
                snapshot.height = answer
            case 3:
                try:
                    snapshot.weight_lost_lbs = float("".join(c for c in answer if c.isdigit() or c == "."))
                except ValueError:
                    pass
            case 4:
                snapshot.side_effects = answer
            case 5:
                snapshot.satisfaction = answer
            case 6:
                try:
                    snapshot.goal_weight_lbs = float("".join(c for c in answer if c.isdigit() or c == "."))
                except ValueError:
                    pass
            case 7:
                snapshot.dosage_requests = answer
            case 8:
                snapshot.new_medications = answer
            case 9:
                snapshot.new_conditions = answer
            case 10:
                snapshot.allergies = answer
            case 11:
                snapshot.surgeries = answer
            case 12:
                snapshot.doctor_questions = answer
            case 13:
                snapshot.address_changed = answer

    session.add(snapshot)
    logger.info("Created health snapshot for patient %s from voice call %s", patient_id, call_id)


async def _create_snapshot_from_call(
    session: AsyncSession,
    call_id: str,
    state: CallState,
) -> None:
    """Create a HealthSnapshot from captured call responses."""
    snapshot = HealthSnapshot(
        patient_id=state.patient.id,
        source_call_id=call_id,
    )

    for r in state.responses:
        answer = r.normalized_answer or r.raw_answer
        if not answer:
            continue

        match r.question_index:
            case 1:
                try:
                    snapshot.weight_lbs = float(
                        "".join(c for c in answer if c.isdigit() or c == ".")
                    )
                except ValueError:
                    pass
            case 2:
                snapshot.height = answer
            case 3:
                try:
                    snapshot.weight_lost_lbs = float(
                        "".join(c for c in answer if c.isdigit() or c == ".")
                    )
                except ValueError:
                    pass
            case 4:
                snapshot.side_effects = answer
            case 5:
                snapshot.satisfaction = answer
            case 6:
                try:
                    snapshot.goal_weight_lbs = float(
                        "".join(c for c in answer if c.isdigit() or c == ".")
                    )
                except ValueError:
                    pass
            case 7:
                snapshot.dosage_requests = answer
            case 8:
                snapshot.new_medications = answer
            case 9:
                snapshot.new_conditions = answer
            case 10:
                snapshot.allergies = answer
            case 11:
                snapshot.surgeries = answer
            case 12:
                snapshot.doctor_questions = answer
            case 13:
                snapshot.address_changed = answer

    session.add(snapshot)
    logger.info("Created health snapshot for patient %s from call %s", state.patient.id, call_id)


def _phase_to_ui_status(state: CallState) -> str:
    """Map internal FSM phase to UI-compatible status string."""
    _TERMINAL = {"completed", "wrong_number", "opted_out", "scheduled", "escalated", "incomplete", "voicemail"}
    phase = state.phase.value
    if phase in _TERMINAL:
        return "escalated" if phase == "escalated" else "completed"
    return "in-progress"
