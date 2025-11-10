#!/usr/bin/env python3
"""
Find top 10 categories for each RIPA audience based on composite index
"""

import sys
from pathlib import Path
import pandas as pd

sys.path.append(str(Path(__file__).parent))

from data_processors.snowflake_connector import set_schema, query_to_dataframe
from utils.team_config_manager import TeamConfigManager


def get_top_categories_for_audience(audience_name, comparison_pop, top_n=10):
    """Get top N categories for an audience based on composite index"""
    
    # Escape apostrophes for SQL
    audience_name_escaped = audience_name.replace("'", "''")
    comparison_pop_escaped = comparison_pop.replace("'", "''")
    
    query = f"""
    SELECT 
        CATEGORY,
        PERC_AUDIENCE,
        PERC_COMPARISON,
        COMPOSITE_INDEX
    FROM SIL_CATEGORY_INDEXING_ALL
    WHERE AUDIENCE = '{audience_name_escaped}'
      AND COMPARISON_POPULATION = '{comparison_pop_escaped}'
      AND CATEGORY IS NOT NULL
    ORDER BY COMPOSITE_INDEX DESC
    LIMIT {top_n}
    """
    
    df = query_to_dataframe(query)
    return df


def main():
    """Get top 10 categories for all RIPA audiences"""
    print("=" * 80)
    print("FINDING TOP 10 CATEGORIES FOR RIPA AUDIENCES")
    print("=" * 80)
    
    # Set schema
    set_schema('RIPA_GS')
    
    # Get RIPA audience configurations
    config_manager = TeamConfigManager()
    ripa_configs = {
        'icahn_stadium_visitors': config_manager.get_team_config('icahn_stadium_visitors'),
        'ripa_donors': config_manager.get_team_config('ripa_donors'),
        'regional_randalls_island_visitors': config_manager.get_team_config('regional_randalls_island_visitors'),
        'randall_island_visitors': config_manager.get_team_config('randall_island_visitors')
    }
    
    results = {}
    
    for team_key, config in ripa_configs.items():
        print(f"\n{'=' * 80}")
        print(f"{config['team_name']}")
        print(f"{'=' * 80}")
        
        audience_name = config['audience_name']
        comparison_pop = config['comparison_population']
        
        print(f"Audience: {audience_name}")
        print(f"Comparison: {comparison_pop}")
        print()
        
        df = get_top_categories_for_audience(audience_name, comparison_pop, top_n=10)
        
        if df.empty:
            print("❌ No data found!")
            continue
        
        print("Top 10 Categories:")
        print()
        for idx, row in df.iterrows():
            print(f"{idx+1:2d}. {row['CATEGORY']:<35s} "
                  f"Index: {row['COMPOSITE_INDEX']:>6.1f}  "
                  f"Penetration: {row['PERC_AUDIENCE']*100:>5.1f}%")
        
        # Store for command generation
        results[team_key] = df['CATEGORY'].tolist()
    
    # Generate commands
    print("\n" + "=" * 80)
    print("COMMANDS TO RUN REPORTS")
    print("=" * 80)
    
    for team_key, categories in results.items():
        cat_string = ','.join(categories)
        print(f"\n# {ripa_configs[team_key]['team_name']}")
        print(f"python3 main.py {team_key} --category-mode custom --custom-categories \"{cat_string}\"")
    
    # Also generate batch command
    print("\n" + "=" * 80)
    print("NOTE: For batch processing, each audience needs different categories.")
    print("Run them individually with the commands above.")
    print("=" * 80)


if __name__ == "__main__":
    main()

