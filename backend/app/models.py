from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import JSON


class Base(DeclarativeBase):
    pass


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(120), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    assessments: Mapped[list["Assessment"]] = relationship(back_populates="patient")


class Assessment(Base):
    __tablename__ = "assessments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patients.id"), index=True)

    # Core inputs/outputs
    name_at_time: Mapped[str] = mapped_column(String(120))
    age: Mapped[int] = mapped_column(Integer)
    height_cm: Mapped[float] = mapped_column(Float)
    weight_kg: Mapped[float] = mapped_column(Float)
    bmi: Mapped[float] = mapped_column(Float)

    cycle_regularity: Mapped[str] = mapped_column(String(20), default="", nullable=False)
    symptoms: Mapped[list[str]] = mapped_column(JSON().with_variant(SQLiteJSON(), "sqlite"), default=list)
    family_history: Mapped[list[str]] = mapped_column(JSON().with_variant(SQLiteJSON(), "sqlite"), default=list)

    exercise_days_per_week: Mapped[int] = mapped_column(Integer)
    sleep_hours_per_night: Mapped[int] = mapped_column(Integer)
    stress_level: Mapped[int] = mapped_column(Integer)
    diet_quality: Mapped[str] = mapped_column(String(20), default="", nullable=False)
    water_intake: Mapped[str] = mapped_column(String(20), default="", nullable=False)
    blood_test_status: Mapped[str] = mapped_column(String(50), default="unknown", nullable=False)

    # Output scoring
    score: Mapped[int] = mapped_column(Integer)
    risk_label: Mapped[str] = mapped_column(String(60))
    risk_badge: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(String(2000))

    factors: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON().with_variant(SQLiteJSON(), "sqlite"), default=list
    )
    recommendations: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON().with_variant(SQLiteJSON(), "sqlite"), default=list
    )
    input_json: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(SQLiteJSON(), "sqlite"), default=dict
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    patient: Mapped[Patient] = relationship(back_populates="assessments")

