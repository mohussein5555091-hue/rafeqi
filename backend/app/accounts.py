"""Account logic, shared by the API and the admin scripts."""

import shutil
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import clock
from app.config import get_settings
from app.models import LoginAttempt, Profile, User, UserSession
from app.security import (
    burn_verify_time, hash_password, needs_rehash, new_session_token, normalise_email, sha256, verify_password,
)


class EmailTaken(Exception):
    pass


class TooManyAttempts(Exception):
    def __init__(self, retry_after_s: int):
        self.retry_after_s = retry_after_s


class InvalidCredentials(Exception):
    pass


@dataclass
class NewSession:
    token: str  # goes into the cookie; never stored
    session: UserSession


def create_user(db: Session, *, email: str, password: str, first_name: str) -> User:
    now = clock.now()
    user = User(email=normalise_email(email), password_hash=hash_password(password), first_name=first_name,
                adult_confirmed_at=now, created_at=now)
    db.add(user)
    try:
        db.flush()
    except IntegrityError as e:
        db.rollback()
        raise EmailTaken from e
    db.add(Profile(user_id=user.id, updated_at=now))
    return user


# ── Login rate limit ────────────────────────────────────────────────────────────
def _retry_after(db: Session, email_hash: str, ip: str) -> int | None:
    """Seconds until another login may be tried, or None if not blocked."""
    s = get_settings()
    now = clock.now()
    window_start = now - timedelta(minutes=s.login_window_minutes)
    last_success = db.scalar(select(func.max(LoginAttempt.attempted_at))
                             .where(LoginAttempt.email_hash == email_hash, LoginAttempt.success.is_(True)))
    since = max(window_start, last_success.replace(tzinfo=window_start.tzinfo)) if last_success else window_start

    def oldest_blocking(where, since_: datetime, limit: int) -> datetime | None:
        rows = db.scalars(select(LoginAttempt.attempted_at).where(where, LoginAttempt.success.is_(False),
                          LoginAttempt.attempted_at > since_).order_by(LoginAttempt.attempted_at.desc()).limit(limit)).all()
        return rows[-1] if len(rows) >= limit else None

    blockers = [t for t in (
        oldest_blocking(LoginAttempt.email_hash == email_hash, since, s.login_max_failures_per_email),
        oldest_blocking(LoginAttempt.ip == ip, window_start, s.login_max_failures_per_ip),
    ) if t]
    if not blockers:
        return None
    unblock_at = max(blockers).replace(tzinfo=now.tzinfo) + timedelta(minutes=s.login_window_minutes)
    return max(1, int((unblock_at - now).total_seconds()))


def authenticate(db: Session, *, email: str, password: str, ip: str) -> User:
    email = normalise_email(email)
    email_hash = sha256(email)
    retry = _retry_after(db, email_hash, ip)
    if retry:
        raise TooManyAttempts(retry)

    user = db.scalar(select(User).where(User.email == email))
    ok = verify_password(user.password_hash, password) if user else (burn_verify_time(password) or False)
    now = clock.now()
    db.add(LoginAttempt(email_hash=email_hash, ip=ip, success=ok, attempted_at=now))
    # Housekeeping: attempts older than a day are no longer needed.
    db.execute(delete(LoginAttempt).where(LoginAttempt.attempted_at < now - timedelta(days=1)))
    if not ok or user is None:
        db.commit()
        raise InvalidCredentials
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
    user.last_login_at = now
    return user


# ── Sessions ────────────────────────────────────────────────────────────────────
def start_session(db: Session, user: User, user_agent: str = "") -> NewSession:
    token = new_session_token()
    now = clock.now()
    sess = UserSession(user_id=user.id, token_hash=sha256(token), created_at=now, last_seen_at=now,
                       expires_at=now + timedelta(days=get_settings().session_days), user_agent=user_agent[:300])
    db.add(sess)
    return NewSession(token, sess)


def find_session(db: Session, token: str) -> UserSession | None:
    sess = db.scalar(select(UserSession).where(UserSession.token_hash == sha256(token)))
    if sess is None or sess.revoked_at is not None or sess.expires_at <= clock.now():
        return None
    return sess


def touch_session(sess: UserSession) -> bool:
    """Sliding expiry: each visit pushes expiry to 30 days from now (at most once an hour). True if extended."""
    now = clock.now()
    if now - sess.last_seen_at < timedelta(hours=1):
        return False
    sess.last_seen_at = now
    sess.expires_at = now + timedelta(days=get_settings().session_days)
    return True


def revoke_sessions(db: Session, user_id: str, *, except_id: str | None = None) -> int:
    q = update(UserSession).where(UserSession.user_id == user_id, UserSession.revoked_at.is_(None))
    if except_id:
        q = q.where(UserSession.id != except_id)
    return db.execute(q.values(revoked_at=clock.now())).rowcount


def set_password(db: Session, user: User, new_password: str, *, keep_session_id: str | None = None) -> None:
    """New password; every other session is logged out."""
    user.password_hash = hash_password(new_password)
    revoke_sessions(db, user.id, except_id=keep_session_id)


# ── Deleting an account ─────────────────────────────────────────────────────────
def delete_account(db: Session, user_id: str) -> None:
    """Deletes the user; the database cascades to every table holding their data.
    llm_calls rows stay with user_id = null (ON DELETE SET NULL) so AI usage totals stay correct."""
    db.execute(delete(User).where(User.id == user_id))
    db.commit()
    uploads = get_settings().uploads_dir / user_id
    if uploads.resolve().parent == get_settings().uploads_dir.resolve():  # only ever inside data/uploads/
        shutil.rmtree(uploads, ignore_errors=True)
