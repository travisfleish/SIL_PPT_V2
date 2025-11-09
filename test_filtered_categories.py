#!/usr/bin/env python3
"""
Generate category slides for RIPA data - FILTERED version
Only selects categories that have matching subcategory/merchant data
"""

import sys
from pathlib import Path
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

sys.path.append(str(Path(__file__).parent))

from data_processors.snowflake_connector import set_schema, query_to_dataframe
from report_builder.pptx_builder import PowerPointBuilder
from utils.team_config_manager import TeamConfigManager


# The 33 categories that have subcategory data
VALID_CATEGORIES = [
    'Accessories', 'Apparel', 'Athleisure', 'Athletic', 'Attractions', 'Auto', 'Baby',
    'Beauty', 'Business Services', 'Collectibles', 'Dating', 'Education Resources',
    'Electronics', 'Entertainment & News', 'Finance', 'Fitness', 'Footwear', 'Gambling',
    'Gaming', 'Health', 'Home', 'Home Furnishings & Goods', 'Lodging & Accommodation',
    'Pets', 'Resale', 'Restaurants', 'Retailers', 'Specialty Food & Gifts',
    'Specialty Retailers', 'Sportstainment', 'Streaming', 'Telcom', 'Travel'
]


def get_top_categories_with_data(team_key: str, top_n: int = 10):
    """
    Get top N categories from the high-level table,
    but ONLY those that have matching subcategory/merchant data
    """
    config_manager = TeamConfigManager()
    team_config = config_manager.get_team_config(team_key)
    
    # Set schema
    if 'snowflake_schema' in team_config:
        set_schema(team_config['snowflake_schema'])
    
    view_prefix = team_config.get('view_prefix', 'V_' + team_key.upper())
    audience_name = team_config['audience_name']
    comparison_pop = team_config['comparison_population']
    
    # Escape single quotes
    safe_audience = audience_name.replace("'", "''")
    safe_comparison = comparison_pop.replace("'", "''")
    
    # Build WHERE clause to filter by valid categories
    valid_cats_sql = "', '".join(VALID_CATEGORIES)
    
    query = f"""
    SELECT 
        CATEGORY,
        COMPOSITE_INDEX,
        PERC_AUDIENCE
    FROM {view_prefix}_CATEGORY_INDEXING_ALL
    WHERE AUDIENCE = '{safe_audience}'
        AND COMPARISON_POPULATION = '{safe_comparison}'
        AND CATEGORY IN ('{valid_cats_sql}')
    ORDER BY COMPOSITE_INDEX DESC
    LIMIT {top_n}
    """
    
    logger.info(f"Fetching top {top_n} categories (filtered to 33 valid ones)...")
    df = query_to_dataframe(query)
    
    if df.empty:
        logger.error("No categories found!")
        return []
    
    categories = df['CATEGORY'].tolist()
    logger.info(f"Found {len(categories)} categories with data:")
    for i, cat in enumerate(categories, 1):
        comp_idx = df[df['CATEGORY'] == cat]['COMPOSITE_INDEX'].values[0]
        logger.info(f"  {i}. {cat} (Composite Index: {comp_idx:.0f})")
    
    return categories


def generate_filtered_category_slides(team_key: str, top_n: int = 10):
    """
    Generate category slides for the top N categories that have actual data
    """
    print(f"\n{'='*70}")
    print(f"GENERATING CATEGORY SLIDES (FILTERED TO VALID CATEGORIES)")
    print(f"{'='*70}")
    
    # Get team config
    config_manager = TeamConfigManager()
    team_config = config_manager.get_team_config(team_key)
    
    print(f"\nTeam: {team_config['team_name']}")
    print(f"Schema: {team_config.get('snowflake_schema', 'default')}")
    print(f"Audience: {team_config['audience_name']}")
    print(f"Filtering to {len(VALID_CATEGORIES)} valid categories")
    
    # Get top categories with data
    top_categories = get_top_categories_with_data(team_key, top_n)
    
    if not top_categories:
        print("\n❌ No valid categories found!")
        return
    
    print(f"\n✅ Found {len(top_categories)} categories to generate")
    print(f"\nGenerating slides...")
    
    # Initialize PowerPoint builder
    builder = PowerPointBuilder(team_key)
    
    # Create output directory
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_dir = Path('output') / 'filtered_categories' / f'{team_key}_{timestamp}'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate slides for each category
    successful_slides = []
    failed_slides = []
    
    for i, category_name in enumerate(top_categories, 1):
        print(f"\n[{i}/{len(top_categories)}] Generating slide for: {category_name}")
        
        try:
            # Generate the category slide using the internal method
            # IMPORTANT: Pass the original properly-cased category name for RIPA data
            # The PowerPointBuilder will use this exact name in SQL queries
            builder._create_category_slide(
                category_key=category_name,  # Keep original case!
                is_custom=True  # Treat as custom to avoid fixed category restrictions
            )
            successful_slides.append(category_name)
            print(f"  ✅ Success!")
            
        except Exception as e:
            logger.error(f"  ❌ Failed to generate slide for {category_name}: {e}")
            import traceback
            traceback.print_exc()
            failed_slides.append((category_name, str(e)))
    
    # Save presentation
    if successful_slides:
        output_file = output_dir / f'{team_key}_filtered_{len(successful_slides)}_categories_{timestamp}.pptx'
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
    
    parser = argparse.ArgumentParser(description='Generate category slides (filtered to valid categories)')
    parser.add_argument('team_key', help='Team identifier (e.g., randall_island_visitors)')
    parser.add_argument('--top-n', type=int, default=10, help='Number of top categories (default: 10)')
    
    args = parser.parse_args()
    
    try:
        generate_filtered_category_slides(args.team_key, args.top_n)
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

