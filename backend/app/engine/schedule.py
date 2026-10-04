"""Moving a session to another day this week (data/rules/training.yaml `reschedule`).

A session can go to today or a later day of this week that has no other workout, as long as every other session that
trains the same muscles (they share a main muscle) stays at least `min_rest_days` full days away.
"""

import datetime as dt
from dataclasses import dataclass

from app.engine.rules import load_rules


@dataclass(frozen=True)
class OtherSession:
    date: dt.date
    muscles: frozenset[str]
    name: dict  # {en, ar}
    done: bool = False


@dataclass(frozen=True)
class MoveCheck:
    ok: bool
    why: str | None = None  # dayTaken | tooClose | past
    other: OtherSession | None = None  # the session it clashes with


def check_move(to: dt.date, today: dt.date, muscles: frozenset[str], others: list[OtherSession]) -> MoveCheck:
    """Whether a session training `muscles` can happen on `to`, given the week's other sessions (at their dates)."""
    if to < today:
        return MoveCheck(False, "past")
    if (o := next((o for o in others if o.date == to), None)) is not None:
        return MoveCheck(False, "dayTaken", o)
    gap = load_rules()["training"]["reschedule"]["min_rest_days"]
    for o in sorted(others, key=lambda o: abs((o.date - to).days)):
        if muscles & o.muscles and abs((o.date - to).days) <= gap:
            return MoveCheck(False, "tooClose", o)
    return MoveCheck(True)
