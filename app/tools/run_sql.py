"""run_sql tool — validate and execute a read-only SQL query.

Used by the text-to-SQL agent. Validates via ``sql_validator`` (role-aware),
then executes against PostgreSQL and returns JSON rows.
"""

from __future__ import annotations

import json
import logging
from decimal import Decimal
from datetime import datetime, date
from typing import TYPE_CHECKING, Any

from pydantic_ai import Agent, RunContext
from sqlalchemy import text

from app.services.sql_validator import SQLValidationError, validate_sql

if TYPE_CHECKING:
    from app.services.sql_agent import SQLAgentDeps

logger = logging.getLogger(__name__)

_MAX_ROWS = 50
_MAX_RESULT_CHARS = 8_000


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


def register(agent: Agent) -> None:
    """Attach the ``run_sql`` tool to *agent*."""

    @agent.tool
    def run_sql(ctx: RunContext["SQLAgentDeps"], sql_query: str) -> str:
        """Validate and execute a read-only SQL query against the database.

        Args:
            sql_query: A single PostgreSQL SELECT statement.

        Returns:
            JSON string with keys ``columns``, ``rows``, ``row_count``, or
            an ``error`` key if validation / execution fails.
        """
        try:
            clean_sql = validate_sql(sql_query, user_role=ctx.deps.user_role)
        except SQLValidationError as exc:
            logger.warning("SQL validation rejected: %s — %s", sql_query[:120], exc)
            return json.dumps({"error": f"SQL rejected: {exc}"})

        db = ctx.deps.db
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
