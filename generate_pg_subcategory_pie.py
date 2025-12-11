#!/usr/bin/env python3
"""
Generate P&G Subcategory Pie Chart
Creates a pie chart with 10 equal slices for the P&G subcategories
"""

import sys
from pathlib import Path
import pandas as pd
import logging

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from visualizations.pg_subcategory_pie import PGSubcategoryPie
from utils.team_config_manager import TeamConfigManager
from export_f1_index_data import export_f1_pg_subcategories

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def generate_pie_chart(csv_path: Path = None, output_path: Path = None):
    """
    Generate pie chart from P&G subcategories CSV
    
    Args:
        csv_path: Path to P&G subcategories CSV (if None, will generate it)
        output_path: Where to save the pie chart
    """
    # Get F1 team configuration
    config_manager = TeamConfigManager()
    team_config = config_manager.get_team_config('f1_racing_fans')
    
    # Generate CSV if not provided
    if csv_path is None or not csv_path.exists():
        logger.info("Generating P&G subcategories CSV...")
        csv_path = export_f1_pg_subcategories()
    
    # Load subcategory data
    logger.info(f"Loading subcategory data from {csv_path}")
    df = pd.read_csv(csv_path)
    
    # Verify we have 12 items (10 subcategories + 2 categories)
    if len(df) != 12:
        logger.warning(f"Expected 12 items (10 subcategories + 2 categories), found {len(df)}")
    
    # Create pie chart
    logger.info("Generating pie chart...")
    pie_chart = PGSubcategoryPie(team_config)
    
    if output_path is None:
        output_path = Path('output') / 'f1_pg_subcategory_pie.png'
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    chart_path = pie_chart.create(df, output_path)
    
    logger.info(f"✅ Pie chart saved to: {chart_path}")
    return chart_path


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate P&G subcategory pie chart')
    parser.add_argument('--csv', type=Path, help='Path to P&G subcategories CSV (will generate if not provided)')
    parser.add_argument('--output', type=Path, help='Output path for pie chart')
    
    args = parser.parse_args()
    
    generate_pie_chart(csv_path=args.csv, output_path=args.output)

