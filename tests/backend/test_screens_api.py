"""Phase 5: the endpoints behind every screen (frontend/src/data/api.ts).

The test clock is Monday 2026-09-28. The week runs Saturday 26 September to Friday 2 October, and the onboarding answers
(4 days a week) train on Saturday, Monday, Wednesday and Thursday, so Saturday is a missed session and Monday is today.
"""

import pytest
from sqlalchemy import func, select

from app.models import CheckInAnswer, Injury, PainLog, Plan, SetLog, WeightLog
from test_plans import catalogue, onboarded  # noqa: F401 (fixtures)

MONEY = ("price", "cost", "budget", "brand", "egp")


@pytest.fixture
def planned(onboarded):  # noqa: F811
    assert onboarded.client.post("/api/plan").status_code == 200
    return onboarded


def week(c):
    return c.get("/api/workouts/week").json()


def lifting(c):
    """This week's lifting sessions (the week also has cardio-only days)."""
    return [s for s in week(c)["sessions"] if s["kind"] == "strength"]


def today_session(c):
    return next(s for s in lifting(c) if s["status"] == "today")


# ── Account & onboarding ──

def test_me_says_whether_there_is_a_plan(onboarded):  # noqa: F811
    assert onboarded.client.get("/api/me").json()["hasPlan"] is False
    onboarded.client.post("/api/plan")
    assert onboarded.client.get("/api/me").json()["hasPlan"] is True


def test_completing_onboarding_records_the_first_weight(onboarded, db):  # noqa: F811
    rows = db.scalars(select(WeightLog).where(WeightLog.user_id == onboarded.id)).all()
    assert [(r.weight_kg, r.date.isoformat()) for r in rows] == [(88.0, "2026-09-28")]


def test_screens_need_a_plan_first(onboarded):  # noqa: F811
    for url in ("/api/workouts/week", "/api/meals/week", "/api/groceries", "/api/checkins/draft"):
        assert onboarded.client.get(url).status_code == 404, url


# ── Exercises ──

def test_exercise_catalogue(planned):
    exs = planned.client.get("/api/exercises").json()
    assert len(exs) > 10
    one = planned.client.get(f"/api/exercises/{exs[0]['id']}").json()
    assert one["name"]["en"] and one["name"]["ar"] and len(one["instructions"]) >= 3
    assert {"primary", "secondary"} == set(one["muscles"])
    assert planned.client.get("/api/exercises/ex_nope").status_code == 404


def test_alternatives_in_the_catalogue_come_with_their_photo(planned):
    band = planned.client.get("/api/exercises/ex_band_pull_apart").json()
    assert band["alternatives"] == [{"exerciseId": "ex_arm_circles", "name": {"en": "Arm circles", "ar": "دوائر بالدراع"},
                                     "kind": "noEquipment", "imageUrl": "/exercises/Arm_Circles/0.jpg"}]
    every = planned.client.get("/api/exercises").json()
    linked = [a for e in every for a in e["alternatives"] if "exerciseId" in a]
    assert linked and all(a["imageUrl"].startswith("/exercises/") for a in linked)
    assert all("imageUrl" not in a for e in every for a in e["alternatives"] if "exerciseId" not in a)


# ── Workouts ──

def test_workout_week(planned):
    w = week(planned.client)
    assert (w["start"], w["end"], w["weekNumber"]) == ("2026-09-26", "2026-10-02", 1)
    strength = [s for s in w["sessions"] if s["kind"] == "strength"]
    assert [(s["day"], s["status"]) for s in strength] == [("sat", "missed"), ("mon", "today"), ("wed", "planned"), ("thu", "planned")]
    s = strength[1]
    assert s["date"] == "2026-09-28" and s["exercises"]
    e = s["exercises"][0]
    assert e["target"]["reason"] == "start" and "lastTime" not in e
    # The left-shoulder injury shows on the exercises it changed.
    swaps = [x["swap"] for d in w["sessions"] for x in d["exercises"] if "swap" in x]
    assert swaps and all(x["region"] == "shoulderL" for x in swaps)


def test_log_one_exercise_then_finish(planned, db):
    c = planned.client
    s = today_session(c)
    first, second = s["exercises"][0], s["exercises"][1]
    url = f"/api/workouts/{s['id']}/exercises/{first['exerciseId']}"
    assert c.put(url, json={"sets": 2, "reps": 7, "weightKg": 20, "struggled": True}).status_code == 204
    assert c.put(url, json={"sets": 3, "reps": 8, "weightKg": 20, "struggled": False}).status_code == 204  # logging again replaces it
    assert c.delete(f"/api/workouts/{s['id']}/exercises/{second['exerciseId']}").status_code == 204  # undo: nothing logged

    r = c.post(f"/api/workouts/{s['id']}/finish", json={"effort": 7, "pain": [], "redFlags": []})
    assert r.status_code == 200 and r.json() == {"paused": []}
    done = c.get(f"/api/workouts/{s['id']}").json()
    assert done["status"] == "done" and done["log"]["effort"] == 7
    assert done["log"]["results"][first["exerciseId"]] == {"sets": 3, "reps": 8, "weightKg": 20, "struggled": False}
    # Not logged → saved as its target ("Finish workout" = done as planned).
    t = second["target"]
    assert done["log"]["results"][second["exerciseId"]] == {"sets": t["sets"], "reps": t["reps"], "weightKg": t["weightKg"], "struggled": False}
    assert done["summary"]["setsDone"] == sum(r["sets"] for r in done["log"]["results"].values())
    assert c.post(f"/api/workouts/{s['id']}/finish", json={"effort": 7}).status_code == 409


def test_only_todays_session_can_be_logged(planned):
    c = planned.client
    later = next(s for s in lifting(c) if s["status"] == "planned")
    r = c.put(f"/api/workouts/{later['id']}/exercises/{later['exercises'][0]['exerciseId']}", json={"sets": 3, "reps": 8, "weightKg": 20})
    assert r.status_code == 409 and r.json()["detail"] == "not_today"


def test_next_session_target_follows_last_time(planned, clock):
    c = planned.client
    s = today_session(c)
    e = s["exercises"][0]
    hi = int(e["reps"].split("–")[-1].split()[0])
    c.put(f"/api/workouts/{s['id']}/exercises/{e['exerciseId']}", json={"sets": e["sets"], "reps": hi, "weightKg": 20})
    c.post(f"/api/workouts/{s['id']}/finish", json={"effort": 6})
    clock.advance(days=7)  # next Monday
    nxt = today_session(c)["exercises"][0]
    assert nxt["lastTime"]["reps"] == hi
    assert nxt["target"]["reason"] in ("addWeight", "repeat")


def test_pain_after_a_workout_is_logged_and_a_red_flag_pauses_the_area(planned, db):
    c = planned.client
    inj = c.get("/api/injuries").json()[0]
    s = today_session(c)
    version = db.scalar(select(func.max(Plan.version)).where(Plan.user_id == planned.id))
    r = c.post(f"/api/workouts/{s['id']}/finish", json={"effort": 8, "pain": [{"injuryId": inj["id"], "pain": 3}], "redFlags": ["swelling"]})
    assert r.json() == {"paused": [inj["id"]]}
    db.expire_all()
    assert db.scalar(select(func.count()).select_from(PainLog).where(PainLog.injury_id == inj["id"])) == 1
    assert db.get(Injury, inj["id"]).paused_at is not None
    assert db.scalar(select(func.max(Plan.version)).where(Plan.user_id == planned.id)) == version + 1  # rebuilt without that area
    after = c.get(f"/api/injuries/{inj['id']}").json()
    assert after["paused"] and after["redFlags"]["swelling"] and after["painLog"] == [{"date": "2026-09-28", "pain": 3}]


def test_pain_for_someone_elses_injury_is_refused(planned, make_user):
    other = make_user()
    other.client.put("/api/onboarding/injuries", json={"injuries": [{"region": "kneeL", "side": "left", "type": "sprain", "severity": 2}]})
    theirs = other.client.get("/api/onboarding").json()["injuries"][0]["id"]
    s = today_session(planned.client)
    r = planned.client.post(f"/api/workouts/{s['id']}/finish", json={"effort": 5, "pain": [{"injuryId": theirs, "pain": 2}]})
    assert r.status_code == 404


# ── Meals, recipes, groceries ──

def test_meal_week_and_days(planned):
    c = planned.client
    days = c.get("/api/meals/week").json()
    assert [d["date"] for d in days] == [f"2026-09-{d}" for d in (26, 27, 28, 29, 30)] + ["2026-10-01", "2026-10-02"]
    day = c.get("/api/meals/day/2026-09-28").json()
    assert day["day"] == "mon" and day["isTrainingDay"] is True and len(day["meals"]) == 4
    m = day["meals"][0]
    assert m["portions"]["en"].endswith(" g") and m["portions"]["ar"].endswith("جم")
    plan = c.get("/api/plan").json()
    assert abs(sum(x["kcal"] for x in day["meals"]) - plan["calories"]) <= plan["calories"] * 0.05
    assert c.get("/api/meals/day/2026-09-27").json()["isTrainingDay"] is False
    assert c.get("/api/meals/day/2026-10-03").status_code == 404  # next week


def test_swap_keeps_the_day_inside_the_limits_and_updates_groceries(planned):
    c = planned.client
    plan = c.get("/api/plan").json()
    day = c.get("/api/meals/day/2026-09-28").json()
    swapped = None
    for meal in day["meals"]:
        options = c.get(f"/api/meals/{meal['id']}/swap-options").json()
        if options:
            swapped = (meal, options[0])
            break
    assert swapped, "no meal on Monday has a swap option"
    meal, option = swapped
    assert c.post(f"/api/meals/{meal['id']}/swap", json={"recipeId": "r_not_an_option"}).status_code == 422
    after = c.post(f"/api/meals/{meal['id']}/swap", json={"recipeId": option["recipeId"]}).json()
    new = next(m for m in after["meals"] if m["id"] == meal["id"])
    assert new["recipeId"] == option["recipeId"] and new["kcal"] == option["kcal"]
    total = sum(m["kcal"] for m in after["meals"])
    assert abs(total - plan["calories"]) <= plan["calories"] * 0.05
    assert sum(m["proteinG"] for m in after["meals"]) >= plan["proteinG"]
    assert c.get("/api/groceries").json()["changeNote"]["en"].startswith("Updated")


def test_recipe_is_scaled_to_your_portion(planned):
    c = planned.client
    meal = c.get("/api/meals/day/2026-09-28").json()["meals"][0]
    r = c.get(f"/api/recipes/{meal['recipeId']}").json()
    assert abs(r["kcal"] - meal["kcal"]) <= 3
    assert r["ingredients"] and r["steps"]
    assert c.get("/api/recipes/r_nope").status_code == 404


def test_grocery_list_ticks_and_have_it(planned):
    c = planned.client
    g = c.get("/api/groceries").json()
    assert (g["start"], g["end"]) == ("2026-09-26", "2026-10-02")
    assert {i["period"] for i in g["items"]} == {"week", "month"}
    item = g["items"][0]
    g2 = c.patch(f"/api/groceries/items/{item['id']}", json={"checked": True, "haveIt": True}).json()
    changed = next(i for i in g2["items"] if i["id"] == item["id"])
    assert changed["checked"] and changed["haveIt"]
    text = str(g2).lower()
    assert not any(word in text for word in MONEY)
    assert c.get("/api/pantry").json() == []


# ── Injuries ──

def test_add_edit_resolve_and_delete_an_injury(planned, db):
    c = planned.client
    body = {"region": "kneeR", "side": "right", "type": "sprain", "severity": 2, "painfulMovements": ["squat"], "restrictions": []}
    version = lambda: db.scalar(select(func.max(Plan.version)).where(Plan.user_id == planned.id))  # noqa: E731
    v0 = version()
    added = c.post("/api/injuries", json=body)
    assert added.status_code == 201, added.text
    knee = added.json()
    assert version() == v0 + 1  # the plan is rebuilt around it
    assert c.post("/api/injuries", json=body).status_code == 409  # one open injury per area
    edited = c.put(f"/api/injuries/{knee['id']}", json={**body, "severity": 4, "status": "recovering"}).json()
    assert (edited["severity"], edited["status"]) == (4, "recovering")
    assert c.put(f"/api/injuries/{knee['id']}", json={**body, "region": "kneeL"}).status_code == 422
    assert c.delete(f"/api/injuries/{knee['id']}").status_code == 204
    assert [i["region"] for i in c.get("/api/injuries").json()] == ["shoulderL"]


def test_injury_shows_what_it_changed(planned):
    shoulder = planned.client.get("/api/injuries").json()[0]
    assert shoulder["avoided"] and all(a["from"]["en"] and a["to"]["ar"] for a in shoulder["avoided"])
    assert shoulder["redFlags"] == {"sharpPain": False, "swelling": False, "numbness": False, "worsening": False}


# ── Weekly check-in & review ──

def checkin_body(c, **overrides):
    draft = c.get("/api/checkins/draft").json()
    body = draft["draft"]
    body["body"]["weightKg"] = 87.4
    body["body"]["measurementsCm"] = {"waist": 94}
    body["nutrition"]["adherencePct"] = 90
    body["note"] = "Busy week at work."
    for k, v in overrides.items():
        body[k] = v
    return draft, body


def test_checkin_due_from_thursday(planned, clock):
    c = planned.client
    assert c.get("/api/checkins/next").json() == {"date": "2026-10-01", "due": False}
    clock.advance(days=3)  # Thursday
    assert c.get("/api/checkins/next").json() == {"date": "2026-10-01", "due": True}


def test_checkin_runs_the_review(planned, db, clock):
    c = planned.client
    clock.advance(days=3)
    draft, body = checkin_body(c)
    assert draft["draft"]["training"]["sessionsPlanned"] == 4 and draft["last"]["weightKg"] == 88
    assert draft["mealOptions"] and all(o["name"]["ar"] for o in draft["mealOptions"])
    r = c.post("/api/checkins", json=body)
    assert r.status_code == 201, r.text
    review_id = r.json()["reviewId"]
    assert db.scalar(select(func.count()).select_from(CheckInAnswer).where(CheckInAnswer.user_id == planned.id)) > 10
    review = c.get(f"/api/reviews/{review_id}").json()
    assert (review["state"], review["weekNumber"], review["start"]) == ("ready", 1, "2026-09-26")
    assert review["summary"]["en"] and review["summary"]["ar"]
    assert [x["id"] for x in c.get("/api/reviews").json()] == [review_id]
    assert c.get("/api/checkins/next").json()["due"] is False
    assert c.post("/api/checkins", json=body).status_code == 409  # one a week
    assert c.get("/api/progress").json()["measurements"] == [{"date": "2026-09-26", "waist": 94}]


def test_checkin_answers_are_checked(planned):
    c = planned.client
    _, body = checkin_body(c)
    body["training"]["sessionsDone"] = 9  # only 4 planned
    r = c.post("/api/checkins", json=body)
    assert r.status_code == 422 and "sessions_done" in str(r.json())
    _, body = checkin_body(c, note="x" * 301)
    assert c.post("/api/checkins", json=body).status_code == 422


def test_checkin_red_flag_skips_the_normal_review(planned):
    c = planned.client
    shoulder = c.get("/api/injuries").json()[0]
    _, body = checkin_body(c, injuries=[{"injuryId": shoulder["id"], "pain": 4, "trend": "worse"}])
    review = c.get(f"/api/reviews/{c.post('/api/checkins', json=body).json()['reviewId']}").json()
    assert review["status"] == "warning" and review["stats"]["pain"] == 4
    assert "doctor" in review["summary"]["en"]


# ── Progress ──

def test_progress(planned):
    c = planned.client
    c.post("/api/weights", json={"weightKg": 87.5, "date": "2026-09-27"})
    s = today_session(c)
    c.post(f"/api/workouts/{s['id']}/finish", json={"effort": 7})
    p = c.get("/api/progress").json()
    assert p["since"] == "2026-09-28"
    assert [w["kg"] for w in p["weights"]] == [87.5, 88.0]
    assert p["lifts"] and len(p["lifts"]) <= 3 and p["records"]
    assert p["records"][0]["value"]["ar"].endswith(tuple("0123456789"))


def test_set_logs_belong_to_the_person(planned, db):
    s = today_session(planned.client)
    planned.client.post(f"/api/workouts/{s['id']}/finish", json={"effort": 7})
    assert db.scalar(select(func.count()).select_from(SetLog).where(SetLog.user_id != planned.id)) == 0


def test_meal_day_today_and_bad_dates(planned):
    c = planned.client
    assert c.get("/api/meals/day/today").json()["date"] == "2026-09-28"
    assert c.get("/api/meals/day/not-a-date").status_code == 404


def test_plan_has_what_the_plan_ready_screen_needs(planned):
    plan = planned.client.get("/api/plan").json()
    assert plan["program"]["currentWeek"] == 1 and all(d["id"] for d in plan["program"]["days"])
    swaps = [e for d in plan["program"]["days"] for e in d["exercises"] if e["swapKind"] == "swapped" and e["injuryId"]]
    assert swaps and all(e["injuryRegion"] == "shoulderL" and e["replacedName"]["ar"] for e in swaps)


def test_finish_with_skipped_exercises(planned):
    c = planned.client
    s = today_session(c)
    first = s["exercises"][0]
    c.put(f"/api/workouts/{s['id']}/exercises/{first['exerciseId']}", json={"sets": 3, "reps": 8, "weightKg": 20})
    c.post(f"/api/workouts/{s['id']}/finish", json={"effort": 6, "done": [first["exerciseId"]]})
    results = c.get(f"/api/workouts/{s['id']}").json()["log"]["results"]
    assert list(results) == [first["exerciseId"]]  # the rest were skipped, not saved as planned


def test_week_carries_the_real_program_name(planned, make_user):  # noqa: F811
    """The Workouts header shows the program's own name (it used to say "Upper / Lower" for every program)."""
    from test_onboarding import TRAINING, answer_all

    assert week(planned.client)["programName"] == {"en": "Upper / Lower (sample)", "ar": "علوي / سفلي (عينة)"}
    c = make_user().client
    answer_all(c, training=TRAINING | {"experience": "beginner", "daysPerWeek": 3})
    c.post("/api/onboarding/complete")
    c.post("/api/plan")
    assert week(c)["programName"]["en"] == "Full body (sample)"


def test_equipment_alternatives_name_their_equipment(planned):  # noqa: F811
    c = planned.client
    leg_press = c.get("/api/exercises/ex_leg_press").json()["alternatives"]
    assert leg_press[0]["kind"] == "equipment" and leg_press[0]["equipment"] == {"en": "dumbbells", "ar": "دمبلز"}
    curl = c.get("/api/exercises/ex_seated_leg_curl").json()["alternatives"][0]  # not in the catalogue: equipment from the file
    assert curl["equipment"] == {"en": "machine", "ar": "جهاز"}
    every = c.get("/api/exercises").json()
    assert all("equipment" in a for e in every for a in e["alternatives"] if a["kind"] == "equipment")


# ── The program's lighter (deload) week ──

def test_the_planned_lighter_week_has_fewer_sets_lower_effort_and_the_same_weights(planned, clock):  # noqa: F811
    from app.engine.rules import load_rules

    dl = load_rules()["training"]["deload"]
    c = planned.client
    w1 = week(c)
    assert w1["weekNumber"] == 1 and w1["deload"] == {"week": 5, "thisWeek": False, "byCheckIn": False,
                                                      "setsMinus": dl["sets_minus"], "rpeMinus": dl["rpe_minus"]}
    mon = today_session(c)
    assert not mon["lighter"]
    normal = {e["exerciseId"]: e for e in mon["exercises"]}
    # Log Monday's session a bit above target, so a normal week would add weight or reps.
    for e in mon["exercises"]:
        t = e["target"]
        assert c.put(f"/api/workouts/{mon['id']}/exercises/{e['exerciseId']}",
                     json={"sets": t["sets"], "reps": 12, "weightKg": t["weightKg"]}).status_code == 204
    assert c.post(f"/api/workouts/{mon['id']}/finish", json={"effort": 7}).status_code == 200

    clock.advance(days=7 * 4)  # Monday of week 5
    w5 = week(c)
    assert w5["weekNumber"] == 5 and w5["deload"]["thisWeek"] is True
    s = today_session(c)
    assert s["lighter"] is True
    for e in s["exercises"]:
        before = normal[e["exerciseId"]]
        assert e["sets"] == max(1, before["sets"] - dl["sets_minus"])
        assert e["rpe"] == before["rpe"] - dl["rpe_minus"]
        assert e["target"]["reason"] == "deload" and e["target"]["sets"] == e["sets"]
        assert e["target"]["weightKg"] == e["lastTime"]["weightKg"]  # same weight as last time: no step up
    clock.advance(days=7)  # week 6: back to normal
    assert not today_session(c)["lighter"] and week(c)["deload"]["thisWeek"] is False


def test_a_check_in_lighter_week_is_not_made_lighter_twice(planned, clock, db):  # noqa: F811
    from sqlalchemy import select

    from app.models import Plan

    c = planned.client
    before = {e["exerciseId"]: e["sets"] for e in today_session(c)["exercises"]}
    clock.advance(days=7 * 4)  # week 5, the planned lighter week
    plan = db.scalar(select(Plan).where(Plan.user_id == planned.id, Plan.status == "active"))
    plan.inputs = {**plan.inputs, "adjustments": {**plan.inputs["adjustments"], "deload": True}}  # as a check-in deload would
    db.commit()
    w = week(c)
    assert w["deload"]["thisWeek"] is True and w["deload"]["byCheckIn"] is True
    s = today_session(c)
    assert not s["lighter"] and {e["exerciseId"]: e["sets"] for e in s["exercises"]} == before  # the plan's own sets, unchanged here
