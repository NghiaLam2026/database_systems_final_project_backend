"""query_database tool — delegate a data question to the text-to-SQL agent.

Used by the orchestrator. Passes the user's natural-language question to the
SQL agent, which generates SQL, validates it, runs it, and returns a summary.
"""

from __future__ import annotations
from pydantic_ai import Agent, RunContext
import structlog
from app.deps import OrchestratorDeps
from app.services.sql_agent import ask_sql_agent

logger = structlog.get_logger(__name__)

def register(agent: Agent) -> None:
    """Attach the ``query_database`` tool to *agent*."""

    @agent.tool
    def query_database(ctx: RunContext["OrchestratorDeps"], question: str) -> str:
        """Look up live data from the PC parts catalog or builds database.

        Use this tool when the user asks about specific pricing, component
        specs, availability, comparisons, build contents, or any question
        that requires data from the database.

        Args:
            question: The natural-language question to answer using SQL.

        Returns:
            A natural-language summary of the query results, or an error
            message if the lookup failed.
        """
        logger.info(
            "agent.delegate",
            from_agent="orchestrator",
            to_agent="sql_agent",
            role=ctx.deps.user_role,
            question_chars=len(question or ""),
        )
        return ask_sql_agent(
            ctx.deps.db,
            ctx.deps.settings,
            user_question=question,
            user_role=ctx.deps.user_role,
        )