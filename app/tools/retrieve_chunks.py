"""retrieve_chunks tool — vector-similarity search over document chunks.

Used by the RAG agent. Embeds the user's question with
``RETRIEVAL_QUERY`` task type, then runs a hardcoded pgvector cosine
similarity query.  No LLM-generated SQL — the query is fully static.
"""

from __future__ import annotations
import logging
from typing import TYPE_CHECKING
from pydantic_ai import Agent, RunContext
from sqlalchemy import text
from app.services.embedding import embed_texts

if TYPE_CHECKING:
    from app.services.rag_agent import RAGAgentDeps

logger = logging.getLogger(__name__)

_TOP_K = 5

def register(agent: Agent) -> None:
    """Attach the ``retrieve_chunks`` tool to *agent*."""

    @agent.tool
    def retrieve_chunks(ctx: RunContext["RAGAgentDeps"], question: str) -> str:
        """Search the knowledge base for document chunks relevant to *question*.

        Returns the top-k most similar chunk texts, separated by dividers.
        """
        vectors = embed_texts(
            [question],
            ctx.deps.settings,
            task_type="RETRIEVAL_QUERY",
        )
        if not vectors:
            return "(no embedding could be generated)"

        query_embedding = vectors[0]

        db = ctx.deps.db
        try:
            rows = db.execute(
                text(
                    "SELECT dc.chunk_text, d.title, "
                    "       dc.embedding <=> :emb AS distance "
                    "FROM document_chunks dc "
                    "JOIN documents d ON d.id = dc.document_id "
                    "WHERE dc.embedding IS NOT NULL "
                    "ORDER BY dc.embedding <=> :emb "
                    "LIMIT :k"
                ),
                {"emb": str(query_embedding), "k": _TOP_K},
            ).fetchall()
        except Exception:
            logger.exception("Vector similarity search failed")
            return "(vector search error — no results)"

        if not rows:
            return "(no relevant documents found)"

        parts: list[str] = []
        for chunk_text, title, distance in rows:
            parts.append(f"[source: {title} | distance: {distance:.4f}]\n{chunk_text}")

        return "\n\n---\n\n".join(parts)