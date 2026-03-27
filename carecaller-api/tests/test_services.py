"""Tests for the service layer — context builder and call service."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from services import context_builder
from repositories import call_repo, patient_repo


class TestContextBuilder:
    async def test_builds_context_with_patient_name(self, seeded_session: AsyncSession):
        ctx = await context_builder.build_patient_context(seeded_session, "pat_001")
        assert "Gabriella Shelton" in ctx
        assert "Tirzepatide" in ctx

    async def test_includes_health_snapshot(self, seeded_session: AsyncSession):
        ctx = await context_builder.build_patient_context(seeded_session, "pat_001")
        assert "345" in ctx  # weight
        assert "250" in ctx  # goal weight
        assert "5'6" in ctx  # height

    async def test_first_call_patient_has_no_prior_checkin(self, seeded_session: AsyncSession):
        ctx = await context_builder.build_patient_context(seeded_session, "pat_001")
        assert "first call" in ctx.lower() or "None" in ctx

    async def test_raises_for_unknown_patient(self, seeded_session: AsyncSession):
        with pytest.raises(ValueError, match="not found"):
            await context_builder.build_patient_context(seeded_session, "pat_999")

    async def test_empty_snapshot_patient(self, seeded_session: AsyncSession):
        ctx = await context_builder.build_patient_context(seeded_session, "pat_005")
        assert "Maria Garcia" in ctx


class TestCallServiceStartCall:
    """Tests for call_service.start_call — uses DB directly, no LLM calls."""

    async def test_start_call_creates_db_records(self, seeded_session: AsyncSession):
        from services import call_service

        call, greeting = await call_service.start_call(
            seeded_session, "svc_001", "pat_001"
        )

        assert call.id == "svc_001"
        assert call.patient_id == "pat_001"
        assert "Gabriella Shelton" in greeting
        assert "Jessica" in greeting

        # Verify 14 responses created
        responses = await call_repo.get_responses(seeded_session, "svc_001")
        assert len(responses) == 14

        # Q0 should be "asking"
        assert responses[0].status == "asking"
        assert responses[1].status == "pending"

    async def test_start_call_uses_provided_call_id(self, seeded_session: AsyncSession):
        from services import call_service

        call, _ = await call_service.start_call(
            seeded_session, "my_custom_id", "pat_002"
        )
        assert call.id == "my_custom_id"

    async def test_start_call_persists_greeting_to_transcript(self, seeded_session: AsyncSession):
        from services import call_service

        await call_service.start_call(seeded_session, "svc_002", "pat_001")
        transcript = await call_repo.get_transcript(seeded_session, "svc_002")
        assert len(transcript) == 1
        assert transcript[0].role == "agent"
        assert "Gabriella Shelton" in transcript[0].message

    async def test_start_call_unknown_patient_raises(self, seeded_session: AsyncSession):
        from services import call_service

        with pytest.raises(ValueError, match="not found"):
            await call_service.start_call(seeded_session, "svc_003", "pat_999")


class TestCallServiceEndCall:
    async def test_end_call_sets_outcome(self, seeded_session: AsyncSession):
        from services import call_service

        await call_service.start_call(seeded_session, "end_001", "pat_001")
        call = await call_service.end_call(seeded_session, "end_001", "completed")

        assert call.outcome == "completed"
        assert call.ended_at is not None
        assert call.duration_secs is not None

    async def test_end_call_incomplete(self, seeded_session: AsyncSession):
        from services import call_service

        await call_service.start_call(seeded_session, "end_002", "pat_001")
        call = await call_service.end_call(seeded_session, "end_002", "incomplete")

        assert call.outcome == "incomplete"

    async def test_end_call_cleans_up_state(self, seeded_session: AsyncSession):
        from services import call_service

        await call_service.start_call(seeded_session, "end_003", "pat_001")
        assert "end_003" in call_service._active_states

        await call_service.end_call(seeded_session, "end_003", "completed")
        assert "end_003" not in call_service._active_states


class TestCallServiceGetState:
    async def test_get_call_state_returns_all_data(self, seeded_session: AsyncSession):
        from services import call_service

        await call_service.start_call(seeded_session, "state_001", "pat_001")
        call, responses, transcript, duration = await call_service.get_call_state(
            seeded_session, "state_001"
        )

        assert call is not None
        assert call.id == "state_001"
        assert len(responses) == 14
        assert len(transcript) == 1  # greeting
        assert duration is not None

    async def test_get_call_state_unknown_call(self, seeded_session: AsyncSession):
        from services import call_service

        call, responses, transcript, duration = await call_service.get_call_state(
            seeded_session, "nonexistent"
        )
        assert call is None
        assert responses == []
