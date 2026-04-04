"""rename_psu_case_columns

Rename columns for clarity:
  psu.efficiency        → psu.efficiency_rating
  case.volume           → case.external_volume
  case.bays             → case.internal_bays

Revision ID: c7f3a9d41b02
Revises: b4e2a7f31c09
Create Date: 2026-04-02 03:00:00.000000

"""
from typing import Sequence, Union
from alembic import op

revision: str = 'c7f3a9d41b02'
down_revision: Union[str, Sequence[str], None] = 'b4e2a7f31c09'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('psu', 'efficiency', new_column_name='efficiency_rating')
    op.alter_column('case', 'volume', new_column_name='external_volume')
    op.alter_column('case', 'bays', new_column_name='internal_bays')


def downgrade() -> None:
    op.alter_column('psu', 'efficiency_rating', new_column_name='efficiency')
    op.alter_column('case', 'external_volume', new_column_name='volume')
    op.alter_column('case', 'internal_bays', new_column_name='bays')