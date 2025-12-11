#!/usr/bin/env python3
"""
Query the top 10 categories for F1 by composite index
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from data_processors.snowflake_connector import query_to_dataframe
from utils.team_config_manager import TeamConfigManager
import pandas as pd

def get_top_f1_categories(top_n: int = 10):
    """Get top N categories for F1 by composite index"""
    
    # Get F1 team configuration
    config_manager = TeamConfigManager()
    team_config = config_manager.get_team_config('f1_racing_fans')
    
    view_prefix = team_config['view_prefix']
    audience_name = team_config['audience_name']
    comparison_pop = team_config['comparison_population']
    
    print(f"🔍 Querying F1 categories...")
    print(f"   View prefix: {view_prefix}")
    print(f"   Audience: {audience_name}")
    print(f"   Comparison: {comparison_pop}\n")
    
    # Query top categories by composite index
    query = f"""
    SELECT 
        TRIM(CATEGORY) as CATEGORY,
        COMPOSITE_INDEX,
        PERC_AUDIENCE,
        PERC_INDEX,
        SPC_INDEX,
        SPP_INDEX,
        PPC_INDEX
    FROM {view_prefix}_CATEGORY_INDEXING_ALL_TIME
    WHERE AUDIENCE = '{audience_name}'
    AND COMPARISON_POPULATION = '{comparison_pop}'
    ORDER BY COMPOSITE_INDEX DESC
    LIMIT {top_n}
    """
    
    df = query_to_dataframe(query)
    
    if df.empty:
        print("❌ No categories found")
        return None
    
    # Format and display results
    print(f"📊 Top {len(df)} Categories for F1 by Composite Index:\n")
    print(f"{'Rank':<6} {'Category':<35} {'Composite Index':<18} {'% Fans':<10} {'% Index':<10}")
    print("-" * 85)
    
    for idx, row in df.iterrows():
        rank = idx + 1
        category = row['CATEGORY']
        composite_idx = row['COMPOSITE_INDEX']
        perc_audience = row['PERC_AUDIENCE'] * 100 if pd.notna(row['PERC_AUDIENCE']) else 0
        perc_index = row['PERC_INDEX'] if pd.notna(row['PERC_INDEX']) else 0
        
        print(f"{rank:<6} {category:<35} {composite_idx:<18.2f} {perc_audience:<10.1f}% {perc_index:<10.1f}")
    
    print("\n" + "=" * 85)
    print("\nDetailed metrics:")
    print(df.to_string(index=False))
    
    return df

if __name__ == "__main__":
    df = get_top_f1_categories(top_n=10)
    
    if df is not None:
        print(f"\n✅ Successfully retrieved {len(df)} categories")

