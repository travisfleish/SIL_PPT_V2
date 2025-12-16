#!/usr/bin/env python3
"""
Export source data for a World Cup "fan wheel" visualization.

Logic:
- Select top N categories from WORLD_CUP_INSIGHTS.GENIUS_SPORTS_CATEGORY_INDEXING_SNAPSHOT
  ordered by COMPOSITE_INDEX (descending).
- For each of those categories, select top M merchants from
  WORLD_CUP_INSIGHTS.GENIUS_SPORTS_MERCHANT_INDEXING_SNAPSHOT ordered by PERC_INDEX (descending),
  applying a PERC_AUDIENCE >= threshold filter.

Outputs a CSV suitable to drive a fan wheel chart (category -> merchants).
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import pandas as pd

# Allow running from repo root
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from data_processors.snowflake_connector import query_to_dataframe  # noqa: E402


DEFAULT_DB_SCHEMA = "SILAB_DATA_SHARING.WORLD_CUP_INSIGHTS"
DEFAULT_AUDIENCE = "FIFA World Cup Fans"
DEFAULT_COMPARISON = "General Population"


SQL = """
WITH top_categories AS (
  SELECT
    CATEGORY,
    COMPOSITE_INDEX AS CATEGORY_COMPOSITE_INDEX,
    PERC_INDEX      AS CATEGORY_PERC_INDEX,
    PERC_AUDIENCE   AS CATEGORY_PERC_AUDIENCE,
    ROW_NUMBER() OVER (ORDER BY COMPOSITE_INDEX DESC) AS CATEGORY_RANK
  FROM {db_schema}.GENIUS_SPORTS_CATEGORY_INDEXING_SNAPSHOT
  WHERE AUDIENCE = %(audience)s
    AND COMPARISON_POPULATION = %(comparison_population)s
  QUALIFY CATEGORY_RANK <= %(top_categories)s
),
ranked_merchants AS (
  SELECT
    m.CATEGORY,
    m.MERCHANT,
    m.PARENT_MERCHANT,
    m.SUBCATEGORY,
    m.PERC_INDEX     AS MERCHANT_PERC_INDEX,
    m.PERC_AUDIENCE  AS MERCHANT_PERC_AUDIENCE,
    m.COMPOSITE_INDEX AS MERCHANT_COMPOSITE_INDEX,
    ROW_NUMBER() OVER (PARTITION BY m.CATEGORY ORDER BY m.PERC_INDEX DESC) AS MERCHANT_RANK
  FROM {db_schema}.GENIUS_SPORTS_MERCHANT_INDEXING_SNAPSHOT m
  JOIN top_categories c
    ON c.CATEGORY = m.CATEGORY
  WHERE m.AUDIENCE = %(audience)s
    AND m.COMPARISON_POPULATION = %(comparison_population)s
    AND m.PERC_AUDIENCE >= %(perc_audience_threshold)s
)
SELECT
  %(audience)s AS AUDIENCE,
  %(comparison_population)s AS COMPARISON_POPULATION,
  c.CATEGORY_RANK,
  c.CATEGORY,
  c.CATEGORY_COMPOSITE_INDEX,
  c.CATEGORY_PERC_INDEX,
  c.CATEGORY_PERC_AUDIENCE,
  r.MERCHANT_RANK,
  r.MERCHANT,
  r.PARENT_MERCHANT,
  r.SUBCATEGORY,
  r.MERCHANT_PERC_INDEX,
  r.MERCHANT_PERC_AUDIENCE,
  r.MERCHANT_COMPOSITE_INDEX
FROM top_categories c
LEFT JOIN ranked_merchants r
  ON r.CATEGORY = c.CATEGORY
 AND r.MERCHANT_RANK <= %(top_merchants)s
ORDER BY c.CATEGORY_RANK, COALESCE(r.MERCHANT_RANK, 999)
"""


def export_world_cup_fan_wheel_csv(
    output_path: Path,
    audience: str = DEFAULT_AUDIENCE,
    comparison_population: str = DEFAULT_COMPARISON,
    top_categories: int = 10,
    top_merchants: int = 10,
    perc_audience_threshold: float = 0.01,
    db_schema: str = DEFAULT_DB_SCHEMA,
) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    sql = SQL.format(db_schema=db_schema)
    params = {
        "audience": audience,
        "comparison_population": comparison_population,
        "top_categories": int(top_categories),
        "top_merchants": int(top_merchants),
        "perc_audience_threshold": float(perc_audience_threshold),
    }

    df = query_to_dataframe(sql, params=params)

    # Ensure stable dtypes for CSV consumers
    int_cols = ["CATEGORY_RANK", "MERCHANT_RANK"]
    for c in int_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").astype("Int64")

    df.to_csv(output_path, index=False)
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Export World Cup fan wheel source data to CSV")
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "output" / "world_cup_fan_wheel_source_data.csv",
        help="Output CSV path",
    )
    parser.add_argument("--audience", type=str, default=DEFAULT_AUDIENCE)
    parser.add_argument("--comparison-population", type=str, default=DEFAULT_COMPARISON)
    parser.add_argument("--top-categories", type=int, default=10)
    parser.add_argument("--top-merchants", type=int, default=10)
    parser.add_argument(
        "--perc-audience-threshold",
        type=float,
        default=0.01,
        help="Minimum PERC_AUDIENCE (fraction, e.g. 0.01 = 1%%) for merchants to be eligible",
    )
    parser.add_argument(
        "--db-schema",
        type=str,
        default=DEFAULT_DB_SCHEMA,
        help="Fully qualified db.schema containing WORLD_CUP_INSIGHTS tables",
    )

    args = parser.parse_args()

    out = export_world_cup_fan_wheel_csv(
        output_path=args.output,
        audience=args.audience,
        comparison_population=args.comparison_population,
        top_categories=args.top_categories,
        top_merchants=args.top_merchants,
        perc_audience_threshold=args.perc_audience_threshold,
        db_schema=args.db_schema,
    )

    print(f"✅ Wrote CSV: {out}")


if __name__ == "__main__":
    main()


