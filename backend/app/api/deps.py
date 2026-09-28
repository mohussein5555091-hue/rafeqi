"""Shared request dependencies: the database session and the logged-in user."""

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from app.accounts import find_session, touch_session
from app.config import get_settings
from app.db import get_db
from app.models import User, UserSession

Db = Annotated[Session, Depends(get_db)]


def set_session_cookie(response: Response, token: str) -> None:
    s = get_settings()
    response.set_cookie(
        s.session_cookie, token, max_age=s.session_days * 86400, path="/",
        httponly=True,  # page scripts can't read it
        samesite="lax",  # not sent on form posts or scripted requests from other sites
        secure=s.is_production,  # https-only in production
    )


def clear_session_cookie(response: Response) -> None:
    s = get_settings()
    response.delete_cookie(s.session_cookie, path="/", httponly=True, samesite="lax", secure=s.is_production)


@dataclass
class Auth:
    user: User
    session: UserSession


def current_auth(request: Request, response: Response, db: Db) -> Auth:
    """401 unless a valid, unexpired, not-logged-out session cookie is present."""
    token = request.cookies.get(get_settings().session_cookie)
    sess = find_session(db, token) if token else None
    user = db.get(User, sess.user_id) if sess else None
    if sess is None or user is None:
        raise HTTPException(401, "not_logged_in")
    if touch_session(sess):
        db.commit()
        set_session_cookie(response, token)
    return Auth(user, sess)


CurrentAuth = Annotated[Auth, Depends(current_auth)]


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"
