"""SQLAlchemy ORM models — these ARE the database schema."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    dob: Mapped[str] = mapped_column(String, nullable=False)
    phone: Mapped[str] = mapped_column(String, nullable=False)
    medication: Mapped[str] = mapped_column(String, nullable=False)
    dosage: Mapped[str] = mapped_column(String, nullable=False)
    pharmacy: Mapped[str] = mapped_column(String, nullable=False)
    enrolled_at: Mapped[str] = mapped_column(String, default=lambda: datetime.now().isoformat())

    health_snapshots: Mapped[list[HealthSnapshot]] = relationship(back_populates="patient")
    calls: Mapped[list[Call]] = relationship(back_populates="patient")


class HealthSnapshot(Base):
    __tablename__ = "health_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), nullable=False)
    weight_lbs: Mapped[float | None] = mapped_column(Float, nullable=True)
    height: Mapped[str | None] = mapped_column(String, nullable=True)
    goal_weight_lbs: Mapped[float | None] = mapped_column(Float, nullable=True)
    weight_lost_lbs: Mapped[float | None] = mapped_column(Float, nullable=True)
    side_effects: Mapped[str] = mapped_column(Text, default="")
    satisfaction: Mapped[str] = mapped_column(Text, default="")
    dosage_requests: Mapped[str] = mapped_column(Text, default="")
    new_medications: Mapped[str] = mapped_column(Text, default="")
    new_conditions: Mapped[str] = mapped_column(Text, default="")
    allergies: Mapped[str] = mapped_column(Text, default="")
    surgeries: Mapped[str] = mapped_column(Text, default="")
    doctor_questions: Mapped[str] = mapped_column(Text, default="")
    address_changed: Mapped[str] = mapped_column(Text, default="")
    snapshot_date: Mapped[str] = mapped_column(String, default=lambda: date.today().isoformat())
    source_call_id: Mapped[str | None] = mapped_column(ForeignKey("calls.id"), nullable=True)

    patient: Mapped[Patient] = relationship(back_populates="health_snapshots")


class Call(Base):
    __tablename__ = "calls"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), nullable=False)
    outcome: Mapped[str | None] = mapped_column(String, nullable=True)
    started_at: Mapped[str] = mapped_column(String, default=lambda: datetime.now().isoformat())
    ended_at: Mapped[str | None] = mapped_column(String, nullable=True)
    duration_secs: Mapped[float | None] = mapped_column(Float, nullable=True)
    completeness: Mapped[float] = mapped_column(Float, default=0.0)
    config_tone: Mapped[str] = mapped_column(String, default="friendly")
    config_speed: Mapped[float] = mapped_column(Float, default=1.0)
    notes: Mapped[str] = mapped_column(Text, default="")

    patient: Mapped[Patient] = relationship(back_populates="calls")
    responses: Mapped[list[CallResponse]] = relationship(back_populates="call")
    transcript: Mapped[list[CallTranscript]] = relationship(back_populates="call")


class CallResponse(Base):
    __tablename__ = "call_responses"
    __table_args__ = (UniqueConstraint("call_id", "question_index"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    call_id: Mapped[str] = mapped_column(ForeignKey("calls.id"), nullable=False)
    question_index: Mapped[int] = mapped_column(Integer, nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    raw_answer: Mapped[str] = mapped_column(Text, default="")
    normalized_answer: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String, default="pending")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)

    call: Mapped[Call] = relationship(back_populates="responses")


class CallTranscript(Base):
    __tablename__ = "call_transcript"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    call_id: Mapped[str] = mapped_column(ForeignKey("calls.id"), nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[float] = mapped_column(Float, default=0.0)

    call: Mapped[Call] = relationship(back_populates="transcript")
