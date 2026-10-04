"""Moving one of this week's sessions: "Do this workout today" and "Move to another day", keeping a rest day between
sessions for the same muscles (data/rules/training.yaml `reschedule`).

The test clock is Monday 2026-09-28. The plan: Upper A Sat, Lower A Mon, Upper B Wed, Lower B Thu; cardio Tue and Fri.
"""

from test_plans import catalogue, onboarded  # noqa: F401 (fixtures)
from test_screens_api import lifting, planned, week  # noqa: F401 (fixtures)


def session(c, day):
    return next(s for s in lifting(c) if s["day"] == day)


def options(c, s):
    r = c.get(f"/api/workouts/{s['id']}/move-options")
    assert r.status_code == 200, r.text
    return {o["day"]: o for o in r.json()}


def test_move_options_respect_other_workouts_and_rest_for_the_same_muscles(planned):  # noqa: F811
    c = planned.client
    wed = session(c, "wed")  # Upper B
    opts = options(c, wed)
    assert set(opts) == {"mon", "tue", "thu", "fri"}  # today on, not its own day
    assert opts["mon"] == opts["mon"] | {"ok": False, "why": "dayTaken"} and opts["mon"]["other"]["name"]["en"].startswith("Lower")
    assert opts["tue"]["ok"] and opts["fri"]["ok"]  # Monday and Thursday are lower-body days: no shared muscles
    assert opts["thu"]["why"] == "dayTaken"
    thu = session(c, "thu")  # Lower B
    opts = options(c, thu)
    assert opts["tue"] == opts["tue"] | {"ok": False, "why": "tooClose"}  # the day after Lower A (Monday)
    assert opts["tue"]["other"] == {"name": {"en": "Lower body A", "ar": opts["tue"]["other"]["name"]["ar"]}, "day": "mon"}
    assert opts["fri"]["ok"]


def test_move_to_another_day_and_back(planned):  # noqa: F811
    c = planned.client
    wed = session(c, "wed")
    out = c.post(f"/api/workouts/{wed['id']}/move", json={"date": "2026-09-29"})
    assert out.status_code == 200, out.text
    assert (out.json()["day"], out.json()["date"], out.json()["movedFrom"], out.json()["status"]) == ("tue", "2026-09-29", "wed", "planned")
    days = {s["day"]: s for s in week(c)["sessions"]}
    assert days["tue"]["kind"] == "strength" and days["tue"]["id"] == wed["id"] and days["tue"]["cardio"]  # Tuesday's cardio stays
    assert "wed" not in days
    # Lower B can't go to Wednesday now? It can: Upper B moved away, and Thursday's neighbours share no muscles.
    thu = session(c, "thu")
    assert options(c, thu)["wed"]["ok"]
    # Back to its own day: the move is undone.
    back = c.post(f"/api/workouts/{wed['id']}/move", json={"date": "2026-09-30"}).json()
    assert back["day"] == "wed" and "movedFrom" not in back


def test_cant_move_onto_a_busy_or_too_close_day_or_a_past_session(planned):  # noqa: F811
    c = planned.client
    thu = session(c, "thu")
    r = c.post(f"/api/workouts/{thu['id']}/move", json={"date": "2026-09-29"})
    assert r.status_code == 409 and r.json()["detail"]["why"] == "tooClose"
    r = c.post(f"/api/workouts/{thu['id']}/move", json={"date": "2026-09-30"})
    assert r.status_code == 409 and r.json()["detail"]["why"] == "dayTaken"
    r = c.post(f"/api/workouts/{thu['id']}/move", json={"date": "2026-10-09"})
    assert r.status_code == 409 and r.json()["detail"] == "outside_week"
    sat = session(c, "sat")  # already over
    assert c.post(f"/api/workouts/{sat['id']}/move", json={"date": "2026-10-02"}).status_code == 409
    mon = session(c, "mon")  # today's: do it today, it's already today
    assert c.get(f"/api/workouts/{mon['id']}/move-options").status_code == 409


def test_do_this_workout_today_then_log_it(planned, clock):  # noqa: F811
    c = planned.client
    clock.advance(days=1)  # Tuesday: a rest day with cardio
    wed = session(c, "wed")
    assert options(c, wed)["tue"]["ok"]
    s = c.post(f"/api/workouts/{wed['id']}/move", json={"date": "2026-09-29"}).json()
    assert s["status"] == "today"
    ex = s["exercises"][0]
    t = ex["target"]
    assert c.put(f"/api/workouts/{wed['id']}/exercises/{ex['exerciseId']}", json={"sets": t["sets"], "reps": t["reps"], "weightKg": t["weightKg"]}).status_code == 204
    assert c.post(f"/api/workouts/{wed['id']}/finish", json={"effort": 6}).status_code == 200
    assert session(c, "tue")["status"] == "done"
    clock.advance(days=1)  # Wednesday: nothing left to do that day
    assert "wed" not in {s["day"] for s in lifting(c)}
    clock.advance(days=3)  # next Saturday: a new week, every session back on its own day
    assert {s["day"] for s in lifting(c)} == {"sat", "mon", "wed", "thu"}
