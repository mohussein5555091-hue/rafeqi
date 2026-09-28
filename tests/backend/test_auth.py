"""Sign up, log in, log out, change password, sessions and the login rate limit."""

from sqlalchemy import select

from app.config import get_settings
from app.models import User, UserSession
from tests_helpers import COOKIE, cookie_header, signup_body

PW = "correct-horse-1"


# ── Sign up ─────────────────────────────────────────────────────────────────────
def test_signup_logs_you_in_with_a_safe_cookie(client_factory):
    c = client_factory()
    r = c.post("/api/auth/signup", json=signup_body("Mona@Example.com"))
    assert r.status_code == 201
    me = r.json()
    assert me["email"] == "mona@example.com"  # stored lowercase
    assert me["onboardingComplete"] is False
    cookie = cookie_header(r)
    assert "httponly" in cookie and "samesite=lax" in cookie and "path=/" in cookie
    assert c.get("/api/me").json()["id"] == me["id"]


def test_signup_rules(client_factory):
    c = client_factory()
    cases = {
        "under 18 box not ticked": signup_body(adultConfirmed=False),
        "password without a number": signup_body(password="onlyletters"),
        "password too short": signup_body(password="abc1"),
        "not an email": signup_body("not-an-email"),
        "blank first name": signup_body(firstName="   "),
    }
    for label, body in cases.items():
        assert c.post("/api/auth/signup", json=body).status_code == 422, label


def test_email_can_only_be_used_once_ignoring_case(client_factory):
    c = client_factory()
    assert c.post("/api/auth/signup", json=signup_body("sara@example.com")).status_code == 201
    r = client_factory().post("/api/auth/signup", json=signup_body("SARA@example.com"))
    assert (r.status_code, r.json()["detail"]) == (409, "email_taken")


def test_password_and_session_token_are_never_stored_in_plain_text(make_user, db):
    u = make_user()
    user = db.get(User, u.id)
    assert user.password_hash.startswith("$argon2id$") and PW not in user.password_hash
    token = u.client.cookies.get(COOKIE)
    sess = db.scalar(select(UserSession).where(UserSession.user_id == u.id))
    assert token and sess.token_hash != token and len(sess.token_hash) == 64


# ── Log in / log out ────────────────────────────────────────────────────────────
def test_login_and_wrong_details_get_the_same_answer(make_user, client_factory):
    u = make_user("ali@example.com")
    c = client_factory()
    ok = c.post("/api/auth/login", json={"email": "ALI@example.com ", "password": PW})
    assert ok.status_code == 200 and ok.json()["id"] == u.id
    wrong_pw = client_factory().post("/api/auth/login", json={"email": "ali@example.com", "password": "nope-1234"})
    no_user = client_factory().post("/api/auth/login", json={"email": "ghost@example.com", "password": "nope-1234"})
    assert wrong_pw.status_code == no_user.status_code == 401
    assert wrong_pw.json() == no_user.json() == {"detail": "invalid_credentials"}


def test_logout_ends_that_session_only(make_user, client_factory):
    u = make_user()
    other = client_factory()
    other.post("/api/auth/login", json={"email": u.email, "password": PW})
    old_token = u.client.cookies.get(COOKIE)
    assert u.client.post("/api/auth/logout").status_code == 204
    assert u.client.get("/api/me").status_code == 401
    # Replaying the old cookie doesn't work either: the session is revoked on the server.
    replay = client_factory()
    replay.cookies.set(COOKIE, old_token)
    assert replay.get("/api/me").status_code == 401
    assert other.get("/api/me").status_code == 200


def test_every_private_endpoint_needs_login(client_factory):
    c = client_factory()
    public = {("get", "/api/health"), ("post", "/api/auth/signup"), ("post", "/api/auth/login")}
    for path, ops in c.app.openapi()["paths"].items():
        for method in ops:
            if (method, path) in public:
                continue
            url = path.replace("{", "").replace("}", "")  # any value: we must be stopped before it's used
            r = c.request(method.upper(), url, json={})
            assert r.status_code == 401, f"{method.upper()} {path} answered {r.status_code} without login"


# ── Sessions ────────────────────────────────────────────────────────────────────
def test_session_lasts_30_days_and_each_visit_extends_it(make_user, clock):
    u = make_user()
    clock.advance(days=20)
    assert u.client.get("/api/me").status_code == 200  # extends to day 50
    clock.advance(days=20)
    assert u.client.get("/api/me").status_code == 200
    clock.advance(days=31)
    assert u.client.get("/api/me").status_code == 401


# ── Change password ─────────────────────────────────────────────────────────────
def test_change_password_logs_out_other_devices(make_user, client_factory):
    u = make_user()
    phone = client_factory()
    phone.post("/api/auth/login", json={"email": u.email, "password": PW})

    wrong = u.client.post("/api/auth/change-password", json={"currentPassword": "wrong-1", "newPassword": "new-pass-2"})
    assert (wrong.status_code, wrong.json()["detail"]) == (400, "wrong_current_password")
    assert u.client.post("/api/auth/change-password", json={"currentPassword": PW, "newPassword": "short"}).status_code == 422

    assert u.client.post("/api/auth/change-password", json={"currentPassword": PW, "newPassword": "new-pass-2"}).status_code == 204
    assert u.client.get("/api/me").status_code == 200  # this device stays in
    assert phone.get("/api/me").status_code == 401  # the other one is out
    assert client_factory().post("/api/auth/login", json={"email": u.email, "password": PW}).status_code == 401
    assert client_factory().post("/api/auth/login", json={"email": u.email, "password": "new-pass-2"}).status_code == 200


# ── Login rate limit ────────────────────────────────────────────────────────────
def test_five_wrong_passwords_lock_that_email_for_15_minutes(make_user, client_factory, clock):
    u = make_user()
    c = client_factory()
    for _ in range(5):
        assert c.post("/api/auth/login", json={"email": u.email, "password": "wrong-123"}).status_code == 401
    blocked = c.post("/api/auth/login", json={"email": u.email, "password": PW})  # even the right password
    assert blocked.status_code == 429 and blocked.json()["detail"] == "too_many_attempts"
    assert 0 < int(blocked.headers["Retry-After"]) <= 15 * 60
    clock.advance(minutes=15, seconds=1)
    assert c.post("/api/auth/login", json={"email": u.email, "password": PW}).status_code == 200


def test_a_successful_login_resets_the_count(make_user, client_factory, clock):
    u = make_user()
    c = client_factory()
    for _ in range(4):
        c.post("/api/auth/login", json={"email": u.email, "password": "wrong-123"})
    clock.advance(seconds=1)
    assert c.post("/api/auth/login", json={"email": u.email, "password": PW}).status_code == 200
    clock.advance(seconds=1)
    for _ in range(4):
        assert c.post("/api/auth/login", json={"email": u.email, "password": "wrong-123"}).status_code == 401


def test_one_ip_address_is_limited_across_many_emails(client_factory):
    c = client_factory()
    limit = get_settings().login_max_failures_per_ip
    for i in range(limit):
        assert c.post("/api/auth/login", json={"email": f"guess{i}@example.com", "password": "x1234567"}).status_code == 401
    assert c.post("/api/auth/login", json={"email": "another@example.com", "password": "x1234567"}).status_code == 429


# ── Account settings and cross-site protection ──────────────────────────────────
def test_update_language_and_theme(make_user):
    u = make_user()
    r = u.client.patch("/api/me", json={"language": "ar", "theme": "dark", "lastName": " Hassan "})
    assert r.status_code == 200 and (r.json()["language"], r.json()["theme"], r.json()["lastName"]) == ("ar", "dark", "Hassan")
    assert u.client.patch("/api/me", json={"theme": "purple"}).status_code == 422
    assert u.client.patch("/api/me", json={"email": "new@example.com"}).status_code == 422  # not changeable here


def test_changes_from_another_website_are_refused(make_user):
    u = make_user()
    evil = u.client.patch("/api/me", json={"language": "ar"}, headers={"Origin": "https://evil.example"})
    assert (evil.status_code, evil.json()["detail"]) == (403, "cross_origin_request")
    same = u.client.patch("/api/me", json={"language": "ar"}, headers={"Origin": "http://testserver"})
    assert same.status_code == 200
