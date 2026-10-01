"""Calories and macros (engine/nutrition.py): one test per rule, with numbers worked out by hand."""

import pytest

from app.engine.nutrition import bmr_mifflin, compute_targets
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


@pytest.mark.parametrize("pace", ["gentle", "steady", "faster"])
def test_fat_loss_deficit_matches_the_pace(pace):
    t = compute_targets(person(pace=pace, weight_kg=90))
    rate = rules("nutrition")["goal"]["loseFat"]["kg_per_week"][pace]
    assert t.expected_weekly_change_kg == pytest.approx(-rate, abs=0.02)


def test_build_muscle_and_strength_add_a_small_surplus():
    for goal in ("buildMuscle", "strength"):
        for exp in ("beginner", "intermediate", "advanced"):
            t = compute_targets(person(goal=goal, experience=exp))
            surplus = rules("nutrition")["goal"][goal]["surplus_kcal"][exp]
            assert abs(t.calories - t.maintenance - surplus) <= 10


def test_recomp_is_a_percentage_below_maintenance():
    t = compute_targets(person(goal="recomp"))
    assert t.calories == pytest.approx(t.maintenance * 0.9, abs=10)


def test_calorie_floor():
    t = compute_targets(person(sex="female", age=60, height_cm=150, weight_kg=48, days_per_week=2, pace="faster"))
    assert t.calories == rules("safety")["calorie_floor"]["kcal"]["female"]
    assert any(r.rule == "safety.calorie_floor" for r in t.reasons["calories"])


def test_never_lose_more_than_the_maximum_weekly_rate():
    # 50 kg × 1% = 0.5 kg a week at most, so "faster" (0.75 kg) is capped.
    t = compute_targets(person(sex="female", age=25, height_cm=170, weight_kg=50, days_per_week=6, pace="faster"))
    assert t.expected_weekly_change_kg >= -0.5 - 0.01
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


def test_protein_per_kg_and_reference_weight_above_bmi_25():
    lean = compute_targets(person(weight_kg=75))  # BMI 23
    assert lean.protein_g == round(2.0 * 75)
    heavy = compute_targets(person(weight_kg=110))  # BMI 34 → protein from the weight at BMI 25 (81 kg)
    assert heavy.protein_g == round(2.0 * 25 * 1.8 ** 2)


def test_fat_is_the_higher_of_the_two_minimums():
    t = compute_targets(person())
    fr = rules("nutrition")["fat"]
    assert t.fat_g == round(max(fr["min_g_per_kg"] * 75, fr["min_pct_of_calories"] / 100 * t.calories / 9))


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
    assert t.expected_weekly_change_kg >= -0.55 - 0.01  # 1% of 55 kg
    assert {"safety.max_weekly_loss", "safety.calorie_floor"} & {r.rule for r in t.reasons["calories"]}
    assert t.reasons["calories"][-1].rule == "nutrition.goal.final"
