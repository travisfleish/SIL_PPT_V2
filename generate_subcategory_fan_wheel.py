#!/usr/bin/env python3
"""
Generate subcategory-based fan wheel
Shows top subcategory from each of the top 10 categories
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from data_processors.subcategory_fan_wheel_data import SubcategoryFanWheelData
from visualizations.subcategory_fan_wheel import SubcategoryFanWheel
from utils.team_config_manager import TeamConfigManager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_subcategory_fan_wheel(team_key: str, output_path: Path = None):
    """
    Generate subcategory-based fan wheel
    
    Args:
        team_key: Team key from config (e.g., 'nba_league')
        output_path: Optional output path
    """
    # Get team config
    config_manager = TeamConfigManager()
    team_config = config_manager.get_team_config(team_key)
    
    view_prefix = team_config['view_prefix']
    audience_name = team_config.get('audience_name', team_config['team_name'])
    # Use "General Population" as comparison population for subcategory fan wheel
    # (Note: "General Sports Fans" doesn't exist in the data, using "General Population" instead)
    comparison_pop = "General Population"
    
    logger.info(f"Generating subcategory fan wheel for {team_config['team_name']}")
    logger.info(f"  View prefix: {view_prefix}")
    logger.info(f"  Audience: {audience_name}")
    logger.info(f"  Comparison: {comparison_pop}")
    
    # Get data
    data_retriever = SubcategoryFanWheelData(
        view_prefix=view_prefix,
        audience_name=audience_name,
        comparison_population=comparison_pop
    )
    
    wheel_data = data_retriever.get_fan_wheel_data(top_n_categories=10)
    
    if wheel_data.empty:
        logger.error("No data available for fan wheel")
        return None
    
    logger.info(f"\nTop subcategories by category:")
    for i, (_, row) in enumerate(wheel_data.iterrows(), 1):
        logger.info(f"  {i}. {row['CATEGORY']} → {row['SUBCATEGORY']} (blended: {row['BLENDED_INDEX']:.2f})")
    
    # Generate fan wheel
    if output_path is None:
        output_path = Path('output') / f'{team_key}_subcategory_fan_wheel.png'
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    fan_wheel = SubcategoryFanWheel(team_config, enable_logos=False)
    result_path = fan_wheel.create(wheel_data, output_path)
    
    logger.info(f"\n✅ Fan wheel generated: {result_path}")
    return result_path


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate subcategory-based fan wheel')
    parser.add_argument('team_key', help='Team key from config (e.g., nba_league)')
    parser.add_argument('--output', type=Path, help='Output path for fan wheel')
    
    args = parser.parse_args()
    
    generate_subcategory_fan_wheel(args.team_key, args.output)

