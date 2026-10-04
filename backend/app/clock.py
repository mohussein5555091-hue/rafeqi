"""One place to ask for the time, so tests can move it forward (e.g. to expire a rate limit).

RAFEQI_TODAY (testing only, see app/config.py) shifts the clock by whole days so that today is that date."""

from datetime import UTC, date, datetime, timedelta
from functools import lru_cache


@lru_cache
def _shift() -> timedelta:
    from app.config import get_settings

    s = get_settings()
    if s.today is None or s.is_production:
        return timedelta(0)
    return timedelta(days=(s.today - datetime.now(UTC).date()).days)


def now() -> datetime:
    return datetime.now(UTC) + _shift()


def today() -> date:
    return now().date()
