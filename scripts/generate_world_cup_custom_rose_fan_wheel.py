#!/usr/bin/env python3
"""
Generate a custom World Cup rose-diagram fan wheel using explicit category/merchant picks.

This script:
1) Resolves each (category_hint, merchant_hint) to canonical rows in
   WORLD_CUP_INSIGHTS.GENIUS_SPORTS_MERCHANT_INDEXING_SNAPSHOT
2) Pulls category-level metrics from GENIUS_SPORTS_CATEGORY_INDEXING_SNAPSHOT
3) Writes a CSV (the exact data used for the visualization)
4) Renders a polar-bar (rose) fan wheel PNG
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import os
from pathlib import Path
import re
import sys
from typing import Optional

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

# Make Matplotlib/fontconfig caches writable (avoids crashes on some macOS setups).
# IMPORTANT: must be set before matplotlib is imported by any module.
cache_root = REPO_ROOT / ".cache"
os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("MPLCONFIGDIR", str(cache_root / "matplotlib"))
os.environ.setdefault("XDG_CACHE_HOME", str(cache_root))
(cache_root / "matplotlib").mkdir(parents=True, exist_ok=True)
(cache_root / "fontconfig").mkdir(parents=True, exist_ok=True)

from data_processors.snowflake_connector import query_to_dataframe  # noqa: E402
from visualizations.rose_fan_wheel import RoseFanWheel  # noqa: E402


DB_SCHEMA_DEFAULT = "SILAB_DATA_SHARING.WORLD_CUP_INSIGHTS"
AUDIENCE_DEFAULT = "FIFA World Cup Fans"
COMPARISON_DEFAULT = "General Population"
PERC_AUDIENCE_THRESHOLD_DEFAULT = 0.01


@dataclass(frozen=True)
class Pick:
    category_hint: str
    merchant_hint: str


PICKS: list[Pick] = [
    Pick("Lodging & Accommodation", "Hilton"),
    Pick("Travel", "Southwest"),
    Pick("Business Services", "TurboTax"),
    Pick("Specialty Food", "TeleFlora"),
    Pick("Streaming", "Hulu"),
    Pick("Electronics", "HP"),
    Pick("Finance", "Venmo"),
    Pick("Home Goods", "Wayfair"),
    Pick("Athletic Gear", "Dicks Sporting Goods"),
    Pick("Pets", "Chewy"),
]


def _normalize_hint(s: str) -> str:
    s = (s or "").strip().upper()
    # Treat apostrophes as deletions (DICK'S -> DICKS) rather than token splits
    s = s.replace("'", "")
    s = re.sub(r"[^A-Z0-9 ]+", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s


def _score_candidate(category: str, merchant: str, category_hint: str, merchant_hint: str, perc_index: float) -> float:
    ch = _normalize_hint(category_hint)
    mh = _normalize_hint(merchant_hint)
    c = _normalize_hint(category)
    m = _normalize_hint(merchant)

    score = 0.0
    # Merchant match is the most important signal
    if mh and mh in m:
        score += 1000.0
    # Category hint secondary (because category names vary: Home Goods vs Home, Athletic Gear vs Athletic)
    if ch and (ch in c or any(tok in c for tok in ch.split() if len(tok) >= 4)):
        score += 150.0
    # Prefer higher PERC_INDEX
    if perc_index is not None:
        score += float(perc_index)
    return score


def resolve_pick(
    *,
    db_schema: str,
    audience: str,
    comparison_population: str,
    perc_audience_threshold: float,
    pick: Pick,
) -> dict:
    """
    Resolve a pick to a canonical merchant snapshot row.
    Returns a dict with canonical category/merchant + merchant metrics.
    """
    sql = f"""
    SELECT
      CATEGORY,
      MERCHANT,
      PARENT_MERCHANT,
      SUBCATEGORY,
      PERC_INDEX,
      PERC_AUDIENCE,
      COMPOSITE_INDEX
    FROM {db_schema}.GENIUS_SPORTS_MERCHANT_INDEXING_SNAPSHOT
    WHERE AUDIENCE = %(audience)s
      AND COMPARISON_POPULATION = %(comparison_population)s
      AND PERC_AUDIENCE >= %(perc_audience_threshold)s
      AND UPPER(MERCHANT) LIKE %(merchant_like)s
    ORDER BY PERC_INDEX DESC
    LIMIT 250
    """

    merchant_like = f"%{_normalize_hint(pick.merchant_hint)}%"
    df = query_to_dataframe(
        sql,
        params={
            "audience": audience,
            "comparison_population": comparison_population,
            "perc_audience_threshold": float(perc_audience_threshold),
            "merchant_like": merchant_like,
        },
    )

    if df.empty:
        # Fallback: try parent merchant match
        sql2 = f"""
        SELECT
          CATEGORY,
          MERCHANT,
          PARENT_MERCHANT,
          SUBCATEGORY,
          PERC_INDEX,
          PERC_AUDIENCE,
          COMPOSITE_INDEX
        FROM {db_schema}.GENIUS_SPORTS_MERCHANT_INDEXING_SNAPSHOT
        WHERE AUDIENCE = %(audience)s
          AND COMPARISON_POPULATION = %(comparison_population)s
          AND PERC_AUDIENCE >= %(perc_audience_threshold)s
          AND UPPER(PARENT_MERCHANT) LIKE %(merchant_like)s
        ORDER BY PERC_INDEX DESC
        LIMIT 250
        """
        df = query_to_dataframe(
            sql2,
            params={
                "audience": audience,
                "comparison_population": comparison_population,
                "perc_audience_threshold": float(perc_audience_threshold),
                "merchant_like": merchant_like,
            },
        )

    if df.empty:
        return {
            "CATEGORY": pick.category_hint,
            "MERCHANT": pick.merchant_hint,
            "PARENT_MERCHANT": None,
            "SUBCATEGORY": None,
            "MERCHANT_PERC_INDEX": None,
            "MERCHANT_PERC_AUDIENCE": None,
            "MERCHANT_COMPOSITE_INDEX": None,
            "RESOLUTION_STATUS": "not_found",
        }

    # Score candidates and choose best
    best = None
    best_score = None
    for _, row in df.iterrows():
        score = _score_candidate(
            category=str(row.get("CATEGORY", "")),
            merchant=str(row.get("MERCHANT", "")),
            category_hint=pick.category_hint,
            merchant_hint=pick.merchant_hint,
            perc_index=float(row.get("PERC_INDEX", 0) or 0),
        )
        if best is None or score > (best_score or -1):
            best = row
            best_score = score

    return {
        "CATEGORY": str(best["CATEGORY"]),
        "MERCHANT": str(best["MERCHANT"]),
        "PARENT_MERCHANT": best.get("PARENT_MERCHANT"),
        "SUBCATEGORY": best.get("SUBCATEGORY"),
        "MERCHANT_PERC_INDEX": float(best.get("PERC_INDEX")) if pd.notna(best.get("PERC_INDEX")) else None,
        "MERCHANT_PERC_AUDIENCE": float(best.get("PERC_AUDIENCE")) if pd.notna(best.get("PERC_AUDIENCE")) else None,
        "MERCHANT_COMPOSITE_INDEX": float(best.get("COMPOSITE_INDEX")) if pd.notna(best.get("COMPOSITE_INDEX")) else None,
        "RESOLUTION_STATUS": "matched",
    }


def enrich_categories(
    *,
    db_schema: str,
    audience: str,
    comparison_population: str,
    rows: list[dict],
) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    categories = sorted(df["CATEGORY"].dropna().unique().tolist())
    if not categories:
        return df

    # Snowflake connector uses pyformat (%(name)s) params; build a named IN list
    cat_param_names = [f"cat_{i}" for i in range(len(categories))]
    in_list = ", ".join([f"%({n})s" for n in cat_param_names])
    params: dict = {
        "audience": audience,
        "comparison_population": comparison_population,
    }
    for name, value in zip(cat_param_names, categories):
        params[name] = value

    cat_df = query_to_dataframe(
        f"""
        SELECT
          CATEGORY,
          COMPOSITE_INDEX AS CATEGORY_COMPOSITE_INDEX,
          PERC_INDEX AS CATEGORY_PERC_INDEX,
          PERC_AUDIENCE AS CATEGORY_PERC_AUDIENCE
        FROM {db_schema}.GENIUS_SPORTS_CATEGORY_INDEXING_SNAPSHOT
        WHERE AUDIENCE = %(audience)s
          AND COMPARISON_POPULATION = %(comparison_population)s
          AND CATEGORY IN ({in_list})
        """,
        params=params,
    )

    if cat_df.empty:
        df["CATEGORY_COMPOSITE_INDEX"] = None
        df["CATEGORY_PERC_INDEX"] = None
        df["CATEGORY_PERC_AUDIENCE"] = None
        return df

    merged = df.merge(cat_df, on="CATEGORY", how="left")
    return merged


def generate(
    *,
    output_csv: Path,
    output_png: Path,
    db_schema: str,
    audience: str,
    comparison_population: str,
    perc_audience_threshold: float,
    title: Optional[str],
) -> tuple[Path, Path]:
    resolved = [
        resolve_pick(
            db_schema=db_schema,
            audience=audience,
            comparison_population=comparison_population,
            perc_audience_threshold=perc_audience_threshold,
            pick=p,
        )
        for p in PICKS
    ]

    df = enrich_categories(
        db_schema=db_schema,
        audience=audience,
        comparison_population=comparison_population,
        rows=resolved,
    )

    # Display tweaks requested for the wheel
    df.loc[df["CATEGORY"] == "Lodging & Accommodation", "CATEGORY"] = "Hotels"
    df.loc[df["CATEGORY"] == "Home Furnishings & Goods", "CATEGORY"] = "Home Goods"
    df.loc[df["CATEGORY"] == "Specialty Food & Gifts", "CATEGORY"] = "Specialty Gifts"

    df.insert(0, "AUDIENCE", audience)
    df.insert(1, "COMPARISON_POPULATION", comparison_population)
    df["CATEGORY_ORDER"] = list(range(1, len(df) + 1))

    output_csv = Path(output_csv)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_csv, index=False)

    # Use the root `worldcup_fanpic.png` as the center image if present
    center_img = REPO_ROOT / "worldcup_fanpic.png"
    wheel = RoseFanWheel(center_image_path=center_img if center_img.exists() else None)
    wheel.create(df[["CATEGORY", "MERCHANT", "MERCHANT_PERC_INDEX"]], output_png)
    return output_csv, output_png


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate custom World Cup rose-diagram fan wheel (CSV + PNG)")
    parser.add_argument("--db-schema", type=str, default=DB_SCHEMA_DEFAULT)
    parser.add_argument("--audience", type=str, default=AUDIENCE_DEFAULT)
    parser.add_argument("--comparison-population", type=str, default=COMPARISON_DEFAULT)
    parser.add_argument("--perc-audience-threshold", type=float, default=PERC_AUDIENCE_THRESHOLD_DEFAULT)
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=REPO_ROOT / "output" / "world_cup_custom_rose_fan_wheel.csv",
    )
    parser.add_argument(
        "--output-png",
        type=Path,
        default=REPO_ROOT / "output" / "world_cup_custom_rose_fan_wheel.png",
    )

    args = parser.parse_args()
    csv_path, png_path = generate(
        output_csv=args.output_csv,
        output_png=args.output_png,
        db_schema=args.db_schema,
        audience=args.audience,
        comparison_population=args.comparison_population,
        perc_audience_threshold=args.perc_audience_threshold,
        title=None,
    )
    print(f"✅ CSV: {csv_path}")
    print(f"✅ PNG: {png_path}")


if __name__ == "__main__":
    main()


