"""Progress photos from the weekly check-in: front, side and back.

Stored on disk under data/uploads/<user_id>/ (never in the database, never public), and served only to their owner
through GET /api/photos/{checkin_id}/{view}. The database keeps the file name per check-in (checkins.photo_*_path).
Deleting the account deletes the folder (app/accounts.py).
"""

from pathlib import Path

from app.config import get_settings
from app.models import CheckIn

VIEWS = ("front", "side", "back")
MAX_BYTES = 8 * 1024 * 1024
# What the file starts with → its type. Only real photos are kept, whatever the request says.
MAGIC = ((b"\xff\xd8\xff", "jpg"), (b"\x89PNG\r\n\x1a\n", "png"), (b"RIFF", "webp"))


class PhotoProblem(ValueError):
    pass


def kind_of(data: bytes) -> str:
    for start, ext in MAGIC:
        if data.startswith(start) and (ext != "webp" or data[8:12] == b"WEBP"):
            return ext
    raise PhotoProblem("not_a_photo")


def user_dir(user_id: str) -> Path:
    return get_settings().uploads_dir / user_id


def save_photo(ci: CheckIn, view: str, data: bytes) -> str:
    """Saves (or replaces) one view's photo for this check-in and records it. Returns the file name."""
    if view not in VIEWS:
        raise PhotoProblem("unknown_view")
    if not data:
        raise PhotoProblem("empty")
    if len(data) > MAX_BYTES:
        raise PhotoProblem("too_large")
    ext = kind_of(data)
    folder = user_dir(ci.user_id)
    folder.mkdir(parents=True, exist_ok=True)
    old = getattr(ci, f"photo_{view}_path")
    name = f"{ci.id}-{view}.{ext}"
    (folder / name).write_bytes(data)
    if old and old != name:
        (folder / old).unlink(missing_ok=True)
    setattr(ci, f"photo_{view}_path", name)
    return name


def photo_file(ci: CheckIn, view: str) -> Path | None:
    """The file on disk for one view, if there is one (and it really is inside the person's own folder)."""
    name = getattr(ci, f"photo_{view}_path", None) if view in VIEWS else None
    if not name:
        return None
    folder = user_dir(ci.user_id).resolve()
    path = (folder / name).resolve()
    return path if path.parent == folder and path.is_file() else None


def photo_url(ci: CheckIn, view: str) -> str:
    return f"/api/photos/{ci.id}/{view}"
