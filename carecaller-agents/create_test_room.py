"""Create a LiveKit room with patient metadata and print a join token.

Usage:
    uv run create_test_room.py
"""

import json

from livekit.api import (
    LiveKitAPI,
    CreateRoomRequest,
    UpdateRoomMetadataRequest,
    AccessToken,
    VideoGrants,
)

from carecaller_agents.config import get_settings


async def main():
    settings = get_settings()

    api = LiveKitAPI(
        url=settings.livekit_url.replace("wss://", "https://"),
        api_key=settings.livekit_api_key,
        api_secret=settings.livekit_api_secret,
    )

    patient_metadata = json.dumps({
        "id": "pat_003",
        "name": "Gabriella Shelton",
        "date_of_birth": "1985-07-22",
        "medication": "Tirzepatide",
        "dosage": "2.5mg weekly injection",
        "pharmacy": "CVS Pharmacy",
        "phone": "+1-555-0103",
    })

    room_name = "test-call-001"

    # Create room
    room = await api.room.create_room(
        CreateRoomRequest(name=room_name, metadata=patient_metadata)
    )
    print(f"Room created: {room.name}")

    # Explicitly update metadata (in case create doesn't persist it)
    updated = await api.room.update_room_metadata(
        UpdateRoomMetadataRequest(room=room_name, metadata=patient_metadata)
    )
    print(f"Metadata set: {updated.metadata[:60]}...")
    print()

    # Generate participant token
    token = (
        AccessToken(settings.livekit_api_key, settings.livekit_api_secret)
        .with_identity("patient-test")
        .with_name("Test Patient")
        .with_grants(VideoGrants(
            room_join=True,
            room=room_name,
        ))
        .to_jwt()
    )

    ws_url = settings.livekit_url
    print(f"Join URL: https://agents-playground.livekit.io/#conn_details={ws_url}&token={token}")
    print()
    print(f"Or manually:")
    print(f"  URL: {ws_url}")
    print(f"  Token: {token}")

    await api.aclose()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
