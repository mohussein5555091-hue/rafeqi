"""The 5 test personas from docs/PLAN.md: each generated plan is checked against the safety bounds.

Readable versions of these plans: docs/personas.md (`npm run personas`).
"""

from functools import lru_cache

import pytest

from app.engine.injuries import allowed
from app.engine.rules import load_rules
from app.engine.training import fits_equipment
from engine_fixtures import exercise_catalogue, recipe_infos
from personas import PERSONAS, run

CAT = exercise_catalogue()
RECIPES = {r.id: r for r in recipe_infos()}
KEYS = list(PERSONAS)


@lru_cache
def plan(key):
    return run(key)


@pytest.mark.parametrize("key", KEYS)
def test_calories_are_within_the_safety_bounds(key):
    r = plan(key)
    p, t = r.person, r.targets
    s = load_rules()["safety"]
    assert t.calories >= s["calorie_floor"]["kcal"][p.sex]
    assert t.expected_weekly_change_kg >= -s["max_weekly_loss"]["pct_of_body_weight"] / 100 * p.weight_kg - 0.01
    if p.conservative:
        assert t.calories >= t.maintenance * (1 - s["conservative"]["max_deficit_pct"] / 100) - 10
        assert t.calories <= t.maintenance + s["conservative"]["max_surplus_kcal"] + 10
    assert abs(4 * t.protein_g + 4 * t.carbs_g + 9 * t.fat_g - t.calories) <= 15


@pytest.mark.parametrize("key", KEYS)
def test_every_number_has_a_reason(key):
    r = plan(key)
    for k in ("calories", "protein", "fat", "carbs"):
        assert r.targets.reasons[k] and all(x.en and x.ar and x.source for x in r.targets.reasons[k])
    for d in r.program.days:
        for e in d.exercises:
            assert e.reasons or not e.start_weight_kg, e.exercise_id
            if e.replaced_exercise_id:
                assert any(x.rule in ("training.injuries", "training.equipment") for x in e.reasons)


@pytest.mark.parametrize("key", KEYS)
def test_meals_hit_calories_and_protein_every_day(key):
    r = plan(key)
    tol = load_rules()["nutrition"]["meals"]["calorie_tolerance_pct"] / 100
    assert not {"protein", "calories"} & set(r.meals.relaxed), r.meals.relaxed
    days = sorted({m.date for m in r.meals.meals})
    assert len(days) == 7
    for d in days:
        tot = r.meals.totals(d)
        assert abs(tot["kcal"] - r.targets.calories) <= r.targets.calories * tol + 5, (d, tot)
        assert tot["protein"] >= r.targets.protein_g - 2, (d, tot)
        assert len(r.meals.day(d)) == r.person.meals_per_day


@pytest.mark.parametrize("key", KEYS)
def test_meals_respect_dislikes_and_allergies(key):
    r = plan(key)
    for m in r.meals.meals:
        assert not RECIPES[m.recipe_id].tags & r.person.avoided_food_tags, m.recipe_id


@pytest.mark.parametrize("key", KEYS)
def test_program_is_safe_for_injuries_and_fits_the_equipment(key):
    r = plan(key)
    for d in r.program.days:
        for e in d.exercises:
            ex = CAT[e.exercise_id]
            assert allowed(ex, r.person.injuries), e.exercise_id
            assert fits_equipment(ex, r.person.location), e.exercise_id
            assert e.start_weight_kg >= 0 and e.sets >= 1


@pytest.mark.parametrize("key", KEYS)
def test_grocery_list_is_generic_and_split_by_shelf_life(key):
    r = plan(key)
    assert r.grocery
    assert all(g.qty > 0 for g in r.grocery)
    assert {g.period for g in r.grocery} == {"week", "month"}


def test_beginner_woman_gets_full_body_at_home():
    r = plan("beginner_woman")
    assert r.program.template_id == "sample_full_body" and r.program.days_per_week == 3
    assert all(not (set(CAT[e.exercise_id].equipment) - {"dumbbells", "bench", "bodyweight", "bands"})
               for d in r.program.days for e in d.exercises)
    assert r.targets.calories < r.targets.maintenance


def test_shoulder_man_has_no_overhead_or_full_range_pressing():
    r = plan("shoulder_man")
    swapped = [e for d in r.program.days for e in d.exercises if e.swap_kind == "swapped"]
    assert {e.replaced_exercise_id for e in swapped} >= {"ex_bb_bench_press", "ex_ohp", "ex_db_shoulder_press", "ex_pull_up"}
    for d in r.program.days:
        for e in d.exercises:
            ex = CAT[e.exercise_id]
            assert ex.rom != "overhead" and not (ex.pattern == "horizontalPush" and ex.rom == "full")


def test_advanced_lifter_trains_5_days_with_a_lighter_knee():
    r = plan("advanced_lifter")
    assert r.program.days_per_week == 5 and r.targets.calories > r.targets.maintenance
    knee = [e for d in r.program.days for e in d.exercises if "knee" in CAT[e.exercise_id].joints]
    assert knee and all(e.load_factor == 0.8 for e in knee)


def test_health_flag_is_conservative_everywhere():
    r = plan("health_flag")
    assert r.person.conservative
    assert any(x.rule == "safety.conservative" for x in r.targets.reasons["calories"])
    for d in r.program.days:
        for e in d.exercises:
            assert e.load_factor <= 0.85 and e.target_rpe <= 7  # template RPE 7-8, one lower
    assert r.targets.protein_g == round(2.0 * 25 * 1.72 ** 2)  # BMI 34: protein from the weight at BMI 25


def test_ramadan_two_meals_are_suhoor_and_iftar():
    r = plan("ramadan_two_meals")
    assert {m.slot for m in r.meals.meals} == {"suhoor", "iftar"}
    assert {m.time for m in r.meals.meals} == {"03:30", "18:00"}


@pytest.mark.parametrize("key", list(PERSONAS))
def test_warm_up_cool_down_cardio_and_session_length(key):
    r = plan(key)
    p = r.person
    week = ["sat", "sun", "mon", "tue", "wed", "thu", "fri"]
    kinds = {d.weekday: d.kind for d in r.program.days}
    for d in r.program.days:
        assert d.warmup["general"]["id"] and 3 <= len(d.warmup["moves"]) <= 4
        assert 4 <= len(d.cooldown["stretches"]) <= 6
        assert d.est_minutes <= p.session_minutes + 15, (key, d.name, d.est_minutes)
        if d.kind == "full":
            assert any(CAT[e.exercise_id].pattern in ("squat", "hinge", "lunge", "kneeExtension", "kneeFlexion") for e in d.exercises), d.name
    assert r.program.cardio.sessions, key
    for s in r.program.cardio.sessions:
        assert kinds.get(week[(week.index(s.weekday) + 1) % 7]) not in ("lower", "full"), (key, s.weekday)
        if p.conservative:
            assert s.intensity == "easy"
    assert any(x.rule == "nutrition.cardio_counted" for x in r.targets.reasons["calories"])
