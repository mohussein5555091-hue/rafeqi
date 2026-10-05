"""Lists the messages people sent with "Send feedback" in Profile & settings, newest first:

    npm run feedback                 # the last 50
    npm run feedback -- --all
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from sqlalchemy import select  # noqa: E402

from app.db import SessionLocal  # noqa: E402
from app.models import Feedback, User  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="List feedback messages, newest first.")
    p.add_argument("--all", action="store_true", help="every message, not just the last 50")
    args = p.parse_args(argv)
    with SessionLocal() as db:
        q = select(Feedback, User.first_name, User.email).join(User, User.id == Feedback.user_id).order_by(Feedback.created_at.desc())
        rows = db.execute(q if args.all else q.limit(50)).all()
    if not rows:
        print("No feedback yet.")
    for f, name, email in rows:
        print(f"{f.created_at:%Y-%m-%d %H:%M} · {name} <{email}> · {f.page or '-'}\n  {f.message}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
