"""LLM-as-Judge: evaluate each call for quality issues using an LLM provider."""

import json
import hashlib
from pathlib import Path

import pandas as pd

from ..config import OUTPUT_DIR
from ..llm import get_provider

CACHE_DIR = OUTPUT_DIR / "llm_cache"

SYSTEM_PROMPT = """You are a QA evaluator for healthcare medication refill check-in calls made by an AI voice agent.
You must detect quality issues in these calls. Be thorough and precise."""

EVAL_PROMPT_TEMPLATE = """Evaluate this healthcare check-in call for quality issues.

## Call Metadata
- Outcome: {outcome}
- Call Duration: {call_duration}s
- Response Completeness: {response_completeness}
- Answered: {answered_count}/14 questions
- Whisper Mismatch Count: {whisper_mismatch_count}

## Transcript
{transcript_text}

## Recorded Responses (what the system captured)
{responses_json}

## Post-Call Validation Notes
{validation_notes}

---

Check for these specific issues:
1. OUTCOME_MISMATCH: Does the outcome "{outcome}" match what actually happened in the transcript?
2. SKIPPED_QUESTIONS: Were all required health questions asked? Count how many were actually asked.
3. MEDICAL_ADVICE: Did the agent give any medical advice, treatment recommendations, or clinical guidance?
4. DATA_CAPTURE_ERROR: Do the recorded responses match what the patient actually said in the transcript?
5. STT_ERROR: Are there signs of speech-to-text errors (garbled text, impossible values, numbers that don't match)?
6. WRONG_NUMBER_MISCLASS: If outcome is wrong_number, does the transcript actually show a wrong number scenario?

Return JSON:
{{
    "has_issue": true/false,
    "confidence": 0.0-1.0,
    "outcome_mismatch": true/false,
    "skipped_questions": true/false,
    "questions_actually_asked": <int>,
    "medical_advice": true/false,
    "data_capture_error": true/false,
    "stt_error": true/false,
    "wrong_number_misclass": true/false,
    "issue_summary": "<brief description or empty string>"
}}"""


def _cache_key(call_id: str, model: str) -> str:
    return hashlib.md5(f"{call_id}:{model}".encode()).hexdigest()


def _load_cache(call_id: str, model: str) -> dict | None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / f"{_cache_key(call_id, model)}.json"
    if path.exists():
        return json.loads(path.read_text())
    return None


def _save_cache(call_id: str, model: str, result: dict):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / f"{_cache_key(call_id, model)}.json"
    path.write_text(json.dumps(result))


def evaluate_call(row: pd.Series, provider_name: str = "groq", model: str | None = None) -> dict:
    """Evaluate a single call using the LLM."""
    call_id = row["call_id"]
    provider = get_provider(provider_name, model=model)

    # Check cache
    cached = _load_cache(call_id, provider.model)
    if cached is not None:
        return cached

    prompt = EVAL_PROMPT_TEMPLATE.format(
        outcome=row.get("outcome", ""),
        call_duration=row.get("call_duration", ""),
        response_completeness=row.get("response_completeness", ""),
        answered_count=row.get("answered_count", ""),
        whisper_mismatch_count=row.get("whisper_mismatch_count", ""),
        transcript_text=str(row.get("transcript_text", ""))[:3000],  # truncate for token limit
        responses_json=str(row.get("responses_json", ""))[:1500],
        validation_notes=str(row.get("validation_notes", "")),
    )

    try:
        result = provider.complete_json(prompt, system=SYSTEM_PROMPT)
    except Exception as e:
        print(f"  LLM error for {call_id}: {e}")
        result = {
            "has_issue": False, "confidence": 0.0,
            "outcome_mismatch": False, "skipped_questions": False,
            "questions_actually_asked": 0, "medical_advice": False,
            "data_capture_error": False, "stt_error": False,
            "wrong_number_misclass": False, "issue_summary": f"error: {e}",
        }

    _save_cache(call_id, provider.model, result)
    return result


def extract(df: pd.DataFrame, provider_name: str = "groq", model: str | None = None) -> pd.DataFrame:
    """Run LLM-as-judge on all calls, return features."""
    results = []
    total = len(df)
    for i, (_, row) in enumerate(df.iterrows()):
        if (i + 1) % 25 == 0 or i == 0:
            print(f"  LLM judge: {i + 1}/{total}")
        result = evaluate_call(row, provider_name=provider_name, model=model)
        results.append(result)

    features = pd.DataFrame(index=df.index)
    features["llm_has_issue"] = [int(r.get("has_issue", False)) for r in results]
    features["llm_confidence"] = [float(r.get("confidence", 0.0)) for r in results]
    features["llm_outcome_mismatch"] = [int(r.get("outcome_mismatch", False)) for r in results]
    features["llm_skipped_questions"] = [int(r.get("skipped_questions", False)) for r in results]
    features["llm_questions_asked"] = [int(r.get("questions_actually_asked", 0)) for r in results]
    features["llm_medical_advice"] = [int(r.get("medical_advice", False)) for r in results]
    features["llm_data_capture_error"] = [int(r.get("data_capture_error", False)) for r in results]
    features["llm_stt_error"] = [int(r.get("stt_error", False)) for r in results]
    features["llm_wrong_number_misclass"] = [int(r.get("wrong_number_misclass", False)) for r in results]

    return features
