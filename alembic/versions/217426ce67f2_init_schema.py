"""init_schema

Revision ID: 217426ce67f2
Revises: 
Create Date: 2026-03-12 23:02:00.194316

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM

# revision identifiers, used by Alembic.
revision: str = '217426ce67f2'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """Create initial schema."""

    # --- Custom types ---
    # Use postgresql.ENUM (not sa.Enum): create_type=False is honored so we do not
    # emit CREATE TYPE again inside op.create_table (duplicate without this).
    part_type_enum = ENUM(
        'cpu',
        'gpu',
        'mobo',
        'memory',
        'psu',
        'case',
        'cpu_cooler',
        'case_fans',
        'storage',
        name='part_type',
        create_type=False,
    )

    role_enum = ENUM(
        'user',
        'admin',
        name='user_role',
        create_type=False,
    )

    # Register enums
    part_type_enum.create(op.get_bind(), checkfirst=True)
    role_enum.create(op.get_bind(), checkfirst=True)

    # Enable pgvector for RAG, if available (PostgreSQL)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # --- Core tables ---
    op.create_table(
        'users',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('first_name', sa.String(length=100), nullable=False),
        sa.Column('last_name', sa.String(length=100), nullable=False),
        sa.Column('role', role_enum, nullable=False, server_default='user'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        'uq_users_email_active',
        'users',
        ['email'],
        unique=True,
        postgresql_where=sa.text('deleted_at IS NULL'),
    )

    op.create_table(
        'builds',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('build_name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_builds_user_id', 'builds', ['user_id'])

    op.create_table(
        'threads',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('thread_name', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_threads_user_id', 'threads', ['user_id'])

    op.create_table(
        'messages',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('thread_id', sa.Integer, sa.ForeignKey('threads.id', ondelete='CASCADE'), nullable=False),
        sa.Column('build_id', sa.Integer, sa.ForeignKey('builds.id', ondelete='RESTRICT'), nullable=True),
        sa.Column('user_request', sa.Text, nullable=False),
        sa.Column('ai_response', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_messages_thread_id', 'messages', ['thread_id'])
    op.create_index('ix_messages_build_id', 'messages', ['build_id'])

    # --- Component tables ---
    op.create_table(
        'mobo',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('socket', sa.String(length=50), nullable=True),
        sa.Column('form_factor', sa.String(length=50), nullable=False),
        sa.Column('memory_max', sa.Integer, nullable=True),
        sa.Column('memory_slot', sa.Integer, nullable=True),
        sa.Column('color', sa.String(length=50), nullable=True),
        sa.Column('price', sa.Numeric(10, 2), nullable=False),
    )

    op.create_table(
        'cpu',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('core_count', sa.Integer, nullable=False),
        sa.Column('perf_clock', sa.Numeric(4, 2), nullable=True),
        sa.Column('boost_clock', sa.Numeric(4, 2), nullable=True),
        sa.Column('microarch', sa.String(length=100), nullable=True),
        sa.Column('tdp', sa.Integer, nullable=True),
        sa.Column('graphics', sa.String(length=100), nullable=True),
        sa.Column('price', sa.Numeric(10, 2), nullable=False),
    )

    op.create_table(
        'memory',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('speed', sa.Integer, nullable=False),
        sa.Column('modules', sa.Integer, nullable=False),
        sa.Column('color', sa.String(length=50), nullable=True),
        sa.Column('first_word_latency', sa.Numeric(6, 3), nullable=True),
        sa.Column('cas_latency', sa.Numeric(4, 2), nullable=True),
        sa.Column('price', sa.Numeric(10, 2), nullable=False),
    )

    op.create_table(
        'case',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('color', sa.String(length=50), nullable=True),
        sa.Column('power_supply', sa.String(length=100), nullable=True),
        sa.Column('side_panel', sa.String(length=100), nullable=True),
        sa.Column('volume', sa.Numeric(10, 2), nullable=True),
        sa.Column('bays', sa.Integer, nullable=True),
        sa.Column('price', sa.Numeric(10, 2), nullable=False),
    )

    op.create_table(
        'storage',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('capacity', sa.Integer, nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('cache', sa.Integer, nullable=True),
        sa.Column('form_factor', sa.String(length=50), nullable=False),
        sa.Column('interface', sa.String(length=50), nullable=False),
        sa.Column('price', sa.Numeric(10, 2), nullable=False),
    )

    op.create_table(
        'cpu_cooler',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('fan_rpm', sa.Integer, nullable=True),
        sa.Column('noise_level', sa.Numeric(5, 2), nullable=True),
        sa.Column('color', sa.String(length=50), nullable=True),
        sa.Column('radiator_size', sa.Integer, nullable=True),
        sa.Column('price', sa.Numeric(10, 2), nullable=False),
    )

    op.create_table(
        'psu',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('efficiency', sa.String(length=50), nullable=True),
        sa.Column('wattage', sa.Integer, nullable=False),
        sa.Column('modular', sa.Boolean, nullable=True),
        sa.Column('color', sa.String(length=50), nullable=True),
        sa.Column('price', sa.Numeric(10, 2), nullable=False),
    )

    op.create_table(
        'case_fans',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('size', sa.Integer, nullable=False),
        sa.Column('color', sa.String(length=50), nullable=True),
        sa.Column('rpm', sa.Integer, nullable=True),
        sa.Column('airflow', sa.Numeric(6, 2), nullable=True),
        sa.Column('noise_level', sa.Numeric(5, 2), nullable=True),
        sa.Column('pwm', sa.Boolean, nullable=True),
        sa.Column('price', sa.Numeric(10, 2), nullable=False),
    )

    op.create_table(
        'gpu',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('chipset', sa.String(length=100), nullable=False),
        sa.Column('memory', sa.Integer, nullable=False),
        sa.Column('core_clock', sa.Numeric(6, 2), nullable=True),
        sa.Column('boost_clock', sa.Numeric(6, 2), nullable=True),
        sa.Column('color', sa.String(length=50), nullable=True),
        sa.Column('length', sa.Numeric(6, 2), nullable=True),
        sa.Column('price', sa.Numeric(10, 2), nullable=False),
    )

    # --- Build parts (polymorphic association to components) ---
    op.create_table(
        'build_parts',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('build_id', sa.Integer, sa.ForeignKey('builds.id', ondelete='CASCADE'), nullable=False),
        sa.Column('part_type', part_type_enum, nullable=False),
        sa.Column('part_id', sa.Integer, nullable=False),
        sa.Column('quantity', sa.Integer, nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_build_parts_build_id', 'build_parts', ['build_id'])
    op.create_index('ix_build_parts_part_type_part_id', 'build_parts', ['part_type', 'part_id'])

    # --- RAG tables (documents + chunks with pgvector embeddings) ---
    op.create_table(
        'documents',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('source', sa.String(length=50), nullable=True),
        sa.Column('url', sa.String(length=500), nullable=True),
        sa.Column('metadata', sa.JSON, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        'document_chunks',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('document_id', sa.Integer, sa.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('chunk_text', sa.Text, nullable=False),
        sa.Column('embedding', sa.dialects.postgresql.ARRAY(sa.Float), nullable=True),
        sa.Column('metadata', sa.JSON, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_document_chunks_document_id', 'document_chunks', ['document_id'])


def downgrade() -> None:
    """Drop initial schema."""

    # Drop RAG tables
    op.drop_index('ix_document_chunks_document_id', table_name='document_chunks')
    op.drop_table('document_chunks')
    op.drop_table('documents')

    # Drop build_parts and component tables
    op.drop_index('ix_build_parts_part_type_part_id', table_name='build_parts')
    op.drop_index('ix_build_parts_build_id', table_name='build_parts')
    op.drop_table('build_parts')

    op.drop_table('gpu')
    op.drop_table('case_fans')
    op.drop_table('psu')
    op.drop_table('cpu_cooler')
    op.drop_table('storage')
    op.drop_table('case')
    op.drop_table('memory')
    op.drop_table('cpu')
    op.drop_table('mobo')

    # Drop messaging and core tables
    op.drop_index('ix_messages_build_id', table_name='messages')
    op.drop_index('ix_messages_thread_id', table_name='messages')
    op.drop_table('messages')

    op.drop_index('ix_threads_user_id', table_name='threads')
    op.drop_table('threads')

    op.drop_index('ix_builds_user_id', table_name='builds')
    op.drop_table('builds')

    op.drop_table('users')

    # Drop enums
    bind = op.get_bind()
    sa.Enum(name='part_type').drop(bind, checkfirst=True)
    sa.Enum(name='user_role').drop(bind, checkfirst=True)