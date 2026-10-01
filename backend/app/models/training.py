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
    rules_version: Mapped[str] = mapped_column(String(40), default="")
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


class ProgramDay(Base, UserOwned):
    __tablename__ = "program_days"

    id: Mapped[str] = uuid_pk()
    user_id: Mapped[str] = owner()
    program_id: Mapped[str] = mapped_column(ForeignKey("training_programs.id", ondelete="CASCADE"), index=True)
    day_index: Mapped[int]
    weekday: Mapped[str] = mapped_column(String(3))  # sat … fri
    name_en: Mapped[str] = mapped_column(String(80))
    name_ar: Mapped[str] = mapped_column(String(80))
    est_minutes: Mapped[int]
    warmup_minutes: Mapped[int]


class Exercise(Base):
    """Catalogue (shared, loaded from data/catalogue/exercises.yaml). Tags use ids from data/vocab/movements.yaml."""

    __tablename__ = "exercises"

    id: Mapped[str] = mapped_column(String(60), primary_key=True)  # slug, e.g. ex_face_pull
    name_en: Mapped[str] = mapped_column(String(120))
    name_ar: Mapped[str] = mapped_column(String(120))
    description_en: Mapped[str] = mapped_column(Text)
    description_ar: Mapped[str] = mapped_column(Text)
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
    kind: Mapped[str] = mapped_column(String(16))  # easier | injuryFriendly | equipment
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
    swap_kind: Mapped[str | None] = mapped_column(String(8))  # swapped | added
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
    started_at: Mapped[datetime] = timestamp()
    finished_at: Mapped[datetime | None]

    __table_args__ = (CheckConstraint("effort BETWEEN 1 AND 10", name="effort_range"),)


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
