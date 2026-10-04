"""This week, as the screens show it.

A plan version holds one week of sessions and meals. That week repeats until the next version (the weekly review or
"regenerate my plan"), so a date is matched to the plan by its weekday: Saturday's sessions and meals are the plan's
Saturday, whichever week it is. Weeks run Saturday to Friday (the Egyptian week).
"""

import datetime as dt
from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import clock
from app.models import MealPlan, Plan, ProgramDay, TrainingProgram, WorkoutMove
from app.plans import current_plan, week_start

WEEKDAYS = ("sat", "sun", "mon", "tue", "wed", "thu", "fri")
# The weekly check-in opens this many days before the week ends (Friday): Thursday and Friday.
CHECKIN_OPENS_DAYS_BEFORE_END = 1


class NoPlan(Exception):
    """No plan yet (onboarding not finished, or the plan wasn't built)."""


def weekday_of(d: dt.date) -> str:
    return WEEKDAYS[(d - week_start(d)).days]


@dataclass
class Week:
    """The logged-in person's current plan, and this week's dates."""

    plan: Plan
    program: TrainingProgram
    days: list[ProgramDay]
    meal_plan: MealPlan
    today: dt.date
    start: dt.date  # Saturday
    number: int  # week of the program, 1…total_weeks
    moves: dict[str, dt.date] = field(default_factory=dict)  # program weekday → the date it was moved to this week

    @property
    def end(self) -> dt.date:
        return self.start + dt.timedelta(days=6)

    @property
    def dates(self) -> list[dt.date]:
        return [self.start + dt.timedelta(days=i) for i in range(7)]

    def planned_date_of(self, day: ProgramDay) -> dt.date:
        """The program's own day this week (before any move)."""
        return self.start + dt.timedelta(days=WEEKDAYS.index(day.weekday))

    def date_of(self, day: ProgramDay) -> dt.date:
        """The day the session happens this week: the program's day, or the day the person moved it to."""
        return self.moves.get(day.weekday) or self.planned_date_of(day)

    def day_on(self, d: dt.date) -> ProgramDay | None:
        return next((x for x in self.days if self.date_of(x) == d), None)

    def meal_date(self, d: dt.date) -> dt.date:
        """The date in the stored meal plan whose meals apply on `d` (same weekday)."""
        return self.meal_plan.week_start + dt.timedelta(days=(d - self.meal_plan.week_start).days % 7)

    def in_week(self, d: dt.date) -> bool:
        return self.start <= d <= self.end


def program_week_number(db: Session, user_id: str, start: dt.date, total_weeks: int) -> int:
    """Weeks since the first plan's program started (plan versions continue the count), 1…total_weeks."""
    first = db.scalar(select(func.min(TrainingProgram.start_date)).where(TrainingProgram.user_id == user_id)) or start
    return max(1, min(total_weeks, (start - first).days // 7 + 1))


def this_week(db: Session, user_id: str) -> Week:
    plan = current_plan(db, user_id)
    if plan is None:
        raise NoPlan
    tp = db.scalar(select(TrainingProgram).where(TrainingProgram.plan_id == plan.id, TrainingProgram.user_id == user_id))
    mp = db.scalar(select(MealPlan).where(MealPlan.plan_id == plan.id, MealPlan.user_id == user_id))
    if tp is None or mp is None:
        raise NoPlan
    days = list(db.scalars(select(ProgramDay).where(ProgramDay.program_id == tp.id).order_by(ProgramDay.day_index)))
    today = clock.today()
    start = week_start(today)
    moves = {m.from_weekday: m.to_date for m in db.scalars(select(WorkoutMove).where(WorkoutMove.user_id == user_id,
                                                                                     WorkoutMove.week_start == start))}
    return Week(plan, tp, days, mp, today, start, program_week_number(db, user_id, start, tp.total_weeks), moves)
