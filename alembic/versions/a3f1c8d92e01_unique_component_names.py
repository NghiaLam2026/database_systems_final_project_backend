"""unique_component_names

Revision ID: a3f1c8d92e01
Revises: 909500e590cf
Create Date: 2026-03-30 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op

revision: str = 'a3f1c8d92e01'
down_revision: Union[str, Sequence[str], None] = '909500e590cf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

COMPONENT_TABLES = ['cpu', 'gpu', 'mobo', 'memory', 'psu', 'case', 'cpu_cooler', 'case_fans', 'storage']

def upgrade() -> None:
    for table in COMPONENT_TABLES:
        op.create_index(
            f'uq_{table}_name',
            table,
            ['name'],
            unique=True,
        )

def downgrade() -> None:
    for table in COMPONENT_TABLES:
        op.drop_index(f'uq_{table}_name', table_name=table)