"""Tests for API endpoints using FastAPI TestClient."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from db.entities import Base
from db.connection import get_session
from db.seed import seed_db
from main import app


@pytest.fixture
async def client():
    """AsyncClient with an in-memory DB injected via dependency override."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Seed the test DB
    async with factory() as session:
        await seed_db(session)

    async def _override_get_session():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_session] = _override_get_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
    await engine.dispose()


class TestHealthEndpoint:
    async def test_health(self, client: AsyncClient):
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestPatientsEndpoint:
    async def test_list_patients(self, client: AsyncClient):
        resp = await client.get("/api/patients")
        assert resp.status_code == 200
        data = resp.json()
        assert "patients" in data
        assert len(data["patients"]) == 5

    async def test_list_patients_has_required_fields(self, client: AsyncClient):
        resp = await client.get("/api/patients")
        patient = resp.json()["patients"][0]
        for field in ("id", "name", "date_of_birth", "medication", "pharmacy", "phone"):
            assert field in patient, f"Missing field: {field}"

    async def test_get_patient_by_id(self, client: AsyncClient):
        resp = await client.get("/api/patients/pat_001")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Gabriella Shelton"

    async def test_get_patient_not_found(self, client: AsyncClient):
        resp = await client.get("/api/patients/pat_999")
        assert resp.status_code == 404


class TestQuestionsEndpoint:
    async def test_list_questions(self, client: AsyncClient):
        resp = await client.get("/api/questions")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["questions"]) == 14

    async def test_question_shape(self, client: AsyncClient):
        resp = await client.get("/api/questions")
        q = resp.json()["questions"][0]
        assert "index" in q
        assert "text" in q
        assert q["index"] == 0


class TestCallEndpoints:
    async def test_start_call(self, client: AsyncClient):
        resp = await client.post("/api/call/start", json={
            "patient_id": "pat_001",
            "call_id": "test_call",
            "config": {"tone": "friendly", "speed": 1.0, "auto_greet": True, "skip_answered": True},
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["call_id"] == "test_call"
        assert data["status"] == "in-progress"
        assert "Gabriella Shelton" in data["greeting_message"]

    async def test_start_call_unknown_patient(self, client: AsyncClient):
        resp = await client.post("/api/call/start", json={
            "patient_id": "pat_999",
            "config": {"tone": "friendly", "speed": 1.0, "auto_greet": True, "skip_answered": True},
        })
        assert resp.status_code == 404

    async def test_get_responses_after_start(self, client: AsyncClient):
        await client.post("/api/call/start", json={
            "patient_id": "pat_001",
            "call_id": "resp_call",
            "config": {"tone": "friendly", "speed": 1.0, "auto_greet": True, "skip_answered": True},
        })

        resp = await client.get("/api/call/resp_call/responses")
        assert resp.status_code == 200
        data = resp.json()
        assert data["call_id"] == "resp_call"
        assert len(data["responses"]) == 14
        assert data["responses"][0]["status"] == "asking"
        assert data["completeness"] == 0.0
        assert len(data["transcript"]) == 1  # greeting

    async def test_get_responses_unknown_call(self, client: AsyncClient):
        resp = await client.get("/api/call/nonexistent/responses")
        assert resp.status_code == 404

    async def test_end_call(self, client: AsyncClient):
        await client.post("/api/call/start", json={
            "patient_id": "pat_001",
            "call_id": "end_call",
            "config": {"tone": "friendly", "speed": 1.0, "auto_greet": True, "skip_answered": True},
        })

        resp = await client.post("/api/call/end_call/end", json={
            "call_id": "end_call",
            "reason": "incomplete",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["outcome"] == "incomplete"
        assert "responses" in data
        assert "transcript" in data

    async def test_start_call_generates_id_if_not_provided(self, client: AsyncClient):
        resp = await client.post("/api/call/start", json={
            "patient_id": "pat_001",
            "config": {"tone": "friendly", "speed": 1.0, "auto_greet": True, "skip_answered": True},
        })
        assert resp.status_code == 200
        assert resp.json()["call_id"].startswith("call_")
