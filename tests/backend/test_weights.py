"""weight_logs: one weight per person per day, from the dashboard or the check-in."""

import datetime as dt

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import WeightLog
from app.weights import record_weight, seven_day_average, weights_between


def test_log_todays_weight_then_correct_it(make_user, clock):
    u = make_user()
    first = u.client.post("/api/weights", json={"weightKg": 88.4})
    assert first.status_code == 200
    assert first.json() | {"id": "x"} == {"id": "x", "date": "2026-09-28", "weightKg": 88.4, "source": "daily"}
    again = u.client.post("/api/weights", json={"weightKg": 88.1})
    assert again.json()["id"] == first.json()["id"]  # same day → same row, updated
    assert [w["weightKg"] for w in u.client.get("/api/weights").json()] == [88.1]


def test_weight_input_rules(make_user):
    u = make_user()
    assert u.client.post("/api/weights", json={"weightKg": 12}).status_code == 422
    assert u.client.post("/api/weights", json={"weightKg": 400}).status_code == 422
    assert u.client.post("/api/weights", json={"weightKg": 80, "date": "2026-10-05"}).status_code == 422  # future
    assert u.client.post("/api/weights", json={"weightKg": 80, "date": "2026-09-20"}).status_code == 200  # back-fill


def test_list_is_in_date_order_and_can_be_filtered(make_user):
    u = make_user()
    for day, kg in [("2026-09-27", 88.0), ("2026-09-25", 88.6), ("2026-09-26", 88.3)]:
        u.client.post("/api/weights", json={"weightKg": kg, "date": day})
    assert [w["date"] for w in u.client.get("/api/weights").json()] == ["2026-09-25", "2026-09-26", "2026-09-27"]
    assert len(u.client.get("/api/weights", params={"start": "2026-09-26"}).json()) == 2


def test_delete_a_weight(make_user):
    u = make_user()
    wid = u.client.post("/api/weights", json={"weightKg": 88}).json()["id"]
    assert u.client.delete(f"/api/weights/{wid}").status_code == 204
    assert u.client.delete(f"/api/weights/{wid}").status_code == 404
    assert u.client.get("/api/weights").json() == []


def test_checkin_weight_writes_the_same_table(make_user, db):
    u = make_user()
    u.client.post("/api/weights", json={"weightKg": 88.4})
    record_weight(db, u.id, dt.date(2026, 9, 28), 88.2, "checkin")  # what the check-in will call
    db.commit()
    rows = weights_between(db, u.id)
    assert [(r.weight_kg, r.source) for r in rows] == [(88.2, "checkin")]


def test_one_row_per_user_per_day_is_enforced_by_the_database(make_user, db):
    u = make_user()
    day = dt.date(2026, 9, 28)
    db.add(WeightLog(user_id=u.id, date=day, weight_kg=80, source="daily"))
    db.commit()
    db.add(WeightLog(user_id=u.id, date=day, weight_kg=81, source="checkin"))
    with pytest.raises(IntegrityError):
        db.commit()


def test_seven_day_average():
    rows = [WeightLog(date=dt.date(2026, 9, d), weight_kg=kg) for d, kg in [(20, 90.0), (22, 89.0), (25, 88.0), (28, 87.0)]]
    assert seven_day_average(rows, dt.date(2026, 9, 28)) == 88.0  # 22, 25, 28; the 20th is outside the week
    assert seven_day_average(rows, dt.date(2026, 9, 10)) is None
