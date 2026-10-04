"""The logged-in person's account: read, update, delete."""

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy.orm import Session

from app import accounts, clock
from app.api.deps import CurrentAuth, Db, clear_session_cookie
from app.engine.catalogue import exercises_from_db
from app.engine.rules import load_rules
from app.models import Profile, User
from app.plans import active_swaps, current_plan, rebuild_plan
from app.schemas.account import EquipmentIn, MeOut, MePatch
from app.vocab import get_vocab

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


# ── Equipment: what the training place has, and what the person said isn't available ──

def _equipment_out(profile: Profile) -> dict:
    labels = get_vocab().data["equipment"]
    have = [e for e in load_rules()["training"]["equipment_by_location"].get(profile.location or "gym", []) if e != "bodyweight"]
    missing = set(profile.missing_equipment or [])
    return {"location": profile.location,
            "items": [{"id": e, "name": {"en": labels[e]["en"], "ar": labels[e]["ar"]}, "available": e not in missing} for e in have]}


@router.get("/equipment")
def get_equipment(auth: CurrentAuth, db: Db):
    """The equipment where the person trains (bodyweight is always there), each marked available or missing."""
    profile = db.get(Profile, auth.user.id)
    if profile is None or profile.location is None:
        raise HTTPException(409, "onboarding_incomplete")
    return _equipment_out(profile)


@router.put("/equipment")
def save_equipment(body: EquipmentIn, auth: CurrentAuth, db: Db):
    """Saves what's missing and rebuilds the plan around it (the week's meals stay). Equipment that's available again
    also ends the "from now on" swaps made because it was missing, so those exercises come back."""
    profile = db.get(Profile, auth.user.id)
    if profile is None or profile.location is None:
        raise HTTPException(409, "onboarding_incomplete")
    offered = set(load_rules()["training"]["equipment_by_location"][profile.location]) - {"bodyweight"}
    if bad := sorted(set(body.missing) - offered):
        raise HTTPException(422, {"error": "unknown_equipment", "equipment": bad})
    before = set(profile.missing_equipment or [])
    profile.missing_equipment = sorted(set(body.missing))
    back = before - set(body.missing)
    if back:
        cat = exercises_from_db(db)
        for s in active_swaps(db, auth.user.id):
            if s.reason == "equipment" and s.from_exercise_id in cat and set(cat[s.from_exercise_id].equipment) & back:
                s.ended_at = clock.now()
    db.flush()
    if before != set(body.missing):
        rebuild_plan(db, auth.user.id, "equipment")
    db.commit()
    return _equipment_out(profile)
