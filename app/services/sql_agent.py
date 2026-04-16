"""Text-to-SQL agent: translates natural-language questions into safe,
read-only SQL, executes them, and returns the results.

Flow
----
1. Load the semantic layer YAML once (cached).
2. Build a Pydantic AI agent with a system prompt that includes the full
   semantic layer so the model knows every table, column, relationship,
   metric, and verified-query example.
3. The agent has a single tool — ``run_sql`` (registered from
   ``app.tools.run_sql``) — which validates the SQL (read-only check +
   role-based table/column enforcement via ``sql_validator``) and executes
   it against PostgreSQL, returning rows as dicts.
4. The orchestrator calls ``ask_sql_agent()`` when it needs catalog /
   build / pricing data from the database.
"""

from __future__ import annotations

import time
from pathlib import Path
from functools import lru_cache
from typing import TYPE_CHECKING
from pydantic_ai import Agent
from pydantic_ai.models.google import GoogleModel, GoogleModelSettings
from pydantic_ai.providers.google import GoogleProvider
import structlog
from app.deps import SQLAgentDeps
from app.tools import register_run_sql

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from app.config import Settings

logger = structlog.get_logger(__name__)

_SEMANTIC_LAYER_PATH = Path(__file__).resolve().parents[2] / "semantic_layer.yaml"


# ---------------------------------------------------------------------------
# Semantic layer loading
# ---------------------------------------------------------------------------
@lru_cache(maxsize=1)
def _load_semantic_layer() -> str:
    """Read the YAML file and return it as a string for the system prompt."""
    return _SEMANTIC_LAYER_PATH.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# System prompts (role-dependent preamble + shared body)
# ---------------------------------------------------------------------------
_ROLE_PREAMBLE_USER = """\
## Access control — you are serving a **regular user**
You may ONLY query the hardware catalog tables:
  cpu, gpu, mobo, memory, "case", storage, cpu_cooler, psu, case_fans.
You MUST NOT query users, builds, build_parts, threads, messages,
documents, or document_chunks. If the user asks about those topics,
reply that this information is not available to regular users.
You MUST NOT select the column `password_hash` from any table.
"""

_ROLE_PREAMBLE_ADMIN = """\
## Access control — you are serving an **admin**
You may query all application tables: users, builds, build_parts,
threads, messages, documents, document_chunks, and all catalog tables
(cpu, gpu, mobo, memory, "case", storage, cpu_cooler, psu, case_fans).
You MUST NOT select the column `password_hash` — ever.
When querying user-related tables, always apply `deleted_at IS NULL`
unless the admin explicitly asks about deleted records.
"""

_SQL_AGENT_SYSTEM_PROMPT = """\
You are a **text-to-SQL specialist** embedded inside the PC Build Assistant.
Your ONLY job is to convert the user's natural-language question into a single,
safe, read-only PostgreSQL SELECT statement, execute it via the `run_sql` tool,
and then present the results in a clear, conversational summary.

{role_preamble}

## Rules — follow every one without exception
1. **Read-only**: Generate ONLY `SELECT` statements. Never `INSERT`, `UPDATE`,
   `DELETE`, `DROP`, `ALTER`, `TRUNCATE`, `CREATE`, or any DDL/DML/DCL.
2. **Single statement**: Produce exactly ONE SQL statement per request.
   No semicolons separating multiple statements.
3. **Soft deletes**: For tables that have a `deleted_at` column (`users`,
   `builds`, `build_parts`, `threads`, `messages`), ALWAYS add
   `deleted_at IS NULL` to the WHERE clause unless the user explicitly
   asks about deleted records.
4. **Quoting**: The table named `case` is a PostgreSQL reserved word —
   always double-quote it as `"case"` in your SQL.
5. **Polymorphic joins**: `build_parts` references catalog tables via
   `(part_type, part_id)`. When joining, filter `part_type` first, then
   join on `part_id = <catalog_table>.id`.
6. **Limit results**: Unless the user asks for a specific count or "all",
   add `LIMIT 25` to avoid huge result sets.
7. **Privacy**: Never expose `password_hash`. Never use SELECT * on the
   users table — always list specific columns.
8. **No fabrication**: If the data doesn't exist or the query returns no
   rows, say so honestly. Do not invent data.
9. **Explain your answer**: After getting results from `run_sql`, summarise
   them in natural language. Include the most relevant numbers, names, and
   prices. You may use markdown tables for clarity.
10. **If you cannot answer**: If the question cannot be answered with the
    tables you have access to, say so and explain what is outside your scope.

## Workflow
1. Read the semantic layer (provided below) to understand tables, columns,
   relationships, and sample queries.
2. Formulate a PostgreSQL SELECT statement that answers the user's question.
3. Call the `run_sql` tool with your SQL.
4. Read the result rows and compose a helpful answer.

## Semantic Layer
The full semantic layer is provided below. Use it as your schema reference.

```yaml
{semantic_layer}
```
"""


# ---------------------------------------------------------------------------
# Build the agent and register tool(s)
# ---------------------------------------------------------------------------
def _build_sql_agent(settings: "Settings", *, user_role: str) -> Agent[SQLAgentDeps, str]:
    provider = GoogleProvider(api_key=settings.gemini_api_key)
    model = GoogleModel(settings.gemini_model, provider=provider)
    model_settings = GoogleModelSettings(temperature=0.0, max_tokens=4096)

    semantic_layer_text = _load_semantic_layer()
    role_preamble = (
        _ROLE_PREAMBLE_ADMIN if user_role == "admin" else _ROLE_PREAMBLE_USER
    )
    system_prompt = (
        _SQL_AGENT_SYSTEM_PROMPT
        .replace("{role_preamble}", role_preamble)
        .replace("{semantic_layer}", semantic_layer_text)
    )

    agent: Agent[SQLAgentDeps, str] = Agent(
        model,
        instructions=system_prompt,
        model_settings=model_settings,
        deps_type=SQLAgentDeps,
    )

    register_run_sql(agent)

    return agent


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
def ask_sql_agent(
    db: "Session",
    settings: "Settings",
    *,
    user_question: str,
    user_role: str = "user",
) -> str:
    """Run the text-to-SQL agent and return its final natural-language answer.

    Called by the orchestrator when a question requires live database data.

    Parameters
    ----------
    user_role:
        ``"user"`` or ``"admin"``.  Controls which tables the generated
        SQL is allowed to touch.
    """
    start = time.perf_counter()
    agent = _build_sql_agent(settings, user_role=user_role)
    deps = SQLAgentDeps(db=db, settings=settings, user_role=user_role)

    try:
        result = agent.run_sync(user_question, deps=deps)
        out = (result.output or "").strip()
        if out:
            logger.info(
                "agent.finish",
                name="sql_agent",
                role=user_role,
                duration_ms=round((time.perf_counter() - start) * 1000, 1),
                output_chars=len(out),
            )
            return out
        logger.info(
            "agent.finish",
            name="sql_agent",
            role=user_role,
            duration_ms=round((time.perf_counter() - start) * 1000, 1),
            output_chars=0,
        )
        return "The SQL agent returned an empty response. Please try rephrasing."
    except Exception:
        logger.exception("SQL agent run failed")
        return (
            "I tried to look that up in the database but hit an error. "
            "Please try again or rephrase your question."
        )