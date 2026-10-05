"""Database connection. Everything talks to the database through a Session from here."""

from collections.abc import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings, normalize_db_url


def make_engine(url: str) -> Engine:
    url = normalize_db_url(url)
    is_sqlite = url.startswith("sqlite")
    # PostgreSQL: check a pooled connection still works before using it (hosted databases close idle connections), and
    # no server-side prepared statements, which connection poolers like Neon's and Supabase's don't support.
    engine = (create_engine(url, connect_args={"check_same_thread": False}) if is_sqlite
              else create_engine(url, pool_pre_ping=True, pool_size=5, connect_args={"prepare_threshold": None}))
    if is_sqlite:
        @event.listens_for(engine, "connect")
        def _sqlite_pragmas(dbapi_conn, _record):  # noqa: ANN001
            cur = dbapi_conn.cursor()
            # SQLite ignores foreign keys (and so ON DELETE CASCADE) unless this is on, per connection.
            cur.execute("PRAGMA foreign_keys=ON")
            cur.execute("PRAGMA journal_mode=WAL")  # readers don't block the writer
            cur.close()
    return engine


engine = make_engine(get_settings().database_url)
SessionLocal = sessionmaker(engine, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """FastAPI dependency: one session per request, closed afterwards."""
    with SessionLocal() as session:
        yield session
