"""LiveKit room management — creates rooms with enriched patient metadata and generates tokens.

Phase 5: The API creates LiveKit rooms so the voice agent worker auto-joins
with full DB-enriched patient context (profile + health history).
"""

from __future__ import annotations

import json
import logging

from livekit.api import AccessToken, LiveKitAPI, VideoGrants
from livekit.protocol.room import CreateRoomRequest
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from repositories import patient_repo
from services.context_builder import build_patient_context

logger = logging.getLogger("carecaller-api.livekit")

_livekit_api: LiveKitAPI | None = None


def _get_api() -> LiveKitAPI:
    global _livekit_api
    if _livekit_api is None:
        settings = get_settings()
        _livekit_api = LiveKitAPI(
            url=settings.livekit_url.replace("wss://", "https://"),
            api_key=settings.livekit_api_key,
            api_secret=settings.livekit_api_secret,
        )
    return _livekit_api


async def create_voice_room(
    session: AsyncSession,
    call_id: str,
    patient_id: str,
) -> str:
    """Create a LiveKit room with DB-enriched patient metadata.

    The room name is the call_id. The room metadata is a JSON blob containing:
    - Basic patient fields (id, name, dob, medication, dosage, pharmacy, phone)
    - health_context: formatted string from context_builder (health history, prior calls)
    - call_id: so the agent can POST results back

    Returns the room name (== call_id).
    """
    settings = get_settings()
    patient = await patient_repo.get_by_id(session, patient_id)
    if patient is None:
        raise ValueError(f"Patient {patient_id} not found")

    # Build enriched context from DB
    health_context = await build_patient_context(session, patient_id)

    metadata = json.dumps({
        "id": patient.id,
        "name": patient.name,
        "date_of_birth": patient.dob,
        "medication": patient.medication,
        "dosage": patient.dosage,
        "pharmacy": patient.pharmacy,
        "phone": patient.phone,
        "health_context": health_context,
        "call_id": call_id,
        "api_base_url": f"http://localhost:8004",
    })

    api = _get_api()
    room = await api.room.create_room(
        CreateRoomRequest(name=call_id, metadata=metadata)
    )
    logger.info("Created LiveKit room %s for patient %s", room.name, patient.name)
    return room.name


def generate_participant_token(room_name: str, identity: str, name: str) -> str:
    """Generate a LiveKit access token for a participant to join a room."""
    settings = get_settings()
    token = (
        AccessToken(settings.livekit_api_key, settings.livekit_api_secret)
        .with_identity(identity)
        .with_name(name)
        .with_grants(VideoGrants(
            room_join=True,
            room=room_name,
        ))
        .to_jwt()
    )
    return token


async def close() -> None:
    """Shutdown the LiveKit API client."""
    global _livekit_api
    if _livekit_api is not None:
        await _livekit_api.aclose()
        _livekit_api = None
