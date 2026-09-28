"""Sign up, log in, log out, change password."""

from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse

from app import accounts, clock
from app.api.deps import CurrentAuth, Db, clear_session_cookie, client_ip, set_session_cookie
from app.api.me import me_out
from app.schemas.account import ChangePasswordIn, LoginIn, MeOut, SignupIn
from app.security import verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/signup", status_code=status.HTTP_201_CREATED, response_model=MeOut)
def signup(body: SignupIn, request: Request, response: Response, db: Db):
    try:
        user = accounts.create_user(db, email=body.email, password=body.password, first_name=body.first_name)
    except accounts.EmailTaken:
        raise HTTPException(409, "email_taken") from None
    new = accounts.start_session(db, user, request.headers.get("user-agent", ""))
    db.commit()
    set_session_cookie(response, new.token)
    return me_out(db, user)


@router.post("/login", response_model=MeOut)
def login(body: LoginIn, request: Request, response: Response, db: Db):
    try:
        user = accounts.authenticate(db, email=body.email, password=body.password, ip=client_ip(request))
    except accounts.TooManyAttempts as e:
        return JSONResponse({"detail": "too_many_attempts"}, status_code=429, headers={"Retry-After": str(e.retry_after_s)})
    except accounts.InvalidCredentials:
        # The same answer for "no such email" and "wrong password".
        raise HTTPException(401, "invalid_credentials") from None
    new = accounts.start_session(db, user, request.headers.get("user-agent", ""))
    db.commit()
    set_session_cookie(response, new.token)
    return me_out(db, user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(auth: CurrentAuth, response: Response, db: Db):
    auth.session.revoked_at = clock.now()
    db.commit()
    clear_session_cookie(response)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(body: ChangePasswordIn, auth: CurrentAuth, db: Db):
    if not verify_password(auth.user.password_hash, body.current_password):
        raise HTTPException(400, "wrong_current_password")
    accounts.set_password(db, auth.user, body.new_password, keep_session_id=auth.session.id)
    db.commit()
