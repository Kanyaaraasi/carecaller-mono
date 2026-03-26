"""Silero VAD (Voice Activity Detection) configuration for the LiveKit voice pipeline."""

from __future__ import annotations

from livekit.plugins.silero import VAD


def create_vad() -> VAD:
    """Create a configured Silero VAD instance.

    Runs locally (no API calls). Configuration choices:
    - min_speech_duration=0.25: Ignore noise bursts shorter than 250ms
    - min_silence_duration=0.5: Wait 500ms of silence before end-of-turn
    - padding_duration=0.3: Include 300ms of audio context before/after speech
    - activation_threshold=0.5: Balanced sensitivity for phone-quality audio
    """
    return VAD.load(
        min_speech_duration=0.25,
        min_silence_duration=0.5,
        padding_duration=0.3,
        activation_threshold=0.5,
    )
