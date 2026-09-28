"""Daily body weight (the dashboard's "log today's weight")."""

import datetime as dt

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app import clock
from app.api.deps import CurrentAuth, Db
from app.models import WeightLog
from app.schemas.weights import WeightIn, WeightOut
from app.weights import record_weight, weights_between

router = APIRouter(prefix="/api/weights", tags=["weights"])


@router.get("", response_model=list[WeightOut])
def list_weights(auth: CurrentAuth, db: Db, start: dt.date | None = None, end: dt.date | None = None):
    return weights_between(db, auth.user.id, start, end)


@router.post("", response_model=WeightOut)
def log_weight(body: WeightIn, auth: CurrentAuth, db: Db):
    row = record_weight(db, auth.user.id, body.date or clock.today(), body.weight_kg, "daily")
    db.commit()
    return row


@router.delete("/{weight_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_weight(weight_id: str, auth: CurrentAuth, db: Db):
    # Filtering by user_id means another person's id is simply not found: 404, with no hint that it exists.
    row = db.scalar(select(WeightLog).where(WeightLog.id == weight_id, WeightLog.user_id == auth.user.id))
    if row is None:
        raise HTTPException(404, "not_found")
    db.delete(row)
    db.commit()
