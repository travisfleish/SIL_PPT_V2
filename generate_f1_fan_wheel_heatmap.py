#!/usr/bin/env python3
"""
Generate F1 Racing Fans fan wheel with heat map inner ring
Standalone script to test the heat map functionality
"""

import sys
from pathlib import Path
import pandas as pd
import logging
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))

from data_processors.merchant_ranker import MerchantRanker
from utils.team_config_manager import TeamConfigManager
from visualizations.fan_wheel_heatmap import FanWheelHeatmap

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_f1_heatmap_fan_wheel():
    """Generate F1 fan wheel with heat map inner ring"""
    logger.info("="*100)
    logger.info("GENERATING F1 FAN WHEEL WITH HEAT MAP")
    logger.info("="*100)
    
    # Get team config
    config_manager = TeamConfigManager()
    team_config = config_manager.get_team_config('f1_racing_fans')
    
    logger.info(f"\nTeam: {team_config['team_name']}")
    logger.info(f"View Prefix: {team_config['view_prefix']}")
    
    # Determine threshold (5% for F1)
    threshold = 0.05
    
    # Initialize MerchantRanker
    merchant_ranker = MerchantRanker(
        team_view_prefix=team_config['view_prefix'],
        comparison_population=team_config.get('comparison_population')
    )
    
    # Get fan wheel data
    logger.info(f"\n📊 Fetching fan wheel data (threshold: {threshold*100}%)...")
    wheel_data = merchant_ranker.get_fan_wheel_data(
        min_audience_pct=threshold,
        top_n_communities=10,
        comparison_pop=team_config.get('comparison_population')
    )
    
    logger.info(f"✅ Found {len(wheel_data)} communities with merchants")
    
    # Display the data
    logger.info("\n📋 Fan Wheel Data:")
    logger.info("="*100)
    for idx, row in wheel_data.iterrows():
        logger.info(f"  {row['COMMUNITY']:30s} → {row['MERCHANT']:25s} "
                   f"(Composite Index: {row.get('COMPOSITE_INDEX', row.get('PERC_INDEX', 'N/A')):.2f})")
    
    # Create heat map fan wheel
    logger.info("\n🎨 Creating fan wheel with heat map inner ring...")
    fan_wheel = FanWheelHeatmap(team_config, enable_logos=True)
    
    # Optional: customize heat map settings
    # fan_wheel.set_heatmap_colormap('hot')  # Options: 'hot', 'cool', 'viridis', 'plasma', 'inferno'
    # fan_wheel.set_heatmap_intensity_range(min_intensity=0.3, max_intensity=1.0)
    
    # Generate the visualization
    output_path = Path('output') / 'f1_fan_wheel_heatmap.png'
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    fan_wheel.create(wheel_data, output_path)
    
    logger.info("\n" + "="*100)
    logger.info("✅ SUCCESS!")
    logger.info("="*100)
    logger.info(f"📁 Fan wheel saved to: {output_path}")
    logger.info(f"\n💡 The inner ring shows a rose diagram (polar bar chart) where:")
    logger.info(f"   - Bar length represents composite index")
    logger.info(f"   - Longer bars = higher composite index")
    logger.info(f"   - Shorter bars = lower composite index")
    
    return output_path


if __name__ == "__main__":
    try:
        generate_f1_heatmap_fan_wheel()
    except Exception as e:
        logger.error(f"Error generating fan wheel: {e}", exc_info=True)
        sys.exit(1)

