"""Seed the database with patients and health snapshots from transcript_samples.json."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.entities import HealthSnapshot, Patient

logger = logging.getLogger("carecaller-api.seed")

_DATASETS_DIR = Path(__file__).resolve().parent.parent.parent / "datasets" / "Datasets"

# 14 health questions — map index to snapshot field for extracting seed data
_QUESTION_TO_FIELD = {
    0: "feeling",        # "How have you been feeling overall?" — not stored in snapshot
    1: "weight_lbs",
    2: "height",
    3: "weight_lost_lbs",
    4: "side_effects",
    5: "satisfaction",
    6: "goal_weight_lbs",
    7: "dosage_requests",
    8: "new_medications",
    9: "new_conditions",
    10: "allergies",
    11: "surgeries",
    12: "doctor_questions",
    13: "address_changed",
}

# Patients to seed — manually curated from transcript_samples.json
# These cover different outcomes and provide realistic demo data
_SEED_PATIENTS = [
    {
        "id": "pat_001",
        "name": "Gabriella Shelton",
        "dob": "1985-07-22",
        "phone": "+1-555-0101",
        "medication": "Tirzepatide",
        "dosage": "2.5mg weekly injection",
        "pharmacy": "CVS Pharmacy",
    },
    {
        "id": "pat_002",
        "name": "Austin Daniels",
        "dob": "1990-08-15",
        "phone": "+1-555-0102",
        "medication": "Contrave",
        "dosage": "two tablets twice daily",
        "pharmacy": "Walgreens",
    },
    {
        "id": "pat_003",
        "name": "Shannon Miller",
        "dob": "1978-11-05",
        "phone": "+1-555-0103",
        "medication": "Tirzepatide",
        "dosage": "5mg weekly injection",
        "pharmacy": "Rite Aid",
    },
    {
        "id": "pat_004",
        "name": "Kevin Gardner",
        "dob": "1995-02-18",
        "phone": "+1-555-0104",
        "medication": "Tirzepatide",
        "dosage": "2.5mg weekly injection",
        "pharmacy": "Walmart Pharmacy",
    },
    {
        "id": "pat_005",
        "name": "Maria Garcia",
        "dob": "1982-03-15",
        "phone": "+1-555-0105",
        "medication": "Semaglutide",
        "dosage": "0.5mg weekly injection",
        "pharmacy": "CVS Pharmacy",
    },
]


def _parse_numeric(value: str) -> float | None:
    """Try to extract a number from a response string like '345', '5 pounds', etc."""
    if not value:
        return None
    cleaned = value.strip().replace(",", "")
    for word in cleaned.split():
        try:
            return float(word)
        except ValueError:
            continue
    return None


def _find_patient_responses(transcripts: list[dict], patient_name: str) -> dict | None:
    """Find the transcript entry for a given patient name."""
    for t in transcripts:
        first_msg = t["transcript"][0]["message"]
        if patient_name.split()[-1] in first_msg:
            if t.get("responses") and any(r["answer"] for r in t["responses"]):
                return t
    return None


def _build_snapshot_from_responses(
    patient_id: str,
    responses: list[dict],
) -> HealthSnapshot:
    """Convert transcript_samples responses into a HealthSnapshot entity."""
    snapshot = HealthSnapshot(patient_id=patient_id)

    for r in responses:
        idx = responses.index(r)
        answer = r.get("answer", "")
        if not answer or idx not in _QUESTION_TO_FIELD:
            continue

        field = _QUESTION_TO_FIELD[idx]
        if field == "feeling":
            continue
        elif field == "weight_lbs":
            snapshot.weight_lbs = _parse_numeric(answer)
        elif field == "height":
            snapshot.height = answer
        elif field == "goal_weight_lbs":
            snapshot.goal_weight_lbs = _parse_numeric(answer)
        elif field == "weight_lost_lbs":
            snapshot.weight_lost_lbs = _parse_numeric(answer)
        elif field == "side_effects":
            snapshot.side_effects = answer
        elif field == "satisfaction":
            snapshot.satisfaction = answer
        elif field == "dosage_requests":
            snapshot.dosage_requests = answer
        elif field == "new_medications":
            snapshot.new_medications = answer
        elif field == "new_conditions":
            snapshot.new_conditions = answer
        elif field == "allergies":
            snapshot.allergies = answer
        elif field == "surgeries":
            snapshot.surgeries = answer
        elif field == "doctor_questions":
            snapshot.doctor_questions = answer
        elif field == "address_changed":
            snapshot.address_changed = answer

    return snapshot


async def seed_db(session: AsyncSession) -> None:
    """Insert seed patients and health snapshots if the patients table is empty."""
    result = await session.execute(select(Patient).limit(1))
    if result.scalar_one_or_none() is not None:
        logger.info("Database already seeded — skipping")
        return

    # Load transcript data for health snapshots
    transcripts_path = _DATASETS_DIR / "transcript_samples.json"
    transcripts = []
    if transcripts_path.exists():
        with open(transcripts_path) as f:
            data = json.load(f)
            transcripts = data.get("transcripts", [])

    # Insert patients
    for p in _SEED_PATIENTS:
        patient = Patient(**p)
        session.add(patient)

    await session.flush()

    # Insert health snapshots from transcript data
    for p in _SEED_PATIENTS:
        match = _find_patient_responses(transcripts, p["name"])
        if match and match.get("responses"):
            snapshot = _build_snapshot_from_responses(p["id"], match["responses"])
            session.add(snapshot)
            logger.info("Seeded snapshot for %s", p["name"])
        else:
            # Create an empty snapshot so the LLM knows this is a first call
            session.add(HealthSnapshot(patient_id=p["id"]))
            logger.info("Seeded empty snapshot for %s (no prior data)", p["name"])

    await session.commit()
    logger.info("Seeded %d patients", len(_SEED_PATIENTS))
