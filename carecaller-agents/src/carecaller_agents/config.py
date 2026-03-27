"""Centralized application settings loaded from environment variables / .env file."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- LiveKit ---
    livekit_url: str = "ws://localhost:7880"
    livekit_api_key: str = "devkey"
    livekit_api_secret: str = "secret"

    # --- Deepgram ---
    deepgram_api_key: str = ""
    deepgram_stt_model: str = "nova-2"
    deepgram_tts_model: str = "aura-asteria-en"
    deepgram_tts_sample_rate: int = 24000

    # --- Groq (OpenAI-compatible) ---
    groq_api_key: str = ""
    groq_model: str = "gpt-oss-20b"
    groq_base_url: str = "https://api.groq.com/openai/v1"

    # --- API Callback (Phase 5) ---
    api_base_url: str = "http://localhost:8004"

    # --- Agent ---
    agent_name: str = "Jessica"
    llm_temperature: float = 0.7
    log_level: str = "INFO"


def get_settings() -> Settings:
    """Return a cached Settings instance. Call once at startup."""
    return Settings()
