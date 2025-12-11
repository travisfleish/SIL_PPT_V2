#!/usr/bin/env python3
"""
Export top 20 subcategories by blended index (50% SPC_INDEX + 50% PERC_INDEX)
"""

import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from data_processors.snowflake_connector import query_to_dataframe
from utils.team_config_manager import TeamConfigManager
import pandas as pd
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def export_top_subcategories(team_key: str, top_n: int = 20, output_path: Path = None):
    """
    Export top N subcategories by blended index
    
    Args:
        team_key: Team key from config (e.g., 'f1_racing_fans')
        top_n: Number of top subcategories to export (default: 20)
        output_path: Optional output path for CSV
    """
    # Get team config
    config_manager = TeamConfigManager()
    team_config = config_manager.get_team_config(team_key)
    
    view_prefix = team_config['view_prefix']
    audience_name = team_config.get('audience_name', team_config['team_name'])
    # Use "General Population" as comparison population for subcategory export
    comparison_pop = "General Population"
    
    subcategory_view = f"{view_prefix}_SUBCATEGORY_INDEXING_ALL_TIME"
    
    logger.info(f"Exporting top {top_n} subcategories for {team_config['team_name']}")
    logger.info(f"  View: {subcategory_view}")
    logger.info(f"  Audience: {audience_name}")
    logger.info(f"  Comparison: {comparison_pop}")
    logger.info(f"  Min PERC_AUDIENCE: 5% (0.05)")
    
    # Query top subcategories by blended index with minimum PERC_AUDIENCE filter
    min_perc_audience = 0.05  # 5%
    query = f"""
    SELECT 
        TRIM(CATEGORY) as CATEGORY,
        TRIM(SUBCATEGORY) as SUBCATEGORY,
        PERC_INDEX,
        SPC_INDEX,
        SPP_INDEX,
        PPC_INDEX,
        COMPOSITE_INDEX,
        (PERC_INDEX * 0.5 + SPC_INDEX * 0.5) as BLENDED_INDEX,
        PERC_AUDIENCE,
        MEDIAN_SPEND_PER_CUSTOMER,
        SPC,
        SPP,
        PPC,
        PERC_COMPARISON,
        COMPARISON_MEDIAN_SPEND_PER_CUSTOMER,
        COMPARISON_SPC,
        COMPARISON_SPP,
        COMPARISON_PPC
    FROM {subcategory_view}
    WHERE AUDIENCE = '{audience_name}'
      AND COMPARISON_POPULATION = '{comparison_pop}'
      AND SUBCATEGORY IS NOT NULL
      AND TRIM(SUBCATEGORY) != ''
      AND PERC_AUDIENCE >= {min_perc_audience}
    ORDER BY BLENDED_INDEX DESC
    LIMIT {top_n}
    """
    
    df = query_to_dataframe(query)
    
    if df.empty:
        logger.error("No subcategories found")
        return None
    
    # Sort by blended index descending
    df = df.sort_values('BLENDED_INDEX', ascending=False).reset_index(drop=True)
    
    # Add rank column
    df.insert(0, 'RANK', range(1, len(df) + 1))
    
    # Save to CSV
    if output_path is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = Path('output') / f'{team_key}_top_{top_n}_subcategories_{timestamp}.csv'
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    
    logger.info(f"\n✅ Exported {len(df)} subcategories to: {output_path}")
    logger.info(f"\nTop 5 subcategories:")
    for i, row in df.head(5).iterrows():
        logger.info(f"  {row['RANK']}. {row['SUBCATEGORY']} ({row['CATEGORY']}) - Blended: {row['BLENDED_INDEX']:.2f}")
    
    return output_path


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Export top subcategories by blended index')
    parser.add_argument('team_key', help='Team key from config (e.g., f1_racing_fans)')
    parser.add_argument('--top-n', type=int, default=20, help='Number of top subcategories (default: 20)')
    parser.add_argument('--output', type=Path, help='Output path for CSV')
    
    args = parser.parse_args()
    
    export_top_subcategories(args.team_key, args.top_n, args.output)

