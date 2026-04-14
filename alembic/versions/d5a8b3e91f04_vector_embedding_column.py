"""vector_embedding_column

Change document_chunks.embedding from float[] to vector(768)
and add an HNSW index for cosine similarity search.

Revision ID: d5a8b3e91f04
Revises: c7f3a9d41b02
Create Date: 2026-04-12 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'd5a8b3e91f04'
down_revision: Union[str, Sequence[str], None] = 'c7f3a9d41b02'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE document_chunks "
        "ALTER COLUMN embedding TYPE vector(768) "
        "USING embedding::vector(768)"
    )
    op.execute(
        "CREATE INDEX ix_document_chunks_embedding_hnsw "
        "ON document_chunks USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.drop_index("ix_document_chunks_embedding_hnsw", table_name="document_chunks")
    op.execute(
        "ALTER TABLE document_chunks "
        "ALTER COLUMN embedding TYPE float[] "
        "USING embedding::float[]"
    )