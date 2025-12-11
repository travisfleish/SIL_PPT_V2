#!/usr/bin/env python3
"""
Export all data used for F1 Racing Fans behaviors slide to CSV
Includes:
1. Top communities data (for community index chart)
2. Top merchants per community (for fan wheel)
"""

import sys
from pathlib import Path
import pandas as pd
import logging
import os
from datetime import datetime
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))

from data_processors.merchant_ranker import MerchantRanker
from utils.team_config_manager import TeamConfigManager

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def export_behaviors_data(team_key: str = 'f1_racing_fans'):
    """
    Export all data used for behaviors slide
    
    Args:
        team_key: Team identifier
    """
    logger.info("="*100)
    logger.info(f"EXPORTING BEHAVIORS SLIDE DATA FOR {team_key.upper()}")
    logger.info("="*100)
    
    # Get team config
    config_manager = TeamConfigManager()
    team_config = config_manager.get_team_config(team_key)
    
    logger.info(f"\nTeam: {team_config['team_name']}")
    logger.info(f"View Prefix: {team_config['view_prefix']}")
    logger.info(f"Comparison Population: {team_config['comparison_population']}")
    
    # Determine threshold (5% for F1, 20% for others)
    default_threshold = 0.20
    if team_config.get('league') == 'F1' or team_config.get('market_size') == 'small':
        default_threshold = 0.05
    
    logger.info(f"Using threshold: {default_threshold * 100}%")
    
    # Initialize MerchantRanker
    merchant_ranker = MerchantRanker(
        team_view_prefix=team_config['view_prefix'],
        comparison_population=team_config.get('comparison_population')
    )
    
    # ============================================================
    # STEP 1: Export Top Communities Data (for Community Index Chart)
    # ============================================================
    logger.info("\n" + "="*100)
    logger.info("STEP 1: EXPORTING TOP COMMUNITIES DATA")
    logger.info("="*100)
    
    communities_df = merchant_ranker.get_top_communities(
        min_audience_pct=default_threshold,
        top_n=10,
        comparison_pop=team_config.get('comparison_population')
    )
    
    if communities_df.empty:
        logger.error("No communities found!")
        return
    
    logger.info(f"Found {len(communities_df)} communities")
    
    # Add percentage columns for readability
    communities_export = communities_df.copy()
    communities_export['PERC_AUDIENCE_PCT'] = communities_export['PERC_AUDIENCE'] * 100
    communities_export['PERC_INDEX_ROUNDED'] = communities_export['PERC_INDEX'].round(2)
    communities_export['COMPOSITE_INDEX_ROUNDED'] = communities_export['COMPOSITE_INDEX'].round(2)
    
    # Reorder columns for better readability
    communities_export = communities_export[[
        'COMMUNITY',
        'PERC_AUDIENCE',
        'PERC_AUDIENCE_PCT',
        'PERC_INDEX',
        'PERC_INDEX_ROUNDED',
        'COMPOSITE_INDEX',
        'COMPOSITE_INDEX_ROUNDED'
    ]]
    
    # ============================================================
    # STEP 2: Export Top Merchants Per Community (for Fan Wheel)
    # ============================================================
    logger.info("\n" + "="*100)
    logger.info("STEP 2: EXPORTING TOP MERCHANTS PER COMMUNITY")
    logger.info("="*100)
    
    communities = communities_df['COMMUNITY'].tolist()
    logger.info(f"Fetching merchants for {len(communities)} communities...")
    
    merchants_df = merchant_ranker.get_top_merchants_for_communities(
        communities=communities,
        comparison_pop=team_config.get('comparison_population'),
        top_n_per_community=5,  # Get top 5 per community
        exclude_live_entertainment_sports=True
    )
    
    logger.info(f"Found {len(merchants_df)} merchant-community pairs")
    
    # Add percentage columns for readability
    merchants_export = merchants_df.copy()
    if 'PERC_AUDIENCE' in merchants_export.columns:
        merchants_export['PERC_AUDIENCE_PCT'] = merchants_export['PERC_AUDIENCE'] * 100
    
    # ============================================================
    # STEP 3: Export Fan Wheel Data (final selection)
    # ============================================================
    logger.info("\n" + "="*100)
    logger.info("STEP 3: EXPORTING FAN WHEEL DATA (FINAL SELECTION)")
    logger.info("="*100)
    
    fan_wheel_data = merchant_ranker.get_fan_wheel_data(
        min_audience_pct=default_threshold,
        top_n_communities=10,
        comparison_pop=team_config.get('comparison_population')
    )
    
    logger.info(f"Final fan wheel selection: {len(fan_wheel_data)} communities with unique merchants")
    
    # Add percentage columns
    fan_wheel_export = fan_wheel_data.copy()
    if 'PERC_INDEX' in fan_wheel_export.columns:
        fan_wheel_export['PERC_INDEX_ROUNDED'] = fan_wheel_export['PERC_INDEX'].round(2)
    
    # ============================================================
    # STEP 4: Save to CSV files
    # ============================================================
    logger.info("\n" + "="*100)
    logger.info("STEP 4: SAVING TO CSV FILES")
    logger.info("="*100)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path('output') / 'behaviors_exports'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save communities data
    communities_file = output_dir / f'{team_key}_communities_{timestamp}.csv'
    communities_export.to_csv(communities_file, index=False)
    logger.info(f"✅ Saved communities data: {communities_file}")
    logger.info(f"   Rows: {len(communities_export)}")
    
    # Save all merchants data
    merchants_file = output_dir / f'{team_key}_merchants_all_{timestamp}.csv'
    merchants_export.to_csv(merchants_file, index=False)
    logger.info(f"✅ Saved all merchants data: {merchants_file}")
    logger.info(f"   Rows: {len(merchants_export)}")
    
    # Save fan wheel final selection
    fan_wheel_file = output_dir / f'{team_key}_fan_wheel_final_{timestamp}.csv'
    fan_wheel_export.to_csv(fan_wheel_file, index=False)
    logger.info(f"✅ Saved fan wheel final selection: {fan_wheel_file}")
    logger.info(f"   Rows: {len(fan_wheel_export)}")
    
    # Create combined summary
    summary_file = output_dir / f'{team_key}_behaviors_summary_{timestamp}.csv'
    
    # Create a summary that shows community + selected merchant
    summary_data = []
    for _, row in fan_wheel_export.iterrows():
        summary_data.append({
            'COMMUNITY': row.get('COMMUNITY', ''),
            'SELECTED_MERCHANT': row.get('MERCHANT', ''),
            'MERCHANT_PERC_AUDIENCE': row.get('PERC_AUDIENCE', 0),
            'MERCHANT_PERC_INDEX': row.get('PERC_INDEX', 0),
            'COMMUNITY_PERC_AUDIENCE': communities_export[
                communities_export['COMMUNITY'] == row.get('COMMUNITY', '')
            ]['PERC_AUDIENCE'].values[0] if len(communities_export[
                communities_export['COMMUNITY'] == row.get('COMMUNITY', '')
            ]) > 0 else 0,
            'COMMUNITY_COMPOSITE_INDEX': communities_export[
                communities_export['COMMUNITY'] == row.get('COMMUNITY', '')
            ]['COMPOSITE_INDEX'].values[0] if len(communities_export[
                communities_export['COMMUNITY'] == row.get('COMMUNITY', '')
            ]) > 0 else 0,
            'BEHAVIOR_TEXT': row.get('behavior', ''),
        })
    
    summary_df = pd.DataFrame(summary_data)
    summary_df.to_csv(summary_file, index=False)
    logger.info(f"✅ Saved summary: {summary_file}")
    logger.info(f"   Rows: {len(summary_df)}")
    
    logger.info("\n" + "="*100)
    logger.info("EXPORT COMPLETE!")
    logger.info("="*100)
    logger.info(f"\nFiles saved to: {output_dir}")
    logger.info(f"  - Communities: {communities_file.name}")
    logger.info(f"  - All Merchants: {merchants_file.name}")
    logger.info(f"  - Fan Wheel Final: {fan_wheel_file.name}")
    logger.info(f"  - Summary: {summary_file.name}")
    
    return {
        'communities': communities_file,
        'merchants_all': merchants_file,
        'fan_wheel_final': fan_wheel_file,
        'summary': summary_file
    }


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Export behaviors slide data to CSV')
    parser.add_argument('--team', type=str, default='f1_racing_fans', help='Team key')
    
    args = parser.parse_args()
    
    export_behaviors_data(args.team)

