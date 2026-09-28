"""Body weight: one row per person per day (weight_logs).
Daily logs and the weekly check-in both write here; the progress chart and weekly review read from here."""

import datetime as dt

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import clock
from app.models import WeightLog


def record_weight(db: Session, user_id: str, day: dt.date, weight_kg: float, source: str) -> WeightLog:
    """Insert or update the weight for that day. The latest entry for a day wins."""
    row = db.scalar(select(WeightLog).where(WeightLog.user_id == user_id, WeightLog.date == day))
    now = clock.now()
    if row is None:
        row = WeightLog(user_id=user_id, date=day, weight_kg=round(weight_kg, 1), source=source, created_at=now, updated_at=now)
        db.add(row)
    else:
        row.weight_kg, row.source, row.updated_at = round(weight_kg, 1), source, now
    db.flush()
    return row


def weights_between(db: Session, user_id: str, start: dt.date | None = None, end: dt.date | None = None) -> list[WeightLog]:
    q = select(WeightLog).where(WeightLog.user_id == user_id)
    if start:
        q = q.where(WeightLog.date >= start)
    if end:
        q = q.where(WeightLog.date <= end)
    return list(db.scalars(q.order_by(WeightLog.date)))


def seven_day_average(rows: list[WeightLog], on: dt.date) -> float | None:
    """Average of the entries in the 7 days ending on `on` (fewer if some days weren't logged)."""
    window = [r.weight_kg for r in rows if on - dt.timedelta(days=6) <= r.date <= on]
    return round(sum(window) / len(window), 2) if window else None
