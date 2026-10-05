"""Progress photos from the weekly check-in: front, side and back.

Never public: served only to their owner through GET /api/photos/{checkin_id}/{view}. Two places to keep them
(RAFEQI_PHOTO_STORAGE):
- "disk" (the default): data/uploads/<user_id>/<checkin>-<view>.jpg; the check-in row keeps the file name
  (checkins.photo_*_path). Deleting the account deletes the folder (app/accounts.py).
- "database": the photo_blobs table, for hosts whose disk is wiped on every deploy (Render's free plan). The check-in
  row keeps "db:<view>". Deleting the account deletes the rows (ON DELETE CASCADE).
"""

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import clock
from app.config import get_settings
from app.models import CheckIn, PhotoBlob

VIEWS = ("front", "side", "back")
MAX_BYTES = 8 * 1024 * 1024
# What the file starts with → its type. Only real photos are kept, whatever the request says.
MAGIC = ((b"\xff\xd8\xff", "jpg"), (b"\x89PNG\r\n\x1a\n", "png"), (b"RIFF", "webp"))
MEDIA = {"jpg": "image/jpeg", "png": "image/png", "webp": "image/webp"}
IN_DB = "db:"


class PhotoProblem(ValueError):
    pass


def kind_of(data: bytes) -> str:
    for start, ext in MAGIC:
        if data.startswith(start) and (ext != "webp" or data[8:12] == b"WEBP"):
            return ext
    raise PhotoProblem("not_a_photo")


def user_dir(user_id: str) -> Path:
    return get_settings().uploads_dir / user_id


def save_photo(db: Session, ci: CheckIn, view: str, data: bytes) -> str:
    """Saves (or replaces) one view's photo for this check-in and records it. Returns what the check-in row keeps."""
    if view not in VIEWS:
        raise PhotoProblem("unknown_view")
    if not data:
        raise PhotoProblem("empty")
    if len(data) > MAX_BYTES:
        raise PhotoProblem("too_large")
    ext = kind_of(data)
    old = getattr(ci, f"photo_{view}_path")
    if get_settings().photo_storage == "database":
        row = db.scalar(select(PhotoBlob).where(PhotoBlob.checkin_id == ci.id, PhotoBlob.view == view))
        if row is None:
            row = PhotoBlob(user_id=ci.user_id, checkin_id=ci.id, view=view, created_at=clock.now())
            db.add(row)
        row.content_type, row.data = MEDIA[ext], data
        name = IN_DB + view
    else:
        folder = user_dir(ci.user_id)
        folder.mkdir(parents=True, exist_ok=True)
        name = f"{ci.id}-{view}.{ext}"
        (folder / name).write_bytes(data)
    if old and old != name and not old.startswith(IN_DB):
        (user_dir(ci.user_id) / old).unlink(missing_ok=True)
    setattr(ci, f"photo_{view}_path", name)
    return name


def read_photo(db: Session, ci: CheckIn, view: str) -> tuple[bytes, str] | Path | None:
    """The photo for one view: its bytes and type (database), the file (disk, and only inside the person's own
    folder), or None."""
    name = getattr(ci, f"photo_{view}_path", None) if view in VIEWS else None
    if not name:
        return None
    if name.startswith(IN_DB):
        row = db.scalar(select(PhotoBlob).where(PhotoBlob.checkin_id == ci.id, PhotoBlob.view == view, PhotoBlob.user_id == ci.user_id))
        return (row.data, row.content_type) if row else None
    folder = user_dir(ci.user_id).resolve()
    path = (folder / name).resolve()
    return path if path.parent == folder and path.is_file() else None


def photo_url(ci: CheckIn, view: str) -> str:
    return f"/api/photos/{ci.id}/{view}"
