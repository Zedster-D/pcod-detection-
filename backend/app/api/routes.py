from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.schemas import (
    AssessmentCreateIn,
    AssessmentOut,
    DoctorPatientOut,
    RiskLevelOut,
)
from app.core.db import get_db
from app.models import Assessment, Patient
from app.services.scoring import score_assessment


router = APIRouter(prefix="/api", tags=["api"])


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


@router.post("/assessments", response_model=AssessmentOut)
def create_assessment(payload: AssessmentCreateIn, db: Session = Depends(get_db)) -> AssessmentOut:
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="`name` is required")

    # Find or create patient (case-insensitive)
    patient_stmt = select(Patient).where(func.lower(Patient.name) == func.lower(name))
    patient = db.execute(patient_stmt).scalars().first()
    if patient is None:
        patient = Patient(name=name)
        db.add(patient)
        db.flush()  # ensures patient.id is available

    bmi, score, level, description, factors, recommendations = score_assessment(payload)

    assessment = Assessment(
        patient_id=patient.id,
        name_at_time=name,
        age=payload.age,
        height_cm=payload.heightCm,
        weight_kg=payload.weightKg,
        bmi=bmi,
        cycle_regularity=payload.cycleRegularity or "",
        symptoms=payload.symptoms or [],
        family_history=payload.familyHistory or [],
        exercise_days_per_week=payload.exerciseDaysPerWeek,
        sleep_hours_per_night=payload.sleepHoursPerNight,
        stress_level=payload.stressLevel,
        diet_quality=payload.dietQuality or "",
        water_intake=payload.waterIntake or "",
        blood_test_status=payload.bloodTestStatus or "unknown",
        score=score,
        risk_label=level.label,
        risk_badge=level.badge,
        description=description,
        factors=[{"name": f.name, "pct": f.pct} for f in factors],
        recommendations=[{"icon": r.icon, "title": r.title, "text": r.text} for r in recommendations],
        input_json=payload.model_dump(),
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)

    return AssessmentOut(
        assessmentId=UUID(assessment.id),
        bmi=assessment.bmi,
        score=assessment.score,
        level=RiskLevelOut(label=assessment.risk_label, badge=assessment.risk_badge),
        description=assessment.description,
        factors=[{"name": f["name"], "pct": f["pct"]} for f in assessment.factors or []],  # type: ignore[arg-type]
        recommendations=[
            {"icon": r["icon"], "title": r["title"], "text": r["text"]}
            for r in assessment.recommendations or []
        ],  # type: ignore[arg-type]
    )


@router.get("/doctor/patients", response_model=list[DoctorPatientOut])
def doctor_patients(db: Session = Depends(get_db)) -> list[DoctorPatientOut]:
    # Simplified: return patients with their latest assessment by created_at.
    latest_subq = (
        select(Assessment.patient_id, func.max(Assessment.created_at).label("max_created_at"))
        .group_by(Assessment.patient_id)
        .subquery()
    )

    q = (
        select(Patient, Assessment)
        .join(Assessment, Assessment.patient_id == Patient.id)
        .join(
            latest_subq,
            (latest_subq.c.patient_id == Assessment.patient_id)
            & (latest_subq.c.max_created_at == Assessment.created_at),
        )
        .order_by(Assessment.created_at.desc())
    )

    rows = db.execute(q).all()
    out: list[DoctorPatientOut] = []
    for patient, assessment in rows:
        initials = "".join([p[0].upper() for p in patient.name.split() if p][:2]) or "P"
        out.append(
            DoctorPatientOut(
                patientId=UUID(patient.id),
                patientInitials=initials,
                patientName=patient.name,
                age=assessment.age,
                latestScore=assessment.score,
                latestBadge=assessment.risk_badge,
                latestCreatedAtIso=_iso(assessment.created_at),
            )
        )
    return out


@router.get("/assessments/{assessment_id}", response_model=AssessmentOut)
def get_assessment(assessment_id: UUID, db: Session = Depends(get_db)) -> AssessmentOut:
    stmt = select(Assessment).where(Assessment.id == str(assessment_id))
    assessment = db.execute(stmt).scalars().first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    return AssessmentOut(
        assessmentId=UUID(assessment.id),
        bmi=assessment.bmi,
        score=assessment.score,
        level=RiskLevelOut(label=assessment.risk_label, badge=assessment.risk_badge),
        description=assessment.description,
        factors=[{"name": f["name"], "pct": f["pct"]} for f in assessment.factors or []],  # type: ignore[arg-type]
        recommendations=[
            {"icon": r["icon"], "title": r["title"], "text": r["text"]}
            for r in assessment.recommendations or []
        ],  # type: ignore[arg-type]
    )

