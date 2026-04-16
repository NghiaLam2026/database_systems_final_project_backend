"""query_rag tool — delegate a knowledge-base question to the RAG agent.

Used by the orchestrator. Passes the user's natural-language question to
the RAG agent, which retrieves relevant document chunks and returns a
grounded answer.
"""

from __future__ import annotations
from pydantic_ai import Agent, RunContext
import structlog
from app.deps import OrchestratorDeps
from app.services.rag_agent import ask_rag_agent

logger = structlog.get_logger(__name__)

def register(agent: Agent) -> None:
    """Attach the ``query_rag`` tool to *agent*."""

    @agent.tool
    def query_rag(ctx: RunContext["OrchestratorDeps"], question: str) -> str:
        """Search the knowledge base for hardware reviews, benchmarks, guides, and articles.

        Use this tool when the user asks for component recommendations,
        "which part is best for gaming/productivity/etc.", real-world
        performance comparisons, benchmark data, build guides,
        compatibility explanations, overclocking tips, or any question
        that benefits from expert reviews and articles rather than raw
        catalog data.

        Args:
            question: The natural-language question to answer from docs.

        Returns:
            A grounded answer based on retrieved document chunks, or an
            error message if the lookup failed.
        """
        logger.info(
            "agent.delegate",
            from_agent="orchestrator",
            to_agent="rag_agent",
            question_chars=len(question or ""),
        )
        return ask_rag_agent(
            ctx.deps.db,
            ctx.deps.settings,
            user_question=question,
        )