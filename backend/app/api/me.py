"""The logged-in person's account: read, update, delete."""

from fastapi import APIRouter, Response, status
from sqlalchemy.orm import Session

from app import accounts
from app.api.deps import CurrentAuth, Db, clear_session_cookie
from app.models import Profile, User
from app.plans import current_plan
from app.schemas.account import MeOut, MePatch

router = APIRouter(prefix="/api/me", tags=["me"])


def me_out(db: Session, user: User) -> MeOut:
    profile = db.get(Profile, user.id)
    return MeOut(id=user.id, email=user.email, first_name=user.first_name, last_name=user.last_name,
                 language=user.language, theme=user.theme, member_since=user.created_at.date(),
                 onboarding_complete=bool(profile and profile.completed_at),
                 has_plan=current_plan(db, user.id) is not None)


@router.get("", response_model=MeOut)
def get_me(auth: CurrentAuth, db: Db):
    return me_out(db, auth.user)


@router.patch("", response_model=MeOut)
def update_me(body: MePatch, auth: CurrentAuth, db: Db):
    for field, value in body.model_dump(exclude_unset=True, exclude_none=True).items():
        setattr(auth.user, field, value.strip() if field.endswith("name") else value)
    db.commit()
    return me_out(db, auth.user)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def delete_me(auth: CurrentAuth, response: Response, db: Db):
    """Deletes the account and all its data, including progress photos on disk."""
    accounts.delete_account(db, auth.user.id)
    clear_session_cookie(response)
