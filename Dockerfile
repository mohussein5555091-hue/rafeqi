# Rafeqi in one container for Render (docs/DEPLOY.md): the React app is built once, and the FastAPI backend serves it
# together with the API at a single address. Not needed for local development (npm run dev).

# 1. Build the frontend (frontend/dist).
FROM node:22-slim AS web
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# 2. The backend, with the built frontend next to it.
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy \
    RAFEQI_ENV=production RAFEQI_FRONTEND_DIST=/app/frontend/dist
RUN pip install --no-cache-dir uv==0.8.17
WORKDIR /app/backend
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY backend/ ./
COPY data/ /app/data/
COPY scripts/backup.py scripts/restore.py /app/scripts/
COPY --from=web /app/frontend/dist /app/frontend/dist
# Render sets PORT. Migrations and the exercise/food catalogue run on every start (both only ever add or update).
CMD ["sh", "-c", "uv run --no-dev alembic upgrade head && uv run --no-dev python -m app.catalogue && uv run --no-dev uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
