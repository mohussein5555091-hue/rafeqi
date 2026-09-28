"""scripts/reset_password.py: the admin's way to set a new password (email reset comes later)."""

import importlib.util
import io
from pathlib import Path

import pytest

from tests_helpers import COOKIE

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "reset_password.py"


@pytest.fixture
def script(SessionTest, monkeypatch):
    spec = importlib.util.spec_from_file_location("reset_password", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    monkeypatch.setattr(mod, "SessionLocal", SessionTest)
    return mod


def run(script, monkeypatch, email: str, password: str) -> int:
    monkeypatch.setattr("sys.stdin", io.StringIO(password + "\n"))
    return script.main([email, "--password-stdin"])


def test_reset_sets_password_logs_out_everywhere_and_lifts_lockout(script, monkeypatch, make_user, client_factory, capsys):
    u = make_user("forgot@example.com")
    c = client_factory()
    for _ in range(5):
        c.post("/api/auth/login", json={"email": u.email, "password": "wrong-123"})
    assert c.post("/api/auth/login", json={"email": u.email, "password": u.password}).status_code == 429

    assert run(script, monkeypatch, "Forgot@Example.com", "brand-new-9") == 0
    assert "Password changed for forgot@example.com" in capsys.readouterr().out
    assert u.client.get("/api/me").status_code == 401  # logged out everywhere
    assert client_factory().post("/api/auth/login", json={"email": u.email, "password": "brand-new-9"}).status_code == 200


def test_reset_refuses_unknown_email_and_weak_password(script, monkeypatch, make_user, capsys):
    u = make_user()
    assert run(script, monkeypatch, "nobody@example.com", "brand-new-9") == 1
    assert run(script, monkeypatch, u.email, "weak") == 1
    err = capsys.readouterr().err
    assert "No account with the email nobody@example.com" in err and "at least 8 characters" in err
    assert u.client.get("/api/me").status_code == 200  # nothing changed
    assert u.client.cookies.get(COOKIE)
