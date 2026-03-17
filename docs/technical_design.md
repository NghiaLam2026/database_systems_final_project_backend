## PC Build Assistant – Technical Design

This document describes how the PC Build Assistant application will work from a technical perspective. It is not the main `README.md`, but a deeper design reference for architecture, data modeling, agent behavior, and system interactions.

---

## 1. High-Level Overview

The application is a **PC-building assistant** with:

- **Frontend**: React.js single-page application.
- **Backend**: FastAPI service exposing REST APIs.
- **Database**: PostgreSQL as the single source of truth, including both relational data and vector embeddings (via `pgvector`).
- **AI Layer**: A **multi-agent system** built with Pydantic AI:
  - **Orchestrator (Supervisor)** – routes requests and aggregates results.
  - **SQL Agent** – converts natural language into read-only SQL queries over PostgreSQL.
  - **RAG Agent** – retrieval-augmented generation over external hardware knowledge stored as embeddings in PostgreSQL.

Key features:

- Users can manage **PC builds**, browse a **hardware catalog**, and chat with an **AI hardware assistant**.
- Admins can manage the **user base** and the **hardware catalog**.
- All responses from the AI assistant are generated using:
  - **Structured data** from PostgreSQL (via the SQL agent), and/or
  - **Unstructured knowledge** via the RAG agent.
- The **database is the only source of truth**; external APIs are used only for periodic data ingestion.

---

## 2. Data Model & Relational Schema

### 2.1 Core User & Build Tables

- **`users`**
  - **Columns**:
    - `id` (PK)
    - `email`
    - `password_hash`
    - `first_name`
    - `last_name`
    - `role` (e.g. `'user'` or `'admin'`)
    - `created_at`
    - `updated_at`
    - `deleted_at` (NULL = active; non-NULL = soft-deleted)
  - **Notes**:
    - Application queries treat `deleted_at IS NOT NULL` as deleted and ignore such rows in normal flows.
    - **Email uniqueness with soft delete**:
      - Email is unique **only among active users** (`deleted_at IS NULL`).
      - This allows re-registering/recreating an account with the same email after the previous account is soft-deleted.

- **`builds`**
  - **Columns**:
    - `id` (PK)
    - `user_id` (FK → `users.id`)
    - `build_name`
    - `description`
    - `created_at`
    - `updated_at`
    - `deleted_at`
  - **Relationships**:
    - One `user` has many `builds`.
    - A `build` owns multiple `build_parts` rows.

- **`build_parts`**
  - **Columns**:
    - `id` (PK)
    - `build_id` (FK → `builds.id`)
    - `part_type` – enum indicating component type (see below).
    - `part_id` – integer ID of the component row in its respective table.
    - `quantity` – integer count of that part in the build.
    - `created_at`
    - `updated_at`
    - `deleted_at`
  - **`part_type` enum**:
    - Values (fixed set): `'cpu' | 'gpu' | 'mobo' | 'memory' | 'psu' | 'case' | 'cpu_cooler' | 'case_fans' | 'storage'`.
    - Implemented as either:
      - PostgreSQL enum type, and/or
      - Pydantic / Python enum for type safety.
  - **Polymorphic reference**:
    - `(part_type, part_id)` acts as a logical pointer `(table_name, row_id)`:
      - e.g. `('gpu', 5)` means **GPU table row with `id = 5`**.
    - PostgreSQL cannot enforce a single FK across multiple tables for `part_id`, so:
      - `build_id` is a **true FK**.
      - `(part_type, part_id)` integrity is enforced in application logic and by the SQL agent templates.
  - **Soft deletes**:
    - As with other tables, `deleted_at` is used for soft deletion and audit.

### 2.2 Hardware Component Tables

Each hardware component type has its own table. All use `id` as their PK and have a `price` column.

- **`mobo`**
  - `id`, `name`, `socket`, `form_factor`, `memory_max`, `memory_slot`, `color`, `price`

- **`cpu`**
  - `id`, `name`, `core_count`, `perf_clock`, `boost_clock`, `microarch`, `tdp`, `graphics`, `price`

- **`memory`**
  - `id`, `name`, `speed`, `modules`, `color`, `first_word_latency`, `cas_latency`, `price`

- **`case`**
  - `id`, `name`, `type`, `color`, `power_supply`, `side_panel`, `volume`, `bays`, `price`

- **`storage`**
  - `id`, `name`, `capacity`, `type`, `cache`, `form_factor`, `interface`, `price`

- **`cpu_cooler`**
  - `id`, `name`, `fan_rpm`, `noise_level`, `color`, `radiator_size`, `price`

- **`psu`**
  - `id`, `name`, `type`, `efficiency`, `wattage`, `modular`, `color`, `price`

- **`case_fans`**
  - `id`, `size`, `color`, `rpm`, `airflow`, `noise_level`, `pwm`, `price`

- **`gpu`**
  - `id`, `name`, `chipset`, `memory`, `core_clock`, `boost_clock`, `color`, `length`, `price`

**Notes on component usage**:

- These tables are populated from:
  - Periodic ingestion from external APIs (e.g. PCPartPicker, Newegg).
  - Manual admin entry through the admin portal.
- The **UI** and **backend** always specify `part_type` explicitly when manipulating `build_parts` (e.g. GPU flow sets `part_type = 'gpu'`), so no inference is required.

### 2.3 Conversation History Tables

Conversation history is stored separately from builds to support multiple chats per user and long-lived AI sessions.

- **`threads`**
  - **Columns**:
    - `id` (PK)
    - `user_id` (FK → `users.id`) – owner of the thread.
    - `thread_name` – optional, editable chat title.
    - `created_at`
    - `updated_at`
    - `deleted_at`
  - **Semantics**:
    - Each **"New Chat"** action in the UI creates a new `threads` row.
    - A user can only see threads they own (`user_id = current_user.id` and `deleted_at IS NULL`).
    - Build context is **not** stored at the thread level; it is stored per message (see `messages.build_id`).

- **`messages`**
  - **Design choice**: one row per **exchange** (user request + AI response).
  - **Columns**:
    - `id` (PK)
    - `thread_id` (FK → `threads.id`)
    - `build_id` (nullable FK → `builds.id`) – build context for this message (see semantics below).
    - `user_request` (text) – raw user message payload.
    - `ai_response` (text) – orchestrator’s final response to that request.
    - `created_at`
    - `updated_at`
    - `deleted_at`
  - **Build context semantics**:
    - When **`build_id` IS NULL**: the user’s question is not about a specific build; the orchestrator treats it as a general hardware question (e.g. “top 5 cheapest GPUs”).
    - When **`build_id` IS NOT NULL**: the user has attached a build for this message; the orchestrator uses that build for build-specific analysis, compatibility checks, or recommendations.
    - Storing `build_id` **per message** (instead of per thread) means the user can switch builds in the same thread without losing data: each message preserves which build (if any) was in context, and full history of “which build was analyzed when” remains queryable.
  - **Flow**:
    - When user sends a message:
      1. Insert `messages` row with `user_request`, `build_id` (from request, or NULL), `ai_response = NULL`.
      2. Invoke orchestrator (passing this message’s `build_id` and recent thread context).
      3. Update `ai_response` with orchestrator’s final output.
    - This supports a simple **1-row-per-turn** model that fits the project requirements.

### 2.4 RAG / Vector Tables

To support RAG, PostgreSQL will use `pgvector` to store embeddings for documents and/or document chunks.

- **`documents`** (conceptual)
  - `id` (PK)
  - `title`
  - `source` (e.g. `'paper'`, `'blog'`, `'benchmark'`)
  - `url` (optional, if applicable)
  - `created_at`
  - `metadata` (JSONB, e.g. tags like `"gpu"`, `"psu"`, `"gaming"`)

- **`document_chunks`** (conceptual)
  - `id` (PK)
  - `document_id` (FK → `documents.id`)
  - `chunk_text`
  - `embedding` (vector) – `pgvector` column.
  - `created_at`
  - `metadata` (JSONB) – optional additional tags.

RAG queries will:

1. Embed the user query.
2. Perform vector similarity search: `ORDER BY embedding <-> :query_embedding LIMIT k`.
3. Feed top chunks + user question into the LLM for final answer generation.

---

## 3. Data Acquisition Flow

### 3.1 External APIs (PCPartPicker, Newegg)

- The application will periodically ingest component data from:
  - PCPartPicker
  - Newegg
- Ingestion flow:
  1. A background job or admin-triggered script calls the external API.
  2. The script maps external fields to the local schema (e.g. API GPU fields → `gpu` table).
  3. The script **upserts** rows in the corresponding component tables (`INSERT ... ON CONFLICT ...`).
  4. Prices and specs are updated in PostgreSQL.
- **Important**:
  - **No live external calls** are made during normal user interactions.
  - The **database remains the only source of truth** for user-facing queries.

### 3.2 Manual Admin Entry

- Admins access an **Administrative Portal** with:
  - CRUD forms for all component tables.
  - Capabilities to:
    - Add new or niche hardware.
    - Update specs and prices.
    - Deprecate parts (e.g. set `deleted_at` to hide them without hard-deleting).
- All admin operations mutate data **only in Postgres**.

---

## 4. Backend Design (FastAPI)

### 4.1 Service Layout

The FastAPI backend will be roughly organized into modules such as:

- `auth` – JWT-based authentication, user registration, login.
- `users` – user profile endpoints and admin user management.
- `builds` – CRUD for PC builds and their parts.
- `catalog` – read-only browsing and filtering of components.
- `admin_catalog` – admin-only CRUD for components.
- `threads` / `messages` – chat thread and message management.
- `ai` – endpoints for interacting with the orchestrator and agents.

### 4.2 Authentication & Authorization

- **Authentication**:
  - JWT tokens issued on login.
  - JWT payload includes at least:
    - `sub` = `user_id`
    - `role` = `'user'` / `'admin'`
- **Authorization**:
  - Route dependencies check:
    - User is authenticated.
    - Role is appropriate (admin-only routes vs base user).
  - Resource scoping examples:
    - A user can access only their own `builds`, `threads`, and `messages`.
    - Admins can access broader user and catalog data.

### 4.3 Bootstrap Admin (RBAC Source-of-Truth)

The first admin user is **not created via the public registration flow**. Instead, it is configured via environment variables and ensured on backend startup.

- **Configuration** (in `.env`):
  - `ADMIN_EMAIL`
  - `ADMIN_PASSWORD`
  - `ADMIN_FIRST_NAME` (optional)
  - `ADMIN_LAST_NAME` (optional)

- **Startup behavior**:
  - If `ADMIN_EMAIL` is not set, bootstrap admin logic is skipped.
  - If `ADMIN_EMAIL` is set but `ADMIN_PASSWORD` is missing, the backend fails fast on startup.
  - If an **active** user exists with `ADMIN_EMAIL`:
    - If that user is already an admin, do nothing.
    - If that user is **not** an admin, fail fast (no privilege escalation).
  - If no **active** user exists with that email, create a new admin user from the configured credentials.
    - This is compatible with soft delete email reuse because email uniqueness is enforced only for active users.

### 4.3 Database Access

- Likely using SQLAlchemy or async PostgreSQL driver.
- All queries:
  - Respect soft deletes: `WHERE deleted_at IS NULL` in normal operations.
  - Use specific models for `users`, `builds`, `build_parts`, components, `threads`, `messages`, etc.

### 4.4 Thread & Message Flow

**Creating a thread**:

- Endpoint: `POST /threads`
  - Authenticated user.
  - Creates `threads` row with `user_id = current_user.id`.
  - Optionally accepts `thread_name`.

**Sending a message**:

- Endpoint: `POST /threads/{thread_id}/messages`
  - Request body includes `user_request` and optionally `build_id` (the build to attach to **this** message; omit or null for general questions).
  - Backend checks:
    - `thread.user_id == current_user.id`.
    - `threads.deleted_at IS NULL`.
  - Inserts a new row into `messages`:
    - `user_request`, `build_id` (from request or NULL), `ai_response` = NULL.
  - Invokes the orchestrator with this message’s `build_id` and recent thread context.
  - Once orchestrator responds, backend updates `ai_response` for that `messages` row.
  - Returns the completed message to the client.

**Current implementation note (CRUD-first phase)**:

- The API currently implements CRUD for builds, threads, messages, and read-only catalog browsing.
- The AI orchestrator call is intentionally stubbed; `ai_response` is filled with a placeholder until the AI layer is implemented later.

**Pagination & context**:

- When the orchestrator is invoked, backend may:
  - Fetch the latest N `messages` for that `thread` as conversational context.
  - The orchestrator uses this context to maintain state across turns.

---

## 5. Multi-Agent AI System (Pydantic AI)

### 5.1 Orchestrator (Supervisor)

The orchestrator is the central controller that:

- Receives:
  - User’s latest request (`user_request`).
  - Conversation context (recent messages from the same `thread`).
  - Build context for this message (`messages.build_id`): when non-null, the orchestrator reasons about that build (e.g. compatibility, analysis); when null, the question is treated as not about a specific build.
- Determines the **intent** and routes to:
  - **SQL agent only** – for strictly data retrieval questions.
  - **RAG agent only** – for conceptual/expert advice that does not depend on the DB.
  - **Both agents** – for hybrid questions requiring structured data + nuanced guidance.
  - **Self** – for trivial or meta questions it can answer directly without sub-agents.
- Returns a **final natural-language response**, which is stored as `ai_response` in the `messages` table.

**Intent categories (conceptual)**:

- `DATABASE_FACT` – e.g. “Top 5 cheapest GPUs”, “Show AM5 motherboards under $200”.
  - Orchestrator routes to **SQL agent** only.
- `EXPERT_ADVICE` – e.g. “Is DLSS better than FSR?”, “Explain SLC vs TLC NAND endurance”.
  - Orchestrator routes to **RAG agent** only.
- `MIXED` – e.g. “Given my current build, is this PSU enough for a 4090?”
  - Orchestrator fetches build data via **SQL agent** and contextual info via **RAG agent**, then synthesizes.
- `CHITCHAT` / simple meta questions – e.g. “What did I just ask?”, “Which build am I working on?”
  - Orchestrator answers directly using context.

### 5.2 SQL Agent (Data Specialist)

Responsibilities:

- Translate natural language requests into **safe, read-only SQL** over the application database.
- Common use cases:
  - List components by price, performance, or spec filters.
  - Summarize a user’s builds and build parts.
  - Compute basic compatibility checks (e.g. socket matching, form-factor checks, PSU wattage vs estimated load).

Design constraints:

- **Read-only access**:
  - The SQL agent operates with a DB role that only has `SELECT` privileges.
  - No `INSERT`, `UPDATE`, or `DELETE` statements are allowed.
- **Soft delete awareness**:
  - Templates include `WHERE deleted_at IS NULL` for relevant tables.
  - Ensures “deleted” entities are not surfaced to normal users or the assistant.
- **Schema awareness**:
  - The agent is configured with an explicit schema description (tables, columns, relationships).

### 5.3 RAG Agent (Expert Consultant)

Responsibilities:

- Answer questions requiring **domain knowledge** not directly stored as structured data.
- Use hardware-related docs (papers, blogs, benchmarks) stored as embeddings in PostgreSQL.

Flow:

1. Take the natural language question.
2. Embed the question vector.
3. Query `document_chunks` via `pgvector` similarity.
4. Combine top-k chunks plus the user question into the LLM prompt.
5. Produce a grounded explanation or recommendation.

The RAG agent is especially useful for:

- Explaining hardware concepts.
- Summarizing real-world performance discussions.
- Comparing product families or architectures holistically.

### 5.4 Hybrid Reasoning

When the orchestrator detects a **mixed** intent (build-specific + conceptual advice), it:

1. Uses SQL agent to fetch the relevant structured data for the active build or requested components.
2. Uses RAG agent to retrieve external knowledge about those parts, benchmarks, or technologies.
3. Synthesizes a single **coherent report** (compatibility, performance, pros/cons, upgrade paths).

This hybrid answer is then stored as the `ai_response` in the `messages` table.

---

## 6. Frontend Design (React)

### 6.1 High-Level Pages / Views

- **Authentication**
  - Login and registration forms.
  - JWT is stored securely (e.g. httpOnly cookie or secure storage).

- **User Dashboard / Build Workspace**
  - Lists the user’s builds.
  - Allows CRUD operations on builds:
    - Create new build.
    - Edit build metadata.
    - Soft-delete build (set `deleted_at`).
  - Within a build:
    - View and modify `build_parts` (add/remove/adjust quantity).
    - See build-level summaries (price, components list).

- **Hardware Library**
  - Filterable catalog view over all hardware component tables.
  - Filters:
    - Price range.
    - Brand (if captured).
    - Spec-based filters (e.g. core count, capacity, wattage).
  - Add-to-build actions that trigger backend calls to insert `build_parts` with proper `part_type`.

- **AI Hardware Assistant**
  - Thread list (chat sidebar).
  - Chat view showing message exchanges:
    - User messages (from `user_request`).
    - AI responses (from `ai_response`).
  - “New Chat” creates a new `threads` row.
  - User can attach a build to the **current message** (optional); that `build_id` is sent with the message and stored on the `messages` row. When non-null, the orchestrator reasons about that build; when null, the question is general. No data is lost when the user switches builds in the same thread—each message preserves which build (if any) was in context, so history of “which build was analyzed when” remains available.

- **Admin Portal**
  - User supervision:
    - List/search users.
    - View a user’s builds and histories.
  - Catalog management:
    - CRUD forms for each component table.
    - Deprecate parts (set `deleted_at`) instead of hard-deleting.

### 6.2 Interaction with Backend & Agents

- The React app communicates with FastAPI via REST APIs:
  - `GET /catalog/...` for hardware library.
  - `GET/POST/PUT/DELETE /builds` and `/builds/{id}/parts` for build workspace.
  - `GET/POST /threads` and `/threads/{id}/messages` for chat.
  - `POST /ai/chat` or `POST /threads/{id}/messages` for orchestrator entrypoint.
- The backend hides the multi-agent mechanics:
  - The frontend only sees a single endpoint for sending a chat message and receiving a reply.

---

## 7. Performance & Asynchronous Behavior

- **FastAPI**:
  - Endpoints are async where appropriate.
  - Long-running agent calls may be:
    - Handled synchronously with timeouts, or
    - Offloaded to background tasks with progress handling (if needed).

- **Perceived performance**:
  - The AI chat UI can show “thinking” indicators while the orchestrator and agents run.
  - Results are streamed or delivered once the orchestrator finalizes `ai_response`.

- **SQL and RAG agent performance**:
  - Use indexes on key columns (`id`, `user_id`, `build_id`, `thread_id`, etc.).
  - Consider indexes on filter-heavy fields (e.g. `price`, `socket`) for catalog queries.
  - Configure `pgvector` indexes for efficient similarity search on `document_chunks.embedding`.

---

## 8. Security & Safety Considerations

- **DB Role for SQL Agent**:
  - The SQL agent uses a **read-only** PostgreSQL user.
  - This user has only `SELECT` privileges on relevant tables.
  - Mitigates risks from prompt injection trying to manipulate data.

- **Prompt & query validation**:
  - SQL generated by the agent is restricted to:
    - `SELECT` statements.
    - Table and column names from a controlled whitelist.

- **Application-level authorization**:
  - Even read-only SQL agent queries must:
    - Respect per-user scoping (e.g. a user should not see other users’ builds).
    - Respect soft deletions (`deleted_at IS NULL`).
  - This may be done by:
    - Preconstructed SQL templates, or
    - Post-processing SQL to inject required constraints.

- **JWT security**:
  - JWTs are signed with a secure secret.
  - Tokens have reasonable expiration times and optional refresh logic.

---

## 9. Testing & Validation Strategy

- **Unit tests**:
  - For core business logic:
    - Build creation and manipulation.
    - Catalog filtering.
    - Auth mechanisms.

- **Integration tests**:
  - For key API flows:
    - End-to-end build creation and part addition.
    - AI chat round trip (message insertion → orchestrator → `ai_response` storage).
    - Admin catalog operations.

- **Agent tests (where feasible)**:
  - Prompt-based tests to ensure:
    - SQL agent generates correct and safe queries for defined intents.
    - Orchestrator routes simple vs mixed queries correctly.
    - RAG agent remains grounded in retrieved documents.

---

## 10. Summary

This technical design describes how:

- A normalized PostgreSQL schema models users, builds, build parts, hardware components, conversation threads, messages, and RAG documents.
- FastAPI and React coordinate to provide authenticated user and admin experiences.
- A Pydantic AI-based multi-agent system (Orchestrator, SQL Agent, RAG Agent) answers user questions, either from structured data, unstructured docs, or a combination.
- Soft deletes, strict read-only DB roles for the SQL agent, and careful API design help maintain security and data integrity.

This document serves as the blueprint for initial implementation in the upcoming development phases.