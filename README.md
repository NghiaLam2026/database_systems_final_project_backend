# PC Build Assistant — Backend

FastAPI backend for the PC Build Assistant. Users register, create PC builds from a catalog of real hardware parts, and chat with an AI assistant that can look up live data from the database and answer questions using an ingested knowledge base of hardware reviews and guides.

> The React frontend lives in a [separate repository](https://github.com/NghiaLam2026/database_systems_final_project_frontend). The two communicate over REST.

For a deep dive into how everything works under the hood, see [`docs/technical_design.md`](docs/technical_design.md).

## Features

- **Auth** — email/password registration, JWT login, user vs admin roles.
- **Catalog** — nine hardware categories (`cpu`, `gpu`, `mobo`, `memory`, `case`, `storage`, `cpu_cooler`, `psu`, `case_fans`) with search, sort, filter, and pagination.
- **Builds** — users assemble parts into builds. Polymorphic `build_parts` table, singular-slot enforcement (one CPU, one case, etc.), build cloning, total-price aggregation.
- **Chat** — multi-turn conversations tied to threads. Each turn can optionally attach a build for context.
- **AI assistant** — a multi-agent system (orchestrator, text-to-SQL agent, RAG agent) powered by Pydantic AI + Google Gemini. Embeddings run locally via Ollama (`qwen3-embedding:8b`).
- **Safety** — deterministic chat guardrails (prompt-injection / secret-exfiltration / code-abuse patterns), role-aware SQL validator, read-only-by-design DB access for the SQL agent.
- **Soft deletes** — nothing gets hard-deleted; users, builds, threads, and messages all carry `deleted_at`.
- **Observability** — structured logging with request-scoped context binding (`structlog`).

---

## Prerequisites

- **Python 3.12+**
- **PostgreSQL 15+** with the `pgvector` extension (easiest via the official [`pgvector/pgvector`](https://hub.docker.com/r/pgvector/pgvector) Docker image)
- **Ollama** (optional, required only for the RAG pipeline) — install from [ollama.com](https://ollama.com/download) and pull the embedding model:

  ```bash
  ollama pull qwen3-embedding:8b
  ```

- **Google Gemini API key** (optional, required only for chat replies)

---

## Setup

1. **Create a virtualenv and install dependencies** (from the repo root):

   ```bash
   python -m venv .venv

   # Activate
   .venv\Scripts\activate        # Windows
   source .venv/bin/activate     # macOS / Linux

   pip install -r requirements.txt
   ```

   For the test suite, also install dev dependencies:

   ```bash
   pip install -r requirements-dev.txt
   ```

2. **Configure environment variables.** Copy `.env.example` to `.env` and fill in at minimum `DATABASE_URL` and `SECRET_KEY`. See [Configuration](#configuration).

3. **Create the database** (if it doesn't exist yet):

   ```sql
   CREATE DATABASE pc_build_assistant_v1;
   ```

4. **Run migrations:**

   ```bash
   alembic upgrade head
   ```

   To reset and re-run:

   ```bash
   alembic downgrade base && alembic upgrade head
   ```

5. **Seed the hardware catalog** (optional but recommended — the app is not much fun with an empty parts list):

   ```bash
   python -m scripts.seed_catalog              # all categories
   python -m scripts.seed_catalog cpu gpu      # specific categories
   python -m scripts.seed_catalog --dry-run    # preview without writing
   ```

   Supported categories: `cpu`, `gpu`, `mobo`, `memory`, `psu`, `case`, `cpu_cooler`, `case_fans`, `storage`. Each expects a CSV at `data/catalog/{category}_data.csv`. Rows without a name or price are skipped. Re-running upserts by name.

   To wipe the catalog:

   ```bash
   python -m scripts.reset_catalog              # wipe everything
   python -m scripts.reset_catalog cpu gpu      # wipe specific categories
   python -m scripts.reset_catalog --dry-run    # preview
   ```

6. **Run the API:**

   ```bash
   uvicorn app.main:app --reload
   ```

   - Interactive docs: http://localhost:8000/docs
   - Health check: http://localhost:8000/health

---

## Populating the Knowledge Base (Optional)

The RAG agent answers hardware questions using ingested articles and reviews. To give it something to retrieve:

1. **Fetch and extract web pages** into a per-category folder under `data/`:

   ```bash
   python -m scripts.get_documents https://example.com/some-gpu-review \
       --category gpu \
       --favor-precision --no-images --clean
   ```

   Output lands in `data/gpu_documents/` as a `.txt` or `.md` file plus a `.meta.json` sidecar (source URL, extraction flags, fetched-at timestamp).

   > **Note on source tuning.** The `--clean` heuristics are tailored for Tom's Hardware article boilerplate (comment sections, newsletter CTAs, "MORE: ..." nav links). For other sources, either skip `--clean` or adjust the regex patterns at the top of `scripts/get_documents.py`.

   Multiple URLs at once:

   ```bash
   python -m scripts.get_documents --file urls.txt --category cpu --clean
   ```

2. **Make sure Ollama is running** and the embedding model is pulled:

   ```bash
   ollama serve                          # if not already running
   ollama pull qwen3-embedding:8b
   ```

3. **Embed and store** the documents:

   ```bash
   python -m scripts.ingest_documents                     # all *_documents/ folders
   python -m scripts.ingest_documents --folder gpu_documents  # one folder
   python -m scripts.ingest_documents --dry-run           # preview
   ```

   Documents live in category-specific folders (`cpu_documents/`, `gpu_documents/`, `motherboard_documents/`, etc.) so you can re-index one category without touching the others.

---

## Configuration

All settings are read from environment variables or a `.env` file at the project root. A complete template lives in `.env.example`.

**Core:**

| Variable                      | Purpose                                     | Default |
| ----------------------------- | ------------------------------------------- | ------- |
| `DATABASE_URL`                | SQLAlchemy Postgres URL                     | —       |
| `SECRET_KEY`                  | JWT signing secret                          | `change-me-in-production` |
| `ALGORITHM`                   | JWT algorithm                               | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT expiry                                  | `60`    |
| `CORS_ORIGINS`                | Comma-separated origins                     | `http://localhost:3000` |
| `DEBUG`                       | Enable SQL echo and debug behavior          | `false` |
| `LOG_LEVEL`                   | Root log level                              | `INFO`  |

**Bootstrap admin** (creates the first admin on startup — see the technical design for exact semantics):

| Variable             | Purpose                                   |
| -------------------- | ----------------------------------------- |
| `ADMIN_EMAIL`        | Email for the bootstrap admin             |
| `ADMIN_PASSWORD`     | Required if `ADMIN_EMAIL` is set          |
| `ADMIN_FIRST_NAME`   | Optional                                  |
| `ADMIN_LAST_NAME`    | Optional                                  |

**AI:**

| Variable                 | Purpose                                           | Default                   |
| ------------------------ | ------------------------------------------------- | ------------------------- |
| `GEMINI_API_KEY`         | Google Gemini key for chat replies (optional)     | —                         |
| `GEMINI_MODEL`           | Gemini model name                                 | `gemini-2.5-flash-lite`   |
| `OLLAMA_BASE_URL`        | Local Ollama server                               | `http://localhost:11434`  |
| `EMBEDDING_MODEL`        | Ollama embedding model                            | `qwen3-embedding:8b`      |
| `EMBEDDING_DIMENSIONS`   | Must match the DB `vector(N)` column              | `768`                     |

**Chat guardrails** (pre-LLM input filter):

| Variable                             | Purpose                                                   | Default  |
| ------------------------------------ | --------------------------------------------------------- | -------- |
| `CHAT_GUARDRAIL_ENABLED`             | Master switch                                             | `true`   |
| `CHAT_GUARDRAIL_MAX_MESSAGE_LENGTH`  | Max characters per user message (256–200,000)             | `32000`  |
| `CHAT_GUARDRAIL_EXTRA_PHRASES`       | Extra substrings to block (comma-separated, min 3 chars)  | —        |

---

## API

The OpenAPI spec is browsable at http://localhost:8000/docs. Brief tour:

- **Auth** — `POST /api/v1/auth/register`, `POST /api/v1/auth/login`, `GET /api/v1/auth/me`.
- **Users** — `GET /api/v1/users/me`, `PATCH /api/v1/users/me`. Admin: `GET /users`, `POST /users`, `PATCH /users/{id}/role`.
- **Builds** — `GET/POST /api/v1/builds`, `GET/PATCH/DELETE /api/v1/builds/{id}`, `POST /api/v1/builds/{id}/clone`, `GET/POST /api/v1/builds/{id}/parts`, `PATCH/DELETE /api/v1/builds/{id}/parts/{part_id}`, `GET /api/v1/builds/part-types`.
- **Threads** — `GET/POST /api/v1/threads`, `GET/PATCH/DELETE /api/v1/threads/{id}`.
- **Messages** — `POST /api/v1/threads/{id}/messages`, `GET /api/v1/threads/{id}/messages`, `GET /api/v1/threads/{id}/messages/{message_id}`. If chat guardrails block the input, the endpoint still returns **201** with a canned refusal in `ai_response` — no LLM is called. **401** means the JWT is missing or expired.
- **Catalog** — `GET /api/v1/catalog/{category}` where category is one of `mobo | cpu | memory | case | storage | cpu_cooler | psu | case_fans | gpu`. Supports `page`, `size`, `min_price`, `max_price`, `search`, `sort_by`, `order`. `GET /api/v1/catalog/{category}/{id}` for a single component.

---

## Testing

Unit and integration tests live under `tests/` (201 tests total). They use an in-memory SQLite database, a stubbed LLM, and do not require Postgres, Ollama, or any cloud credentials.

```bash
pytest                          # run everything (~15s)
pytest tests/unit               # unit tests only
pytest tests/integration        # integration tests only
pytest -k test_auth_api -v      # filter by name
```

See `tests/README.md` for layout details and what is / isn't covered.

---

## Project Layout

```
app/                 FastAPI application (routes, services, models, tools, agents)
alembic/             Database migrations (six revisions)
scripts/             CLI utilities: seed/reset catalog, fetch and ingest docs
tests/               Pytest suite (unit + integration)
data/
  catalog/           Component CSV seed files
  {category}_documents/   Per-category RAG corpus (populated via scripts/get_documents.py)
docs/
  technical_design.md     Full backend engineering reference
semantic_layer.yaml  Machine-readable schema consumed by the text-to-SQL agent
```

---

## Troubleshooting

### Port 5432 conflict — local PostgreSQL vs Docker pgvector

This project requires the `pgvector` extension, which the Docker image provides. If you also have a host PostgreSQL installed, both may listen on 5432 and the app can silently connect to the host instance (which lacks `pgvector`), breaking migrations and queries.

**Diagnose:**

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

**Fix (pick one):**

1. **Stop the host PostgreSQL service** so only the Docker container serves 5432:

   ```bash
   # Windows (run as Administrator)
   net stop postgresql-x64-<version>

   # macOS (Homebrew)
   brew services stop postgresql

   # Linux (systemd)
   sudo systemctl stop postgresql
   ```

2. **Use a different port for the Docker container** (e.g. map to `5433`) and update `DATABASE_URL` accordingly.

Verify by running `alembic upgrade head` — it should complete without pgvector errors.

### "database does not exist"

```
psycopg2.OperationalError: FATAL:  database "pc_build_assistant_v1" does not exist
```

Create it:

```bash
psql -h localhost -U <your_user> -d postgres
```

```sql
CREATE DATABASE pc_build_assistant_v1;
```

Then `alembic upgrade head`.

### "connection refused" from the RAG agent

The embedding service talks to Ollama on `OLLAMA_BASE_URL` (default `http://localhost:11434`). Make sure Ollama is running (`ollama serve` or the desktop app) and the model is pulled (`ollama pull qwen3-embedding:8b`). The RAG agent will return a friendly error instead of crashing the turn, but retrieval will be empty.

### Chat just says "GEMINI_API_KEY is not configured"

Set `GEMINI_API_KEY` in `.env` and restart the app. Without it, the orchestrator short-circuits rather than calling the API.

---

## License

See [LICENSE](LICENSE).
