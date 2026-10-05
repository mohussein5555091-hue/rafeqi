"""Swapping exercises (just today / from now on / missing equipment / undo), cardio days marked done, and the warm-up
and cool-down sections with their ticks, through the API.

The test clock is Monday 2026-09-28. The onboarding answers (intermediate, 4 days, gym, losing fat, left shoulder)
give Upper/Lower on Sat, Mon, Wed, Thu, and 3 cardio sessions: after lifting on Saturday, and Tuesday and Friday.
"""

from sqlalchemy import select

from app.catalogue import read_exercises
from app.config import get_settings
from app.engine.injuries import allowed
from app.engine.types import ExerciseInfo, InjuryInfo
from app.models import Profile
from app.vocab import get_vocab
from test_plans import catalogue, onboarded  # noqa: F401 (fixtures)
from test_screens_api import checkin_body, lifting, planned, today_session, week  # noqa: F401 (fixtures)

EXERCISES = {e["id"]: e for e in read_exercises(get_settings().catalogue_dir / "exercises.yaml", get_vocab())}


def program_ids(c) -> set[str]:
    return {e["exerciseId"] for d in c.get("/api/plan").json()["program"]["days"] for e in d["exercises"]}


def alt(c, s, ex_id, reason="busy"):
    r = c.get(f"/api/workouts/{s['id']}/exercises/{ex_id}/alternatives", params={"reason": reason})
    assert r.status_code == 200, r.text
    return r.json()


def swap(c, s, ex_id, to, reason="busy", scope="today"):
    r = c.post(f"/api/workouts/{s['id']}/exercises/{ex_id}/swap", json={"toExerciseId": to, "reason": reason, "scope": scope})
    assert r.status_code == 200, r.text
    return r.json()


# ── Cardio ──

def test_week_has_cardio_days_and_a_step_target(planned):  # noqa: F811
    w = week(planned.client)
    cardio_days = [s for s in w["sessions"] if s["kind"] == "cardio"]
    assert [s["day"] for s in cardio_days] == ["tue", "fri"]
    assert all(s["id"].startswith("cardio-") and s["cardio"]["intensity"] == "easy" for s in cardio_days)
    sat = next(s for s in w["sessions"] if s["day"] == "sat")
    assert sat["kind"] == "strength" and sat["cardio"]["when"] == "afterLifting"
    assert w["cardio"]["sessionsPerWeek"] == 3 and w["cardio"]["stepsPerDay"] == 8000
    assert "Cardio" in w["cardio"]["why"]["en"] and w["cardio"]["why"]["ar"]
    reasons = planned.client.get("/api/plan").json()["reasons"]
    assert any("aren't added again" in r["en"] for r in reasons["calories"])  # counted once, and the plan says so


def test_cardio_is_marked_done_with_minutes(planned):  # noqa: F811
    c = planned.client
    assert c.put("/api/cardio/sat", json={"minutes": 25}).status_code == 204
    assert next(s for s in week(c)["sessions"] if s["day"] == "sat")["cardio"]["done"] == {"minutes": 25}
    assert c.put("/api/cardio/tue", json={"minutes": 20}).status_code == 409  # Tuesday hasn't come yet
    assert c.put("/api/cardio/sun", json={"minutes": 20}).status_code == 404  # no cardio on Sunday
    assert c.put("/api/cardio/sat", json={"minutes": 0}).status_code == 422
    assert c.get("/api/cardio/tue").json()["status"] == "planned"
    assert c.delete("/api/cardio/sat").status_code == 204
    assert "done" not in next(s for s in week(c)["sessions"] if s["day"] == "sat")["cardio"]


# ── Warm-up and cool-down ──

def test_warm_up_and_cool_down_sections(planned):  # noqa: F811
    c = planned.client
    s = today_session(c)
    w, cd = s["warmup"], s["cooldown"]
    assert w["general"] == {"exerciseId": "ex_bike", "minutes": 5}
    assert 3 <= len(w["moves"]) <= 4 and all(m["amount"]["ar"] for m in w["moves"])
    first = next(e for e in s["exercises"] if e["target"]["weightKg"] > 0)
    ramp = w["rampUp"]
    assert ramp["exerciseId"] == first["exerciseId"]
    assert 2 <= len(ramp["sets"]) <= 3 and all(x["weightKg"] < first["target"]["weightKg"] for x in ramp["sets"])
    assert 4 <= len(cd["stretches"]) <= 6 and cd["breathing"]["exerciseId"] == "ex_slow_breathing"
    assert (w["done"], cd["done"]) == (False, False)
    assert c.put(f"/api/workouts/{s['id']}/warmup", json={"done": True}).status_code == 204
    assert c.put(f"/api/workouts/{s['id']}/cooldown", json={"done": True}).status_code == 204
    again = c.get(f"/api/workouts/{s['id']}").json()
    assert (again["warmup"]["done"], again["cooldown"]["done"]) == (True, True)
    later = next(x for x in lifting(c) if x["status"] == "planned")
    assert c.put(f"/api/workouts/{later['id']}/warmup", json={"done": True}).status_code == 409


def test_warm_up_moves_and_stretches_have_how_to_pages(planned):  # noqa: F811
    c = planned.client
    s = today_session(c)
    ids = [s["warmup"]["general"]["exerciseId"], *[m["exerciseId"] for m in s["warmup"]["moves"]],
           *[x["exerciseId"] for x in s["cooldown"]["stretches"]], s["cooldown"]["breathing"]["exerciseId"]]
    for i in ids:
        ex = c.get(f"/api/exercises/{i}").json()
        assert ex["type"] in ("cardio", "mobility", "stretch", "strength")
        assert ex["imageUrl"] and ex["videoUrl"] and len(ex["instructions"]) >= 3 and 3 <= len(ex["cues"]) <= 5


# ── Swaps ──

def test_alternatives_fit_the_movement_and_the_injury(planned):  # noqa: F811
    c = planned.client
    shoulder = c.get("/api/injuries").json()[0]
    inj = InjuryInfo(shoulder["id"], shoulder["region"], painful_movements=tuple(shoulder["painfulMovements"]),
                     restrictions=tuple(shoulder["restrictions"]))
    vocab = get_vocab()
    for s in lifting(c):
        in_session = {e["exerciseId"] for e in s["exercises"]}
        for e in s["exercises"]:
            alts = alt(c, s, e["exerciseId"], "cantDo")
            assert len(alts) <= 4
            for a in alts:
                x = EXERCISES[a["exerciseId"]]
                info = ExerciseInfo(x["id"], x["name"], x["movement_pattern"], tuple(x["joints_loaded"]), x["range_of_motion"],
                                    tuple(x["equipment"]), x["difficulty"])
                assert allowed(info, (inj,), vocab), (e["exerciseId"], a["exerciseId"])
                assert a["exerciseId"] not in in_session and a["imageUrl"] and a["target"]["sets"] > 0


def test_swap_just_today_changes_only_this_session(planned, clock):  # noqa: F811
    c = planned.client
    s = today_session(c)
    original = s["exercises"][0]["exerciseId"]
    plan_before = c.get("/api/plan").json()["id"]
    to = alt(c, s, original)[0]["exerciseId"]
    out = swap(c, s, original, to, "busy", "today")
    assert out["workoutId"] == s["id"]
    now = c.get(f"/api/workouts/{s['id']}").json()
    first = now["exercises"][0]
    assert first["exerciseId"] == to and original not in [e["exerciseId"] for e in now["exercises"]]
    assert first["swap"]["scope"] == "today" and first["swap"]["why"]["en"] == "machine busy"
    assert first["target"]["reason"] == "findWeight"  # a new exercise starts as "find your weight"
    # Logging the new exercise works, and the plan itself didn't change.
    assert c.put(f"/api/workouts/{s['id']}/exercises/{to}", json={"sets": 3, "reps": 8, "weightKg": 20}).status_code == 204
    assert c.get("/api/plan").json()["id"] == plan_before
    clock.advance(days=7)  # next Monday: the program's exercise is back
    assert today_session(c)["exercises"][0]["exerciseId"] == original


def test_swap_from_now_on_changes_every_future_week(planned, clock):  # noqa: F811
    c = planned.client
    s = today_session(c)
    original = s["exercises"][0]["exerciseId"]
    meals_before = [m["recipeId"] for m in c.get("/api/meals/day/today").json()["meals"]]
    to = alt(c, s, original, "cantDo")[0]["exerciseId"]
    out = swap(c, s, original, to, "cantDo", "always")
    now = c.get(f"/api/workouts/{out['workoutId']}").json()
    assert now["exercises"][0]["exerciseId"] == to and now["exercises"][0]["swap"]["scope"] == "always"
    assert original not in program_ids(c) and to in program_ids(c)
    assert [m["recipeId"] for m in c.get("/api/meals/day/today").json()["meals"]] == meals_before  # meals untouched
    # Next week, after the weekly review, and after "regenerate my plan": still swapped, never put back.
    clock.advance(days=3)
    _, body = checkin_body(c)
    assert c.post("/api/checkins", json=body).status_code == 201
    assert original not in program_ids(c) and to in program_ids(c)
    assert c.post("/api/plan").status_code == 200
    assert original not in program_ids(c) and to in program_ids(c)
    clock.advance(days=4)
    assert today_session(c)["exercises"][0]["exerciseId"] == to


def test_undo_a_from_now_on_swap(planned):  # noqa: F811
    c = planned.client
    s = today_session(c)
    original = s["exercises"][0]["exerciseId"]
    to = alt(c, s, original)[0]["exerciseId"]
    swap(c, s, original, to, "busy", "always")
    swaps = c.get("/api/swaps").json()
    assert [(x["fromExerciseId"], x["toExerciseId"]) for x in swaps] == [(original, to)]
    assert c.delete(f"/api/swaps/{swaps[0]['id']}").status_code == 204
    assert c.get("/api/swaps").json() == []
    assert original in program_ids(c)


def test_equipment_not_available_is_remembered_and_never_used(planned, db):  # noqa: F811
    c = planned.client
    s = today_session(c)  # Monday: lower body, with the leg press (a machine)
    leg_press = next(e for e in s["exercises"] if e["exerciseId"] == "ex_leg_press")
    alts = alt(c, s, leg_press["exerciseId"], "equipment")
    assert alts and all("machine" not in EXERCISES[a["exerciseId"]]["equipment"] for a in alts)
    swap(c, s, leg_press["exerciseId"], alts[0]["exerciseId"], "equipment", "today")
    db.expire_all()
    assert db.scalar(select(Profile.missing_equipment).where(Profile.user_id == planned.id)) == ["machine"]
    badge = next(e for e in c.get(f"/api/workouts/{s['id']}").json()["exercises"] if e["exerciseId"] == alts[0]["exerciseId"])
    assert badge["swap"]["why"]["en"] == "no machine"
    assert c.post("/api/plan").status_code == 200  # a regenerated plan avoids it everywhere
    plan = c.get("/api/plan").json()
    for i in program_ids(c):
        assert "machine" not in EXERCISES[i]["equipment"], i
    for w in lifting(c):
        assert "machine" not in EXERCISES[w["warmup"]["general"]["exerciseId"]]["equipment"]
    assert all("machine" not in EXERCISES[x["exerciseId"]]["equipment"] for x in plan["program"].get("cardio", {}).get("sessions", []))


def test_swap_must_be_one_of_the_alternatives(planned):  # noqa: F811
    c = planned.client
    s = today_session(c)
    ex = s["exercises"][0]["exerciseId"]
    r = c.post(f"/api/workouts/{s['id']}/exercises/{ex}/swap", json={"toExerciseId": "ex_ohp", "reason": "pain", "scope": "today"})
    assert r.status_code == 422  # overhead press: not an alternative, and the shoulder injury rules it out
    r = c.post(f"/api/workouts/{s['id']}/exercises/{ex}/swap", json={"toExerciseId": "ex_cs_row", "reason": "bored", "scope": "today"})
    assert r.status_code == 422


def test_pain_swap_is_saved_like_the_others(planned):  # noqa: F811
    c = planned.client
    s = today_session(c)
    ex = s["exercises"][1]["exerciseId"]
    to = alt(c, s, ex, "pain")[0]["exerciseId"]
    swap(c, s, ex, to, "pain", "today")
    e = next(x for x in c.get(f"/api/workouts/{s['id']}").json()["exercises"] if x["exerciseId"] == to)
    assert e["swap"]["reason"] == "pain" and e["swap"]["why"]["en"] == "it caused pain"


# ── Bug reports: swapping and regenerating on a fresh account; past sessions are locked ──

def test_fresh_account_swaps_for_every_reason_then_regenerates(make_user, catalogue):  # noqa: F811
    """A brand-new account (beginner, full body) can swap for every reason, "just today" and "from now on", and then
    regenerate its plan: every call succeeds and the swap is kept."""
    from test_onboarding import TRAINING, answer_all

    u = make_user()
    c = u.client
    answer_all(c, training=TRAINING | {"experience": "beginner", "daysPerWeek": 3}, injuries={"injuries": []})
    assert c.post("/api/onboarding/complete").status_code == 200
    assert c.post("/api/plan").status_code == 200
    for reason in ("busy", "cantDo", "pain", "equipment"):
        s = next(x for x in lifting(c) if x["status"] in ("today", "planned"))
        ex = s["exercises"][0]["exerciseId"]
        options = alt(c, s, ex, reason)
        assert options, reason
        swap(c, s, ex, options[0]["exerciseId"], reason, "today")
        s = next(x for x in lifting(c) if x["day"] == s["day"])
        ex = s["exercises"][1]["exerciseId"]
        to = alt(c, s, ex, reason)[0]["exerciseId"]
        swap(c, s, ex, to, reason, "always")
        assert to in program_ids(c)
    r = c.post("/api/plan")
    assert r.status_code == 200, r.text
    assert to in program_ids(c)  # the last "from now on" swap (each one replaced the one before in that slot) is kept
    assert [x["toExerciseId"] for x in c.get("/api/swaps").json()] == [to]


def test_past_and_finished_sessions_cannot_be_swapped(planned):  # noqa: F811
    c = planned.client  # Monday: Saturday's session is over
    sat = next(s for s in lifting(c) if s["day"] == "sat")
    assert sat["status"] == "missed"
    ex, to = next((e["exerciseId"], a[0]["exerciseId"]) for e in sat["exercises"] if (a := alt(c, sat, e["exerciseId"])))
    for scope in ("today", "always"):
        r = c.post(f"/api/workouts/{sat['id']}/exercises/{ex}/swap", json={"toExerciseId": to, "reason": "busy", "scope": scope})
        assert (r.status_code, r.json()["detail"]) == (409, "session_is_over")
    today = today_session(c)
    assert c.post(f"/api/workouts/{today['id']}/finish", json={"effort": 7}).status_code == 200
    ex, to = next((e["exerciseId"], a[0]["exerciseId"]) for e in today["exercises"] if (a := alt(c, today, e["exerciseId"])))
    r = c.post(f"/api/workouts/{today['id']}/exercises/{ex}/swap", json={"toExerciseId": to, "reason": "busy", "scope": "today"})
    assert r.status_code == 409


# ── Missing equipment, editable in Profile & settings ──

def test_missing_equipment_can_be_seen_and_changed(planned, db):  # noqa: F811
    c = planned.client
    eq = c.get("/api/me/equipment").json()
    assert eq["location"] == "gym" and all(i["available"] for i in eq["items"])
    assert {"machine", "cable", "barbell"} <= {i["id"] for i in eq["items"]} and "bodyweight" not in {i["id"] for i in eq["items"]}
    assert next(i for i in eq["items"] if i["id"] == "machine")["name"] == {"en": "Machine", "ar": "جهاز"}
    out = c.put("/api/me/equipment", json={"missing": ["machine"]}).json()
    assert not next(i for i in out["items"] if i["id"] == "machine")["available"]
    assert all("machine" not in EXERCISES[i]["equipment"] for i in program_ids(c))  # the plan was rebuilt without it
    assert c.put("/api/me/equipment", json={"missing": ["spaceship"]}).status_code == 422
    assert c.put("/api/me/equipment", json={"missing": []}).status_code == 200
    assert "ex_leg_press" in program_ids(c)  # back again


def test_equipment_back_ends_the_swaps_it_caused(planned):  # noqa: F811
    c = planned.client
    s = today_session(c)
    alts = alt(c, s, "ex_leg_press", "equipment")
    swap(c, s, "ex_leg_press", alts[0]["exerciseId"], "equipment", "always")
    assert [x["reason"] for x in c.get("/api/swaps").json()] == ["equipment"]
    assert "ex_leg_press" not in program_ids(c)
    c.put("/api/me/equipment", json={"missing": []})
    assert c.get("/api/swaps").json() == [] and "ex_leg_press" in program_ids(c)
