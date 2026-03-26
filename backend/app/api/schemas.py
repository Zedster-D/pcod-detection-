from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class FactorOut(BaseModel):
    name: str
    pct: int = Field(ge=0, le=100)


class RecommendationOut(BaseModel):
    icon: str
    title: str
    text: str


class RiskLevelOut(BaseModel):
    label: str
    badge: str


class AssessmentCreateIn(BaseModel):
    # Identity
    name: str = Field(min_length=1, max_length=120)
    age: int = Field(ge=13, le=100)
    heightCm: float = Field(gt=0, le=250)
    weightKg: float = Field(gt=0, le=400)

    # Medical inputs (from the UI)
    cycleRegularity: Literal["regular", "irregular", "absent", "heavy", ""] = ""
    symptoms: list[str] = Field(default_factory=list)

    exerciseDaysPerWeek: int = Field(ge=0, le=7)
    sleepHoursPerNight: int = Field(ge=3, le=10)
    stressLevel: int = Field(ge=1, le=5)
    dietQuality: Literal["poor", "average", "good", "excellent", ""] = ""
    waterIntake: Literal["low", "medium", "high", ""] = ""

    # Doctor/dashboard fields
    familyHistory: list[str] = Field(default_factory=list)
    bloodTestStatus: str = Field(default="unknown", max_length=50)

    # Optional raw payload passthrough for future fields.
    extra: dict[str, Any] = Field(default_factory=dict)


class AssessmentOut(BaseModel):
    assessmentId: UUID
    bmi: float
    score: int = Field(ge=0, le=100)
    level: RiskLevelOut
    description: str
    factors: list[FactorOut]
    recommendations: list[RecommendationOut]


class DoctorPatientOut(BaseModel):
    patientId: UUID
    patientInitials: str
    patientName: str
    age: int
    latestScore: int
    latestBadge: str
    latestCreatedAtIso: str

