"""Agent tools — reusable Pydantic AI tool functions.

Each sub-module exposes a ``register(agent)`` function that attaches the
tool to the given agent instance.
"""

from app.tools.run_sql import register as register_run_sql
from app.tools.query_database import register as register_query_database
from app.tools.retrieve_chunks import register as register_retrieve_chunks
from app.tools.query_rag import register as register_query_rag

__all__ = [
    "register_run_sql",
    "register_query_database",
    "register_retrieve_chunks",
    "register_query_rag",
]
