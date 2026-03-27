"""LiveKit worker entry point — the voice agent that joins rooms and runs the pipeline.

This is the main process. It:
    1. Connects to the LiveKit server as a worker
    2. Listens for new rooms (dispatched by carecaller-api)
    3. Reads patient context from room metadata
    4. Constructs the voice pipeline: Silero VAD -> Deepgram STT -> Groq LLM -> Deepgram TTS
    5. Runs the Agent that handles the conversation
    6. Publishes events (transcript, response_captured) via LiveKit Data Channels

Run with:
    uv run worker.py dev
"""

from __future__ import annotations

import json
import logging
import time

import httpx
from livekit import rtc
from livekit.agents import (
    Agent,
    AgentSession,
    AutoSubscribe,
    JobContext,
    RunContext,
    WorkerOptions,
    cli,
    llm,
)
from livekit.plugins.deepgram import STT, TTS
from livekit.plugins.openai import LLM
from livekit.plugins.silero import VAD

from carecaller_agents.config import Settings, get_settings
from carecaller_agents.handlers.call_state import CallState
from carecaller_agents.handlers.edge_cases import DefaultEdgeCaseHandler
from carecaller_agents.handlers.escalation import DefaultEscalationHandler
from carecaller_agents.handlers.response_capture import DefaultResponseCapture
from carecaller_agents.models.call import CallConfig, CallOutcome, CallPhase
from carecaller_agents.models.patient import PatientContext
from carecaller_agents.models.responses import Question
from carecaller_agents.prompts.system_prompt import build_system_prompt

logger = logging.getLogger("carecaller-agents")


def _parse_room_metadata(metadata: str) -> tuple[PatientContext, dict]:
    """Extract patient context and extra fields from LiveKit room metadata JSON.

    Returns (patient_context, extras) where extras may contain:
        - call_id: str
        - health_context: str (DB-enriched patient history)
        - api_base_url: str
    """
    if not metadata:
        raise ValueError(
            "Room metadata is empty — carecaller-api must set patient context "
            "as JSON in room metadata when creating the room."
        )
    try:
        data = json.loads(metadata)
    except json.JSONDecodeError as e:
        raise ValueError(f"Room metadata is not valid JSON: {e}") from e

    extras = {
        "call_id": data.pop("call_id", None),
        "health_context": data.pop("health_context", None),
        "api_base_url": data.pop("api_base_url", None),
    }
    return PatientContext(**data), extras


class CareCallerAgent(Agent):
    """Voice agent for CareCaller medication refill check-in calls.

    Subclasses LiveKit's Agent with lifecycle hooks for managing
    the call state machine and handler chain.
    """

    def __init__(
        self,
        *,
        patient: PatientContext,
        call_state: CallState,
        settings: Settings,
        room: rtc.Room | None = None,
        call_id: str | None = None,
        health_context: str | None = None,
        api_base_url: str | None = None,
    ) -> None:
        self._patient = patient
        self._call_state = call_state
        self._settings = settings
        self._room = room
        self._call_id = call_id
        self._health_context = health_context
        self._api_base_url = api_base_url or settings.api_base_url
        self._call_start_time = time.monotonic()
        self._response_handler = DefaultResponseCapture()
        self._escalation_handler = DefaultEscalationHandler()
        self._edge_case_handler = DefaultEdgeCaseHandler()

        # Build initial system prompt, inject DB health context if available
        self._call_state.phase = CallPhase.GREETING
        initial_prompt = build_system_prompt(
            phase=self._call_state.phase,
            patient=self._patient,
            config=self._call_state.config,
            responses=self._call_state.responses,
            current_question_index=self._call_state.current_question_index,
        )
        if self._health_context:
            initial_prompt = f"{initial_prompt}\n\n{self._health_context}"

        super().__init__(instructions=initial_prompt)

    async def on_enter(self) -> None:
        """Called when the agent enters the session — deliver the greeting."""
        greeting = (
            f"Thanks for calling CareCaller. This is {self._call_state.config.agent_name}. "
            f"Am I speaking with {self._patient.name}?"
        )
        self._call_state.add_transcript_turn("agent", greeting)
        self.session.say(greeting)
        logger.info("[AGENT]: %s", greeting)

    async def on_user_turn_completed(
        self,
        turn_ctx: llm.ChatContext,
        new_message: llm.ChatMessage,
    ) -> None:
        """Called after VAD + STT finalize a user utterance and the LLM responds.

        This is where we run the handler chain:
            1. Edge case detection
            2. Response capture
            3. Escalation check
            4. Advance state + rebuild prompt
        """
        user_text = new_message.text_content if hasattr(new_message, "text_content") else str(new_message)
        if not user_text:
            return

        logger.info("[USER]: %s", user_text)
        self._call_state.add_transcript_turn("user", user_text)

        if self._call_state.is_terminal:
            return

        # --- Step 1: Edge case detection ---
        edge_result = await self._edge_case_handler.detect_edge_case(
            user_text, self._call_state
        )
        if edge_result is not None:
            outcome = CallOutcome(edge_result.case_type)
            self._call_state.set_outcome(outcome)
            logger.info("Edge case detected: %s", edge_result.case_type)
            await self._publish_event("call_status", {"status": outcome.value})
            await self._post_results_to_api(outcome.value)
            return

        # --- Step 2: Response capture (only during questionnaire) ---
        if self._call_state.phase == CallPhase.QUESTIONNAIRE:
            questions = Question.all_questions()
            current_q = questions[self._call_state.current_question_index]

            captured = await self._response_handler.extract_response(
                question=current_q,
                patient_utterance=user_text,
                conversation_context=self._call_state.transcript,
            )
            self._call_state.record_answer(
                question_index=captured.question_index,
                raw_answer=captured.raw_answer,
                normalized_answer=captured.normalized_answer,
                confidence=captured.confidence,
            )
            await self._publish_event(
                "response_captured",
                {
                    "question_index": captured.question_index,
                    "question": current_q.text,
                    "answer": captured.normalized_answer,
                },
            )

        # --- Step 3: Escalation check ---
        esc_result = await self._escalation_handler.should_escalate(
            patient_utterance=user_text,
            conversation_context=self._call_state.transcript,
            call_state=self._call_state,
        )
        if esc_result.should_escalate:
            if esc_result.urgency == "immediate":
                self._call_state.set_outcome(CallOutcome.ESCALATED)
                await self._publish_event(
                    "call_status",
                    {"status": "escalated", "reason": esc_result.reason},
                )
                await self._post_results_to_api("escalated")
                return
            else:
                self._call_state.flag_pending_escalation()

        # --- Step 4: Advance state ---
        if self._call_state.phase == CallPhase.QUESTIONNAIRE:
            self._call_state.advance_phase()
        elif not self._call_state.phase.is_terminal:
            self._call_state.advance_phase()

        # --- Step 5: Rebuild prompt with new state ---
        if not self._call_state.is_terminal:
            new_prompt = build_system_prompt(
                phase=self._call_state.phase,
                patient=self._patient,
                config=self._call_state.config,
                responses=self._call_state.responses,
                current_question_index=self._call_state.current_question_index,
            )
            if self._health_context:
                new_prompt = f"{new_prompt}\n\n{self._health_context}"
            await self.update_instructions(new_prompt)

        if self._call_state.phase == CallPhase.COMPLETED:
            await self._publish_event(
                "call_status",
                {
                    "status": "completed",
                    "completeness": self._call_state.completeness,
                    "answered_count": self._call_state.answered_count,
                },
            )
            await self._post_results_to_api("completed")

    async def _publish_event(self, event_type: str, data: dict) -> None:
        """Publish a JSON event to all room participants via LiveKit Data Channels."""
        if self._room:
            payload = json.dumps({"event": event_type, **data}).encode()
            await self._room.local_participant.publish_data(
                payload=payload, topic="call_events"
            )

    async def _post_results_to_api(self, outcome: str) -> None:
        """POST final call results to the API so they're persisted to DB.

        Called when the call reaches a terminal state (completed, escalated,
        opted_out, wrong_number, etc.).
        """
        if not self._call_id:
            logger.warning("No call_id — skipping API callback")
            return

        elapsed = time.monotonic() - self._call_start_time

        # Build responses payload from FSM
        responses = []
        for r in self._call_state.responses:
            if r.raw_answer or r.normalized_answer:
                responses.append({
                    "question_index": r.question_index,
                    "raw_answer": r.raw_answer or "",
                    "normalized_answer": r.normalized_answer or "",
                    "confidence": r.confidence,
                })

        # Build transcript payload from FSM
        transcript = []
        for t in self._call_state.transcript:
            transcript.append({
                "id": f"voice-{len(transcript)}",
                "role": t.role,
                "text": t.message,
                "timestamp": t.timestamp,
            })

        payload = {
            "event": "call_completed",
            "call_id": self._call_id,
            "outcome": outcome,
            "completeness": self._call_state.completeness,
            "responses": responses,
            "transcript": transcript,
        }

        url = f"{self._api_base_url}/api/call/{self._call_id}/voice-event"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
            logger.info("Posted voice results to API for call %s (status=%d)", self._call_id, resp.status_code)
        except Exception:
            logger.exception("Failed to POST voice results to API for call %s", self._call_id)


async def entrypoint(ctx: JobContext) -> None:
    """Main entrypoint — called by LiveKit when a new room needs an agent."""
    settings = get_settings()
    logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))

    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    logger.info("Agent connected to room: %s", ctx.room.name)

    # Load patient context + enriched metadata from room
    patient, extras = _parse_room_metadata(ctx.room.metadata or "")
    logger.info("Loaded patient context: %s (call_id=%s)", patient.name, extras.get("call_id"))

    # Initialize call state
    call_config = CallConfig(agent_name=settings.agent_name)
    call_state = CallState(patient=patient, config=call_config)

    # Create the agent with DB-enriched context
    agent = CareCallerAgent(
        patient=patient,
        call_state=call_state,
        settings=settings,
        room=ctx.room,
        call_id=extras.get("call_id"),
        health_context=extras.get("health_context"),
        api_base_url=extras.get("api_base_url"),
    )

    # Create session with pipeline components
    session = AgentSession(
        vad=VAD.load(),
        stt=STT(
            model=settings.deepgram_stt_model,
            api_key=settings.deepgram_api_key,
            language="en-US",
        ),
        llm=LLM(
            model=settings.groq_model,
            api_key=settings.groq_api_key,
            base_url=settings.groq_base_url,
            temperature=settings.llm_temperature,
        ),
        tts=TTS(
            model=settings.deepgram_tts_model,
            api_key=settings.deepgram_api_key,
            sample_rate=settings.deepgram_tts_sample_rate,
        ),
    )

    # Start the agent in the room
    await session.start(agent=agent, room=ctx.room)
    logger.info("Voice pipeline started for patient: %s", patient.name)


# --- LiveKit Worker Configuration ---

settings = get_settings()

worker_options = WorkerOptions(
    entrypoint_fnc=entrypoint,
    api_key=settings.livekit_api_key,
    api_secret=settings.livekit_api_secret,
    ws_url=settings.livekit_url,
)

if __name__ == "__main__":
    cli.run_app(worker_options)
