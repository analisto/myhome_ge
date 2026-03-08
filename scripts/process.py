"""
Post-processing script for data/data.csv
- Deduplicates on `id` (keeps last occurrence = most recent data)
- Drops heavy JSON-blob columns: images, parameters
- Expands price columns (price_1/2/3 -> GEL/USD/EUR total & per_sqm)
- Saves clean output to data/data_clean.csv

Usage:
    python scripts/process.py
    python scripts/process.py --keep-images    # keep images column
    python scripts/process.py --keep-params    # keep parameters column
"""

import argparse
import csv
import json
import sys
from pathlib import Path

csv.field_size_limit(10_000_000)

INPUT_FILE = Path(__file__).parent.parent / "data" / "data.csv"
OUTPUT_FILE = Path(__file__).parent.parent / "data" / "data_clean.csv"

# Columns to drop by default (bloat)
DROP_COLS = {"images", "parameters"}

# price_1 = GEL, price_2 = USD, price_3 = EUR
PRICE_MAP = {
    "price_1": ("gel_total", "gel_per_sqm"),
    "price_2": ("usd_total", "usd_per_sqm"),
    "price_3": ("eur_total", "eur_per_sqm"),
}


def expand_price(raw: str) -> tuple[str, str]:
    """Parse a price JSON blob like '{"price_total":50,"price_square":1}'."""
    try:
        d = json.loads(raw)
        return str(d.get("price_total", "")), str(d.get("price_square", ""))
    except (json.JSONDecodeError, TypeError):
        return "", ""


def build_output_fieldnames(sample_row: dict, drop: set[str]) -> list[str]:
    fields = []
    for col in sample_row:
        if col in drop:
            continue
        if col in PRICE_MAP:
            total_col, sqm_col = PRICE_MAP[col]
            fields += [total_col, sqm_col]
        else:
            fields.append(col)
    return fields


def transform_row(row: dict, drop: set[str]) -> dict:
    out = {}
    for col, val in row.items():
        if col in drop:
            continue
        if col in PRICE_MAP:
            total_col, sqm_col = PRICE_MAP[col]
            out[total_col], out[sqm_col] = expand_price(val)
        else:
            out[col] = val
    return out


def process(keep_images: bool = False, keep_params: bool = False) -> None:
    drop = set(DROP_COLS)
    if keep_images:
        drop.discard("images")
    if keep_params:
        drop.discard("parameters")

    if not INPUT_FILE.exists():
        print(f"Input file not found: {INPUT_FILE}")
        sys.exit(1)

    print(f"Reading: {INPUT_FILE}")

    seen_ids: dict[str, int] = {}  # id -> line index in all_rows
    all_rows: list[dict] = []
    fieldnames: list[str] | None = None
    output_fieldnames: list[str] | None = None

    with INPUT_FILE.open(encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i % 100_000 == 0:
                print(f"  Read {i:,} rows ...", flush=True)

            row_id = row.get("id", "")

            if fieldnames is None:
                fieldnames = list(row.keys())
                output_fieldnames = build_output_fieldnames(row, drop)

            transformed = transform_row(row, drop)

            if row_id in seen_ids:
                # Overwrite with later (more recent) occurrence
                all_rows[seen_ids[row_id]] = transformed
            else:
                seen_ids[row_id] = len(all_rows)
                all_rows.append(transformed)

    total_read = i + 1
    total_unique = len(all_rows)
    duplicates_removed = total_read - total_unique

    print(f"\nRows read:           {total_read:,}")
    print(f"Duplicates removed:  {duplicates_removed:,}")
    print(f"Unique rows:         {total_unique:,}")
    print(f"Columns dropped:     {sorted(drop)}")
    print(f"Writing: {OUTPUT_FILE}")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=output_fieldnames, extrasaction="ignore")
        writer.writeheader()
        for j, row in enumerate(all_rows):
            writer.writerow(row)
            if j % 100_000 == 0 and j > 0:
                print(f"  Written {j:,} rows ...", flush=True)

    size_mb = OUTPUT_FILE.stat().st_size / 1024 / 1024
    print(f"\nDone. Output: {OUTPUT_FILE} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--keep-images", action="store_true", help="Keep images column")
    parser.add_argument("--keep-params", action="store_true", help="Keep parameters column")
    args = parser.parse_args()
    process(keep_images=args.keep_images, keep_params=args.keep_params)
