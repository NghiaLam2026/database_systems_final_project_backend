"""Seed component catalog tables from CSV files in the data/ directory.

Usage:
    python -m scripts.seed_catalog                  # seed all available categories
    python -m scripts.seed_catalog cpu              # seed only CPUs
    python -m scripts.seed_catalog cpu gpu mobo      # seed specific categories
    python -m scripts.seed_catalog --dry-run         # preview without writing to DB
"""

import argparse
import csv
import re
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert as pg_insert

# Allow imports from project root
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.models.component import (  # noqa: E402
    CPU, GPU, Mobo, Memory, PSU, Case, CPUCooler, CaseFan, Storage,
)

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "catalog"

# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def _take_range_max(value: str) -> str:
    """For range values like '600 - 3000', return the max (last part)."""
    parts = re.split(r"\s*-\s*", value.strip())
    return parts[-1] if parts else value

def parse_decimal(value: str) -> Decimal | None:
    """Strip units and currency symbols, return Decimal or None. Takes max of ranges."""
    if not value or value.strip().upper() == "N/A":
        return None
    numeric_part = _take_range_max(value)
    cleaned = re.sub(r"[^\d.]", "", numeric_part)
    if not cleaned:
        return None
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None

def parse_int(value: str) -> int | None:
    """Strip units, return int or None. Takes max of ranges."""
    if not value or value.strip().upper() == "N/A":
        return None
    numeric_part = _take_range_max(value)
    cleaned = re.sub(r"[^\d]", "", numeric_part)
    if not cleaned:
        return None
    try:
        return int(cleaned)
    except ValueError:
        return None

def parse_str(value: str) -> str | None:
    """Return None for empty / 'None' / 'N/A' strings."""
    if not value or value.strip().upper() in ("", "NONE", "N/A"):
        return None
    return value.strip()

def parse_price(value: str) -> Decimal | None:
    """Parse price strings like '$419.95', '$2,700.00'."""
    if not value or not value.strip():
        return None
    cleaned = re.sub(r"[^\d.]", "", value.strip())
    if not cleaned:
        return None
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None

def parse_bool(value: str) -> bool | None:
    if not value or value.strip().upper() in ("", "N/A"):
        return None
    lower = value.strip().lower()
    if lower in ("yes", "true", "1", "full"):
        return True
    if lower in ("no", "false", "0", "none"):
        return False
    return None

def parse_module_count(value: str) -> int | None:
    """Parse module strings like '2 x 16GB' → 2 (the count before 'x')."""
    if not value or value.strip().upper() in ("", "NONE", "N/A"):
        return None
    match = re.match(r"(\d+)\s*x\s*", value.strip())
    if match:
        return int(match.group(1))
    return parse_int(value)

# ---------------------------------------------------------------------------
# Category configurations
# ---------------------------------------------------------------------------

class CategoryConfig:
    """Maps a CSV file to a DB table with field transformers."""

    def __init__(self, key: str, csv_file: str, model, field_map: dict):
        self.key = key
        self.csv_file = csv_file
        self.model = model
        self.field_map = field_map

    def csv_path(self) -> Path:
        return DATA_DIR / self.csv_file

    def parse_row(self, row: dict) -> dict | None:
        """Transform a CSV row dict into a DB column dict. Returns None to skip."""
        result = {}
        for db_col, (csv_col, parser) in self.field_map.items():
            raw = row.get(csv_col, "")
            result[db_col] = parser(raw)

        if result.get("name") is None:
            return None
        if result.get("price") is None:
            return None
        return result

CATEGORIES: dict[str, CategoryConfig] = {
    "cpu": CategoryConfig(
        key="cpu",
        csv_file="cpu_data.csv",
        model=CPU,
        field_map={
            "name":       ("Name", parse_str),
            "core_count": ("Core Count", parse_int),
            "perf_clock":  ("Performance Core Clock", parse_str),
            "boost_clock": ("Performance Core Boost Clock", parse_str),
            "microarch":   ("Microarchitecture", parse_str),
            "tdp":         ("TDP", parse_str),
            "graphics":    ("Integrated Graphics", parse_str),
            "price":       ("Price", parse_price),
        },
    ),
    "gpu": CategoryConfig(
        key="gpu",
        csv_file="gpu_data.csv",
        model=GPU,
        field_map={
            "name":       ("Name", parse_str),
            "chipset":    ("Chipset", parse_str),
            "memory":     ("Memory", parse_str),
            "core_clock": ("Core Clock", parse_str),
            "boost_clock": ("Boost Clock", parse_str),
            "color":      ("Color", parse_str),
            "length":     ("Length", parse_str),
            "price":      ("Price", parse_price),
        },
    ),
    "mobo": CategoryConfig(
        key="mobo",
        csv_file="mobo_data.csv",
        model=Mobo,
        field_map={
            "name":        ("Name", parse_str),
            "socket":      ("Socket", parse_str),
            "form_factor": ("Form Factor", parse_str),
            "memory_max":  ("Memory", parse_str),
            "memory_slot": ("Memory Slots", parse_int),
            "color":       ("Color", parse_str),
            "price":       ("Price", parse_price),
        },
    ),
    "memory": CategoryConfig(
        key="memory",
        csv_file="memory_data.csv",
        model=Memory,
        field_map={
            "name":              ("Name", parse_str),
            "speed":             ("Speed", parse_str),
            "modules":           ("Modules", parse_str),
            "color":             ("Color", parse_str),
            "first_word_latency": ("First Word Latency", parse_str),
            "cas_latency":       ("CAS Latency", parse_decimal),
            "price":             ("Price", parse_price),
        },
    ),
    "psu": CategoryConfig(
        key="psu",
        csv_file="psu_data.csv",
        model=PSU,
        field_map={
            "name":       ("Name", parse_str),
            "type":       ("Type", parse_str),
            "efficiency_rating": ("Efficiency Rating", parse_str),
            "wattage":    ("Wattage", parse_str),
            "modular":    ("Modular", parse_bool),
            "color":      ("Color", parse_str),
            "price":      ("Price", parse_price),
        },
    ),
    "case": CategoryConfig(
        key="case",
        csv_file="case_data.csv",
        model=Case,
        field_map={
            "name":         ("Name", parse_str),
            "type":         ("Type", parse_str),
            "color":        ("Color", parse_str),
            "power_supply": ("Power Supply", parse_str),
            "side_panel":   ("Side Panel", parse_str),
            "external_volume": ("External Volume", parse_str),
            "internal_bays":   ("Internal 3.5\" Bays", parse_int),
            "price":        ("Price", parse_price),
        },
    ),
    "cpu_cooler": CategoryConfig(
        key="cpu_cooler",
        csv_file="cpu_cooler_data.csv",
        model=CPUCooler,
        field_map={
            "name":          ("Name", parse_str),
            "fan_rpm":       ("Fan RPM", parse_str),
            "noise_level":   ("Noise Level", parse_str),
            "color":         ("Color", parse_str),
            "radiator_size": ("Radiator Size", parse_str),
            "price":         ("Price", parse_price),
        },
    ),
    "storage": CategoryConfig(
        key="storage",
        csv_file="storage_data.csv",
        model=Storage,
        field_map={
            "name":        ("Name", parse_str),
            "capacity":    ("Capacity", parse_str),
            "type":        ("Type", parse_str),
            "cache":       ("Cache", parse_str),
            "form_factor": ("Form Factor", parse_str),
            "interface":   ("Interface", parse_str),
            "price":       ("Price", parse_price),
        },
    ),
    "case_fans": CategoryConfig(
        key="case_fans",
        csv_file="case_fans_data.csv",
        model=CaseFan,
        field_map={
            "name":        ("Name", parse_str),
            "size":        ("Size", parse_str),
            "color":       ("Color", parse_str),
            "rpm":         ("RPM", parse_str),
            "airflow":     ("Airflow", parse_str),
            "noise_level": ("Noise Level", parse_str),
            "pwm":         ("PWM", parse_bool),
            "price":       ("Price", parse_price),
        },
    ),
}

# ---------------------------------------------------------------------------
# Seeding logic
# ---------------------------------------------------------------------------

def seed_category(engine: sa.Engine, config: CategoryConfig, dry_run: bool = False) -> int:
    """Read CSV and upsert into the corresponding table. Returns rows processed."""
    csv_path = config.csv_path()
    if not csv_path.exists():
        print(f"  [skip] {csv_path.name} not found")
        return 0

    table = config.model.__table__
    update_cols = [c for c in table.columns.keys() if c not in ("id", "name")]

    rows_processed = 0
    rows_skipped = 0

    with open(csv_path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        batch: list[dict] = []

        for raw_row in reader:
            parsed = config.parse_row(raw_row)
            if parsed is None:
                rows_skipped += 1
                continue
            batch.append(parsed)

    if not batch:
        print(f"  [skip] no valid rows in {csv_path.name}")
        return 0

    if dry_run:
        print(f"  [dry-run] would upsert {len(batch)} rows into '{table.name}'")
        for row in batch[:5]:
            print(f"    {row}")
        if len(batch) > 5:
            print(f"    ... and {len(batch) - 5} more")
        return len(batch)

    stmt = pg_insert(table)
    upsert_stmt = stmt.on_conflict_do_update(
        index_elements=["name"],
        set_={col: stmt.excluded[col] for col in update_cols},
    )

    with engine.begin() as conn:
        conn.execute(upsert_stmt, batch)

    rows_processed = len(batch)
    print(f"  [done] {rows_processed} rows upserted, {rows_skipped} skipped (no price/name)")
    return rows_processed

def main():
    parser = argparse.ArgumentParser(description="Seed catalog tables from CSV files.")
    parser.add_argument(
        "categories",
        nargs="*",
        choices=list(CATEGORIES.keys()),
        help="Categories to seed (default: all available).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview parsed rows without writing to the database.",
    )
    args = parser.parse_args()

    settings = get_settings()
    engine = sa.create_engine(settings.database_url)

    targets = args.categories or list(CATEGORIES.keys())
    total = 0

    for key in targets:
        config = CATEGORIES[key]
        print(f"Seeding {key} from {config.csv_file} ...")
        count = seed_category(engine, config, dry_run=args.dry_run)
        total += count

    print(f"\nFinished. {total} total rows processed.")


if __name__ == "__main__":
    main()