"""Accounts, sessions, questionnaire answers, injuries, pain and weight."""

import datetime as dt
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UserOwned, owner, timestamp, uuid_pk


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = uuid_pk()
    email: Mapped[str] = mapped_column(String(254), unique=True)  # stored lowercase
    password_hash: Mapped[str] = mapped_column(String(255))  # argon2id
    first_name: Mapped[str] = mapped_column(String(80))
    last_name: Mapped[str] = mapped_column(String(80), default="")
    language: Mapped[str] = mapped_column(String(2), default="en")  # en | ar
    theme: Mapped[str] = mapped_column(String(6), default="system")  # light | dark | system
    adult_confirmed_at: Mapped[datetime]  # ticked "I'm 18 or older" at sign-up
    created_at: Mapped[datetime] = timestamp()
    last_login_at: Mapped[datetime | None]


class UserSession(Base, UserOwned):
    """One logged-in browser or phone. The cookie holds a random token; only its SHA-256 is stored."""

    __tablename__ = "sessions"

    id: Mapped[str] = uuid_pk()
    user_id: Mapped[str] = owner()
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = timestamp()
    expires_at: Mapped[datetime]
    last_seen_at: Mapped[datetime]
    revoked_at: Mapped[datetime | None]  # log out, or password changed on another session
    user_agent: Mapped[str] = mapped_column(String(300), default="")


class LoginAttempt(Base):
    """Failed and successful logins, for rate limiting. No user_id: the email may not be an account."""

    __tablename__ = "login_attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email_hash: Mapped[str] = mapped_column(String(64), index=True)
    ip: Mapped[str] = mapped_column(String(64), index=True)
    success: Mapped[bool] = mapped_column(Boolean)
    attempted_at: Mapped[datetime] = timestamp()


class Profile(Base, UserOwned):
    """Onboarding questionnaire answers. Saved step by step, so every answer can be empty until given."""

    __tablename__ = "profiles"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    onboarding_step: Mapped[str] = mapped_column(String(20), default="about")
    completed_at: Mapped[datetime | None]
    sex: Mapped[str | None] = mapped_column(String(6))
    age: Mapped[int | None]
    height_cm: Mapped[float | None]
    weight_kg: Mapped[float | None]
    waist_cm: Mapped[float | None]
    goal: Mapped[str | None] = mapped_column(String(20))
    pace: Mapped[str | None] = mapped_column(String(10))
    experience: Mapped[str | None] = mapped_column(String(12))
    days_per_week: Mapped[int | None]
    session_minutes: Mapped[int | None]
    location: Mapped[str | None] = mapped_column(String(20))
    meals_per_day: Mapped[int | None]
    cooking_minutes: Mapped[int | None]
    dislikes: Mapped[list] = mapped_column(default=list)
    allergies: Mapped[list] = mapped_column(default=list)
    fasting: Mapped[list] = mapped_column(default=list)
    heart_condition: Mapped[bool | None]
    diabetes: Mapped[bool | None]
    pregnancy: Mapped[bool | None]
    recent_surgery: Mapped[bool | None]
    exercise_medication: Mapped[bool | None]
    conservative: Mapped[bool] = mapped_column(default=False)  # any health answer "yes"
    updated_at: Mapped[datetime] = timestamp()

    __table_args__ = (CheckConstraint("age IS NULL OR age BETWEEN 18 AND 90", name="adult_age"),)


class Injury(Base, UserOwned):
    __tablename__ = "injuries"

    id: Mapped[str] = uuid_pk()
    user_id: Mapped[str] = owner()
    region: Mapped[str] = mapped_column(String(20))  # e.g. shoulderL
    side: Mapped[str] = mapped_column(String(6))
    type: Mapped[str] = mapped_column(String(12))
    severity: Mapped[int]
    status: Mapped[str] = mapped_column(String(10), default="active")  # active | recovering | resolved
    painful_movements: Mapped[list] = mapped_column(default=list)  # ids from data/vocab/movements.yaml
    restrictions: Mapped[list] = mapped_column(default=list)  # ids from data/vocab/movements.yaml
    since: Mapped[dt.date]
    paused_at: Mapped[datetime | None]  # set by a red flag: the area is paused, see a professional
    created_at: Mapped[datetime] = timestamp()
    updated_at: Mapped[datetime] = timestamp()

    __table_args__ = (CheckConstraint("severity BETWEEN 1 AND 5", name="severity_range"),)


class PainLog(Base, UserOwned):
    __tablename__ = "pain_logs"

    id: Mapped[str] = uuid_pk()
    user_id: Mapped[str] = owner()
    injury_id: Mapped[str | None] = mapped_column(ForeignKey("injuries.id", ondelete="CASCADE"), index=True)
    region: Mapped[str] = mapped_column(String(20))
    pain: Mapped[int]
    sharp_pain: Mapped[bool] = mapped_column(default=False)
    swelling: Mapped[bool] = mapped_column(default=False)
    numbness: Mapped[bool] = mapped_column(default=False)
    worsening: Mapped[bool] = mapped_column(default=False)
    source: Mapped[str] = mapped_column(String(10))  # workout | checkin
    workout_log_id: Mapped[str | None] = mapped_column(ForeignKey("workout_logs.id", ondelete="SET NULL"))
    checkin_id: Mapped[str | None] = mapped_column(ForeignKey("checkins.id", ondelete="SET NULL"))
    logged_at: Mapped[datetime] = timestamp()

    __table_args__ = (CheckConstraint("pain BETWEEN 0 AND 10", name="pain_range"),)


class WeightLog(Base, UserOwned):
    """One weight per person per day. The check-in weight writes here too (source = checkin)."""

    __tablename__ = "weight_logs"

    id: Mapped[str] = uuid_pk()
    user_id: Mapped[str] = owner()
    date: Mapped[dt.date]
    weight_kg: Mapped[float]
    source: Mapped[str] = mapped_column(String(8))  # daily | checkin
    created_at: Mapped[datetime] = timestamp()
    updated_at: Mapped[datetime] = timestamp()

    __table_args__ = (
        UniqueConstraint("user_id", "date"),
        CheckConstraint("weight_kg BETWEEN 30 AND 300", name="weight_range"),
        CheckConstraint("source IN ('daily', 'checkin')", name="source_values"),
    )

