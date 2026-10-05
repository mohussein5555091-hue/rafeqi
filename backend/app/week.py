"""This week, as the screens show it.

A plan version holds one week of sessions and meals. That week repeats until the next version (the weekly review or
"regenerate my plan"), so a date is matched to the plan by its weekday: Saturday's sessions and meals are the plan's
Saturday, whichever week it is. Weeks run Saturday to Friday (the Egyptian week).

The real programs change every week (data/programs/*.json `weeks`): when a new program week starts and the current
plan was built for an earlier one, the first screen that asks for "this week" builds the new week's sessions as a new
plan version, keeping the meals, calories and the weekly reviews' changes (plans.rebuild_plan, trigger "newWeek").
"""

import datetime as dt
from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import clock
from app.models import MealPlan, Plan, ProgramDay, TrainingProgram, WorkoutMove
from sqlalchemy.exc import IntegrityError

from app.engine.rules import deload_in_tables, template_by_id
from app.plans import current_plan, rebuild_plan, week_start

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
    """Weeks since the first plan's program started (plan versions continue the count), 1…total_weeks, then from 1
    again: the books suggest running a program again once it's finished."""
    first = db.scalar(select(func.min(TrainingProgram.start_date)).where(TrainingProgram.user_id == user_id)) or start
    return max(0, (start - first).days // 7) % total_weeks + 1


def _needs_new_week(db: Session, user_id: str, plan: Plan, tp: TrainingProgram, number: int) -> bool:
    """A real program (one with its weeks written out) whose current plan was built for an earlier program week."""
    if not deload_in_tables(template_by_id(tp.template_id)):
        return False
    built_for = program_week_number(db, user_id, week_start(plan.created_at.date()), tp.total_weeks)
    return built_for != number


def this_week(db: Session, user_id: str, _rebuilt: bool = False) -> Week:
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
    number = program_week_number(db, user_id, start, tp.total_weeks)
    if not _rebuilt and _needs_new_week(db, user_id, plan, tp, number):
        try:
            rebuild_plan(db, user_id, "newWeek")
            db.commit()
        except IntegrityError:  # another request just built it: use that version
            db.rollback()
        return this_week(db, user_id, _rebuilt=True)
    return Week(plan, tp, days, mp, today, start, number, moves)
