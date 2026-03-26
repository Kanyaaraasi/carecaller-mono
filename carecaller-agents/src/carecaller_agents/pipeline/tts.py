"""Deepgram TTS (Text-to-Speech) provider configuration for the LiveKit voice pipeline."""

from __future__ import annotations

from livekit.plugins.deepgram import TTS

from carecaller_agents.config import Settings


def create_tts(settings: Settings) -> TTS:
    """Create a configured Deepgram TTS instance.

    Configuration choices:
    - aura-asteria-en: Natural female voice matching the "Jessica" persona
    - sample_rate=24000: High quality audio for clear phone/WebRTC output
    """
    return TTS(
        model=settings.deepgram_tts_model,
        api_key=settings.deepgram_api_key,
        sample_rate=settings.deepgram_tts_sample_rate,
    )
