"""RAFEQI_TODAY: the browser tests pretend today is a fixed date (scripts/e2e-server.mjs). Never in production."""

import datetime as dt

from app import clock
from app.config import get_settings


def test_today_setting_shifts_the_date_only_outside_production(monkeypatch):
    s = get_settings()
    real = dt.datetime.now(dt.UTC).date()
    monkeypatch.setattr(s, "today", dt.date(2026, 10, 5))
    clock._shift.cache_clear()
    try:
        assert (real + clock._shift()) == dt.date(2026, 10, 5)
        monkeypatch.setattr(s, "env", "production")
        clock._shift.cache_clear()
        assert clock._shift() == dt.timedelta(0)
    finally:
        clock._shift.cache_clear()
