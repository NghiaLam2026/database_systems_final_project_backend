"""Thin wrapper around Gemini gemini-embedding-001 for generating embeddings.

Uses the ``google-genai`` SDK already in the project's dependencies.
Outputs 768-dim vectors via the ``output_dimensionality`` parameter (MRL).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from google import genai
from google.genai import types

if TYPE_CHECKING:
    from app.config import Settings

logger = logging.getLogger(__name__)

_MODEL = "gemini-embedding-001"
_DIMENSIONS = 768
_BATCH_LIMIT = 100  # Gemini embed_content max texts per call

def embed_texts(
    texts: list[str],
    settings: "Settings",
    *,
    task_type: str = "RETRIEVAL_DOCUMENT",
) -> list[list[float]]:
    """Return 768-dim embeddings for each text using Gemini gemini-embedding-001.

    Parameters
    ----------
    task_type:
        One of the supported task types for gemini-embedding-001.
        Use ``RETRIEVAL_DOCUMENT`` when embedding documents for indexing,
        and ``RETRIEVAL_QUERY`` when embedding a search query.
    """
    if not texts:
        return []

    client = genai.Client(api_key=settings.gemini_api_key)
    all_embeddings: list[list[float]] = []

    for start in range(0, len(texts), _BATCH_LIMIT):
        batch = texts[start : start + _BATCH_LIMIT]
        response = client.models.embed_content(
            model=_MODEL,
            contents=batch,
            config=types.EmbedContentConfig(
                task_type=task_type,
                output_dimensionality=_DIMENSIONS,
            ),
        )
        for emb in response.embeddings:
            all_embeddings.append(emb.values)

    return all_embeddings