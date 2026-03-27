"""Tests for database entities, seed data, and repository layer."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from db.entities import Patient, HealthSnapshot, Call, CallResponse, CallTranscript
from repositories import patient_repo, call_repo, question_repo


# --- Seed ---

class TestSeed:
    async def test_seed_creates_five_patients(self, seeded_session: AsyncSession):
        patients = await patient_repo.list_all(seeded_session)
        assert len(patients) == 5

    async def test_seed_is_idempotent(self, seeded_session: AsyncSession):
        from db.seed import seed_db
        await seed_db(seeded_session)  # run again
        patients = await patient_repo.list_all(seeded_session)
        assert len(patients) == 5  # still 5, not 10

    async def test_seed_creates_health_snapshots(self, seeded_session: AsyncSession):
        snap = await patient_repo.get_latest_snapshot(seeded_session, "pat_001")
        assert snap is not None
        assert snap.patient_id == "pat_001"


# --- Patient Repo ---

class TestPatientRepo:
    async def test_list_all_returns_sorted(self, seeded_session: AsyncSession):
        patients = await patient_repo.list_all(seeded_session)
        names = [p.name for p in patients]
        assert names == sorted(names)

    async def test_get_by_id_found(self, seeded_session: AsyncSession):
        patient = await patient_repo.get_by_id(seeded_session, "pat_001")
        assert patient is not None
        assert patient.name == "Gabriella Shelton"
        assert patient.medication == "Tirzepatide"

    async def test_get_by_id_not_found(self, seeded_session: AsyncSession):
        patient = await patient_repo.get_by_id(seeded_session, "pat_999")
        assert patient is None

    async def test_snapshot_has_weight(self, seeded_session: AsyncSession):
        snap = await patient_repo.get_latest_snapshot(seeded_session, "pat_001")
        assert snap is not None
        assert snap.weight_lbs == 345.0
        assert snap.goal_weight_lbs == 250.0
        assert snap.height == "5'6"


# --- Call Repo ---

class TestCallRepo:
    async def test_create_call_inserts_14_responses(self, seeded_session: AsyncSession):
        call = await call_repo.create_call(seeded_session, "call_t1", "pat_001")
        await seeded_session.commit()

        assert call.id == "call_t1"
        assert call.patient_id == "pat_001"

        responses = await call_repo.get_responses(seeded_session, "call_t1")
        assert len(responses) == 14
        assert all(r.status == "pending" for r in responses)

    async def test_update_response(self, seeded_session: AsyncSession):
        await call_repo.create_call(seeded_session, "call_t2", "pat_001")
        await seeded_session.commit()

        await call_repo.update_response(
            seeded_session, "call_t2", 0,
            raw_answer="Pretty good",
            normalized_answer="Pretty good",
        )
        await seeded_session.commit()

        responses = await call_repo.get_responses(seeded_session, "call_t2")
        assert responses[0].status == "answered"
        assert responses[0].normalized_answer == "Pretty good"
        assert responses[1].status == "pending"

    async def test_mark_question_asking(self, seeded_session: AsyncSession):
        await call_repo.create_call(seeded_session, "call_t3", "pat_001")
        await call_repo.mark_question_asking(seeded_session, "call_t3", 2)
        await seeded_session.commit()

        responses = await call_repo.get_responses(seeded_session, "call_t3")
        assert responses[2].status == "asking"

    async def test_transcript_ordering(self, seeded_session: AsyncSession):
        await call_repo.create_call(seeded_session, "call_t4", "pat_001")
        await call_repo.add_transcript_turn(seeded_session, "call_t4", "agent", "Hello", 0.0)
        await call_repo.add_transcript_turn(seeded_session, "call_t4", "user", "Hi", 2.0)
        await call_repo.add_transcript_turn(seeded_session, "call_t4", "agent", "How are you?", 3.5)
        await seeded_session.commit()

        transcript = await call_repo.get_transcript(seeded_session, "call_t4")
        assert len(transcript) == 3
        assert transcript[0].role == "agent"
        assert transcript[1].role == "user"
        assert transcript[2].timestamp == 3.5

    async def test_end_call_sets_outcome(self, seeded_session: AsyncSession):
        await call_repo.create_call(seeded_session, "call_t5", "pat_001")
        await seeded_session.commit()

        await call_repo.end_call(seeded_session, "call_t5", "completed", 0.85)
        await seeded_session.commit()

        call = await call_repo.get_call(seeded_session, "call_t5")
        assert call.outcome == "completed"
        assert call.completeness == 0.85
        assert call.ended_at is not None
        assert call.duration_secs is not None


# --- Question Repo ---

class TestQuestionRepo:
    def test_returns_14_questions(self):
        questions = question_repo.get_all_questions()
        assert len(questions) == 14

    def test_first_question(self):
        questions = question_repo.get_all_questions()
        assert questions[0].index == 0
        assert "feeling" in questions[0].text.lower()

    def test_last_question(self):
        questions = question_repo.get_all_questions()
        assert questions[13].index == 13
        assert "shipping" in questions[13].text.lower()
