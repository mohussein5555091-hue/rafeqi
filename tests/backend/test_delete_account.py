"""Deleting an account removes all of that person's data, and nobody else's.
The one exception: llm_calls rows stay with user_id = null, so AI usage totals stay correct."""

from sqlalchemy import func, select

from app.models import Base, LlmCall, User
from populate import populate
from tests_helpers import COOKIE


def counts_for(db, user_id: str) -> dict[str, int]:
    return {name: db.scalar(select(func.count()).select_from(t).where(t.c.user_id == user_id))
            for name, t in Base.metadata.tables.items() if "user_id" in t.c}


def test_delete_my_account_removes_everything(make_user, client_factory, db, uploads_dir):
    a, b = make_user("leaving@example.com"), make_user()
    populate(db, a.id)
    populate(db, b.id)
    photo_dir = uploads_dir / a.id
    photo_dir.mkdir()
    (photo_dir / "front.jpg").write_bytes(b"jpeg")
    b_before = counts_for(db, b.id)
    a_token = a.client.cookies.get(COOKIE)

    r = a.client.delete("/api/me")
    assert r.status_code == 204
    assert "max-age=0" in r.headers["set-cookie"].lower() or "expires=" in r.headers["set-cookie"].lower()

    db.expire_all()
    assert db.get(User, a.id) is None
    leftovers = {t: n for t, n in counts_for(db, a.id).items() if n}
    assert leftovers == {}, f"rows left behind for the deleted user: {leftovers}"
    assert not photo_dir.exists()

    # The AI usage row survives without its owner.
    orphan_calls = db.scalar(select(func.count()).select_from(LlmCall).where(LlmCall.user_id.is_(None)))
    assert orphan_calls == 1

    # B is untouched.
    assert counts_for(db, b.id) == b_before
    assert b.client.get("/api/me").status_code == 200

    # A's old cookie is dead, and the email can be used again.
    replay = client_factory()
    replay.cookies.set(COOKIE, a_token)
    assert replay.get("/api/me").status_code == 401
    again = client_factory().post("/api/auth/signup", json={"firstName": "A", "email": "leaving@example.com",
                                                            "password": "correct-horse-1", "adultConfirmed": True})
    assert again.status_code == 201
