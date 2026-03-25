"""NLI-based contradiction detection between transcript and structured responses."""

import re

import numpy as np
import pandas as pd

from ..data_loader import parse_responses

# Lazy-loaded model
_nli_pipeline = None


def _get_nli_pipeline():
    global _nli_pipeline
    if _nli_pipeline is None:
        from transformers import pipeline
        print("  Loading NLI model (facebook/bart-large-mnli)...")
        _nli_pipeline = pipeline(
            "zero-shot-classification",
            model="facebook/bart-large-mnli",
            device=-1,  # CPU
        )
    return _nli_pipeline


def _response_to_hypothesis(question: str, answer: str) -> str | None:
    """Convert a Q&A pair into a natural language hypothesis."""
    if not answer or answer.strip() == "":
        return None

    q_lower = question.lower()
    if "weight in pounds" in q_lower and "lost" not in q_lower and "goal" not in q_lower:
        return f"The patient weighs {answer} pounds."
    elif "height" in q_lower:
        return f"The patient's height is {answer}."
    elif "weight have you lost" in q_lower:
        return f"The patient lost {answer} pounds this month."
    elif "side effects" in q_lower:
        return f"The patient reported side effects: {answer}."
    elif "goal weight" in q_lower:
        return f"The patient's goal weight is {answer} pounds."
    elif "feeling overall" in q_lower:
        return f"The patient has been feeling: {answer}."
    elif "new medications" in q_lower:
        return f"Regarding new medications: {answer}."
    elif "allergies" in q_lower:
        return f"Regarding allergies: {answer}."
    elif "shipping address" in q_lower:
        return f"Regarding shipping address changes: {answer}."
    else:
        return f"The patient answered '{answer}' to the question about {question.lower()}."


def _find_relevant_transcript_segment(transcript: str, question_keyword: str) -> str:
    """Find the transcript segment near where a question was asked."""
    if pd.isna(transcript) or not transcript:
        return ""

    # Split into turns
    turns = re.split(r"\[(AGENT|USER)\]:", transcript)
    # Find the turn containing the question keyword
    for i, turn in enumerate(turns):
        if question_keyword.lower() in turn.lower():
            # Return this turn and next 2 turns (agent question + user answer + maybe follow-up)
            segment = " ".join(turns[max(0, i):min(len(turns), i + 4)])
            return segment[:500]
    return ""


def extract(df: pd.DataFrame) -> pd.DataFrame:
    """Run NLI contradiction detection. Returns features per row."""
    nli = _get_nli_pipeline()
    features = pd.DataFrame(index=df.index)

    max_contradiction_scores = []
    mean_contradiction_scores = []
    contradiction_counts = []

    for idx, row in df.iterrows():
        responses = parse_responses(row.get("responses_json", ""))
        transcript = str(row.get("transcript_text", ""))

        contradictions = []

        for resp in responses:
            q = resp.get("question", "")
            a = resp.get("answer", "")
            hypothesis = _response_to_hypothesis(q, a)
            if hypothesis is None:
                continue

            # Find relevant transcript segment
            q_keyword = q.split()[-2] if len(q.split()) >= 2 else q.split()[0] if q.split() else ""
            segment = _find_relevant_transcript_segment(transcript, q_keyword)
            if not segment or len(segment.strip()) < 10:
                continue

            try:
                result = nli(
                    segment[:512],
                    candidate_labels=["true", "false"],
                    hypothesis_template="This statement is {}: " + hypothesis,
                )
                # Score for "false" label = contradiction score
                false_idx = result["labels"].index("false")
                contradiction_score = result["scores"][false_idx]
                contradictions.append(contradiction_score)
            except Exception:
                continue

        if contradictions:
            max_contradiction_scores.append(max(contradictions))
            mean_contradiction_scores.append(np.mean(contradictions))
            contradiction_counts.append(sum(1 for s in contradictions if s > 0.7))
        else:
            max_contradiction_scores.append(0.0)
            mean_contradiction_scores.append(0.0)
            contradiction_counts.append(0)

    features["nli_max_contradiction"] = max_contradiction_scores
    features["nli_mean_contradiction"] = mean_contradiction_scores
    features["nli_contradiction_count"] = contradiction_counts

    return features
