#!/usr/bin/env python3
"""
Compare top 10 categories across all RIPA audiences
Generates a CSV showing side-by-side comparison
"""

import sys
from pathlib import Path
import pandas as pd
from datetime import datetime

sys.path.append(str(Path(__file__).parent))

from data_processors.snowflake_connector import set_schema, query_to_dataframe
from utils.team_config_manager import TeamConfigManager


# The 33 categories that have subcategory data (from user's list)
VALID_CATEGORIES = [
    'Accessories', 'Apparel', 'Athleisure', 'Athletic', 'Attractions', 'Auto', 'Baby',
    'Beauty', 'Business Services', 'Collectibles', 'Dating', 'Education Resources',
    'Electronics', 'Entertainment & News', 'Finance', 'Fitness', 'Footwear', 'Gambling',
    'Gaming', 'Health', 'Home', 'Home Furnishings & Goods', 'Lodging & Accommodation',
    'Pets', 'Resale', 'Restaurants', 'Retailers', 'Specialty Food & Gifts',
    'Specialty Retailers', 'Sportstainment', 'Streaming', 'Telcom', 'Travel'
]


def get_ripa_audiences():
    """Get all RIPA audience configurations"""
    config_manager = TeamConfigManager()
    all_teams = config_manager.list_teams()
    
    ripa_audiences = {}
    for team_key in all_teams:
        config = config_manager.get_team_config(team_key)
        if config.get('snowflake_schema') == 'RIPA_GS':
            ripa_audiences[team_key] = {
                'name': config['team_name'],
                'audience_name': config['audience_name'],
                'comparison_pop': config['comparison_population']
            }
    
    return ripa_audiences


def get_top_categories_for_audience(audience_name, comparison_pop, top_n=10):
    """
    Get top N categories for a specific audience
    Returns DataFrame with category, composite_index, perc_audience, rank
    """
    # Escape single quotes
    safe_audience = audience_name.replace("'", "''")
    safe_comparison = comparison_pop.replace("'", "''")
    
    # Build WHERE clause to filter by valid categories
    valid_cats_sql = "', '".join(VALID_CATEGORIES)
    
    query = f"""
    SELECT 
        CATEGORY,
        COMPOSITE_INDEX,
        PERC_AUDIENCE,
        PERC_INDEX,
        SPC_INDEX,
        SPP_INDEX,
        PPC_INDEX
    FROM SIL_CATEGORY_INDEXING_ALL
    WHERE AUDIENCE = '{safe_audience}'
        AND COMPARISON_POPULATION = '{safe_comparison}'
        AND CATEGORY IN ('{valid_cats_sql}')
    ORDER BY COMPOSITE_INDEX DESC
    LIMIT {top_n}
    """
    
    df = query_to_dataframe(query)
    
    if not df.empty:
        # Add rank column
        df['RANK'] = range(1, len(df) + 1)
    
    return df


def create_comparison_csv():
    """Create CSV comparing top 10 categories across all RIPA audiences"""
    print("=" * 80)
    print("RIPA AUDIENCES CATEGORY COMPARISON")
    print("=" * 80)
    
    # Set schema
    set_schema('RIPA_GS')
    
    # Get all RIPA audiences
    ripa_audiences = get_ripa_audiences()
    
    print(f"\nFound {len(ripa_audiences)} RIPA audiences:")
    for team_key, info in ripa_audiences.items():
        print(f"  • {info['name']}: {info['audience_name']}")
    
    # Collect data for each audience
    all_data = {}
    
    for team_key, info in ripa_audiences.items():
        print(f"\nFetching top 10 categories for {info['name']}...")
        df = get_top_categories_for_audience(
            info['audience_name'],
            info['comparison_pop'],
            top_n=10
        )
        
        if df.empty:
            print(f"  ⚠️  No data found")
            continue
        
        print(f"  ✓ Found {len(df)} categories")
        all_data[team_key] = {
            'info': info,
            'data': df
        }
    
    if not all_data:
        print("\n❌ No data found for any audience!")
        return
    
    # Create comparison DataFrame
    print("\n" + "=" * 80)
    print("CREATING COMPARISON CSV")
    print("=" * 80)
    
    # Build side-by-side comparison with each audience's top 10
    comparison_data = {'Rank': list(range(1, 11))}
    
    for team_key, data in all_data.items():
        audience_name = data['info']['name']
        df = data['data'].sort_values('RANK')
        
        # Create columns for this audience
        categories = []
        composite_indices = []
        perc_fans = []
        
        for rank in range(1, 11):
            row = df[df['RANK'] == rank]
            if not row.empty:
                categories.append(row['CATEGORY'].values[0])
                composite_indices.append(int(row['COMPOSITE_INDEX'].values[0]))
                perc_fans.append(f"{float(row['PERC_AUDIENCE'].values[0]) * 100:.1f}%")
            else:
                categories.append(None)
                composite_indices.append(None)
                perc_fans.append(None)
        
        comparison_data[f'{audience_name} - Category'] = categories
        comparison_data[f'{audience_name} - Index'] = composite_indices
        comparison_data[f'{audience_name} - % Fans'] = perc_fans
    
    # Create DataFrame
    comparison_df = pd.DataFrame(comparison_data)
    
    # Save to CSV
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_dir = Path('output') / 'comparisons'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / f'ripa_audiences_comparison_{timestamp}.csv'
    comparison_df.to_csv(output_file, index=False)
    
    print(f"\n✅ SUCCESS!")
    print(f"📁 Output file: {output_file}")
    
    # Print preview
    print(f"\n📊 Preview (first 10 rows):")
    print(comparison_df.head(10).to_string())
    
    # Print summary statistics
    print(f"\n📈 Summary:")
    print(f"   • Audiences compared: {len(all_data)}")
    print(f"   • Categories per audience: 10")
    
    # Get all unique categories
    all_categories = set()
    for team_key, data in all_data.items():
        all_categories.update(data['data']['CATEGORY'].tolist())
    
    print(f"   • Total unique categories: {len(all_categories)}")
    
    # Find categories that appear in all audiences' top 10
    categories_in_all = []
    for category in all_categories:
        in_all = True
        for team_key, data in all_data.items():
            if category not in data['data']['CATEGORY'].values:
                in_all = False
                break
        if in_all:
            categories_in_all.append(category)
    
    if categories_in_all:
        print(f"\n🎯 Categories in ALL audiences' top 10:")
        for cat in categories_in_all:
            print(f"   • {cat}")
    
    # Find categories unique to specific audiences
    print(f"\n🔍 Unique category insights:")
    for team_key, data in all_data.items():
        audience_name = data['info']['name']
        df = data['data']
        
        # Find categories unique to this audience
        unique_to_this = []
        for cat in df['CATEGORY'].values:
            count = sum(1 for other_key, other_data in all_data.items() 
                       if cat in other_data['data']['CATEGORY'].values)
            if count == 1:
                unique_to_this.append(cat)
        
        if unique_to_this:
            print(f"   • {audience_name}: {', '.join(unique_to_this)}")
    
    return output_file


if __name__ == "__main__":
    try:
        create_comparison_csv()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

