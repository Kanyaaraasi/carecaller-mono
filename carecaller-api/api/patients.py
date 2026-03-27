"""Patient endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from db.connection import get_session
from repositories import patient_repo
from schemas import PatientOut, PatientsListOut

router = APIRouter(prefix="/api", tags=["patients"])


@router.get("/patients", response_model=PatientsListOut)
async def list_patients(session: AsyncSession = Depends(get_session)):
    patients = await patient_repo.list_all(session)
    return PatientsListOut(
        patients=[
            PatientOut(
                id=p.id,
                name=p.name,
                date_of_birth=p.dob,
                medication=p.medication,
                pharmacy=p.pharmacy,
                phone=p.phone,
            )
            for p in patients
        ]
    )


@router.get("/patients/{patient_id}", response_model=PatientOut)
async def get_patient(patient_id: str, session: AsyncSession = Depends(get_session)):
    patient = await patient_repo.get_by_id(session, patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail=f"Patient {patient_id} not found")
    return PatientOut(
        id=patient.id,
        name=patient.name,
        date_of_birth=patient.dob,
        medication=patient.medication,
        pharmacy=patient.pharmacy,
        phone=patient.phone,
    )
