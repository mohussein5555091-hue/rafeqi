"""Plans (versioned), training programs, the exercise catalogue, and workout logs."""

import datetime as dt
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UserOwned, owner, timestamp, uuid_pk


class Plan(Base, UserOwned):
    """Never edited in place: each change makes version n+1 and marks the old one superseded."""

    __tablename__ = "plans"

    id: Mapped[str] = uuid_pk()
    user_id: Mapped[str] = owner()
    version: Mapped[int]
    status: Mapped[str] = mapped_column(String(12), default="active")  # active | superseded
    trigger: Mapped[str] = mapped_column(String(12))  # onboarding | checkin | regenerate
    calories: Mapped[int]
    maintenance_calories: Mapped[int]
    protein_g: Mapped[int]
    carbs_g: Mapped[int]
    fat_g: Mapped[int]
    conservative: Mapped[bool] = mapped_column(default=False)
    reasons: Mapped[dict] = mapped_column(default=dict)  # one line per number, with its rule and source
    inputs: Mapped[dict] = mapped_column(default=dict)  # snapshot of the answers used
    rules_version: Mapped[str] = mapped_column(String(120), default="")
    # The plan's short summary for "Why this plan", written by the AI (app/ai) or the template; never holds a number
    # that the engine didn't produce. ai_model: the model, or "template".
    ai_summary: Mapped[dict | None]
    ai_model: Mapped[str | None] = mapped_column(String(80))
    created_at: Mapped[datetime] = timestamp()

    __table_args__ = (UniqueConstraint("user_id", "version"),)


class TrainingProgram(Base, UserOwned):
    __tablename__ = "training_programs"

    id: Mapped[str] = uuid_pk()
    user_id: Mapped[str] = owner()
    plan_id: Mapped[str] = mapped_column(ForeignKey("plans.id", ondelete="CASCADE"), index=True)
    template_id: Mapped[str] = mapped_column(String(80))  # file in data/programs/
    name_en: Mapped[str] = mapped_column(String(120))
    name_ar: Mapped[str] = mapped_column(String(120))
    days_per_week: Mapped[int]
    total_weeks: Mapped[int]
    deload_week: Mapped[int | None]
    start_date: Mapped[dt.date]
    # Weekly cardio (engine/cardio.py): {sessions: [{weekday, exerciseId, minutes, intensity, when}], stepsPerDay, reasons}
    cardio: Mapped[dict] = mapped_column(default=dict, server_default="{}")


class ProgramDay(Base, UserOwned):
    __tablename__ = "program_days"

    id: Mapped[str] = uuid_pk()
    user_id: Mapped[str] = owner()
    program_id: Mapped[str] = mapped_column(ForeignKey("training_programs.id", ondelete="CASCADE"), index=True)
    day_index: Mapped[int]
    weekday: Mapped[str] = mapped_column(String(3))  # sat … fri
    name_en: Mapped[str] = mapped_column(String(80))
    name_ar: Mapped[str] = mapped_column(String(80))
    est_minutes: Mapped[int]  # warm-up + sets and rests + cool-down (engine/training.py)
    warmup_minutes: Mapped[int]
    kind: Mapped[str] = mapped_column(String(5), default="full", server_default="full")  # upper | lower | full
    warmup: Mapped[dict] = mapped_column(default=dict, server_default="{}")  # engine/warmup.py Warmup.as_dict()
    cooldown: Mapped[dict] = mapped_column(default=dict, server_default="{}")  # engine/warmup.py Cooldown.as_dict()
    reasons: Mapped[list] = mapped_column(default=list, server_default="[]")  # warm-up, cool-down, time estimate


class Exercise(Base):
    """Catalogue (shared, loaded from data/catalogue/exercises.yaml). Tags use ids from data/vocab/movements.yaml."""

    __tablename__ = "exercises"

    id: Mapped[str] = mapped_column(String(60), primary_key=True)  # slug, e.g. ex_face_pull
    name_en: Mapped[str] = mapped_column(String(120))
    name_ar: Mapped[str] = mapped_column(String(120))
    description_en: Mapped[str] = mapped_column(Text)
    description_ar: Mapped[str] = mapped_column(Text)
    # strength (in the program) · cardio · mobility (warm-up moves) · stretch (cool-down). All get the same how-to page.
    type: Mapped[str] = mapped_column(String(10), default="strength", server_default="strength")
    movement_pattern: Mapped[str] = mapped_column(String(30), index=True)
    joints_loaded: Mapped[list] = mapped_column(default=list)
    range_of_motion: Mapped[str] = mapped_column(String(12))
    equipment: Mapped[list] = mapped_column(default=list)
    difficulty: Mapped[str] = mapped_column(String(12))
    primary_muscles: Mapped[list] = mapped_column(default=list)  # body regions, for the body map
    secondary_muscles: Mapped[list] = mapped_column(default=list)
    muscle_names_en: Mapped[str] = mapped_column(String(160), default="")
    muscle_names_ar: Mapped[str] = mapped_column(String(160), default="")
    instructions: Mapped[list] = mapped_column(default=list)  # [{en, ar}]
    cues: Mapped[list] = mapped_column(default=list)  # 3 to 5 × {en, ar}
    mistakes: Mapped[list] = mapped_column(default=list)
    image_url: Mapped[str | None] = mapped_column(String(300))
    image_frames: Mapped[list] = mapped_column(default=list)
    video_url: Mapped[str | None] = mapped_column(String(500))
    media_source: Mapped[dict | None]  # {name, url, license, note}
    source: Mapped[str] = mapped_column(String(200), default="")  # book and page


class ExerciseSubstitution(Base):
    """Catalogue: which exercise can stand in for which (easier, injury-friendly, other equipment)."""

    __tablename__ = "exercise_substitutions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    exercise_id: Mapped[str] = mapped_column(ForeignKey("exercises.id", ondelete="CASCADE"), index=True)
    substitute_id: Mapped[str | None] = mapped_column(ForeignKey("exercises.id", ondelete="CASCADE"))
    name_en: Mapped[str] = mapped_column(String(120), default="")  # for alternatives not in the catalogue yet
    name_ar: Mapped[str] = mapped_column(String(120), default="")
    kind: Mapped[str] = mapped_column(String(16))  # easier | injuryFriendly | equipment | noEquipment
    # The equipment it uses (vocab ids), for the label "Different equipment: cable machine". From the catalogue entry when
    # the alternative is one; given in exercises.yaml otherwise.
    equipment: Mapped[list] = mapped_column(default=list, server_default="[]")
    priority: Mapped[int] = mapped_column(default=0)


class ProgramExercise(Base, UserOwned):
    __tablename__ = "program_exercises"

    id: Mapped[str] = uuid_pk()
    user_id: Mapped[str] = owner()
    program_day_id: Mapped[str] = mapped_column(ForeignKey("program_days.id", ondelete="CASCADE"), index=True)
    exercise_id: Mapped[str] = mapped_column(ForeignKey("exercises.id"))
    position: Mapped[int]
    sets: Mapped[int]
    reps: Mapped[str] = mapped_column(String(20))  # "8-10", "10 each side"
    rest_sec: Mapped[int]
    target_rpe: Mapped[float]
    load_factor: Mapped[float] = mapped_column(default=1.0)  # e.g. 0.8 while an injury is recovering
    weight_step_kg: Mapped[float] = mapped_column(default=2.5)
    start_weight_kg: Mapped[float] = mapped_column(default=0.0, server_default="0")  # first session, when there's no history
    weight_offset_kg: Mapped[float] = mapped_column(default=0.0, server_default="0")  # weekly review: ± one step, next session only
    replaced_exercise_id: Mapped[str | None] = mapped_column(ForeignKey("exercises.id"))
    injury_id: Mapped[str | None] = mapped_column(ForeignKey("injuries.id", ondelete="SET NULL"))
    swap_kind: Mapped[str | None] = mapped_column(String(12))  # swapped (injury) | added | equipment | review (marked uncomfortable) | user (the person's swap)
    user_reason: Mapped[str | None] = mapped_column(String(10))  # user swaps: equipment | busy | cantDo | pain
    swap_reason: Mapped[dict | None]


class WorkoutLog(Base, UserOwned):
    __tablename__ = "workout_logs"

    id: Mapped[str] = uuid_pk()
    user_id: Mapped[str] = owner()
    plan_id: Mapped[str | None] = mapped_column(ForeignKey("plans.id", ondelete="SET NULL"))
    program_day_id: Mapped[str | None] = mapped_column(ForeignKey("program_days.id", ondelete="SET NULL"))
    week_number: Mapped[int]
    date: Mapped[dt.date]
    status: Mapped[str] = mapped_column(String(12), default="inProgress")  # inProgress | done | skipped
    effort: Mapped[int | None]  # "How hard was today's workout?" 1–10, asked once when it's finished
    warmup_done: Mapped[bool] = mapped_column(default=False, server_default="0")
    cooldown_done: Mapped[bool] = mapped_column(default=False, server_default="0")
    started_at: Mapped[datetime] = timestamp()
    finished_at: Mapped[datetime | None]

    # One log per person per day: two saves arriving at once can't each start their own (app/views/training.py open_log).
    __table_args__ = (CheckConstraint("effort BETWEEN 1 AND 10", name="effort_range"),
                      UniqueConstraint("user_id", "date", name="uq_workout_logs_user_date"))


class SetLog(Base, UserOwned):
    """Workouts are logged per exercise (see app/workouts.py): one row per set, all with the same reps and weight.
    rpe is only set on the last set, to 10, when the person said they struggled on it."""

    __tablename__ = "set_logs"

    id: Mapped[str] = uuid_pk()
    user_id: Mapped[str] = owner()
    workout_log_id: Mapped[str] = mapped_column(ForeignKey("workout_logs.id", ondelete="CASCADE"), index=True)
    exercise_id: Mapped[str] = mapped_column(ForeignKey("exercises.id"))
    set_number: Mapped[int]
    reps: Mapped[int]
    weight_kg: Mapped[float]
    rpe: Mapped[float | None]
    logged_at: Mapped[datetime] = timestamp()

    __table_args__ = (
        UniqueConstraint("workout_log_id", "exercise_id", "set_number"),
        CheckConstraint("reps BETWEEN 0 AND 100", name="reps_range"),
    )


class ExerciseSwap(Base, UserOwned):
    """The person swapped an exercise (from the session or the logger), with why.
    scope "today": only the session on `date`. scope "always": every plan version from now on, until undone (`ended_at`)."""

    __tablename__ = "exercise_swaps"

    id: Mapped[str] = uuid_pk()
    user_id: Mapped[str] = owner()
    from_exercise_id: Mapped[str] = mapped_column(ForeignKey("exercises.id"))
    to_exercise_id: Mapped[str] = mapped_column(ForeignKey("exercises.id"))
    reason: Mapped[str] = mapped_column(String(10))  # equipment | busy | cantDo | pain
    scope: Mapped[str] = mapped_column(String(6))  # today | always
    date: Mapped[dt.date | None]  # the session's date (scope today)
    created_at: Mapped[datetime] = timestamp()
    ended_at: Mapped[datetime | None]  # undone

    __table_args__ = (
        CheckConstraint("scope IN ('today', 'always')", name="scope_values"),
        CheckConstraint("reason IN ('equipment', 'busy', 'cantDo', 'pain')", name="reason_values"),
    )


class CardioLog(Base, UserOwned):
    """A cardio session marked done, with the minutes actually done. One per person per day."""

    __tablename__ = "cardio_logs"

    id: Mapped[str] = uuid_pk()
    user_id: Mapped[str] = owner()
    date: Mapped[dt.date]
    exercise_id: Mapped[str] = mapped_column(ForeignKey("exercises.id"))
    minutes: Mapped[int]
    created_at: Mapped[datetime] = timestamp()

    __table_args__ = (UniqueConstraint("user_id", "date"), CheckConstraint("minutes BETWEEN 1 AND 300", name="minutes_range"))


class WorkoutMove(Base, UserOwned):
    """The person moved one of this week's sessions to another day ("Do this workout today" / "Move to another day").
    Keyed by the week (its Saturday) and the program's weekday, so it survives a plan rebuild that week; it only ever
    applies to that week."""

    __tablename__ = "workout_moves"

    id: Mapped[str] = uuid_pk()
    user_id: Mapped[str] = owner()
    week_start: Mapped[dt.date]
    from_weekday: Mapped[str] = mapped_column(String(3))  # the program's day: sat … fri
    to_date: Mapped[dt.date]
    created_at: Mapped[datetime] = timestamp()

    __table_args__ = (UniqueConstraint("user_id", "week_start", "from_weekday"),)
