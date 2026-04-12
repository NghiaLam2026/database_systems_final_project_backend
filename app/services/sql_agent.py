"""Text-to-SQL agent: translates natural-language questions into safe,
read-only SQL, executes them, and returns the results.

Flow
----
1. Load the semantic layer YAML once (cached).
2. Build a Pydantic AI agent with a system prompt that includes the full
   semantic layer so the model knows every table, column, relationship,
   metric, and verified-query example.
3. The agent has a single tool — ``run_sql`` — which validates the SQL
   (read-only check via ``sql_validator``) and executes it against
   PostgreSQL, returning rows as dicts.
4. The orchestrator calls ``ask_sql_agent()`` when it needs catalog /
   build / pricing data from the database.
"""

from __future__ import annotations
import json
import logging
from decimal import Decimal
from datetime import datetime, date
from pathlib import Path
from functools import lru_cache
from typing import TYPE_CHECKING, Any
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.google import GoogleModel, GoogleModelSettings
from pydantic_ai.providers.google import GoogleProvider
from sqlalchemy import text

from app.services.sql_validator import SQLValidationError, validate_sql

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from app.config import Settings

logger = logging.getLogger(__name__)

_SEMANTIC_LAYER_PATH = Path(__file__).resolve().parents[2] / "semantic_layer.yaml"

_MAX_ROWS = 50
_MAX_RESULT_CHARS = 8_000

# ---------------------------------------------------------------------------
# Semantic layer loading
# ---------------------------------------------------------------------------
@lru_cache(maxsize=1)
def _load_semantic_layer() -> str:
    """Read the YAML file and return it as a string for the system prompt."""
    return _SEMANTIC_LAYER_PATH.read_text(encoding="utf-8")

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------
_SQL_AGENT_SYSTEM_PROMPT = """\
You are a **text-to-SQL specialist** embedded inside the PC Build Assistant.
Your ONLY job is to convert the user's natural-language question into a single,
safe, read-only PostgreSQL SELECT statement, execute it via the `run_sql` tool,
and then present the results in a clear, conversational summary.

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
7. **Privacy**: Never expose `password_hash`. Never query other users'
   data unless the question is clearly administrative / aggregate.
8. **No fabrication**: If the data doesn't exist or the query returns no
   rows, say so honestly. Do not invent data.
9. **Explain your answer**: After getting results from `run_sql`, summarise
   them in natural language. Include the most relevant numbers, names, and
   prices. You may use markdown tables for clarity.
10. **If you cannot answer**: If the question cannot be answered with the
    available schema, say so and explain what information is missing.

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
# Dependencies dataclass (passed to tool via RunContext)
# ---------------------------------------------------------------------------
class SQLAgentDeps(BaseModel):
    """Runtime dependencies injected into the agent's tool context."""
    model_config = {"arbitrary_types_allowed": True}
    db: Any  # sqlalchemy Session
    settings: Any  # app Settings

# ---------------------------------------------------------------------------
# Result serialiser
# ---------------------------------------------------------------------------
def _serialise_value(v: Any) -> Any:
    """Make a DB value JSON-friendly."""
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    if isinstance(v, bytes):
        return v.hex()
    return v


def _rows_to_serialisable(columns: list[str], rows: list[tuple]) -> list[dict]:
    return [{c: _serialise_value(v) for c, v in zip(columns, row)} for row in rows]

# ---------------------------------------------------------------------------
# Build the agent and register the tool
# ---------------------------------------------------------------------------
def _build_sql_agent(settings: "Settings") -> Agent[SQLAgentDeps, str]:
    provider = GoogleProvider(api_key=settings.gemini_api_key)
    model = GoogleModel(settings.gemini_model, provider=provider)
    model_settings = GoogleModelSettings(temperature=0.0, max_tokens=4096)

    semantic_layer_text = _load_semantic_layer()
    system_prompt = _SQL_AGENT_SYSTEM_PROMPT.replace(
        "{semantic_layer}", semantic_layer_text
    )

    agent: Agent[SQLAgentDeps, str] = Agent(
        model,
        instructions=system_prompt,
        model_settings=model_settings,
        deps_type=SQLAgentDeps,
    )

    @agent.tool
    def run_sql(ctx: RunContext[SQLAgentDeps], sql_query: str) -> str:
        """Validate and execute a read-only SQL query against the database.

        Args:
            sql_query: A single PostgreSQL SELECT statement.

        Returns:
            JSON string with keys ``columns``, ``rows``, ``row_count``, or
            an ``error`` key if validation / execution fails.
        """
        try:
            clean_sql = validate_sql(sql_query)
        except SQLValidationError as exc:
            logger.warning("SQL validation rejected: %s — %s", sql_query[:120], exc)
            return json.dumps({"error": f"SQL rejected: {exc}"})

        db: Session = ctx.deps.db
        try:
            result = db.execute(text(clean_sql))
            columns = list(result.keys())
            rows = result.fetchmany(_MAX_ROWS)
            data = _rows_to_serialisable(columns, rows)

            payload = json.dumps(
                {"columns": columns, "rows": data, "row_count": len(data)},
                default=str,
            )
            if len(payload) > _MAX_RESULT_CHARS:
                payload = payload[:_MAX_RESULT_CHARS] + '…(truncated)"}'
            return payload
        except Exception as exc:
            logger.exception("SQL execution failed: %s", clean_sql[:120])
            return json.dumps({"error": f"Query execution failed: {exc}"})

    return agent

# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
def ask_sql_agent(
    db: "Session",
    settings: "Settings",
    *,
    user_question: str,
) -> str:
    """Run the text-to-SQL agent and return its final natural-language answer.

    Called by the orchestrator when a question requires live database data.
    """
    agent = _build_sql_agent(settings)
    deps = SQLAgentDeps(db=db, settings=settings)

    try:
        result = agent.run_sync(user_question, deps=deps)
        out = (result.output or "").strip()
        if out:
            return out
        return "The SQL agent returned an empty response. Please try rephrasing."
    except Exception:
        logger.exception("SQL agent run failed")
        return (
            "I tried to look that up in the database but hit an error. "
            "Please try again or rephrase your question."
        )