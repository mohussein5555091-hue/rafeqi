import datetime as dt
from typing import Literal

from pydantic import EmailStr, Field, field_validator

from app.schemas.base import ApiModel
from app.security import PASSWORD_MAX, password_ok

Name = Field(min_length=1, max_length=80)


def _check_password(v: str) -> str:
    if not password_ok(v):
        raise ValueError("password_rules")  # 8+ characters with at least one number
    return v


class SignupIn(ApiModel):
    first_name: str = Name
    email: EmailStr
    password: str = Field(max_length=PASSWORD_MAX)
    adult_confirmed: bool  # "I'm 18 or older and I understand…"

    _pw = field_validator("password")(_check_password)

    @field_validator("first_name")
    @classmethod
    def _strip(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("first_name_required")
        return v.strip()

    @field_validator("adult_confirmed")
    @classmethod
    def _adult(cls, v: bool) -> bool:
        if not v:
            raise ValueError("must_be_adult")
        return v


class LoginIn(ApiModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=PASSWORD_MAX)


class ChangePasswordIn(ApiModel):
    current_password: str = Field(max_length=PASSWORD_MAX)
    new_password: str = Field(max_length=PASSWORD_MAX)

    _pw = field_validator("new_password")(_check_password)


class MeOut(ApiModel):
    id: str
    email: str
    first_name: str
    last_name: str
    language: Literal["en", "ar"]
    theme: Literal["light", "dark", "system"]
    member_since: dt.date
    onboarding_complete: bool
    has_plan: bool = False


class MePatch(ApiModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=80)
    last_name: str | None = Field(default=None, max_length=80)
    language: Literal["en", "ar"] | None = None
    theme: Literal["light", "dark", "system"] | None = None


class EquipmentIn(ApiModel):
    """The equipment the person doesn't have where they train (ids from data/vocab/movements.yaml)."""

    missing: list[str] = Field(default_factory=list, max_length=20)
