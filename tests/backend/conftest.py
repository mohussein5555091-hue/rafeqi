"""Shared test setup.

- The schema is built once per run by running the real Alembic migrations (so migrations are tested too),
  then each test gets its own copy of that database file: fast, and tests can't affect each other.
- PostgreSQL instead of SQLite: set RAFEQI_TEST_POSTGRES_URL to a server's admin URL, e.g.
  postgresql://postgres:postgres@localhost:5432/postgres. The migrations build a template database once, and each
  test gets its own database copied from it (CREATE DATABASE … TEMPLATE …), dropped afterwards.
- `clock` lets a test move time forward (session expiry, login lock-out).
- `make_user` signs someone up and returns a logged-in client.
"""

import itertools
import os
import shutil
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app import clock as clock_module
from app.config import get_settings
from app.db import get_db, make_engine
from app.main import app

BACKEND = Path(__file__).resolve().parents[2] / "backend"
PASSWORD = "correct-horse-1"
_emails = itertools.count(1)


def run_migrations(url: str, target: str = "head", down: bool = False) -> None:
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "migrations"))
    cfg.attributes["url"] = url
    cfg.attributes["configure_logger"] = False
    (command.downgrade if down else command.upgrade)(cfg, target)


PG_ADMIN = os.environ.get("RAFEQI_TEST_POSTGRES_URL")
_dbs = itertools.count(1)


def _pg(name: str) -> str:
    """The admin URL pointed at another database on the same server."""
    base, _, _ = make_engine(PG_ADMIN).url.render_as_string(hide_password=False).rpartition("/")
    return f"{base}/{name}"


def _pg_admin(sql: str) -> None:
    engine = make_engine(PG_ADMIN)
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        conn.exec_driver_sql(sql)
    engine.dispose()


@pytest.fixture(scope="session")
def template_db(tmp_path_factory) -> Path | str:
    if PG_ADMIN:
        name = f"rafeqi_tpl_{os.getpid()}"
        _pg_admin(f"DROP DATABASE IF EXISTS {name} WITH (FORCE)")
        _pg_admin(f"CREATE DATABASE {name}")
        run_migrations(_pg(name))
        yield name
        _pg_admin(f"DROP DATABASE IF EXISTS {name} WITH (FORCE)")
        return
    path = tmp_path_factory.mktemp("template") / "template.db"
    run_migrations(f"sqlite:///{path.as_posix()}")
    yield path


@pytest.fixture
def db_url(template_db: Path | str, tmp_path: Path) -> Iterator[str]:
    if PG_ADMIN:
        name = f"rafeqi_t_{os.getpid()}_{next(_dbs)}"
        _pg_admin(f"CREATE DATABASE {name} TEMPLATE {template_db}")
        yield _pg(name)
        _pg_admin(f"DROP DATABASE IF EXISTS {name} WITH (FORCE)")
        return
    path = tmp_path / "test.db"
    shutil.copy(template_db, path)
    yield f"sqlite:///{path.as_posix()}"


@pytest.fixture
def SessionTest(db_url: str) -> Iterator[sessionmaker]:
    engine = make_engine(db_url)
    yield sessionmaker(engine, expire_on_commit=False)
    engine.dispose()


@pytest.fixture
def db(SessionTest) -> Iterator[Session]:
    with SessionTest() as s:
        yield s


@pytest.fixture(autouse=True)
def uploads_dir(tmp_path: Path, monkeypatch) -> Path:
    d = tmp_path / "uploads"
    d.mkdir()
    monkeypatch.setattr(get_settings(), "uploads_dir", d)
    return d


@dataclass
class Clock:
    at: datetime

    def advance(self, **kw) -> None:
        self.at += timedelta(**kw)


@pytest.fixture(autouse=True)
def clock(monkeypatch) -> Clock:
    c = Clock(datetime(2026, 9, 28, 9, 0, tzinfo=UTC))
    monkeypatch.setattr(clock_module, "now", lambda: c.at)
    return c


@pytest.fixture
def client_factory(SessionTest) -> Iterator[Callable[[], TestClient]]:
    def override_db():
        with SessionTest() as s:
            yield s

    app.dependency_overrides[get_db] = override_db
    clients: list[TestClient] = []

    def make() -> TestClient:
        c = TestClient(app, base_url="http://testserver")
        clients.append(c)
        return c

    yield make
    app.dependency_overrides.clear()
    for c in clients:
        c.close()


@dataclass
class TestUser:
    client: TestClient
    id: str
    email: str
    password: str = PASSWORD


@pytest.fixture
def make_user(client_factory) -> Callable[..., TestUser]:
    def make(email: str | None = None, first_name: str = "Omar") -> TestUser:
        email = email or f"user{next(_emails)}@example.com"
        c = client_factory()
        r = c.post("/api/auth/signup", json={"firstName": first_name, "email": email, "password": PASSWORD, "adultConfirmed": True})
        assert r.status_code == 201, r.text
        return TestUser(c, r.json()["id"], email)

    return make
