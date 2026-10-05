"""scripts/backup.py and scripts/restore.py: a backup restores into an empty database with every row and photo, and
restoring never mixes into a database that already has accounts."""

import gzip
import json
import sys
from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.db import make_engine
from app.models import Base
from test_plans import catalogue, onboarded  # noqa: F401 (fixtures)
from test_screens_api import planned  # noqa: F401 (fixtures)

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import backup  # noqa: E402
import restore  # noqa: E402


def counts(url: str) -> dict[str, int]:
    engine = make_engine(url)
    with engine.connect() as conn:
        out = {t.name: conn.execute(select(func.count()).select_from(t)).scalar() for t in Base.metadata.sorted_tables}
    engine.dispose()
    return out


def test_backup_then_restore_into_an_empty_database(planned, db_url, tmp_path, uploads_dir):  # noqa: F811
    (uploads_dir / planned.id).mkdir()
    (uploads_dir / planned.id / "x-front.jpg").write_bytes(b"\xff\xd8\xffphoto")
    data = backup.dump(db_url, uploads_dir)
    assert data["tables"]["users"] and data["uploads"] == {f"{planned.id}/x-front.jpg": "/9j/cGhvdG8="}
    target = f"sqlite:///{(tmp_path / 'restored.db').as_posix()}"
    restored_uploads = tmp_path / "restored-uploads"
    n = restore.restore(json.loads(json.dumps(data)), target, restored_uploads)  # through JSON, as in the file
    assert n == sum(counts(db_url).values()) - 0
    assert counts(target) == counts(db_url)
    assert (restored_uploads / planned.id / "x-front.jpg").read_bytes() == b"\xff\xd8\xffphoto"
    with pytest.raises(SystemExit, match="already has accounts"):
        restore.restore(data, target, restored_uploads)


def test_the_command_writes_a_file_and_keeps_the_newest(planned, db_url, tmp_path):  # noqa: F811
    for _ in range(3):
        assert backup.main(["--url", db_url, "--dir", str(tmp_path), "--keep", "2"]) == 0
    files = sorted(tmp_path.glob("rafeqi-*.json.gz"))
    assert 1 <= len(files) <= 2  # same-minute names overwrite; never more than --keep
    with gzip.open(files[-1], "rt", encoding="utf-8") as f:
        assert json.load(f)["format"] == 1
