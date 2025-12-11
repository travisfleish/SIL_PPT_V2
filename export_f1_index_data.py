#!/usr/bin/env python3
"""
Export F1 category and subcategory index data to CSV files.

Generates two CSV files:
1. Top 15 categories by PERC_INDEX (with PERC_AUDIENCE >= 5%)
2. Top 15 subcategories by PERC_INDEX (with PERC_AUDIENCE >= 5%)

Categories CSV contains: CATEGORY, PERC_AUDIENCE, PERC_INDEX, SPC_INDEX, COMPOSITE_INDEX
Subcategories CSV contains: CATEGORY, SUBCATEGORY, PERC_AUDIENCE, PERC_INDEX, SPC_INDEX, COMPOSITE_INDEX
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

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def export_f1_category_index_data(top_n: int = 15, min_perc_audience: float = 0.05, output_path: Path = None):
    """
    Export top N categories by PERC_INDEX with PERC_AUDIENCE threshold
    
    Args:
        top_n: Number of top categories to export (default: 15)
        min_perc_audience: Minimum PERC_AUDIENCE threshold (default: 0.05 = 5%)
        output_path: Optional output path for CSV
    """
    # Get F1 team configuration
    config_manager = TeamConfigManager()
    team_config = config_manager.get_team_config('f1_racing_fans')
    
    view_prefix = team_config['view_prefix']
    audience_name = team_config['audience_name']
    comparison_pop = team_config['comparison_population']
    
    category_view = f"{view_prefix}_CATEGORY_INDEXING_ALL_TIME"
    
    logger.info(f"Exporting top {top_n} F1 categories by PERC_INDEX")
    logger.info(f"  View: {category_view}")
    logger.info(f"  Audience: {audience_name}")
    logger.info(f"  Comparison: {comparison_pop}")
    logger.info(f"  Min PERC_AUDIENCE: {min_perc_audience * 100}%")
    
    # Query top categories by PERC_INDEX with PERC_AUDIENCE filter
    query = f"""
    SELECT 
        TRIM(CATEGORY) as CATEGORY,
        PERC_AUDIENCE,
        PERC_INDEX,
        SPC_INDEX,
        COMPOSITE_INDEX
    FROM {category_view}
    WHERE AUDIENCE = '{audience_name}'
      AND COMPARISON_POPULATION = '{comparison_pop}'
      AND PERC_AUDIENCE >= {min_perc_audience}
      AND CATEGORY IS NOT NULL
      AND TRIM(CATEGORY) != ''
    ORDER BY PERC_INDEX DESC
    LIMIT {top_n}
    """
    
    df = query_to_dataframe(query)
    
    if df.empty:
        logger.error("No categories found")
        return None
    
    # Ensure we have the columns in the correct order
    df = df[['CATEGORY', 'PERC_AUDIENCE', 'PERC_INDEX', 'SPC_INDEX', 'COMPOSITE_INDEX']].copy()
    
    # Save to CSV
    if output_path is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = Path('output') / f'f1_top_{top_n}_categories_by_perc_index_{timestamp}.csv'
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    
    logger.info(f"\n✅ Exported {len(df)} categories to: {output_path}")
    logger.info(f"\nTop 5 categories:")
    for i, row in df.head(5).iterrows():
        logger.info(f"  {i+1}. {row['CATEGORY']} - PERC_INDEX: {row['PERC_INDEX']:.2f}, SPC_INDEX: {row['SPC_INDEX']:.2f}, PERC_AUDIENCE: {row['PERC_AUDIENCE']*100:.2f}%, COMPOSITE_INDEX: {row['COMPOSITE_INDEX']:.2f}")
    
    return output_path


def export_f1_pg_subcategories(output_path: Path = None):
    """
    Export 10 specific subcategories + 2 categories for P&G report with custom name mappings
    Total: 12 items (10 subcategories + 2 categories: Fitness, Colleges & Universities)
    
    Args:
        output_path: Optional output path for CSV
    """
    # Get F1 team configuration
    config_manager = TeamConfigManager()
    team_config = config_manager.get_team_config('f1_racing_fans')
    
    view_prefix = team_config['view_prefix']
    audience_name = team_config['audience_name']
    comparison_pop = team_config['comparison_population']
    
    subcategory_view = f"{view_prefix}_SUBCATEGORY_INDEXING_ALL_TIME"
    category_view = f"{view_prefix}_CATEGORY_INDEXING_ALL_TIME"
    
    # Define the 10 subcategories to export with their name mappings
    subcategory_mappings = {
        "Business Services - Artificial Intelligence (AI)": "AI Users",
        "Streaming - Specialty OTT - Anime": "Anime Fans",
        "Sportstainment - Ski & Ski Resorts": "Skiers",
        "Entertainment & News - Influencer Economy": "Influencer Economy",
        "Transit - Micromobility": "Scooter Users",
        "Apparel - Professional": "Professional Apparel",
        "Education Resources - Adults": "Adult Learning",
        "Live Entertainment - Concerts": "Concert Goers",
        "Entertainment & News - News Publications": "News Consumers",
        "Beauty - Cosmetics & Skincare": "Skincare"
    }
    
    # Define the 2 categories to include
    categories_to_include = ["Fitness", "Colleges & Universities"]
    
    logger.info(f"Exporting 10 P&G-specific F1 subcategories + 2 categories with name mappings")
    logger.info(f"  Subcategory View: {subcategory_view}")
    logger.info(f"  Category View: {category_view}")
    logger.info(f"  Audience: {audience_name}")
    logger.info(f"  Comparison: {comparison_pop}")
    
    # Build WHERE clause for the specific subcategories
    subcategory_conditions = " OR ".join([f"TRIM(SUBCATEGORY) = '{subcat}'" for subcat in subcategory_mappings.keys()])
    
    # Query the specific subcategories
    subcategory_query = f"""
    SELECT 
        TRIM(CATEGORY) as CATEGORY,
        TRIM(SUBCATEGORY) as SUBCATEGORY,
        PERC_AUDIENCE,
        PERC_INDEX,
        PPC_INDEX
    FROM {subcategory_view}
    WHERE AUDIENCE = '{audience_name}'
      AND COMPARISON_POPULATION = '{comparison_pop}'
      AND ({subcategory_conditions})
      AND SUBCATEGORY IS NOT NULL
    """
    
    df_subcategories = query_to_dataframe(subcategory_query)
    
    if df_subcategories.empty:
        logger.error("No subcategories found")
        return None
    
    # Apply name mappings to subcategories
    df_subcategories['SUBCATEGORY'] = df_subcategories['SUBCATEGORY'].map(subcategory_mappings).fillna(df_subcategories['SUBCATEGORY'])
    
    # Query the 2 categories
    category_conditions = " OR ".join([f"TRIM(CATEGORY) = '{cat}'" for cat in categories_to_include])
    category_query = f"""
    SELECT 
        TRIM(CATEGORY) as CATEGORY,
        PERC_AUDIENCE,
        PERC_INDEX,
        PPC_INDEX
    FROM {category_view}
    WHERE AUDIENCE = '{audience_name}'
      AND COMPARISON_POPULATION = '{comparison_pop}'
      AND ({category_conditions})
      AND CATEGORY IS NOT NULL
    """
    
    df_categories = query_to_dataframe(category_query)
    
    if df_categories.empty:
        logger.warning("No categories found")
    else:
        # For categories, use the category name as the "SUBCATEGORY" field for consistency
        df_categories['SUBCATEGORY'] = df_categories['CATEGORY']
    
    # Combine subcategories and categories
    if not df_categories.empty:
        # Ensure both have the same columns
        df_combined = pd.concat([df_subcategories, df_categories], ignore_index=True)
    else:
        df_combined = df_subcategories.copy()
    
    # Calculate HYBRID_INDEX as average of PERC_INDEX and PPC_INDEX
    df_combined['HYBRID_INDEX'] = (df_combined['PERC_INDEX'] + df_combined['PPC_INDEX']) / 2.0
    
    # Ensure we have the columns in the correct order
    df_combined = df_combined[['CATEGORY', 'SUBCATEGORY', 'PERC_AUDIENCE', 'PERC_INDEX', 'PPC_INDEX', 'HYBRID_INDEX']].copy()
    
    # Sort by HYBRID_INDEX descending (to match pie chart sorting)
    df_combined = df_combined.sort_values('HYBRID_INDEX', ascending=False).reset_index(drop=True)
    
    # Save to CSV
    if output_path is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = Path('output') / f'f1_pg_subcategories_{timestamp}.csv'
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df_combined.to_csv(output_path, index=False)
    
    logger.info(f"\n✅ Exported {len(df_combined)} items (10 subcategories + {len(df_categories)} categories) to: {output_path}")
    logger.info(f"\nItems with mappings:")
    for i, row in df_combined.iterrows():
        logger.info(f"  {i+1}. {row['SUBCATEGORY']} ({row['CATEGORY']}) - PERC_INDEX: {row['PERC_INDEX']:.2f}, PPC_INDEX: {row['PPC_INDEX']:.2f}, PERC_AUDIENCE: {row['PERC_AUDIENCE']*100:.2f}%, HYBRID_INDEX: {row['HYBRID_INDEX']:.2f}")
    
    return output_path


def export_f1_subcategory_index_data(top_n: int = 15, min_perc_audience: float = 0.05, output_path: Path = None):
    """
    Export top N subcategories by PERC_INDEX with PERC_AUDIENCE threshold
    
    Args:
        top_n: Number of top subcategories to export (default: 15)
        min_perc_audience: Minimum PERC_AUDIENCE threshold (default: 0.05 = 5%)
        output_path: Optional output path for CSV
    """
    # Get F1 team configuration
    config_manager = TeamConfigManager()
    team_config = config_manager.get_team_config('f1_racing_fans')
    
    view_prefix = team_config['view_prefix']
    audience_name = team_config['audience_name']
    comparison_pop = team_config['comparison_population']
    
    subcategory_view = f"{view_prefix}_SUBCATEGORY_INDEXING_ALL_TIME"
    
    logger.info(f"Exporting top {top_n} F1 subcategories by PERC_INDEX")
    logger.info(f"  View: {subcategory_view}")
    logger.info(f"  Audience: {audience_name}")
    logger.info(f"  Comparison: {comparison_pop}")
    logger.info(f"  Min PERC_AUDIENCE: {min_perc_audience * 100}%")
    
    # Query top subcategories by PERC_INDEX with PERC_AUDIENCE filter
    query = f"""
    SELECT 
        TRIM(CATEGORY) as CATEGORY,
        TRIM(SUBCATEGORY) as SUBCATEGORY,
        PERC_AUDIENCE,
        PERC_INDEX,
        SPC_INDEX,
        COMPOSITE_INDEX
    FROM {subcategory_view}
    WHERE AUDIENCE = '{audience_name}'
      AND COMPARISON_POPULATION = '{comparison_pop}'
      AND PERC_AUDIENCE >= {min_perc_audience}
      AND SUBCATEGORY IS NOT NULL
      AND TRIM(SUBCATEGORY) != ''
    ORDER BY PERC_INDEX DESC
    LIMIT {top_n}
    """
    
    df = query_to_dataframe(query)
    
    if df.empty:
        logger.error("No subcategories found")
        return None
    
    # Ensure we have the columns in the correct order
    df = df[['CATEGORY', 'SUBCATEGORY', 'PERC_AUDIENCE', 'PERC_INDEX', 'SPC_INDEX', 'COMPOSITE_INDEX']].copy()
    
    # Save to CSV
    if output_path is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = Path('output') / f'f1_top_{top_n}_subcategories_by_perc_index_{timestamp}.csv'
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    
    logger.info(f"\n✅ Exported {len(df)} subcategories to: {output_path}")
    logger.info(f"\nTop 5 subcategories:")
    for i, row in df.head(5).iterrows():
        logger.info(f"  {i+1}. {row['SUBCATEGORY']} ({row['CATEGORY']}) - PERC_INDEX: {row['PERC_INDEX']:.2f}, SPC_INDEX: {row['SPC_INDEX']:.2f}, PERC_AUDIENCE: {row['PERC_AUDIENCE']*100:.2f}%, COMPOSITE_INDEX: {row['COMPOSITE_INDEX']:.2f}")
    
    return output_path


def main():
    """Generate both CSV files"""
    logger.info("=" * 80)
    logger.info("F1 Index Data Export")
    logger.info("=" * 80)
    
    # Export categories
    logger.info("\n" + "-" * 80)
    logger.info("Exporting Category Index Data")
    logger.info("-" * 80)
    category_path = export_f1_category_index_data(top_n=15, min_perc_audience=0.05)
    
    # Export subcategories
    logger.info("\n" + "-" * 80)
    logger.info("Exporting Subcategory Index Data")
    logger.info("-" * 80)
    subcategory_path = export_f1_subcategory_index_data(top_n=15, min_perc_audience=0.05)
    
    # Export P&G-specific subcategories with name mappings
    logger.info("\n" + "-" * 80)
    logger.info("Exporting P&G-Specific Subcategories with Name Mappings")
    logger.info("-" * 80)
    pg_subcategory_path = export_f1_pg_subcategories()
    
    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("Export Summary")
    logger.info("=" * 80)
    if category_path:
        logger.info(f"✅ Categories CSV: {category_path}")
    else:
        logger.error("❌ Failed to export categories")
    
    if subcategory_path:
        logger.info(f"✅ Subcategories CSV: {subcategory_path}")
    else:
        logger.error("❌ Failed to export subcategories")
    
    if pg_subcategory_path:
        logger.info(f"✅ P&G Subcategories CSV: {pg_subcategory_path}")
    else:
        logger.error("❌ Failed to export P&G subcategories")
    
    logger.info("=" * 80)


if __name__ == "__main__":
    main()

