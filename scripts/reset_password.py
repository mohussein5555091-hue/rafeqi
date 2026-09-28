"""Admin: set a new password for a user, from the terminal.

    npm run reset-password -- someone@example.com

You're asked for the new password twice (it isn't shown as you type). The person is logged out
everywhere and any login lock-out on their email is lifted. For scripts: add --password-stdin
and pipe the password in.
"""

import argparse
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from sqlalchemy import delete, select  # noqa: E402

from app.accounts import set_password  # noqa: E402
from app.db import SessionLocal  # noqa: E402
from app.models import LoginAttempt, User  # noqa: E402
from app.security import normalise_email, password_ok, sha256  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Set a new password for a Rafeqi user.")
    parser.add_argument("email")
    parser.add_argument("--password-stdin", action="store_true", help="read the new password from standard input")
    args = parser.parse_args(argv)
    email = normalise_email(args.email)

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            print(f"No account with the email {email}.", file=sys.stderr)
            return 1

        if args.password_stdin:
            password = sys.stdin.readline().rstrip("\r\n")
        else:
            password = getpass.getpass("New password: ")
            if getpass.getpass("Type it again: ") != password:
                print("The two passwords don't match. Nothing changed.", file=sys.stderr)
                return 1
        if not password_ok(password):
            print("Use at least 8 characters with one number. Nothing changed.", file=sys.stderr)
            return 1

        set_password(db, user, password)  # also logs them out on every device
        db.execute(delete(LoginAttempt).where(LoginAttempt.email_hash == sha256(email), LoginAttempt.success.is_(False)))
        db.commit()
    print(f"Password changed for {email}. They've been logged out everywhere and can log in with the new password.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
