#!/usr/bin/env python3
"""
Generate category-based fan wheel
Shows top categories by PERC_INDEX instead of merchants from communities
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from data_processors.category_fan_wheel_data import CategoryFanWheelData
from visualizations.category_fan_wheel import CategoryFanWheel
from utils.team_config_manager import TeamConfigManager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_category_fan_wheel(team_key: str, output_path: Path = None, top_n_categories: int = 10):
    """
    Generate category-based fan wheel
    
    Args:
        team_key: Team key from config (e.g., 'f1_racing_fans')
        output_path: Optional output path
        top_n_categories: Number of top categories to include (default: 10)
    """
    # Get team config
    config_manager = TeamConfigManager()
    team_config = config_manager.get_team_config(team_key)
    
    view_prefix = team_config['view_prefix']
    audience_name = team_config.get('audience_name', team_config['team_name'])
    comparison_pop = team_config.get('comparison_population', 'General Population')
    
    logger.info(f"Generating category fan wheel for {team_config['team_name']}")
    logger.info(f"  View prefix: {view_prefix}")
    logger.info(f"  Audience: {audience_name}")
    logger.info(f"  Comparison: {comparison_pop}")
    logger.info(f"  Top N categories: {top_n_categories}")
    
    # Get data
    data_retriever = CategoryFanWheelData(
        view_prefix=view_prefix,
        audience_name=audience_name,
        comparison_population=comparison_pop
    )
    
    wheel_data = data_retriever.get_fan_wheel_data(top_n_categories=top_n_categories)
    
    if wheel_data.empty:
        logger.error("No data available for fan wheel")
        return None
    
    logger.info(f"\nTop categories by PERC_INDEX:")
    for i, (_, row) in enumerate(wheel_data.iterrows(), 1):
        logger.info(f"   {i}. {row['CATEGORY']} (PERC_INDEX: {row['PERC_INDEX']:.1f})")
    
    # Generate fan wheel
    if output_path is None:
        output_path = Path('output') / f'{team_key}_category_fan_wheel.png'
    else:
        output_path = Path(output_path)
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    fan_wheel = CategoryFanWheel(team_config, enable_logos=False)
    result_path = fan_wheel.create(wheel_data, output_path)
    
    logger.info(f"\n✅ Category fan wheel generated: {result_path}")
    return result_path


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate category-based fan wheel')
    parser.add_argument('team_key', type=str, help='Team key from config (e.g., f1_racing_fans)')
    parser.add_argument('--output', type=Path, help='Output path for fan wheel')
    parser.add_argument('--top-n', type=int, default=10, help='Number of top categories to include (default: 10)')
    
    args = parser.parse_args()
    
    try:
        generate_category_fan_wheel(args.team_key, args.output, args.top_n)
    except Exception as e:
        logger.error(f"Error generating category fan wheel: {e}", exc_info=True)
        sys.exit(1)

