"""Production mode: the built frontend at the same address as the API, https only, security headers, and a real
secret key required. (Development and the other tests run without any of this.)"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import Settings, get_settings, normalize_db_url
from app.main import add_frontend, app


@pytest.fixture
def production(monkeypatch):
    monkeypatch.setattr(get_settings(), "env", "production")


def test_http_is_redirected_to_https_in_production(production):
    c = TestClient(app, base_url="http://rafeqi.example")
    r = c.get("/api/me", follow_redirects=False)
    assert r.status_code == 308 and r.headers["location"] == "https://rafeqi.example/api/me"
    assert c.get("/api/health").status_code == 200  # the host's health check calls the app directly over http


def test_https_answers_carry_security_headers(production):
    r = TestClient(app, base_url="https://rafeqi.example").get("/api/health")
    assert r.headers["strict-transport-security"].startswith("max-age=")
    assert (r.headers["x-content-type-options"], r.headers["x-frame-options"]) == ("nosniff", "DENY")


def test_session_cookie_is_https_only_in_production(production, client_factory):
    c = client_factory()
    c.base_url = "https://testserver"
    r = c.post("/api/auth/signup", json={"firstName": "A", "email": "p@example.com", "password": "correct-horse-1", "adultConfirmed": True})
    assert r.status_code == 201
    cookie = r.headers["set-cookie"].lower()
    assert "secure" in cookie and "httponly" in cookie and "samesite=lax" in cookie


def test_development_has_none_of_it():
    r = TestClient(app, base_url="http://testserver").get("/api/health")
    assert r.status_code == 200 and "strict-transport-security" not in r.headers


def test_a_real_secret_key_is_required_in_production():
    with pytest.raises(RuntimeError, match="RAFEQI_SECRET_KEY"):
        Settings(env="production", secret_key="dev-only-change-me").check_production()
    with pytest.raises(RuntimeError):
        Settings(env="production", secret_key="short").check_production()
    Settings(env="production", secret_key="x" * 48).check_production()
    Settings(env="development").check_production()  # anything goes locally


def test_hosted_database_urls_get_the_driver():
    assert normalize_db_url("postgres://u:p@host/db") == "postgresql+psycopg://u:p@host/db"
    assert normalize_db_url("postgresql://u:p@host/db?sslmode=require") == "postgresql+psycopg://u:p@host/db?sslmode=require"
    assert normalize_db_url("postgresql+psycopg://u@h/db") == "postgresql+psycopg://u@h/db"
    assert normalize_db_url("sqlite:///x.db") == "sqlite:///x.db"
    assert Settings(database_url="postgres://u:p@h/db").database_url.startswith("postgresql+psycopg://")


def test_the_built_frontend_is_served_with_the_api(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<!doctype html><title>Rafeqi</title>")
    (tmp_path / "assets" / "app-1a2b.js").write_text("console.log(1)")
    (tmp_path / "manifest.webmanifest").write_text("{}")
    web = FastAPI()

    @web.get("/api/health")
    def health():
        return {"status": "ok"}

    add_frontend(web, tmp_path)
    c = TestClient(web)
    assert c.get("/api/health").json() == {"status": "ok"}
    page = c.get("/workouts/abc")  # any screen: the app itself, which shows it
    assert page.status_code == 200 and "Rafeqi" in page.text and page.headers["cache-control"] == "no-cache"
    js = c.get("/assets/app-1a2b.js")
    assert js.status_code == 200 and "immutable" in js.headers["cache-control"]
    assert c.get("/manifest.webmanifest").headers["cache-control"] == "no-cache"
    assert c.get("/api/nope").status_code == 404  # unknown API paths stay 404, never the app
    assert c.get("/../../etc/passwd").status_code in (200, 404) and "root:" not in c.get("/../../etc/passwd").text
