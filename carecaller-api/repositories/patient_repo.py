"""Data access for patients and health snapshots."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db.entities import HealthSnapshot, Patient


async def list_all(session: AsyncSession) -> list[Patient]:
    """Return all patients ordered by name."""
    result = await session.execute(
        select(Patient).order_by(Patient.name)
    )
    return list(result.scalars().all())


async def get_by_id(session: AsyncSession, patient_id: str) -> Patient | None:
    """Return a single patient by ID, or None."""
    result = await session.execute(
        select(Patient).where(Patient.id == patient_id)
    )
    return result.scalar_one_or_none()


async def get_latest_snapshot(
    session: AsyncSession, patient_id: str
) -> HealthSnapshot | None:
    """Return the most recent health snapshot for a patient."""
    result = await session.execute(
        select(HealthSnapshot)
        .where(HealthSnapshot.patient_id == patient_id)
        .order_by(HealthSnapshot.id.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()
