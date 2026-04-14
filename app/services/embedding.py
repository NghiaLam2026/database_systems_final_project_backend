"""Local embedding service using Ollama with Qwen3-Embedding.

Runs entirely on-device via an Ollama server — no cloud API keys or usage
limits.  The default model is ``qwen3-embedding:8b`` (MTEB multilingual #1),
which natively produces 4096-dim vectors but supports Matryoshka
Representation Learning (MRL) so we can request exactly 768 dimensions
for storage efficiency without meaningful quality loss.

Prerequisites
-------------
1. Install Ollama: https://ollama.com/download
2. Pull the model once::

       ollama pull qwen3-embedding:8b

3. Ensure the Ollama server is running (``ollama serve`` or the desktop app).

Configuration (via .env)
------------------------
``OLLAMA_BASE_URL``         – default ``http://localhost:11434``
``EMBEDDING_MODEL``         – default ``qwen3-embedding:8b``
``EMBEDDING_DIMENSIONS``    – default ``768`` (must match the DB vector column)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import ollama as _ollama

if TYPE_CHECKING:
    from app.config import Settings

logger = logging.getLogger(__name__)

_BATCH_LIMIT = 64

_QUERY_INSTRUCTION = (
    "Instruct: Given a user question about PC hardware, retrieve relevant "
    "passages that answer the question\nQuery: "
)


def embed_texts(
    texts: list[str],
    settings: "Settings",
    *,
    task_type: str = "RETRIEVAL_DOCUMENT",
) -> list[list[float]]:
    """Return embeddings for each text using a local Ollama embedding model.

    Parameters
    ----------
    task_type:
        ``RETRIEVAL_DOCUMENT`` (default) for indexing documents — text is
        embedded as-is.
        ``RETRIEVAL_QUERY`` for search queries — a task-specific instruction
        prefix is prepended to improve retrieval quality (~1-5% gain per
        Qwen3-Embedding docs).
    """
    if not texts:
        return []

    client = _ollama.Client(host=settings.ollama_base_url)
    model = settings.embedding_model
    dims = settings.embedding_dimensions

    if task_type == "RETRIEVAL_QUERY":
        texts = [f"{_QUERY_INSTRUCTION}{t}" for t in texts]

    all_embeddings: list[list[float]] = []

    for start in range(0, len(texts), _BATCH_LIMIT):
        batch = texts[start : start + _BATCH_LIMIT]
        try:
            response = client.embed(model=model, input=batch, truncate=True)
        except _ollama.ResponseError as exc:
            logger.error(
                "Ollama embed call failed (model=%s): %s", model, exc
            )
            raise

        for emb in response.embeddings:
            if dims and len(emb) > dims:
                emb = emb[:dims]
            all_embeddings.append(emb)

    return all_embeddings
