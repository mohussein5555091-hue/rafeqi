"""One place to ask for the time, so tests can move it forward (e.g. to expire a rate limit)."""

from datetime import UTC, date, datetime


def now() -> datetime:
    return datetime.now(UTC)


def today() -> date:
    return now().date()
