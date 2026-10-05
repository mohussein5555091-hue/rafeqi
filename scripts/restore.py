"""Restore a backup made by scripts/backup.py into an EMPTY database. Run with:

    npm run restore -- backups/rafeqi-2026-10-05T0300Z.json.gz
    npm run restore -- backups/….json.gz --url "postgresql://…"      # e.g. a new Neon database

It first brings the database to the latest schema (alembic upgrade head), refuses if it already holds any accounts
(so it can never mix two sets of data), then loads every table in order and writes the photo files back. The backup
must come from the same app version or an older one (the schema is upgraded first, and newer columns get their
defaults).
"""

import argparse
import base64
import datetime as dt
import gzip
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from sqlalchemy import Date, DateTime, func, insert, select  # noqa: E402


def _load(v, column):
    if isinstance(v, dict) and "$dt" in v:
        text = v["$dt"]
        return dt.date.fromisoformat(text) if isinstance(column.type, Date) and not isinstance(column.type, DateTime) else dt.datetime.fromisoformat(text)
    if isinstance(v, dict) and "$b64" in v:
        return base64.b64decode(v["$b64"])
    return v


def restore(data: dict, url: str | None = None, uploads: Path | None = None) -> int:
    from alembic import command
    from alembic.config import Config

    from app.config import get_settings
    from app.db import make_engine
    from app.models import Base, User

    url = url or get_settings().database_url
    cfg = Config(str(ROOT / "backend" / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "backend" / "migrations"))
    cfg.attributes["url"] = url
    cfg.attributes["configure_logger"] = False
    command.upgrade(cfg, "head")
    engine = make_engine(url)
    rows = 0
    with engine.begin() as conn:
        if conn.execute(select(func.count()).select_from(User.__table__)).scalar():
            raise SystemExit("This database already has accounts. Restore only into an empty database.")
        for table in Base.metadata.sorted_tables:
            items = data["tables"].get(table.name) or []
            if table.name in ("exercises", "exercise_substitutions", "foods", "grocery_items", "food_grocery_items", "recipes",
                              "recipe_ingredients", "recipe_steps"):
                conn.execute(table.delete())  # the catalogue comes back exactly as it was backed up
            known = {c.name: c for c in table.columns}
            clean = [{k: _load(v, known[k]) for k, v in r.items() if k in known} for r in items]
            if clean:
                conn.execute(insert(table), clean)
                rows += len(clean)
    engine.dispose()
    uploads = uploads or get_settings().uploads_dir
    for rel, b64 in (data.get("uploads") or {}).items():
        dest = (uploads / rel).resolve()
        if uploads.resolve() not in dest.parents:
            continue  # never write outside the uploads folder
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(base64.b64decode(b64))
    return rows


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("file", help="a backups/rafeqi-….json.gz file")
    p.add_argument("--url", default=None, help="database URL (default: RAFEQI_DATABASE_URL from .env, or the local SQLite file)")
    args = p.parse_args(argv)
    with gzip.open(args.file, "rt", encoding="utf-8") as f:
        data = json.load(f)
    n = restore(data, args.url)
    print(f"Restored {n} rows and {len(data.get('uploads') or {})} photo files from {args.file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
