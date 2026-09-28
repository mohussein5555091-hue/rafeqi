"""App settings, read from the project-root .env file (never hard-code secrets)."""

from functools import lru_cache
from pathlib import Path

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

    # Sessions: an httpOnly cookie holding a random token; each visit extends it.
    session_cookie: str = "rafeqi_session"
    session_days: int = 30
    # Login rate limit: failed attempts inside the window, per email and per IP address.
    login_window_minutes: int = 15
    login_max_failures_per_email: int = 5
    login_max_failures_per_ip: int = 20

    @property
    def is_production(self) -> bool:
        return self.env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
