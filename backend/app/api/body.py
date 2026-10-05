"""Injuries, the weekly check-in, weekly reviews and progress."""

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import FileResponse, Response
from sqlalchemy import select

from app import clock
from app.api.deps import CurrentAuth, Db
from app.api.training import current_week
from app.engine.checkin import load_questions
from app.engine.meals import NoMealPlan
from app.models import CheckIn, Injury, Profile, WeeklyReview
from app.photos import MAX_BYTES, PhotoProblem, read_photo, save_photo
from app.plans import NotReady, rebuild_plan, run_weekly_review
from app.schemas.screens import CheckInIn, InjurySaveIn
from app.views import body as v
from app.week import NoPlan, this_week

router = APIRouter(tags=["body"])


def _week_or_none(db, user_id: str):
    try:
        return this_week(db, user_id)
    except NoPlan:
        return None


def _injury(db, user_id: str, injury_id: str) -> Injury:
    inj = db.scalar(select(Injury).where(Injury.id == injury_id, Injury.user_id == user_id))
    if inj is None:
        raise HTTPException(404, "not_found")
    return inj


# ── Injuries ──

@router.get("/api/injuries")
def list_injuries(auth: CurrentAuth, db: Db):
    week = _week_or_none(db, auth.user.id)
    rows = db.scalars(select(Injury).where(Injury.user_id == auth.user.id).order_by(Injury.created_at))
    return [v.injury_out(db, i, week) for i in rows]


@router.get("/api/injuries/{injury_id}")
def get_injury(injury_id: str, auth: CurrentAuth, db: Db):
    return v.injury_out(db, _injury(db, auth.user.id, injury_id), _week_or_none(db, auth.user.id))


def _region_free(db, user_id: str, region: str, except_id: str | None = None) -> None:
    """One open injury per body area (as in onboarding)."""
    q = select(Injury.id).where(Injury.user_id == user_id, Injury.region == region, Injury.status != "resolved")
    if except_id:
        q = q.where(Injury.id != except_id)
    if db.scalar(q):
        raise HTTPException(409, "region_taken")


def _fill(inj: Injury, body: InjurySaveIn) -> None:
    inj.side, inj.type, inj.severity, inj.status = body.side, body.type, body.severity, body.status
    inj.painful_movements, inj.restrictions, inj.updated_at = body.painful_movements, body.restrictions, clock.now()


@router.post("/api/injuries", status_code=status.HTTP_201_CREATED)
def add_injury(body: InjurySaveIn, auth: CurrentAuth, db: Db):
    """Adds an injury and rebuilds the plan around it."""
    if body.status != "resolved":
        _region_free(db, auth.user.id, body.region)
    inj = Injury(user_id=auth.user.id, region=body.region, since=clock.today(), created_at=clock.now())
    _fill(inj, body)
    db.add(inj)
    db.flush()
    rebuild_plan(db, auth.user.id, "injury")
    db.commit()
    return v.injury_out(db, inj, _week_or_none(db, auth.user.id))


@router.put("/api/injuries/{injury_id}")
def update_injury(injury_id: str, body: InjurySaveIn, auth: CurrentAuth, db: Db):
    """Edits an injury (the area can't change) and rebuilds the plan. Saving it also lifts a pause: the screen asks
    for this after "I've had it checked by a professional"."""
    inj = _injury(db, auth.user.id, injury_id)
    if body.region != inj.region:
        raise HTTPException(422, "region_cannot_change")
    if body.status != "resolved":
        _region_free(db, auth.user.id, inj.region, except_id=inj.id)
    _fill(inj, body)
    inj.paused_at = None
    db.flush()
    rebuild_plan(db, auth.user.id, "injury")
    db.commit()
    return v.injury_out(db, inj, _week_or_none(db, auth.user.id))


@router.delete("/api/injuries/{injury_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_injury(injury_id: str, auth: CurrentAuth, db: Db):
    db.delete(_injury(db, auth.user.id, injury_id))
    db.flush()
    rebuild_plan(db, auth.user.id, "injury")
    db.commit()


# ── Weekly check-in ──

@router.get("/api/checkins/questions")
def checkin_questions(auth: CurrentAuth):
    """The check-in's fixed questions from data/checkin_questions.yaml: wording (en, ar), type, ranges and options.
    The screens show this wording, so changing the file changes the questions without a code change."""
    data = load_questions()
    keys = {"min": "min", "max": "max", "max_from": "maxFrom", "step_size": "stepSize", "options": "options", "max_length": "maxLength",
            "trend_options": "trendOptions"}
    return {"steps": data["steps"],
            "questions": [{"id": q["id"], "step": q["step"], "type": q["type"], "text": {"en": q["en"], "ar": q["ar"]},
                           "required": bool(q.get("required")), **{out: q[k] for k, out in keys.items() if k in q}}
                          for q in data["questions"]]}


@router.get("/api/checkins/next")
def next_checkin(auth: CurrentAuth, db: Db):
    """When the next weekly check-in opens, and whether one is due now."""
    return v.next_checkin(db, auth.user.id, clock.today())


@router.get("/api/checkins/draft")
def checkin_draft(auth: CurrentAuth, db: Db):
    week = current_week(db, auth.user.id)
    return v.checkin_draft(db, auth.user.id, week, db.get(Profile, auth.user.id).weight_kg)


@router.post("/api/checkins", status_code=status.HTTP_201_CREATED)
def submit_checkin(body: CheckInIn, auth: CurrentAuth, db: Db):
    """Saves this week's check-in and runs the weekly review, which builds next week's plan. One check-in a week."""
    uid = auth.user.id
    week = current_week(db, uid)
    if v.submitted_checkin(db, uid, week.start):
        raise HTTPException(409, "already_checked_in")
    try:
        ci = v.save_checkin(db, uid, week, v.answers_from(body))
        review = run_weekly_review(db, uid, ci.id)
    except v.CheckInProblem as e:
        raise HTTPException(422, {"error": "invalid_answers", "problems": e.problems}) from e
    except (NotReady, NoMealPlan):
        raise HTTPException(409, "no_plan_yet") from None
    db.commit()
    return {"reviewId": review.id, "checkinId": ci.id}


# ── Progress photos (private: stored under data/uploads/<user_id>/, served only to their owner) ──

def _checkin(db, user_id: str, checkin_id: str) -> CheckIn:
    ci = db.scalar(select(CheckIn).where(CheckIn.id == checkin_id, CheckIn.user_id == user_id))
    if ci is None:
        raise HTTPException(404, "not_found")
    return ci


@router.put("/api/checkins/{checkin_id}/photos/{view}", status_code=status.HTTP_204_NO_CONTENT)
async def upload_photo(checkin_id: str, view: str, request: Request, auth: CurrentAuth, db: Db):
    """One progress photo (front, side or back) for one of the person's check-ins: the request body is the image
    itself (JPEG, PNG or WebP, at most 8 MB). Sending it again replaces it."""
    ci = _checkin(db, auth.user.id, checkin_id)
    if int(request.headers.get("content-length") or 0) > MAX_BYTES:
        raise HTTPException(413, "too_large")
    try:
        save_photo(db, ci, view, await request.body())
    except PhotoProblem as e:
        raise HTTPException(413 if str(e) == "too_large" else 422, str(e)) from None
    db.commit()


@router.get("/api/photos/{checkin_id}/{view}")
def get_photo(checkin_id: str, view: str, auth: CurrentAuth, db: Db):
    """A progress photo, only for its owner (anyone else gets 404). Never cached by shared caches."""
    found = read_photo(db, _checkin(db, auth.user.id, checkin_id), view)
    if found is None:
        raise HTTPException(404, "not_found")
    headers = {"Cache-Control": "private, no-store"}
    if isinstance(found, tuple):
        return Response(found[0], media_type=found[1], headers=headers)
    return FileResponse(found, headers=headers)


# ── Reviews & progress ──

@router.get("/api/reviews")
def list_reviews(auth: CurrentAuth, db: Db):
    return v.reviews_out(db, auth.user.id)


@router.get("/api/reviews/{review_id}")
def get_review(review_id: str, auth: CurrentAuth, db: Db):
    r = db.scalar(select(WeeklyReview).where(WeeklyReview.id == review_id, WeeklyReview.user_id == auth.user.id))
    if r is None:
        raise HTTPException(404, "not_found")
    return v.review_out(db, r)


@router.get("/api/progress")
def get_progress(auth: CurrentAuth, db: Db):
    since = v.first_plan_date(db, auth.user.id) or auth.user.created_at.date()
    return v.progress_out(db, auth.user.id, since)
