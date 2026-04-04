"""units_columns_to_string

Convert numeric columns that carry units in the CSV source data
(e.g. "4.7 GHz", "120 W", "2 x 16GB") from Integer/Numeric to
String(100) so the raw value + unit are preserved for display.

Revision ID: b4e2a7f31c09
Revises: a3f1c8d92e01
Create Date: 2026-04-02 02:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'b4e2a7f31c09'
down_revision: Union[str, Sequence[str], None] = 'a3f1c8d92e01'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TO_STRING = sa.String(length=100)

CHANGES: list[tuple[str, str, sa.types.TypeEngine]] = [
    # (table, column, old_type)
    ("cpu",        "perf_clock",        sa.Numeric(4, 2)),
    ("cpu",        "boost_clock",       sa.Numeric(4, 2)),
    ("cpu",        "tdp",               sa.INTEGER()),
    ("gpu",        "memory",            sa.INTEGER()),
    ("gpu",        "core_clock",        sa.Numeric(6, 2)),
    ("gpu",        "boost_clock",       sa.Numeric(6, 2)),
    ("gpu",        "length",            sa.Numeric(6, 2)),
    ("mobo",       "memory_max",        sa.INTEGER()),
    ("memory",     "speed",             sa.INTEGER()),
    ("memory",     "modules",           sa.INTEGER()),
    ("memory",     "first_word_latency", sa.Numeric(6, 3)),
    ("psu",        "wattage",           sa.INTEGER()),
    ("case",       "volume",            sa.Numeric(10, 2)),
    ("cpu_cooler", "fan_rpm",           sa.INTEGER()),
    ("cpu_cooler", "noise_level",       sa.Numeric(5, 2)),
    ("cpu_cooler", "radiator_size",     sa.INTEGER()),
    ("storage",    "capacity",          sa.INTEGER()),
    ("storage",    "cache",             sa.INTEGER()),
    ("case_fans",  "size",              sa.INTEGER()),
    ("case_fans",  "rpm",               sa.INTEGER()),
    ("case_fans",  "airflow",           sa.Numeric(6, 2)),
    ("case_fans",  "noise_level",       sa.Numeric(5, 2)),
]


def upgrade() -> None:
    for table, column, old_type in CHANGES:
        op.alter_column(
            table, column,
            existing_type=old_type,
            type_=_TO_STRING,
            existing_nullable=True,
            postgresql_using=f"{column}::text",
        )


def downgrade() -> None:
    for table, column, old_type in CHANGES:
        op.alter_column(
            table, column,
            existing_type=_TO_STRING,
            type_=old_type,
            existing_nullable=True,
            postgresql_using=f"regexp_replace({column}, '[^0-9.]', '', 'g')::{old_type.compile()}",
        )