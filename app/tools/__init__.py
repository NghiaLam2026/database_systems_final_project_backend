"""Agent tools — reusable Pydantic AI tool functions.

Each sub-module exposes a ``register(agent)`` function that attaches the
tool to the given agent instance.
"""

from app.tools.run_sql import register as register_run_sql
from app.tools.query_database import register as register_query_database

__all__ = [
    "register_run_sql",
    "register_query_database",
]
