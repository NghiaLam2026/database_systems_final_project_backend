"""Erase all data from catalog tables (component tables only).

Usage:
    python -m scripts.reset_catalog                  # wipe all catalog tables
    python -m scripts.reset_catalog cpu gpu           # wipe specific tables
    python -m scripts.reset_catalog --dry-run         # preview without deleting
"""

import argparse
import sys
from pathlib import Path

import sqlalchemy as sa

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings  # noqa: E402
from app.models.component import (  # noqa: E402
    CPU, GPU, Mobo, Memory, PSU, Case, CPUCooler, CaseFan, Storage,
)

TABLE_MAP: dict[str, type] = {
    "cpu":        CPU,
    "gpu":        GPU,
    "mobo":       Mobo,
    "memory":     Memory,
    "psu":        PSU,
    "case":       Case,
    "cpu_cooler": CPUCooler,
    "case_fans":  CaseFan,
    "storage":    Storage,
}


def main():
    parser = argparse.ArgumentParser(description="Erase data from catalog tables.")
    parser.add_argument(
        "tables",
        nargs="*",
        choices=list(TABLE_MAP.keys()),
        help="Tables to wipe (default: all).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview which tables would be wiped without deleting.",
    )
    args = parser.parse_args()

    settings = get_settings()
    engine = sa.create_engine(settings.database_url)

    targets = args.tables or list(TABLE_MAP.keys())

    for key in targets:
        model = TABLE_MAP[key]
        table = model.__table__

        if args.dry_run:
            with engine.connect() as conn:
                count = conn.execute(sa.select(sa.func.count()).select_from(table)).scalar()
            print(f"  [dry-run] would delete {count} rows from '{table.name}'")
            continue

        with engine.begin() as conn:
            result = conn.execute(sa.delete(table))
            print(f"  [done] deleted {result.rowcount} rows from '{table.name}'")

    print("\nFinished." if not args.dry_run else "\nDry-run finished. No data was deleted.")


if __name__ == "__main__":
    main()