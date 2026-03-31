# PC Build Assistant – Backend

FastAPI backend for the PC Build Assistant. Uses SQLAlchemy + PostgreSQL and JWT auth.

> The frontend lives in a [separate repository](https://github.com/NghiaLam2026/database_systems_final_project_frontend) and communicates with this API over REST.

## Setup

1. **Create a virtualenv and install deps** (from repo root):

   ```bash
   python -m venv .venv
   .venv\Scripts\activate   # Windows
   pip install -r requirements.txt
   ```

2. **Database**: Create a PostgreSQL database and set `DATABASE_URL` in `.env` (see `.env.example`).

3. **Run migrations**:

   ```bash
   alembic upgrade head
   ```

   To reset the DB and re-run from scratch:

   ```bash
   alembic downgrade base
   alembic upgrade head
   ```

4. **Seed the catalog** (optional): Place CSV files in `data/` and run:

   ```bash
   python -m scripts.seed_catalog              # all categories
   python -m scripts.seed_catalog cpu gpu       # specific categories
   python -m scripts.seed_catalog --dry-run     # preview without writing
   ```

   Supported categories: `cpu`, `gpu`, `mobo`, `memory`, `psu`, `case`, `cpu_cooler`, `case_fans`, `storage`. Each expects a corresponding CSV in `data/` (e.g. `cpu_data.csv`). Rows without a name or price are skipped. Re-running upserts by name.

5. **Run the API** (from repo root):

   ```bash
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