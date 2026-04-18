# Tests

Automated test suite for the PC Build Assistant backend.

## Layout

```
tests/
├── conftest.py                        # shared fixtures (engine, client, seeds)
├── unit/                              # pure-function tests, no DB / network
│   ├── test_sql_validator.py
│   ├── test_chat_guardrails.py
│   ├── test_auth_service.py
│   └── test_build_service.py
└── integration/                       # FastAPI TestClient + in-memory SQLite
    ├── test_auth_api.py
    ├── test_users_api.py
    ├── test_threads_api.py
    ├── test_messages_api.py
    ├── test_builds_api.py
    └── test_catalog_api.py
```

## Running

From the project root:

```powershell
pip install -r requirements-dev.txt
pytest                              # run everything
pytest tests/unit                   # only unit tests (fastest)
pytest tests/integration            # only integration tests
pytest -k validator                 # only tests matching a keyword
pytest -v                           # verbose names
pytest --lf                         # re-run last failed
```

## Environment

- **No Postgres required.** Integration tests spin up an in-memory SQLite
  database per test.
- **No Gemini API key required.** The LLM entrypoint
  (`generate_chat_reply`) is monkey-patched with a deterministic stub.
- **No Ollama required.** No test code touches the embedding service.
- `.env` is loaded as usual by Pydantic Settings, but the values that
  matter for tests have safe defaults (e.g. `SECRET_KEY`).

## What is and isn't covered

### Covered

- **Security-critical paths**
  - `sql_validator`: allowed / forbidden statement types, role-based table
    allowlist, column denylist (`password_hash`), `SELECT *` on `users`,
    system catalogs, `SELECT INTO`, multi-statement injection.
  - `chat_guardrails`: role-override / jailbreak / secret-exfil / code-injection
    patterns, Unicode and case normalisation, length limits, config toggles.
  - `auth`: bcrypt hashing + verify, JWT round-trip, tampered/expired/forged
    tokens, missing-claim handling.
- **API behaviour**
  - Auth: register / login / `/me`, duplicate email, invalid payloads,
    soft-deleted users cannot authenticate.
  - Users: profile read/update, admin-only listing and creation, RBAC (403
    for regular users), role change on missing / deleted user.
  - Threads: CRUD, ownership checks (no IDOR), soft-delete cascades to
    messages, pagination + message counts.
  - Messages: stubbed LLM reply, ownership checks, build-id validation,
    guardrail triggers canned reply instead of LLM call, empty/overlong
    payload rejected by schema, list order asc/desc.
  - Builds: CRUD, parts CRUD, singular-slot enforcement (409 on second
    CPU/GPU/etc.), soft-delete allows re-adding to the slot, total-price
    aggregation, clone, ownership checks.
  - Catalog: public access, filter by price / name, sort with invalid
    column → 400 (not a SQL injection), pagination limits, 404 for missing
    IDs and unknown categories.

### Intentionally NOT covered

- **RAG / embeddings / document chunks.** Requires `pgvector` (no SQLite
  equivalent) and a running Ollama server. Add Postgres-backed tests
  separately if you want this covered.
- **Real LLM responses / agent tool-calling.** Deterministic testing of
  agent behaviour requires eval harnesses, not unit tests.
- **Postgres-specific edge cases** (native ENUMs, timezone conversion, real
  `NUMERIC(10,2)` rounding, FK cascade behaviour). SQLite is a reasonable
  proxy for CRUD logic but won't catch these.

## Adding new tests

- **Pure logic?** Put it in `tests/unit/` — no DB, no client, no monkey
  patches. Fast (< 1s suite).
- **Touches HTTP, DB, or auth?** Use the `client` + `*_headers` fixtures
  from `conftest.py`. The in-memory DB is re-created per test — no state
  bleed.
- **Needs catalog data?** Use the `seeded_catalog` fixture. Extend it if you
  need more rows.
- **Reads another user's data?** Use `other_user` / `other_user_headers` for
  IDOR / ownership tests.