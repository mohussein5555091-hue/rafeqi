"""Small helpers shared by the backend tests."""

from app.config import get_settings

COOKIE = get_settings().session_cookie


def signup_body(email: str = "new@example.com", **overrides) -> dict:
    return {"firstName": "Omar", "email": email, "password": "correct-horse-1", "adultConfirmed": True} | overrides


def cookie_header(response) -> str:
    return response.headers.get("set-cookie", "").lower()
