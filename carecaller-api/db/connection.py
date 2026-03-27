"""SQLite connection lifecycle via SQLAlchemy async engine."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from db.entities import Base

logger = logging.getLogger("carecaller-api.db")

engine = None
async_session_factory = None


async def init_db(db_path: str) -> None:
    """Create the engine, session factory, and all tables from ORM models."""
    global engine, async_session_factory

    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    database_url = f"sqlite+aiosqlite:///{db_path}"
    engine = create_async_engine(database_url, echo=False)
    async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Database initialized at %s", db_path)


async def close_db() -> None:
    """Dispose of the engine and close all connections."""
    global engine, async_session_factory
    if engine is not None:
        await engine.dispose()
        engine = None
        async_session_factory = None
        logger.info("Database connection closed")


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async session. Use as a FastAPI dependency."""
    if async_session_factory is None:
        raise RuntimeError("Database not initialized — call init_db() first")
    async with async_session_factory() as session:
        yield session
