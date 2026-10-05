"""Calories and macros (engine/nutrition.py): one test per rule, with numbers worked out by hand."""

import pytest

from app.engine.nutrition import bmr_mifflin, body_fat_pct, compute_targets, slide
from app.engine.rules import load_rules
from app.engine.types import Health, Person


def person(**kw) -> Person:
    base = dict(sex="male", age=29, height_cm=180, weight_kg=75, goal="loseFat", pace="steady", experience="intermediate",
                days_per_week=4, session_minutes=60, location="gym", meals_per_day=4, cooking_minutes=30)
    return Person(**(base | kw))


def rules(name):
    return load_rules()[name]


def test_mifflin_st_jeor():
    assert bmr_mifflin("male", 80, 180, 30) == 10 * 80 + 6.25 * 180 - 5 * 30 + 5 == 1780
    assert bmr_mifflin("female", 60, 165, 30) == 10 * 60 + 6.25 * 165 - 5 * 30 - 161 == 1320.25


def test_maintenance_is_bmr_times_the_activity_factor():
    for days, factor in rules("nutrition")["activity"]["factor_by_training_days"].items():
        t = compute_targets(person(days_per_week=days, goal="strength"))
        assert t.maintenance == round(bmr_mifflin("male", 75, 180, 29) * factor / 10) * 10


def test_body_fat_is_estimated_from_bmi_age_and_sex():
    # Deurenberg: 1.20 × BMI + 0.23 × age − 10.8 (men) − 5.4. 75 kg, 180 cm → BMI 23.15 → 27.78 + 6.67 − 10.8 − 5.4 = 18.25
    assert body_fat_pct("male", 75, 180, 29) == pytest.approx(18.25, abs=0.01)
    # 60 kg, 165 cm, 30 years, woman → BMI 22.04 → 26.45 + 6.9 − 5.4 = 27.95
    assert body_fat_pct("female", 60, 165, 30) == pytest.approx(27.95, abs=0.01)
    assert body_fat_pct("male", 50, 190, 18) == rules("nutrition")["body_fat"]["min_pct"]  # very lean: kept at the minimum


def test_slide_is_a_straight_line_flat_outside_its_range():
    assert slide(5, [5, 30], [1.6, 1.2]) == 1.6
    assert slide(17.5, [5, 30], [1.6, 1.2]) == pytest.approx(1.4)
    assert slide(45, [5, 30], [1.6, 1.2]) == 1.2 and slide(2, [5, 30], [1.6, 1.2]) == 1.6


@pytest.mark.parametrize("pace, pct", [("gentle", 10), ("steady", 20), ("faster", 20)])
def test_fat_loss_is_a_percentage_under_maintenance(pace, pct):
    t = compute_targets(person(pace=pace, weight_kg=90))  # about 26% body fat: not "high" for the faster pace
    assert t.calories == pytest.approx(t.maintenance * (1 - pct / 100), abs=10)
    assert f"{pct}% under maintenance" in t.reasons["calories"][-1].en


def test_the_faster_pace_goes_to_25_percent_only_with_high_body_fat():
    # 120 kg at 180 cm, 29 years → about 35% body fat (≥ 25% for men): 25% under maintenance (Table 5A, exception 2).
    t = compute_targets(person(pace="faster", weight_kg=120))
    assert t.calories == pytest.approx(t.maintenance * 0.75, abs=10)


def test_build_muscle_and_strength_are_a_percentage_over_maintenance_by_experience():
    for goal in ("buildMuscle", "strength"):
        for exp, pct in (("beginner", 25), ("intermediate", 15), ("advanced", 10)):
            t = compute_targets(person(goal=goal, experience=exp))
            assert t.calories == pytest.approx(t.maintenance * (1 + pct / 100), abs=10), (goal, exp)


def test_recomp_is_maintenance():
    t = compute_targets(person(goal="recomp"))
    assert abs(t.calories - t.maintenance) <= 10


def test_calorie_floor():
    # 48 kg woman, 150 cm, 60 years, 2 days: maintenance about 1435, 20% under = 1148 → raised to the 1,400 floor.
    t = compute_targets(person(sex="female", age=60, height_cm=150, weight_kg=48, days_per_week=2, pace="faster"))
    assert t.calories == rules("safety")["calorie_floor"]["kcal"]["female"] == 1400
    assert any(r.rule == "safety.calorie_floor" for r in t.reasons["calories"])


def test_never_lose_more_than_the_maximum_weekly_rate():
    # 160 kg man, 190 cm, 25 years, 6 days: maintenance about 4800; 25% under (high body fat) would be 1200 kcal a day
    # = 1.09 kg a week, more than the 0.9 kg cap.
    t = compute_targets(person(age=25, height_cm=190, weight_kg=160, days_per_week=6, pace="faster"))
    assert t.expected_weekly_change_kg >= -rules("safety")["max_weekly_loss"]["max_kg_per_week"] - 0.01
    assert any(r.rule == "safety.max_weekly_loss" for r in t.reasons["calories"])


def test_health_flag_keeps_the_deficit_small():
    t = compute_targets(person(pace="faster", weight_kg=100, health=Health(diabetes=True)))
    assert t.calories >= t.maintenance * (1 - rules("safety")["conservative"]["max_deficit_pct"] / 100) - 10
    assert any(r.rule == "safety.conservative" for r in t.reasons["calories"])
    surplus = compute_targets(person(goal="buildMuscle", experience="beginner", health=Health(heart_condition=True)))
    assert surplus.calories - surplus.maintenance <= rules("safety")["conservative"]["max_surplus_kcal"] + 10


def test_no_deficit_during_or_soon_after_pregnancy():
    t = compute_targets(person(sex="female", height_cm=165, weight_kg=70, health=Health(pregnancy=True)))
    assert t.calories >= t.maintenance - 10
    assert any(r.rule == "safety.pregnancy" for r in t.reasons["calories"])


def test_protein_slides_from_1_6_to_1_2_g_per_pound_of_lean_mass():
    # 75 kg man at about 18.25% body fat: 1.6 − (18.25 − 5) / 25 × 0.4 = 1.39 g per lb of lean mass;
    # lean mass 75 × 0.8175 = 61.3 kg = 135.2 lb → 188 g.
    t = compute_targets(person(weight_kg=75))
    assert t.protein_g == 188
    assert [r.rule for r in t.reasons["protein"]] == ["nutrition.body_fat", "nutrition.protein"]
    # Above 30% body fat (men) it's 1.2 g: 120 kg, about 35% body fat → lean 78.1 kg = 172.1 lb → 207 g.
    heavy = compute_targets(person(weight_kg=120))
    bf = body_fat_pct("male", 120, 180, 29)
    assert heavy.protein_g == round(1.2 * 120 * (1 - bf / 100) / 0.4536)


def test_fat_is_20_to_35_percent_of_calories_by_body_fat():
    # 75 kg man at about 18.25% body fat: 20 + (18.25 − 5) / 20 × 15 = 29.9 → 30% of calories.
    t = compute_targets(person(weight_kg=75))
    assert t.fat_g == round(0.30 * t.calories / 9)
    lean = compute_targets(person(weight_kg=58, height_cm=185))  # about 9.7% body fat → 23.5% → 24%
    assert lean.fat_g == round(0.24 * lean.calories / 9)
    heavy = compute_targets(person(weight_kg=120))  # above 25% body fat (men): 35%
    assert heavy.fat_g == round(0.35 * heavy.calories / 9)


def test_carbs_are_the_remainder_and_macros_add_up():
    for kw in ({}, {"goal": "buildMuscle"}, {"sex": "female", "weight_kg": 55, "height_cm": 160}):
        t = compute_targets(person(**kw))
        assert abs(4 * t.protein_g + 4 * t.carbs_g + 9 * t.fat_g - t.calories) <= 15
        assert t.carbs_g >= rules("nutrition")["carbs"]["min_g"]


def test_every_number_has_a_reason_in_both_languages():
    t = compute_targets(person(health=Health(diabetes=True)))
    for key in ("calories", "protein", "fat", "carbs"):
        assert t.reasons[key], key
        for r in t.reasons[key]:
            assert r.en and r.ar and r.source and r.rule


def test_review_calories_still_go_through_the_safety_bounds():
    t = compute_targets(person(sex="female", weight_kg=55, height_cm=160), calories_override=900)
    assert t.calories >= rules("safety")["calorie_floor"]["kcal"]["female"]
    assert t.expected_weekly_change_kg >= -0.9 - 0.01
    assert {"safety.max_weekly_loss", "safety.calorie_floor"} & {r.rule for r in t.reasons["calories"]}
    assert t.reasons["calories"][-1].rule == "nutrition.goal.final"
