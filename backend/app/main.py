"""FastAPI entry point. Every route is mounted under /api (the frontend proxies it)."""

from urllib.parse import urlsplit

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse

from app.api import auth, body, me, nutrition, onboarding, plans, training, weights
from app.config import get_settings

get_settings().check_production()
app = FastAPI(title="Rafeqi API", version="0.6.0", docs_url="/api/docs", openapi_url="/api/openapi.json")

UNSAFE = {"POST", "PUT", "PATCH", "DELETE"}


@app.middleware("http")
async def same_origin_writes(request: Request, call_next):
    """Refuse changes sent from another website (backs up the SameSite=Lax cookie)."""
    origin = request.headers.get("origin")
    if request.method in UNSAFE and origin and urlsplit(origin).netloc != request.headers.get("host"):
        return JSONResponse({"detail": "cross_origin_request"}, status_code=403)
    return await call_next(request)


@app.middleware("http")
async def https_only(request: Request, call_next):
    """Production: plain http is redirected to https (the host's health check, which calls the app directly, is
    exempt), and every answer carries the usual security headers. Behind Render's proxy, uvicorn --proxy-headers makes
    request.url.scheme the visitor's real one."""
    s = get_settings()
    if not s.is_production:
        return await call_next(request)
    if request.url.scheme == "http" and request.url.path != "/api/health":
        return RedirectResponse(str(request.url.replace(scheme="https")), status_code=308)
    response = await call_next(request)
    response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "same-origin")
    response.headers.setdefault("X-Frame-Options", "DENY")
    return response


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "env": get_settings().env}


for module in (auth, me, onboarding, plans, weights, training, nutrition, body):
    app.include_router(module.router)


# ── Production: the built frontend at the same address as the API ──
# Every path that isn't /api/… is a file from frontend/dist (photos, icons, the manifest, the app's scripts), or the app
# itself (index.html), which then shows the right screen. Hashed scripts are cached for a year; index.html never is.

def add_frontend(app: FastAPI, dist: Path) -> None:
    """Serves frontend/dist: a file when the path is one (scripts, photos, icons), the app (index.html) otherwise."""
    root = dist.resolve()

    @app.get("/{path:path}", include_in_schema=False)
    def frontend(path: str):
        if path == "api" or path.startswith("api/"):
            raise HTTPException(404, "not_found")
        file = (root / path).resolve()
        if path and file.is_file() and root in file.parents:
            cache = "public, max-age=31536000, immutable" if path.startswith("assets/") else "public, max-age=3600"
            if path in ("sw.js", "manifest.webmanifest"):
                cache = "no-cache"
            return FileResponse(file, headers={"Cache-Control": cache})
        return FileResponse(root / "index.html", headers={"Cache-Control": "no-cache"})


if get_settings().is_production and (get_settings().frontend_dist / "index.html").is_file():
    add_frontend(app, get_settings().frontend_dist)
