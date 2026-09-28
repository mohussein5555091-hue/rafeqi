"""Weekly check-ins, their answers, the review engine's output, and the AI call log."""

import datetime as dt
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UserOwned, owner, timestamp, uuid_pk


class CheckIn(Base, UserOwned):
    __tablename__ = "checkins"

    id: Mapped[str] = uuid_pk()
    user_id: Mapped[str] = owner()
    week_number: Mapped[int]
    week_start: Mapped[dt.date]
    status: Mapped[str] = mapped_column(String(10), default="draft")  # draft | submitted
    submitted_at: Mapped[datetime | None]
    weight_kg: Mapped[float | None]  # also written to weight_logs (source = checkin)
    waist_cm: Mapped[float | None]
    hips_cm: Mapped[float | None]
    chest_cm: Mapped[float | None]
    arm_cm: Mapped[float | None]
    thigh_cm: Mapped[float | None]
    photo_front_path: Mapped[str | None] = mapped_column(String(300))  # under data/uploads/<user_id>/, never public
    photo_side_path: Mapped[str | None] = mapped_column(String(300))
    photo_back_path: Mapped[str | None] = mapped_column(String(300))
    note: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        UniqueConstraint("user_id", "week_start"),
        CheckConstraint("note IS NULL OR length(note) <= 300", name="note_length"),
    )


class CheckInAnswer(Base, UserOwned):
    """One row per answered question. Question ids come from data/checkin_questions.yaml."""

    __tablename__ = "checkin_answers"

    id: Mapped[str] = uuid_pk()
    user_id: Mapped[str] = owner()
    checkin_id: Mapped[str] = mapped_column(ForeignKey("checkins.id", ondelete="CASCADE"), index=True)
    question_id: Mapped[str] = mapped_column(String(60))
    value: Mapped[dict]  # {"value": …} so any answer type fits
    answered_at: Mapped[datetime] = timestamp()

    __table_args__ = (UniqueConstraint("checkin_id", "question_id"),)


class WeeklyReview(Base, UserOwned):
    __tablename__ = "weekly_reviews"

    id: Mapped[str] = uuid_pk()
    user_id: Mapped[str] = owner()
    checkin_id: Mapped[str | None] = mapped_column(ForeignKey("checkins.id", ondelete="SET NULL"), index=True)
    plan_before_id: Mapped[str | None] = mapped_column(ForeignKey("plans.id", ondelete="SET NULL"))
    plan_after_id: Mapped[str | None] = mapped_column(ForeignKey("plans.id", ondelete="SET NULL"))
    week_number: Mapped[int]
    state: Mapped[str] = mapped_column(String(8), default="pending")  # pending | ready | failed
    status: Mapped[str] = mapped_column(String(10), default="onTrack")  # onTrack | attention | warning
    red_flag: Mapped[bool] = mapped_column(default=False)  # skips the normal review
    changes: Mapped[list] = mapped_column(default=list)  # [{kind, what, why, source}]
    ai_summary_en: Mapped[str | None] = mapped_column(Text)  # next session
    ai_summary_ar: Mapped[str | None] = mapped_column(Text)
    citations: Mapped[list] = mapped_column(default=list)
    model_used: Mapped[str | None] = mapped_column(String(80))
    created_at: Mapped[datetime] = timestamp()


class LlmCall(Base, UserOwned):
    """Every AI call. When an account is deleted these rows stay, with user_id set to null,
    so the monthly AI usage count stays correct. They hold no personal content."""

    __tablename__ = "llm_calls"

    id: Mapped[str] = uuid_pk()
    user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), index=True)
    plan_id: Mapped[str | None] = mapped_column(ForeignKey("plans.id", ondelete="SET NULL"))
    weekly_review_id: Mapped[str | None] = mapped_column(ForeignKey("weekly_reviews.id", ondelete="SET NULL"))
    task: Mapped[str] = mapped_column(String(30))  # plan_explanation | weekly_review
    model: Mapped[str] = mapped_column(String(80))
    prompt_tokens: Mapped[int] = mapped_column(default=0)
    completion_tokens: Mapped[int] = mapped_column(default=0)
    latency_ms: Mapped[int] = mapped_column(default=0)
    cost_usd: Mapped[float] = mapped_column(default=0.0)  # internal metric, never shown to users
    status: Mapped[str] = mapped_column(String(10), default="ok")
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = timestamp()
