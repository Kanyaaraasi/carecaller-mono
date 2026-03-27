"""Centralized API settings loaded from environment variables / .env file."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_PROJECT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Database ---
    db_path: str = str(_PROJECT_DIR / "data" / "carecaller.db")

    # --- Groq (OpenAI-compatible) ---
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"
    groq_base_url: str = "https://api.groq.com/openai/v1"

    # --- LiveKit (Phase 5) ---
    livekit_url: str = ""
    livekit_api_key: str = ""
    livekit_api_secret: str = ""

    # --- Agent ---
    agent_name: str = "Jessica"
    llm_temperature: float = 0.7
    log_level: str = "INFO"


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
