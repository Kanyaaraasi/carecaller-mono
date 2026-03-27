"""Shared fixtures — in-memory SQLite DB for isolated tests."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from db.entities import Base


@pytest.fixture
async def session():
    """Yield an async session backed by an in-memory SQLite database."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session

    await engine.dispose()


@pytest.fixture
async def seeded_session(session: AsyncSession):
    """Session with 5 patients and health snapshots already inserted."""
    from db.seed import seed_db

    await seed_db(session)
    return session
