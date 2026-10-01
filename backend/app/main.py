"""FastAPI entry point. Every route is mounted under /api (the frontend proxies it)."""

from urllib.parse import urlsplit

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api import auth, me, onboarding, plans, weights
from app.config import get_settings

app = FastAPI(title="Rafeqi API", version="0.2.0", docs_url="/api/docs", openapi_url="/api/openapi.json")

UNSAFE = {"POST", "PUT", "PATCH", "DELETE"}


@app.middleware("http")
async def same_origin_writes(request: Request, call_next):
    """Refuse changes sent from another website (backs up the SameSite=Lax cookie)."""
    origin = request.headers.get("origin")
    if request.method in UNSAFE and origin and urlsplit(origin).netloc != request.headers.get("host"):
        return JSONResponse({"detail": "cross_origin_request"}, status_code=403)
    return await call_next(request)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "env": get_settings().env}


for module in (auth, me, onboarding, plans, weights):
    app.include_router(module.router)
