"""The weekly check-in answers (engine/checkin.py), the weekly review (engine/review.py), and session targets."""

import pytest

from app.engine.checkin import check_answers, red_flags
from app.engine.review import ReviewInput, review_week
from app.engine.types import InjuryInfo, Person
from app.progression import session_target
from app.workouts import ExerciseResult
from engine_fixtures import exercise_catalogue

CAT = exercise_catalogue()
SHOULDER = InjuryInfo(id="inj1", region="shoulderL", painful_movements=("overheadPress",))
GOOD = {"weight_kg": 87.4, "sessions_done": 4, "difficulty": 3, "soreness": 2, "sharp_pain": False, "swelling": False,
        "numbness": False, "adherence_pct": 85, "hunger": 3, "sleep": 4, "energy": 4, "stress": 2, "days_available": 4}
PROGRAM = ("ex_db_floor_press", "ex_cs_row", "ex_lat_pulldown", "ex_bb_squat")


def ask(**answers):
    return GOOD | answers


def review(answers=None, *, this=(87.5, 87.4), last=(88.0, 88.0), expected=-0.5, effort=7.0, previous_pain=None, recipes=(),
           days_since=30):
    p = Person(sex="male", age=29, height_cm=180, weight_kg=88, goal="loseFat", pace="steady", experience="intermediate",
               days_per_week=4, session_minutes=60, location="gym", meals_per_day=4, cooking_minutes=30, injuries=(SHOULDER,))
    return review_week(ReviewInput(person=p, calories=2250, maintenance=2800, expected_weekly_change_kg=expected,
                                   weights_this_week=this, weights_last_week=last, answers=answers or GOOD, avg_effort=effort,
                                   program_exercise_ids=PROGRAM, previous_pain=previous_pain or {}, plan_recipe_ids=frozenset(recipes),
                                   sessions_planned=4, days_since_calorie_change=days_since), CAT)


# ── Check-in answers ──────────────────────────────────────────────────────────
def check(answers):
    return check_answers(answers, sessions_planned=4, injury_ids={"inj1"}, exercise_ids=set(PROGRAM), recipe_ids={"r_koshary"})


def test_good_answers_pass():
    full = ask(waist_cm=94, exercise_feedback=[{"exercise_id": "ex_cs_row", "feel": "tooEasy"}],
               injury_pain=[{"injury_id": "inj1", "pain": 2, "trend": "better"}], new_pain_regions=["kneeL"],
               meals_to_change=["r_koshary"], more_of=["fish"], obstacles=["work"], note="Busy week.")
    assert check(full) == []


@pytest.mark.parametrize("change,problem", [
    ({"weight_kg": 20}, "weight_kg: must be between 30 and 300"),
    ({"sessions_done": 5}, "sessions_done: must be a whole number between 0 and 4"),
    ({"difficulty": 2.5}, "difficulty: must be a whole number"),
    ({"sharp_pain": "no"}, "sharp_pain: must be true or false"),
    ({"note": "x" * 301}, "note: at most 300 characters"),
    ({"meals_to_change": ["r_pizza"]}, "meals_to_change: must be from"),
    ({"exercise_feedback": [{"exercise_id": "ex_ohp", "feel": "tooEasy"}]}, "exercise_feedback"),
    ({"injury_pain": [{"injury_id": "someone_else", "pain": 2, "trend": "same"}]}, "injury_pain"),
    ({"new_pain_regions": ["tail"]}, "unknown body area"),
    ({"chat": "hello coach"}, "chat: not a check-in question"),
])
def test_bad_answers_are_listed(change, problem):
    assert any(problem in p for p in check(ask(**change))), check(ask(**change))


def test_missing_required_answers():
    answers = dict(GOOD)
    del answers["adherence_pct"]
    assert "adherence_pct: required" in check(answers)


def test_red_flag_answers():
    assert red_flags(ask(swelling=True, numbness=True)) == ["swelling", "numbness"]
    assert red_flags(GOOD) == []


# ── Weekly review ─────────────────────────────────────────────────────────────
def test_on_track_week_changes_nothing():
    r = review()
    assert (r.status, r.red_flag, r.calories, r.changes) == ("onTrack", False, None, [])


def test_red_flag_skips_the_normal_review_and_pauses_the_area():
    r = review(ask(sharp_pain=True, adherence_pct=10, injury_pain=[{"injury_id": "inj1", "pain": 3, "trend": "same"}]))
    assert r.red_flag and r.status == "warning" and r.pause_injuries == ["inj1"]
    assert r.calories is None and all(c.kind == "injury" for c in r.changes)
    assert "doctor or physiotherapist" in r.changes[0].why["en"]


def test_worsening_pain_is_a_red_flag():
    r = review(ask(injury_pain=[{"injury_id": "inj1", "pain": 3, "trend": "worse"}]))
    assert r.red_flag and r.pause_injuries == ["inj1"]


# Steps follow the recomposition guide (ch. 6): 100-250 kcal down or 100-500 kcal up, sized by the gap between the
# planned and actual weekly change (1 kg a week ≈ 7,700 / 7 = 1,100 kcal a day).

def test_losing_too_fast_adds_calories():
    r = review(this=(86.6,), last=(88.0,))  # −1.4 kg vs −0.5 planned: 0.9 kg gap = 990 kcal → the book's maximum, +500
    assert r.calories == 2750 and r.changes[0].kind == "calories"


def test_losing_too_slowly_removes_calories_when_meals_were_followed():
    r = review(this=(88.0,), last=(88.0,))  # 0 vs −0.5 planned: 550 kcal → the book's maximum, −250
    assert r.calories == 2000


def test_a_small_gap_still_moves_at_least_100_kcal():
    r = review(this=(87.82,), last=(88.0,), expected=-0.1)  # −0.18 vs −0.1: not "too fast" (1.5 × 0.1 + 0.2 noise)
    assert r.calories is None
    r = review(this=(88.0,), last=(88.0,), expected=-0.06)  # 0 vs −0.06: 66 kcal → the book's minimum, −100
    assert r.calories == 2150


def test_calories_wait_two_weeks_between_changes():
    r = review(this=(88.0,), last=(88.0,), days_since=7)
    assert r.calories is None and r.status == "onTrack"
    assert "every 2 weeks" in r.changes[0].why["en"] and "7 days" in r.changes[0].why["en"]
    assert review(this=(88.0,), last=(88.0,), days_since=14).calories == 2000


def test_low_adherence_keeps_calories():
    r = review(ask(adherence_pct=50), this=(88.0,), last=(88.0,))
    assert r.calories is None and r.status == "attention" and "50%" in r.changes[0].why["en"]


def test_gaining_goal_works_the_other_way():
    r = review(this=(70.0,), last=(70.0,), expected=0.25)  # 0 vs +0.25 planned: 275 kcal → +280
    assert r.calories == 2530


def test_deload_when_sessions_were_too_hard():
    assert review(ask(difficulty=5, soreness=4)).deload
    assert review(ask(difficulty=5), effort=9.5).deload
    assert not review(ask(difficulty=5)).deload  # one signal isn't enough


def test_exercise_feedback():
    r = review(ask(exercise_feedback=[{"exercise_id": "ex_cs_row", "feel": "tooEasy"}, {"exercise_id": "ex_bb_squat", "feel": "tooHard"},
                                      {"exercise_id": "ex_lat_pulldown", "feel": "uncomfortable"}]))
    assert r.weight_offsets == {"ex_cs_row": 2, "ex_bb_squat": -2.5}
    assert r.avoid_exercises == {"ex_lat_pulldown"}


def test_pain_going_up_lightens_the_area():
    r = review(ask(injury_pain=[{"injury_id": "inj1", "pain": 4, "trend": "same"}]), previous_pain={"inj1": 2})
    assert r.injury_factors == {"inj1": 0.9} and r.status == "attention" and not r.red_flag


def test_meals_to_change_are_replaced():
    r = review(ask(meals_to_change=["r_koshary"]), recipes=("r_koshary", "r_ful_eggs"))
    assert r.ban_recipes == {"r_koshary"} and r.changes[-1].kind == "meals"


def test_few_sessions_needs_attention():
    assert review(ask(sessions_done=1)).status == "attention"


# ── Targets across plan versions ──────────────────────────────────────────────
def test_first_session_ever_uses_the_start_weight():
    t = session_target(3, "8–10", 2, 20, None, last_in_this_program=False, weight_offset_kg=2)
    assert (t.reps, t.weight_kg) == (8, 22)


def test_a_new_version_applies_its_changes_once():
    last = ExerciseResult(sets=3, reps=10, weight_kg=40, struggled=False)
    # Last time hit the top of 8–10 → progression says 42.5 kg; pain went up so this version is at 90%:
    # 42.5 × 0.9 = 38.25 → rounded down to the 2.5 kg step = 37.5 kg, once.
    first = session_target(3, "8–10", 2.5, 30, last, last_in_this_program=False, load_ratio=0.9)
    assert (first.reps, first.weight_kg) == (8, 37.5)
    # After a session in this version, progression continues from the log; the 90% isn't applied again.
    logged = ExerciseResult(sets=3, reps=8, weight_kg=37.5, struggled=False)
    assert session_target(3, "8–10", 2.5, 30, logged, last_in_this_program=True, load_ratio=0.9).weight_kg == 37.5
    # "Too easy" last week: one step more for the next session only.
    assert session_target(3, "8–10", 2.5, 30, logged, last_in_this_program=False, weight_offset_kg=2.5).weight_kg == 40.0
    # Nothing changed in the new version: plain progression.
    assert session_target(3, "8–10", 2.5, 30, logged, last_in_this_program=False).weight_kg == 37.5
