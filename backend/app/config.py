"""App settings, read from the project-root .env file (never hard-code secrets)."""

import datetime as dt
from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[2]  # D:\rafeqi (the repo root)
DATA_DIR = ROOT_DIR / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT_DIR / ".env", env_prefix="RAFEQI_", extra="ignore")

    env: str = "development"
    # Used for anything that needs signing later. Generated into .env by `npm run setup`.
    secret_key: str = "dev-only-change-me"
    # SQLite now; switching to PostgreSQL later is only this line, e.g.
    # postgresql+psycopg://user:pass@localhost/rafeqi
    database_url: str = f"sqlite:///{(DATA_DIR / 'rafeqi.db').as_posix()}"
    uploads_dir: Path = DATA_DIR / "uploads"
    rules_dir: Path = DATA_DIR / "rules"
    programs_dir: Path = DATA_DIR / "programs"
    vocab_file: Path = DATA_DIR / "vocab" / "movements.yaml"
    catalogue_dir: Path = DATA_DIR / "catalogue"
    # Production: the built React app (npm run build → frontend/dist), served by the backend at the same address.
    frontend_dist: Path = ROOT_DIR / "frontend" / "dist"
    # Invite-only sign-up: when set, signing up needs this code (give it to your friends). Empty = open sign-up.
    invite_code: str = ""
    # Where progress photos live: "disk" (data/uploads/<user_id>/) or "database" (for hosts whose disk is wiped on
    # every deploy, like Render's free plan).
    photo_storage: str = "disk"
    # Testing only: pretend today is this date (e.g. 2026-10-05), so browser tests don't depend on the real weekday.
    # The clock keeps running; only the date moves. Ignored in production.
    today: dt.date | None = None

    # Sessions: an httpOnly cookie holding a random token; each visit extends it.
    session_cookie: str = "rafeqi_session"
    session_days: int = 30
    # Login rate limit: failed attempts inside the window, per email and per IP address.
    login_window_minutes: int = 15
    login_max_failures_per_email: int = 5
    login_max_failures_per_ip: int = 20

    @field_validator("database_url")
    @classmethod
    def _driver(cls, url: str) -> str:
        return normalize_db_url(url)

    @property
    def is_production(self) -> bool:
        return self.env == "production"

    def check_production(self) -> None:
        """Refuse to start in production without a real secret key (it must come from the environment)."""
        if self.is_production and (self.secret_key in ("dev-only-change-me", "replace-me") or len(self.secret_key) < 32):
            raise RuntimeError("RAFEQI_SECRET_KEY must be set to a long random value (at least 32 characters) in production")


def normalize_db_url(url: str) -> str:
    """Hosting sites (Neon, Supabase, Render) hand out "postgres://…" or "postgresql://…"; SQLAlchemy needs the driver
    named: "postgresql+psycopg://…". SQLite URLs pass through unchanged."""
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


@lru_cache
def get_settings() -> Settings:
    return Settings()
