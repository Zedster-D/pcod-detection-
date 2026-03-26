from __future__ import annotations

import math
import os
import joblib
import numpy as np

from app.api.schemas import AssessmentCreateIn, FactorOut, RecommendationOut, RiskLevelOut


# ==============================
# LOAD ML MODEL
# ==============================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
model = joblib.load(os.path.join(BASE_DIR, "pcos_model.pkl"))
scaler = joblib.load(os.path.join(BASE_DIR, "scaler.pkl"))


# ==============================
# UTILITY FUNCTIONS
# ==============================
def clamp_int(v: float | int, lo: int = 0, hi: int = 100) -> int:
    return max(lo, min(hi, int(round(v))))


def calc_bmi(height_cm: float, weight_kg: float) -> float:
    h_m = height_cm / 100.0
    if h_m <= 0:
        return 0.0
    return weight_kg / (h_m * h_m)


def risk_level_from_score(score: int) -> RiskLevelOut:
    if score <= 35:
        return RiskLevelOut(label="Low", badge="Low Risk")
    if score <= 60:
        return RiskLevelOut(label="Moderate", badge="Moderate Risk")
    if score <= 80:
        return RiskLevelOut(label="Moderate-High", badge="Moderate-High Risk")
    return RiskLevelOut(label="High", badge="High Risk")


def description_from_level(level: RiskLevelOut, score: int) -> str:
    if level.label == "Low":
        return "Lower PCOS risk signal based on current inputs. Maintain healthy habits."
    if level.label == "Moderate":
        return "Some PCOS risk indicators detected. Lifestyle changes may help reduce risk."
    if level.label == "Moderate-High":
        return "Multiple PCOS indicators found. Early action is recommended."
    return "High PCOS risk signal detected. Consider consulting a healthcare professional."


# ==============================
# RULE-BASED SCORING
# ==============================
def compute_factors_and_score(payload: AssessmentCreateIn) -> tuple[int, list[FactorOut]]:
    bmi = calc_bmi(payload.heightCm, payload.weightKg)

    cycle_points = 25 if payload.cycleRegularity == "irregular" else 5
    cramps_points = {"none": 0, "mild": 5, "moderate": 12, "severe": 20}.get(payload.crampsSeverity, 0)

    symptoms = payload.symptoms or []
    hormonal_points = len(symptoms) * 6

    bmi_points = 10 if bmi < 25 else 25 if bmi < 30 else 40

    family_points = 10 if payload.familyHistory else 0

    exercise_points = (7 - payload.exerciseDaysPerWeek) * 2
    sleep_points = max(0, (7 - payload.sleepHoursPerNight) * 8)
    stress_points = payload.stressLevel * 5

    raw = 20 + cycle_points + cramps_points + hormonal_points + bmi_points + family_points
    raw += exercise_points + sleep_points + stress_points

    score = clamp_int(raw * 0.8)

    factors = [
        FactorOut(name="Cycle irregularity", pct=clamp_int(cycle_points * 2)),
        FactorOut(name="Hormonal symptoms", pct=clamp_int(hormonal_points)),
        FactorOut(name="BMI / Weight", pct=clamp_int(bmi_points)),
        FactorOut(name="Family history", pct=clamp_int(family_points * 3)),
        FactorOut(name="Sleep quality", pct=clamp_int(sleep_points)),
        FactorOut(name="Stress levels", pct=clamp_int(stress_points)),
    ]

    return score, factors


# ==============================
# RECOMMENDATIONS
# ==============================
def build_recommendations(payload: AssessmentCreateIn, level: RiskLevelOut) -> list[RecommendationOut]:
    recs = [
        RecommendationOut(icon="🥗", title="Healthy Diet", text="Reduce sugar, eat balanced meals."),
        RecommendationOut(icon="🏃", title="Exercise", text="Exercise regularly."),
        RecommendationOut(icon="😴", title="Sleep", text="Maintain 7-8 hours sleep."),
        RecommendationOut(icon="🧘", title="Stress", text="Manage stress effectively."),
    ]

    if level.label in ("Moderate-High", "High"):
        recs.append(
            RecommendationOut(
                icon="🩺",
                title="Consult Doctor",
                text="Seek medical advice for proper diagnosis."
            )
        )

    return recs


# ==============================
# MAIN FUNCTION (HYBRID AI)
# ==============================
def score_assessment(payload: AssessmentCreateIn):

    # Rule-based score
    bmi = calc_bmi(payload.heightCm, payload.weightKg)
    rule_score, factors = compute_factors_and_score(payload)

    # ==============================
    # ML PREDICTION
    # ==============================
    features = [
        payload.age,
        payload.weightKg,
        payload.heightCm,
        payload.exerciseDaysPerWeek,
        payload.sleepHoursPerNight,
        payload.stressLevel
    ]

    arr = np.array(features).reshape(1, -1)

    # Padding to match model features
    total_features = model.n_features_in_
    if arr.shape[1] < total_features:
        padding = np.zeros((1, total_features - arr.shape[1]))
        arr = np.hstack((arr, padding))

    scaled = scaler.transform(arr)
    ml_prob = model.predict_proba(scaled)[0][1] * 100

    # ==============================
    # COMBINE SCORES
    # ==============================
    final_score = int((0.85 * rule_score) + (0.15 * ml_prob))

    level = risk_level_from_score(final_score)
    description = f"AI + Clinical Risk Score: {final_score}%"

    recommendations = build_recommendations(payload, level)

    return round(bmi, 1), final_score, level, description, factors, recommendations