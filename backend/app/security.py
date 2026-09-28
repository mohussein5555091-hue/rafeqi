"""Passwords (argon2id) and session tokens."""

import hashlib
import re
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

_hasher = PasswordHasher()  # argon2id with the library's recommended cost settings

PASSWORD_MIN = 8
PASSWORD_MAX = 128
# Same rule as the sign-up screen: at least 8 characters with one number.
PASSWORD_RULE = re.compile(r"^(?=.*\d).{8,128}$", re.S)


def password_ok(password: str) -> bool:
    return bool(PASSWORD_RULE.match(password))


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


# Used when the email doesn't exist, so a wrong email takes as long as a wrong password
# (otherwise response time would reveal which emails have accounts).
_DUMMY_HASH = _hasher.hash("timing-equaliser-not-a-real-password-1")


def burn_verify_time(password: str) -> None:
    verify_password(_DUMMY_HASH, password)


def needs_rehash(password_hash: str) -> bool:
    return _hasher.check_needs_rehash(password_hash)


def new_session_token() -> str:
    return secrets.token_urlsafe(32)  # 256 bits of randomness


def sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def normalise_email(email: str) -> str:
    return email.strip().lower()
