"""Deepgram STT (Speech-to-Text) provider configuration for the LiveKit voice pipeline."""

from __future__ import annotations

from livekit.plugins.deepgram import STT

from carecaller_agents.config import Settings


def create_stt(settings: Settings) -> STT:
    """Create a configured Deepgram STT instance.

    Configuration choices:
    - nova-2: Best accuracy/latency tradeoff for conversational speech
    - interim_results: Enabled for live transcript display in the UI
    - smart_format: Auto-formats numbers, dates, punctuation
    - endpointing_ms=300: Wait 300ms of silence before finalizing (responsive turn-taking)
    - punctuate: Adds sentence-ending punctuation for cleaner LLM input
    """
    return STT(
        model=settings.deepgram_stt_model,
        api_key=settings.deepgram_api_key,
        language="en-US",
        interim_results=True,
        smart_format=True,
        punctuate=True,
        endpointing_ms=300,
    )
