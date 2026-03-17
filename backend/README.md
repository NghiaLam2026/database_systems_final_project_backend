# PC Build Assistant – Backend

FastAPI backend for the PC Build Assistant (monorepo). Uses SQLAlchemy + PostgreSQL and JWT auth.

## Setup

1. **Create a virtualenv and install deps** (from repo root or `backend/`):

   ```bash
   python -m venv .venv
   .venv\Scripts\activate   # Windows
   pip install -r backend/requirements.txt
   ```

2. **Database**: Create a PostgreSQL database and set `DATABASE_URL` in the project-root `.env` (see `.env.example`). Run migrations from the **project root**:

   ```bash
   alembic upgrade head
   ```

3. **Run the API** (from project root so `app` is importable):

   ```bash
   uvicorn backend.app.main:app --reload --app-dir .
   ```

   Or from `backend/`:

   ```bash
   cd backend
   set PYTHONPATH=..   # or $env:PYTHONPATH=".." in PowerShell
   uvicorn app.main:app --reload
   ```

## Config

Env vars (or `.env` at project root):

- `DATABASE_URL` – PostgreSQL URL (same as Alembic).
- `SECRET_KEY` – JWT signing secret (default: change-me-in-production).
- `ACCESS_TOKEN_EXPIRE_MINUTES` – JWT expiry (default: 60).
- `CORS_ORIGINS` – Comma-separated origins (default: `http://localhost:3000`).
- `DEBUG` – Enable SQL echo and debug (default: false).

## API

- **Docs**: http://localhost:8000/docs
- **Auth**: `POST /api/v1/auth/register`, `POST /api/v1/auth/login`, `GET /api/v1/auth/me`
- **Builds**: `GET/POST /api/v1/builds`, `GET/PATCH/DELETE /api/v1/builds/{id}`, `GET/POST/DELETE /api/v1/builds/{id}/parts`
- **Threads**: `GET/POST /api/v1/threads`, `GET/DELETE /api/v1/threads/{id}`
- **Messages**: `POST /api/v1/threads/{id}/messages`, `GET /api/v1/threads/{id}/messages`
- **Catalog**: `GET /api/v1/catalog/{mobo|cpu|memory|case|storage|cpu_cooler|psu|case_fans|gpu}` (optional `min_price`, `max_price`, `limit`)