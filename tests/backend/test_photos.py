"""Progress photos from the weekly check-in: stored privately under the uploads folder, served only to their owner,
listed on the progress page, and deleted with the account."""

from test_plans import catalogue, onboarded  # noqa: F401 (fixtures)
from test_screens_api import checkin_body, planned  # noqa: F401 (fixtures)

JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 200
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 200


def checked_in(c, clock):
    clock.advance(days=3)  # Thursday: the check-in is open
    _, body = checkin_body(c)
    r = c.post("/api/checkins", json=body)
    assert r.status_code == 201, r.text
    return r.json()["checkinId"]


def put(c, ci, view, data, ctype="image/jpeg"):
    return c.put(f"/api/checkins/{ci}/photos/{view}", content=data, headers={"Content-Type": ctype})


def test_upload_view_and_list_photos(planned, clock, uploads_dir):  # noqa: F811
    c = planned.client
    ci = checked_in(c, clock)
    assert put(c, ci, "front", JPEG).status_code == 204
    assert put(c, ci, "side", PNG, "image/png").status_code == 204
    files = sorted(p.name for p in (uploads_dir / planned.id).iterdir())
    assert files == [f"{ci}-front.jpg", f"{ci}-side.png"]
    r = c.get(f"/api/photos/{ci}/front")
    assert r.status_code == 200 and r.content == JPEG and r.headers["cache-control"] == "private, no-store"
    assert c.get(f"/api/photos/{ci}/back").status_code == 404
    photos = c.get("/api/progress").json()["photos"]
    assert [(p["view"], p["url"]) for p in photos] == [("front", f"/api/photos/{ci}/front"), ("side", f"/api/photos/{ci}/side")]
    # Sending it again replaces it (and the old file goes).
    assert put(c, ci, "side", JPEG).status_code == 204
    assert sorted(p.name for p in (uploads_dir / planned.id).iterdir()) == [f"{ci}-front.jpg", f"{ci}-side.jpg"]


def test_only_real_photos_of_a_known_view(planned, clock):  # noqa: F811
    c = planned.client
    ci = checked_in(c, clock)
    assert put(c, ci, "front", b"<script>alert(1)</script>", "image/jpeg").status_code == 422
    assert put(c, ci, "top", JPEG).status_code == 422
    assert put(c, ci, "front", b"").status_code == 422
    assert put(c, ci, "front", b"\xff\xd8\xff" + b"\x00" * (8 * 1024 * 1024)).status_code == 413


def test_photos_are_private(planned, clock, make_user):  # noqa: F811
    c = planned.client
    ci = checked_in(c, clock)
    put(c, ci, "front", JPEG)
    other = make_user().client
    assert other.get(f"/api/photos/{ci}/front").status_code == 404
    assert put(other, ci, "front", PNG, "image/png").status_code == 404
    assert c.get(f"/api/photos/{ci}/front").content == JPEG  # untouched
    c.post("/api/auth/logout")
    assert c.get(f"/api/photos/{ci}/front").status_code == 401


def test_deleting_the_account_deletes_the_photos(planned, clock, uploads_dir):  # noqa: F811
    c = planned.client
    ci = checked_in(c, clock)
    put(c, ci, "front", JPEG)
    assert (uploads_dir / planned.id).exists()
    assert c.delete("/api/me").status_code == 204
    assert not (uploads_dir / planned.id).exists()


def test_check_in_questions_come_from_the_file(planned):  # noqa: F811
    from app.engine.checkin import load_questions

    out = planned.client.get("/api/checkins/questions").json()
    data = load_questions()
    assert out["steps"] == data["steps"]
    by_id = {q["id"]: q for q in out["questions"]}
    assert set(by_id) == {q["id"] for q in data["questions"]}
    assert by_id["weight_kg"] == by_id["weight_kg"] | {"type": "number", "min": 30, "max": 300, "required": True,
                                                       "text": {"en": "This week's weight · morning, before eating", "ar": "وزنك الأسبوع ده · الصبح قبل الأكل"}}
    assert by_id["note"]["maxLength"] == 300 and by_id["obstacles"]["options"][0] == "work"



def test_photos_can_live_in_the_database(planned, clock, uploads_dir, monkeypatch, db):  # noqa: F811
    """RAFEQI_PHOTO_STORAGE=database (Render's free disk is wiped on every deploy): same API, nothing on disk."""
    from app.config import get_settings
    from app.models import PhotoBlob

    monkeypatch.setattr(get_settings(), "photo_storage", "database")
    c = planned.client
    ci = checked_in(c, clock)
    assert put(c, ci, "back", PNG, "image/png").status_code == 204
    assert not (uploads_dir / planned.id).exists()
    r = c.get(f"/api/photos/{ci}/back")
    assert (r.status_code, r.content, r.headers["content-type"]) == (200, PNG, "image/png")
    assert put(c, ci, "back", JPEG).status_code == 204  # replaced, still one row
    assert len(db.query(PhotoBlob).filter_by(user_id=planned.id).all()) == 1
    assert c.get(f"/api/photos/{ci}/back").content == JPEG
    assert c.get("/api/progress").json()["photos"][0]["url"] == f"/api/photos/{ci}/back"
    assert c.delete("/api/me").status_code == 204
    db.expire_all()
    assert db.query(PhotoBlob).count() == 0
