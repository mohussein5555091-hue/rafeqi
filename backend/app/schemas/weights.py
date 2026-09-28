import datetime as dt
from typing import Literal

from pydantic import Field, field_validator

from app import clock
from app.schemas.base import ApiModel


class WeightIn(ApiModel):
    weight_kg: float = Field(ge=30, le=300)
    date: dt.date | None = None  # defaults to today

    @field_validator("date")
    @classmethod
    def _not_future(cls, v: dt.date | None) -> dt.date | None:
        # One day of slack for time zones (Cairo is ahead of UTC).
        if v is not None and v > clock.today() + dt.timedelta(days=1):
            raise ValueError("date_in_future")
        return v


class WeightOut(ApiModel):
    id: str
    date: dt.date
    weight_kg: float
    source: Literal["daily", "checkin"]
