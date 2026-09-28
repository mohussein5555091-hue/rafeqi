"""Alembic: runs migrations against the database named in settings (or -x url=… for tests)."""

from logging.config import fileConfig

from alembic import context

from app.config import get_settings
from app.db import make_engine
from app.models import Base
from app.models.base import UTCDateTime

config = context.config
if config.config_file_name is not None and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def render_item(type_, obj, autogen_context):  # noqa: ANN001
    """Write our UTC datetime column as a plain DateTime in migration files (the conversion lives in Python)."""
    if type_ == "type" and isinstance(obj, UTCDateTime):
        return "sa.DateTime()"
    return False


def db_url() -> str:
    return context.get_x_argument(as_dictionary=True).get("url") or config.attributes.get("url") or get_settings().database_url


def run_migrations_offline() -> None:
    context.configure(url=db_url(), target_metadata=target_metadata, literal_binds=True, render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = make_engine(db_url())
    with engine.connect() as connection:
        # render_as_batch: SQLite can't ALTER most things, so Alembic rebuilds the table instead.
        context.configure(connection=connection, target_metadata=target_metadata, render_as_batch=True,
                          compare_type=True, render_item=render_item)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
