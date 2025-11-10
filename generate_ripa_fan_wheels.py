#!/usr/bin/env python3
"""
Generate fan wheel visualizations for the four RIPA audiences
Uses Snowflake data to create standalone fan wheel images
"""

import sys
from pathlib import Path
import pandas as pd
import logging

sys.path.append(str(Path(__file__).parent))

from visualizations.fan_wheel import FanWheel  # Using original production version
from data_processors.snowflake_connector import set_schema, query_to_dataframe
from utils.team_config_manager import TeamConfigManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_ripa_audience_config(team_key: str, config_manager: TeamConfigManager) -> dict:
    """Get configuration for a RIPA audience"""
    team_config = config_manager.get_team_config(team_key)
    
    return {
        'team_name': team_config['team_name'],
        'team_name_short': team_config['team_name_short'],
        'colors': team_config.get('colors', {
            'primary': '#2B6E41',      # Park Green
            'secondary': '#1A4A2A',    # Dark Green
            'accent': '#4A9E65'        # Light Green
        })
    }


def fetch_ripa_fan_wheel_data(audience_name: str, comparison_pop: str, top_n: int = 10) -> pd.DataFrame:
    """
    Fetch top categories and merchants for a RIPA audience
    
    Args:
        audience_name: Name of the RIPA audience
        comparison_pop: Comparison population name
        top_n: Number of top categories to include
        
    Returns:
        DataFrame formatted for fan wheel generation
    """
    # Escape apostrophes for SQL
    audience_escaped = audience_name.replace("'", "''")
    comparison_escaped = comparison_pop.replace("'", "''")
    
    # Query to get top categories with their top merchant
    query = f"""
    WITH RankedCategories AS (
        SELECT 
            c.CATEGORY,
            c.PERC_AUDIENCE as CATEGORY_PERC_AUDIENCE,
            c.COMPOSITE_INDEX as CATEGORY_INDEX,
            ROW_NUMBER() OVER (ORDER BY c.COMPOSITE_INDEX DESC) as cat_rank
        FROM SIL_CATEGORY_INDEXING_ALL c
        WHERE c.AUDIENCE = '{audience_escaped}'
          AND c.COMPARISON_POPULATION = '{comparison_escaped}'
          AND c.CATEGORY IS NOT NULL
    ),
    TopMerchants AS (
        SELECT 
            m.CATEGORY,
            m.MERCHANT,
            m.PERC_AUDIENCE as MERCHANT_PERC_AUDIENCE,
            m.PERC_INDEX as MERCHANT_INDEX,
            ROW_NUMBER() OVER (PARTITION BY m.CATEGORY ORDER BY m.PERC_AUDIENCE DESC) as merchant_rank
        FROM SIL_MERCHANT_INDEXING_ALL m
        WHERE m.AUDIENCE = '{audience_escaped}'
          AND m.COMPARISON_POPULATION = '{comparison_escaped}'
          AND m.CATEGORY IS NOT NULL
          AND m.MERCHANT IS NOT NULL
    )
    SELECT 
        rc.CATEGORY as COMMUNITY,
        rc.CATEGORY,
        COALESCE(tm.MERCHANT, 'Top Merchant') as MERCHANT,
        rc.CATEGORY_PERC_AUDIENCE * 100 as audience_pct,
        rc.CATEGORY_INDEX as COMMUNITY_INDEX,
        tm.MERCHANT_INDEX,
        tm.MERCHANT_PERC_AUDIENCE as PERC_AUDIENCE
    FROM RankedCategories rc
    LEFT JOIN TopMerchants tm 
        ON rc.CATEGORY = tm.CATEGORY 
        AND tm.merchant_rank = 1
    WHERE rc.cat_rank <= {top_n}
    ORDER BY rc.CATEGORY_INDEX DESC
    """
    
    df = query_to_dataframe(query)
    
    if len(df) == 0:
        logger.warning(f"No data found for {audience_name}")
        return pd.DataFrame()
    
    # Ensure we have the behavior column for the fan wheel
    if 'behavior' not in df.columns:
        df['behavior'] = df['COMMUNITY']
    
    # Handle any remaining NULL merchants
    df['MERCHANT'] = df['MERCHANT'].fillna('Top Merchant')
    
    logger.info(f"Fetched {len(df)} categories for {audience_name}")
    logger.info(f"Top 3 categories: {df['COMMUNITY'].head(3).tolist()}")
    
    return df


def generate_ripa_fan_wheels(output_dir: str = "output/ripa_fan_wheels"):
    """
    Generate fan wheels for all four RIPA audiences
    
    Args:
        output_dir: Directory to save the fan wheel images
    """
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Set Snowflake schema
    set_schema('RIPA_GS')
    
    # Get team config manager
    config_manager = TeamConfigManager()
    
    # Define the four RIPA audiences
    ripa_audiences = [
        'icahn_stadium_visitors',
        'ripa_donors',
        'regional_randalls_island_visitors',
        'randall_island_visitors'
    ]
    
    results = {}
    
    logger.info("=" * 80)
    logger.info("GENERATING RIPA FAN WHEELS")
    logger.info("=" * 80)
    
    for team_key in ripa_audiences:
        logger.info(f"\n{'=' * 80}")
        
        try:
            # Get team configuration
            team_config = config_manager.get_team_config(team_key)
            team_name = team_config['team_name']
            audience_name = team_config['audience_name']
            comparison_pop = team_config['comparison_population']
            
            logger.info(f"Generating fan wheel for: {team_name}")
            logger.info(f"Audience: {audience_name}")
            logger.info(f"Comparison: {comparison_pop}")
            logger.info(f"{'=' * 80}")
            
            # Fetch data from Snowflake
            fan_wheel_df = fetch_ripa_fan_wheel_data(audience_name, comparison_pop, top_n=10)
            
            if len(fan_wheel_df) == 0:
                logger.warning(f"Skipping {team_name} - no data")
                continue
            
            # Get configuration for colors
            config = get_ripa_audience_config(team_key, config_manager)
            
            # Create fan wheel with logo support
            fan_wheel = FanWheel(config, enable_logos=True)
            
            # Generate visualization
            output_file = output_path / f"{team_key}_fan_wheel.png"
            
            fan_wheel.create(
                wheel_data=fan_wheel_df,
                output_path=output_file
            )
            
            logger.info(f"✅ Saved {team_name} fan wheel to {output_file}")
            results[team_name] = output_file
            
            # Print preview of categories
            print(f"\n{team_name} - Top 10 Categories:")
            print("-" * 80)
            for idx, row in fan_wheel_df.iterrows():
                category = row['COMMUNITY']
                merchant = row.get('MERCHANT', 'N/A')
                index = row.get('COMMUNITY_INDEX', 0)
                pct = row.get('audience_pct', 0)
                print(f"  {idx+1:2d}. {category:35} → {merchant:30} (Index: {index:>6.1f}, {pct:>5.1f}%)")
            
        except Exception as e:
            logger.error(f"❌ Failed to generate fan wheel for {team_key}: {e}")
            import traceback
            traceback.print_exc()
    
    logger.info(f"\n{'=' * 80}")
    logger.info(f"Summary: Generated {len(results)}/{len(ripa_audiences)} RIPA fan wheels")
    logger.info(f"Output directory: {output_path.absolute()}")
    logger.info(f"{'=' * 80}")
    
    for team_name, path in results.items():
        print(f"✅ {team_name}: {path}")
    
    return results


if __name__ == "__main__":
    import sys
    
    # Get output directory from command line or use default
    output_dir = sys.argv[1] if len(sys.argv) > 1 else "output/ripa_fan_wheels"
    
    logger.info(f"Starting RIPA fan wheel generation")
    logger.info(f"Output directory: {output_dir}")
    
    results = generate_ripa_fan_wheels(output_dir)
    
    print(f"\n🎉 Complete! Generated {len(results)} RIPA fan wheels in {output_dir}")

