"""Shared dependency containers for Pydantic AI agents.

These classes are injected into agent tools via ``RunContext``.  They live
in their own module to avoid circular imports between agent services
(which build agents) and tool modules (which register tools on agents).
"""

from typing import Any
from pydantic import BaseModel

class OrchestratorDeps(BaseModel):
    """Runtime dependencies for orchestrator tools (``query_database``, ``query_rag``)."""
    model_config = {"arbitrary_types_allowed": True}
    db: Any          # sqlalchemy Session
    settings: Any    # app Settings
    user_role: str   # "user" or "admin"

class SQLAgentDeps(BaseModel):
    """Runtime dependencies for the text-to-SQL agent's ``run_sql`` tool."""
    model_config = {"arbitrary_types_allowed": True}
    db: Any        # sqlalchemy Session
    settings: Any  # app Settings
    user_role: str # "user" or "admin"

class RAGAgentDeps(BaseModel):
    """Runtime dependencies for the RAG agent's ``retrieve_chunks`` tool."""
    model_config = {"arbitrary_types_allowed": True}
    db: Any       # sqlalchemy Session
    settings: Any # app Settings