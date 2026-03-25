"""Predict ticket category from existing signal features."""

import pandas as pd


CATEGORIES = ["audio_issue", "elevenlabs", "openai"]


def predict_category(features_row: pd.Series) -> str:
    """Predict which module caused the issue based on signal features.

    Priority order: audio_issue > elevenlabs > openai (most specific first).
    """
    # Audio/STT issues: whisper mismatch, high WER, number mismatches
    if (
        features_row.get("rule_whisper_mismatch", 0) == 1
        or features_row.get("whisper_mismatch_count", 0) > 0
        or features_row.get("diff_wer", 0) > 0.15
        or features_row.get("num_mismatches", 0) > 0
    ):
        return "audio_issue"

    # ElevenLabs / voice agent guardrail violations
    if features_row.get("rule_medical_advice", 0) == 1:
        return "elevenlabs"

    # OpenAI / agent logic issues (catch-all for remaining)
    return "openai"


def predict_categories(features_df: pd.DataFrame, predictions: pd.Series) -> list[str]:
    """Predict categories for all calls. Empty string for non-flagged calls."""
    categories = []
    for idx, row in features_df.iterrows():
        if predictions.iloc[idx] if hasattr(predictions, 'iloc') else predictions[idx]:
            categories.append(predict_category(row))
        else:
            categories.append("")
    return categories
