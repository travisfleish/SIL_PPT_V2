#!/usr/bin/env python3
"""
List top 10 communities by composite index for a team.

Uses the project's root .env (if present), respects approved communities,
and prints/saves COMMUNITY, PERC_AUDIENCE, PERC_INDEX, COMPOSITE_INDEX.
"""

import argparse
import os
import sys
import time
from pathlib import Path


def _add_repo_to_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))


def main() -> int:
    # Ensure imports work when running from anywhere
    _add_repo_to_path()

    # Load root .env if available
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except Exception:
        pass

    parser = argparse.ArgumentParser(description="Top 10 communities by composite index")
    parser.add_argument("--team", default="serie_a", help="Team key (default: serie_a)")
    parser.add_argument("--min-audience", type=float, default=None,
                        help="Minimum audience pct (0-1). Default: team config or 0.0")
    parser.add_argument("--output-dir", default=str(Path("output")), help="Base output directory")
    args = parser.parse_args()

    # Late imports after sys.path update and dotenv load
    from utils.team_config_manager import TeamConfigManager
    from data_processors.merchant_ranker import MerchantRanker

    cfg = TeamConfigManager().get_team_config(args.team)

    min_aud = args.min_audience
    if min_aud is None:
        # Prefer team override; else allow all (0.0) to truly get top 10 by composite
        fallback = 0.0
        try:
            team_min = cfg.get("min_behavior_audience_pct")
            min_aud = float(team_min) if team_min is not None else fallback
        except Exception:
            min_aud = fallback

    comp_pop = cfg.get("comparison_population")
    ranker = MerchantRanker(
        team_view_prefix=cfg["view_prefix"],
        comparison_population=comp_pop,
        indexing_period=cfg.get("indexing_period", "ALL_TIME"),
    )

    df = ranker.get_top_communities(min_audience_pct=min_aud, top_n=10, comparison_pop=comp_pop)

    ts = time.strftime("%Y%m%d_%H%M%S")
    outdir = Path(args.output_dir) / f"{args.team}_{ts}"
    outdir.mkdir(parents=True, exist_ok=True)
    csv_path = outdir / "top_communities.csv"

    cols = ["COMMUNITY", "PERC_AUDIENCE", "PERC_INDEX", "COMPOSITE_INDEX"]
    df[cols].to_csv(csv_path, index=False)

    # Console output
    print("\nTop 10 Communities by Composite Index")
    print("=" * 36)
    print(f"Team: {cfg['team_name']}")
    print(f"Comparison population: {comp_pop}")
    print(f"Indexing period: {cfg.get('indexing_period', 'ALL_TIME').upper()}")
    print(f"Community view: {ranker.community_view}")
    print(f"Filter: min_audience_pct >= {min_aud:.2f}")
    print("")

    for i, row in enumerate(df.itertuples(index=False), 1):
        community = getattr(row, "COMMUNITY")
        aud = float(getattr(row, "PERC_AUDIENCE", 0.0)) * 100.0
        comp_idx = float(getattr(row, "COMPOSITE_INDEX", 0.0))
        print(f"{i:2d}. {community} — audience {aud:4.1f}% | composite {comp_idx:6.1f}")

    print("")
    print(f"Saved CSV: {csv_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())




