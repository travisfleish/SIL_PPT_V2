#!/usr/bin/env python3
"""
Validate fan wheel community selection for a team.

Prints the selection criteria and the top 10 communities (by composite index)
with their PERC_AUDIENCE and COMPOSITE_INDEX. Saves results to CSV.
"""

import argparse
import os
import sys
import time
from pathlib import Path
from typing import Optional


def _add_repo_to_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))


def _load_dotenv_if_provided(dotenv_path: Optional[str]) -> None:
    if dotenv_path:
        try:
            from dotenv import load_dotenv
            load_dotenv(dotenv_path=dotenv_path)
        except Exception as exc:
            print(f"Warning: failed to load dotenv file: {exc}")


def resolve_min_threshold(ranker, initial_min: float, floor: float = 0.02, step: float = 0.02) -> float:
    thr = initial_min if 0.0 < float(initial_min) < 1.0 else 0.20
    thr = thr if thr < 0.99 else 0.99
    cur = thr
    while cur >= floor:
        df = ranker.get_top_communities(min_audience_pct=cur, top_n=100)
        if len(df) >= 10:
            return cur
        cur = round(cur - step, 4)
    return max(cur, floor)


def main() -> int:
    _add_repo_to_path()

    parser = argparse.ArgumentParser(description="Validate fan wheel communities for a team")
    parser.add_argument("--team", default="serie_a", help="Team key (default: serie_a)")
    parser.add_argument("--dotenv", default=None, help="Path to .env file (optional)")
    parser.add_argument("--output-dir", default=str(Path("output")), help="Base output directory")
    args = parser.parse_args()

    _load_dotenv_if_provided(args.dotenv)

    # Late imports (after sys.path update and dotenv load)
    from utils.team_config_manager import TeamConfigManager
    from data_processors.merchant_ranker import MerchantRanker
    import pandas as pd

    config = TeamConfigManager()
    team_config = config.get_team_config(args.team)

    comparison_population = team_config.get("comparison_population")
    indexing_period = team_config.get("indexing_period", "ALL_TIME").upper()

    ranker = MerchantRanker(
        team_view_prefix=team_config["view_prefix"],
        comparison_population=comparison_population,
        indexing_period=indexing_period,
    )

    initial_min = team_config.get("min_behavior_audience_pct", 0.20)
    resolved_min = resolve_min_threshold(ranker, float(initial_min))

    # Fetch the 10 communities that drive the fan wheel selection
    communities_df = ranker.get_top_communities(
        min_audience_pct=resolved_min, top_n=10, comparison_pop=comparison_population
    )

    # Prepare output directory and save CSV
    ts = time.strftime("%Y%m%d_%H%M%S")
    out_dir = Path(args.output_dir) / f"{args.team}_{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "fan_wheel_communities.csv"

    # Keep the key columns
    cols = ["COMMUNITY", "PERC_AUDIENCE", "PERC_INDEX", "COMPOSITE_INDEX"]
    save_df = communities_df[cols].copy()
    save_df.to_csv(csv_path, index=False)

    # Print criteria and a concise table
    print("\nFan Wheel Community Validation")
    print("=" * 34)
    print(f"Team: {team_config['team_name']}")
    print(f"Comparison population: {comparison_population}")
    print(f"Indexing period: {indexing_period}")
    print(f"Community view: {ranker.community_view}")
    print(f"Criteria: min_audience_pct={resolved_min:.2f}, top_n=10, approved_communities filter applied")
    print("")

    # Nicely formatted rows
    for i, row in enumerate(communities_df.itertuples(index=False), 1):
        community = getattr(row, "COMMUNITY")
        aud = float(getattr(row, "PERC_AUDIENCE", 0.0)) * 100.0
        comp = float(getattr(row, "COMPOSITE_INDEX", 0.0))
        print(f"{i:2d}. {community} — audience {aud:4.1f}% | composite {comp:6.1f}")

    print("")
    print(f"Saved CSV: {csv_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())




