"""Injury input. Used by onboarding (Phase 3) and the injury screens (Phase 6).
painful_movements and restrictions must be ids from data/vocab/movements.yaml."""

from typing import Literal

from pydantic import Field, model_validator

from app.schemas.base import ApiModel
from app.vocab import get_vocab

BodyRegion = Literal[
    "head", "neck", "chest", "abdomen", "upperBack", "lowerBack", "shoulderL", "shoulderR", "armL", "armR",
    "forearmL", "forearmR", "hipL", "hipR", "thighL", "thighR", "kneeL", "kneeR", "shinL", "shinR", "ankleL", "ankleR",
]


class InjuryIn(ApiModel):
    region: BodyRegion
    side: Literal["left", "right", "both", "none"]
    type: Literal["joint", "tendon", "strain", "sprain", "postSurgery", "unsure"]
    severity: int = Field(ge=1, le=5)
    painful_movements: list[str] = Field(default_factory=list, max_length=20)
    restrictions: list[str] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def _vocab(self) -> "InjuryIn":
        get_vocab().check_injury(self.painful_movements, self.restrictions)
        return self
