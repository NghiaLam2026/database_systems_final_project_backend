# PC Build Assistant – Backend

FastAPI backend for the PC Build Assistant. Uses SQLAlchemy + PostgreSQL and JWT auth.

> The frontend lives in a [separate repository](https://github.com/NghiaLam2026/database_systems_final_project_frontend) and communicates with this API over REST.

## Setup

1. **Create a virtualenv and install deps** (from repo root):

   ```bash
   python -m venv .venv

   # Activate the virtualenv
   .venv\Scripts\activate        # Windows
   source .venv/bin/activate     # macOS / Linux

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

   To **erase** catalog data:

   ```bash
   python -m scripts.reset_catalog              # wipe all catalog tables
   python -m scripts.reset_catalog cpu gpu       # wipe specific tables
   python -m scripts.reset_catalog --dry-run     # preview without deleting
   ```

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
- `GEMINI_API_KEY` / `GEMINI_MODEL` – Pydantic AI + Gemini for chat replies (optional).
- `CHAT_GUARDRAIL_ENABLED` – Reject high-risk chat input before the LLM (default: true).
- `CHAT_GUARDRAIL_EXTRA_PHRASES` – Comma-separated extra substrings to block.
- `CHAT_GUARDRAIL_MAX_MESSAGE_LENGTH` – Max characters per message before the model (default: 32000).

## Troubleshooting

### Port 5432 conflict – local PostgreSQL vs Docker pgvector

This project requires the **pgvector** extension, which is provided by the PostgreSQL instance running inside Docker. If you also have a local (non-Docker) PostgreSQL server installed, both may listen on port 5432. When that happens the app can silently connect to the local instance, which lacks pgvector, and migrations or queries will fail.

**Diagnose:** Check which processes are bound to port 5432:

```bash
# Windows (PowerShell / CMD)
netstat -ano | findstr :5432

# macOS / Linux
lsof -i :5432
```

On Windows, identify each PID:

```bash
tasklist /FI "PID eq <PID>"
```

If you see **both** a local `postgres` process **and** a Docker process listening on the same port, the local server is likely intercepting connections.

**Fix (pick one):**

1. **Stop the local PostgreSQL service** so only the Docker container serves port 5432:

   ```bash
   # Windows – stop the service (run as Administrator)
   net stop postgresql-x64-<version>

   # macOS (Homebrew)
   brew services stop postgresql

   # Linux (systemd)
   sudo systemctl stop postgresql
   ```

   You can also disable it from starting automatically:
   - **Windows**: `services.msc` → set PostgreSQL service to "Manual" or "Disabled"
   - **macOS**: `brew services stop postgresql` (Homebrew won't auto-start unless explicitly configured)
   - **Linux**: `sudo systemctl disable postgresql`

2. **Change the port** of either the local server or the Docker container so they no longer collide (e.g. map the Docker container to `5433` and update `DATABASE_URL` accordingly).

After resolving the conflict, verify the app connects to the Docker instance by running `alembic upgrade head` — it should complete without pgvector errors.

### Database does not exist

If the app crashes on startup with an error like:

```
psycopg2.OperationalError: connection to server at "localhost" (::1), port 5432 failed:
FATAL:  database "pc_build_assistant_v1" does not exist
```

it means the PostgreSQL server is reachable but the database referenced in your `DATABASE_URL` hasn't been created yet. Connect to PostgreSQL and create it:

```bash
# Using psql (connect to the default "postgres" database first)
psql -h localhost -U <your_user> -d postgres
```

```sql
CREATE DATABASE pc_build_assistant_v1;
```

Then run migrations as usual:

```bash
alembic upgrade head
```

## API

- **Docs**: http://localhost:8000/docs
- **Auth**: `POST /api/v1/auth/register`, `POST /api/v1/auth/login`, `GET /api/v1/auth/me`
- **Builds**: `GET/POST /api/v1/builds`, `GET/PATCH/DELETE /api/v1/builds/{id}`, `POST /api/v1/builds/{id}/clone`, `GET/POST /api/v1/builds/{id}/parts`, `PATCH/DELETE /api/v1/builds/{id}/parts/{part_id}`, `GET /api/v1/builds/part-types`
- **Threads**: `GET/POST /api/v1/threads`, `GET/DELETE /api/v1/threads/{id}`
- **Messages**: `POST /api/v1/threads/{id}/messages`, `GET /api/v1/threads/{id}/messages` — if chat guardrails block the text, the API still returns **201** with a normal message whose `ai_response` is a short canned refusal (no LLM call). **401** means the JWT is missing or expired.
- **Catalog**: `GET /api/v1/catalog/{mobo|cpu|memory|case|storage|cpu_cooler|psu|case_fans|gpu}` (optional `min_price`, `max_price`, `limit`)