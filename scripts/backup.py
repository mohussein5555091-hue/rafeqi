"""Daily backup of the whole database (and progress photos kept on disk) into one file. Run with:

    npm run backup                       # writes backups/rafeqi-2026-10-05T0300Z.json.gz, keeps the newest 14
    npm run backup -- --keep 30 --dir D:/rafeqi-backups

Works the same for SQLite (local) and PostgreSQL (Render + Neon/Supabase): it reads every table through SQLAlchemy
and writes plain JSON, gzipped, so it needs no database tools (no pg_dump) and a backup from one can be restored into
the other. Restore with scripts/restore.py (docs/DEPLOY.md, "Backups"). The file holds everyone's private data: keep it
somewhere private, never in git (backups/ is git-ignored).
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

from sqlalchemy import select  # noqa: E402

FORMAT = 1


def _value(v):
    if isinstance(v, dt.datetime | dt.date):
        return {"$dt": v.isoformat()}
    if isinstance(v, bytes | bytearray | memoryview):
        return {"$b64": base64.b64encode(bytes(v)).decode()}
    return v


def dump(url: str | None = None, uploads: Path | None = None) -> dict:
    """Every table's rows (in the order they can be loaded back), plus any photo files on disk."""
    from app.config import get_settings
    from app.db import make_engine
    from app.models import Base

    engine = make_engine(url or get_settings().database_url)
    out = {"format": FORMAT, "created": dt.datetime.now(dt.UTC).isoformat(), "tables": {}, "uploads": {}}
    with engine.connect() as conn:
        version = conn.exec_driver_sql("SELECT version_num FROM alembic_version").scalar()
        out["alembic_version"] = version
        for table in Base.metadata.sorted_tables:
            rows = conn.execute(select(table)).mappings().all()
            out["tables"][table.name] = [{k: _value(v) for k, v in r.items()} for r in rows]
    engine.dispose()
    uploads = uploads or get_settings().uploads_dir
    if uploads.is_dir():
        for f in sorted(uploads.rglob("*")):
            if f.is_file():
                out["uploads"][f.relative_to(uploads).as_posix()] = base64.b64encode(f.read_bytes()).decode()
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--dir", default=str(ROOT / "backups"), help="where to write backups (default: backups/)")
    p.add_argument("--keep", type=int, default=14, help="how many backups to keep (older ones are deleted)")
    p.add_argument("--url", default=None, help="database URL (default: RAFEQI_DATABASE_URL from .env, or the local SQLite file)")
    args = p.parse_args(argv)
    folder = Path(args.dir)
    folder.mkdir(parents=True, exist_ok=True)
    data = dump(args.url)
    name = folder / f"rafeqi-{dt.datetime.now(dt.UTC).strftime('%Y-%m-%dT%H%MZ')}.json.gz"
    with gzip.open(name, "wt", encoding="utf-8") as f:
        json.dump(data, f)
    rows = sum(len(r) for r in data["tables"].values())
    print(f"Backed up {rows} rows from {len(data['tables'])} tables and {len(data['uploads'])} photo files to {name}")
    old = sorted(folder.glob("rafeqi-*.json.gz"))[: -args.keep] if args.keep > 0 else []
    for f in old:
        f.unlink()
        print(f"Deleted old backup {f.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
