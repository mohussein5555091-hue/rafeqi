"""Shared building blocks for every table."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, MetaData, String, TypeDecorator
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app import clock

# Predictable constraint names, so migrations can change constraints later (SQLite needs this).
NAMING = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class UTCDateTime(TypeDecorator):
    """Stores UTC; always hands back timezone-aware datetimes (SQLite would drop the timezone)."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect):  # noqa: ANN001
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("naive datetime: use app.clock.now()")
        return value.astimezone(UTC).replace(tzinfo=None)

    def process_result_value(self, value: datetime | None, dialect):  # noqa: ANN001
        return value.replace(tzinfo=UTC) if value is not None else None


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING)
    type_annotation_map = {datetime: UTCDateTime(), dict: JSON, list: JSON}


def new_id() -> str:
    return str(uuid4())


def uuid_pk() -> Mapped[str]:
    """Random id for user data: can't be guessed, and a mobile app can create one offline."""
    return mapped_column(String(36), primary_key=True, default=new_id)


def owner() -> Mapped[str]:
    """The owning user. Deleting the user deletes the row (ON DELETE CASCADE)."""
    return mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)


def timestamp() -> Mapped[datetime]:
    return mapped_column(default=lambda: clock.now())  # via the module, so tests can move time


class UserOwned:
    """Marker for tables that hold one person's data. Tests check each one has a user_id column."""
