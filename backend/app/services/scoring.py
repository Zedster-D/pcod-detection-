from __future__ import annotations

import math
from typing import Any

from app.api.schemas import AssessmentCreateIn, FactorOut, RecommendationOut, RiskLevelOut


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
    # Not medical advice; this is a risk signal.
    if level.label == "Low":
        return (
            "Your responses suggest a lower PCOS risk signal. "
            "Lifestyle still matters—small changes can help maintain hormonal balance over time. "
            "This is not a diagnosis."
        )
    if level.label == "Moderate":
        return (
            "Your profile suggests some PCOS risk signals. Early awareness and lifestyle management "
            "may improve symptoms or reduce future risk. This is not a diagnosis."
        )
    if level.label == "Moderate-High":
        return (
            "Your profile shows several PCOS indicators—particularly around cycle patterns and related "
            "health markers. Early action now can significantly reduce long-term risk. This is not a diagnosis."
        )
    return (
        "Your responses suggest a higher PCOS risk signal. Consider discussing your results with a healthcare "
        "professional for appropriate evaluation. This is not a diagnosis."
    )


def compute_factors_and_score(payload: AssessmentCreateIn) -> tuple[int, list[FactorOut]]:
    bmi = calc_bmi(payload.heightCm, payload.weightKg)

    # Cycle regularity
    cycle_points = 0.0
    if payload.cycleRegularity == "regular":
        cycle_points = 5
    elif payload.cycleRegularity == "irregular":
        cycle_points = 25
    elif payload.cycleRegularity == "absent":
        cycle_points = 40
    elif payload.cycleRegularity == "heavy":
        cycle_points = 35

    # Symptom mapping (these are heuristics to match the UI concept)
    symptoms = payload.symptoms or []
    hormonal_symptoms = [
        "Acne",
        "oily skin",
        "Excess facial hair",
        "hair thinning",
        "Mood swings",
        "Fertility concerns",
    ]
    metabolic_symptoms = ["Sugar cravings", "Weight gain"]
    neuro_symptoms = ["Fatigue", "Brain fog", "Sleep issues"]

    hormonal_points = 0.0
    metabolic_points = 0.0
    neuro_points = 0.0
    for s in symptoms:
        sl = s.lower()
        # Simple keyword checks:
        if any(
            k.lower() in sl
            for k in ["acne", "oily", "excess facial hair", "hair thinning", "mood swings", "fertility"]
        ):
            hormonal_points += 6
        elif any(k.lower() in sl for k in ["sugar cravings", "weight gain"]):
            metabolic_points += 6
        elif any(k.lower() in sl for k in ["fatigue", "brain fog", "sleep issues"]):
            neuro_points += 5

    # BMI / Weight points
    # Rough heuristic: normal 0, overweight +, obesity +++
    if bmi < 18.5:
        bmi_points = 5
    elif bmi < 25:
        bmi_points = 10
    elif bmi < 30:
        bmi_points = 25
    else:
        bmi_points = 40

    # Family history points
    family_points = 0.0
    family = " ".join(payload.familyHistory or []).lower()
    if "mother had pcos" in family or "pcos" in family:
        family_points += 20
    if "family diabetes" in family or "diabetes" in family:
        family_points += 12
    if "thyroid" in family:
        family_points += 8
    if "heart disease" in family:
        family_points += 6
    if "obesity" in family:
        family_points += 8

    # Lifestyle: exercise (lower = worse), sleep (low = worse), stress (high = worse)
    exercise_points = (7 - payload.exerciseDaysPerWeek) * 2.2  # 0..14-ish
    sleep_points = max(0.0, (7.5 - payload.sleepHoursPerNight) * 8.0)  # only penalize below target
    stress_points = (payload.stressLevel - 1) * 5.0  # 0..20

    # Diet & water add to overall score (but factors in UI are limited to 6, so we fold into overall)
    diet_points = 0.0
    if payload.dietQuality == "poor":
        diet_points = 18
    elif payload.dietQuality == "average":
        diet_points = 10
    elif payload.dietQuality == "good":
        diet_points = 6
    elif payload.dietQuality == "excellent":
        diet_points = 2

    water_points = 0.0
    if payload.waterIntake == "low":
        water_points = 10
    elif payload.waterIntake == "medium":
        water_points = 5
    elif payload.waterIntake == "high":
        water_points = 1

    # Total score
    # Keep baseline so scores aren't always 0 for sparse answers.
    raw = 20 + cycle_points + hormonal_points + metabolic_points + neuro_points + bmi_points + family_points
    raw += exercise_points + sleep_points + stress_points + diet_points + water_points

    # Cap/normalize
    score = clamp_int(math.floor(raw * 0.8), 0, 100)

    # Factors: we want them to feel like your UI (percent-like contribution bars)
    max_cycle = 40
    max_hormonal = max(1.0, len(symptoms) * 6.0)  # proportional to selections
    max_bmi = 40
    max_family = 32
    max_sleep = 20
    max_stress = 20

    cycle_pct = clamp_int(cycle_points / max_cycle * 100)
    # Use hormonal_points mostly; clamp to 0..100
    hormonal_pct = clamp_int((hormonal_points / max_hormonal) * 100)
    bmi_pct = clamp_int(bmi_points / max_bmi * 100)
    family_pct = clamp_int(family_points / max_family * 100)
    # sleep_quality and stress_levels use the inverse/penalties: higher penalty => higher risk => higher bar
    sleep_quality_pct = clamp_int((sleep_points / max_sleep) * 100)
    stress_pct = clamp_int((stress_points / max_stress) * 100)

    factors = [
        FactorOut(name="Cycle irregularity", pct=cycle_pct),
        FactorOut(name="Hormonal symptoms", pct=hormonal_pct),
        FactorOut(name="BMI / Weight", pct=bmi_pct),
        FactorOut(name="Family history", pct=family_pct),
        FactorOut(name="Sleep quality", pct=sleep_quality_pct),
        FactorOut(name="Stress levels", pct=stress_pct),
    ]
    return score, factors


def build_recommendations(payload: AssessmentCreateIn, level: RiskLevelOut) -> list[RecommendationOut]:
    diet = payload.dietQuality
    exercise = payload.exerciseDaysPerWeek
    sleep = payload.sleepHoursPerNight
    stress = payload.stressLevel

    recs: list[RecommendationOut] = []

    # These match your UI card titles/icons, but the text can vary slightly.
    recs.append(
        RecommendationOut(
            icon="🥗",
            title="Anti-inflammatory Diet",
            text=(
                "Reduce sugar & refined carbs. Add leafy greens, berries, and omega-3s. "
                "Try a low-GI meal plan."
                if diet in ("poor", "average", "")
                else "Keep plant-rich, minimal sugar intake. Aim for steady low-GI meals and adequate protein."
            ),
        )
    )
    recs.append(
        RecommendationOut(
            icon="🏃‍♀️",
            title="Move Daily",
            text=(
                "Start with 30 min of moderate movement 4–5×/week. Include walking plus 2 short strength sessions."
                if exercise < 3
                else "You’re already fairly active. Keep 30+ min moderate exercise most days and add strength work to support insulin sensitivity."
            ),
        )
    )
    recs.append(
        RecommendationOut(
            icon="😴",
            title="Prioritize Sleep",
            text=(
                "Aim for 7–9 hours. If sleep is short, create a consistent bedtime and reduce late screen time."
                if sleep < 7
                else "Your sleep is closer to target. Keep consistent timing and protect a wind-down routine."
            ),
        )
    )
    recs.append(
        RecommendationOut(
            icon="🧘",
            title="Stress Management",
            text=(
                "High cortisol can worsen symptoms. Try 10 minutes of mindfulness or breathing daily, especially on stressful days."
                if stress >= 4
                else "Maintain stress support with short daily practices (mindfulness, walking, or stretching) to steady your cycle signals."
            ),
        )
    )

    # Optionally tweak text if high risk
    if level.label in ("Moderate-High", "High"):
        recs.append(
            RecommendationOut(
                icon="🩺",
                title="Next Steps",
                text=(
                    "If symptoms persist, consider discussing with a gynecologist or endocrinologist. "
                    "Ask about PCOS-related evaluation and a personalized plan."
                ),
            )
        )

    return recs


def score_assessment(payload: AssessmentCreateIn) -> tuple[
    float, int, RiskLevelOut, str, list[FactorOut], list[RecommendationOut]
]:
    bmi = calc_bmi(payload.heightCm, payload.weightKg)
    score, factors = compute_factors_and_score(payload)
    level = risk_level_from_score(score)
    description = description_from_level(level, score)
    recommendations = build_recommendations(payload, level)

    return round(bmi, 1), score, level, description, factors, recommendations

