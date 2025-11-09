#!/usr/bin/env python3
"""
Test script to generate category slides for top 10 categories
WITHOUT any fixed_categories restrictions - purely data-driven
"""

import sys
from pathlib import Path
import logging
from datetime import datetime
from pptx import Presentation

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from data_processors.snowflake_connector import set_schema, query_to_dataframe
from data_processors.category_analyzer import CategoryAnalyzer
from slide_generators.category_slide import CategorySlide
from utils.team_config_manager import TeamConfigManager
from report_builder.pptx_builder import PowerPointBuilder


def get_top_categories_from_data(view_prefix: str, snowflake_schema: str, 
                                 audience_name: str, comparison_pop: str,
                                 top_n: int = 10):
    """
    Fetch the top N categories directly from Snowflake data
    WITHOUT using any fixed_categories restrictions
    
    Args:
        view_prefix: Snowflake view prefix (e.g., 'SIL')
        snowflake_schema: Snowflake schema name
        audience_name: Audience name (e.g., "Randall's Island Visitors")
        comparison_pop: Comparison population name
        top_n: Number of top categories to fetch
        
    Returns:
        List of top category names
    """
    # Set schema
    set_schema(snowflake_schema)
    
    # Query to get top categories by composite index
    # Escape single quotes in strings for SQL
    safe_audience_name = audience_name.replace("'", "''")
    safe_comparison_pop = comparison_pop.replace("'", "''")
    
    query = f"""
    SELECT 
        CATEGORY,
        COMPOSITE_INDEX,
        PERC_AUDIENCE,
        PERC_INDEX,
        SPC_INDEX,
        SPP_INDEX,
        PPC_INDEX
    FROM {view_prefix}_CATEGORY_INDEXING_ALL
    WHERE AUDIENCE = '{safe_audience_name}'
        AND COMPARISON_POPULATION = '{safe_comparison_pop}'
    ORDER BY COMPOSITE_INDEX DESC
    LIMIT {top_n}
    """
    
    logger.info(f"Fetching top {top_n} categories from Snowflake...")
    logger.info(f"Query: {query}")
    
    df = query_to_dataframe(query)
    
    if df.empty:
        logger.error("No categories found in data!")
        return []
    
    categories = df['CATEGORY'].tolist()
    logger.info(f"Found {len(categories)} top categories:")
    for i, cat in enumerate(categories, 1):
        comp_idx = df[df['CATEGORY'] == cat]['COMPOSITE_INDEX'].values[0]
        logger.info(f"  {i}. {cat} (Composite Index: {comp_idx:.0f})")
    
    return categories


def generate_top_category_slides(team_key: str, top_n: int = 10):
    """
    Generate category slides for the top N categories from actual data
    
    Args:
        team_key: Team identifier (e.g., 'randall_island_visitors')
        top_n: Number of top categories to generate slides for
    """
    print(f"\n{'='*70}")
    print(f"GENERATING TOP {top_n} CATEGORY SLIDES (NO FIXED RESTRICTIONS)")
    print(f"{'='*70}")
    
    # Get team config
    config_manager = TeamConfigManager()
    team_config = config_manager.get_team_config(team_key)
    
    print(f"\nTeam: {team_config['team_name']}")
    print(f"Schema: {team_config.get('snowflake_schema', 'default')}")
    print(f"Audience: {team_config['audience_name']}")
    print(f"Comparison: {team_config['comparison_population']}")
    
    # Set schema if specified
    if 'snowflake_schema' in team_config:
        set_schema(team_config['snowflake_schema'])
    
    # Get view prefix from team config
    view_prefix = team_config.get('view_prefix', 'V_' + team_key.upper())
    
    # Fetch top categories from data
    top_categories = get_top_categories_from_data(
        view_prefix=view_prefix,
        snowflake_schema=team_config.get('snowflake_schema', 'default'),
        audience_name=team_config['audience_name'],
        comparison_pop=team_config['comparison_population'],
        top_n=top_n
    )
    
    if not top_categories:
        print("\n❌ No categories found in data!")
        return
    
    print(f"\n✅ Found {len(top_categories)} categories to generate")
    print(f"\nGenerating slides...")
    
    # Initialize PowerPoint builder
    builder = PowerPointBuilder(team_key)
    
    # Create output directory
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_dir = Path('output') / 'top_categories' / f'{team_key}_{timestamp}'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate slides for each category
    successful_slides = []
    failed_slides = []
    
    for i, category_name in enumerate(top_categories, 1):
        print(f"\n[{i}/{len(top_categories)}] Generating slide for: {category_name}")
        
        try:
            # Generate the category slide using the internal method
            category_key = category_name.lower().replace(' ', '_').replace('&', 'and')
            builder._create_category_slide(
                category_key=category_key,
                is_custom=True  # Treat all as "custom" to avoid fixed category restrictions
            )
            successful_slides.append(category_name)
            print(f"  ✅ Success!")
            
        except Exception as e:
            logger.error(f"  ❌ Failed to generate slide for {category_name}: {e}")
            failed_slides.append((category_name, str(e)))
    
    # Save presentation
    if successful_slides:
        output_file = output_dir / f'{team_key}_top_{len(successful_slides)}_categories_{timestamp}.pptx'
        builder.presentation.save(str(output_file))
        
        print(f"\n{'='*70}")
        print(f"✅ SUCCESS!")
        print(f"{'='*70}")
        print(f"\n📁 Output file: {output_file}")
        print(f"\n📊 Summary:")
        print(f"   • Successful slides: {len(successful_slides)}")
        print(f"   • Failed slides: {len(failed_slides)}")
        
        if successful_slides:
            print(f"\n✅ Generated slides for:")
            for cat in successful_slides:
                print(f"   • {cat}")
        
        if failed_slides:
            print(f"\n❌ Failed to generate slides for:")
            for cat, error in failed_slides:
                print(f"   • {cat}: {error}")
    else:
        print(f"\n❌ No slides were generated successfully!")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate top category slides without fixed restrictions')
    parser.add_argument('team_key', help='Team identifier (e.g., randall_island_visitors)')
    parser.add_argument('--top-n', type=int, default=10, help='Number of top categories to generate (default: 10)')
    
    args = parser.parse_args()
    
    try:
        generate_top_category_slides(args.team_key, args.top_n)
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

