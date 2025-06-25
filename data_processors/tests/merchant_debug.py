# test_merchant_deep_debug.py
"""
Deep debug script to understand the merchant data structure
"""

import sys
from pathlib import Path
import pandas as pd

# Add parent directories to path
sys.path.append(str(Path(__file__).parent.parent))
sys.path.append(str(Path(__file__).parent.parent.parent))

from data_processors.snowflake_connector import query_to_dataframe, test_connection
from utils.team_config_manager import TeamConfigManager


def deep_debug_merchant_data(team_key: str = 'utah_jazz', category: str = 'Auto'):
    """Deep dive into merchant data structure"""
    print(f"\n{'=' * 80}")
    print(f"DEEP DEBUG: {team_key} - {category}")
    print(f"{'=' * 80}")

    # Test connection
    if not test_connection():
        print("❌ Failed to connect to Snowflake")
        return

    # Get team configuration
    config_manager = TeamConfigManager()
    team_config = config_manager.get_team_config(team_key)
    view_prefix = team_config['view_prefix']
    merchant_view = f"{view_prefix}_MERCHANT_INDEXING_ALL_TIME"

    print(f"\nTeam: {team_config['team_name']}")
    print(f"View: {merchant_view}")

    # 1. Check structure of Auto category data
    print(f"\n1. Checking {category} category data structure...")
    structure_query = f"""
    SELECT 
        AUDIENCE,
        COMPARISON_POPULATION,
        COUNT(*) as record_count,
        COUNT(DISTINCT MERCHANT) as merchant_count
    FROM {merchant_view}
    WHERE CATEGORY = '{category}'
    GROUP BY AUDIENCE, COMPARISON_POPULATION
    ORDER BY record_count DESC
    LIMIT 20
    """

    try:
        structure_df = query_to_dataframe(structure_query)
        print(f"\n{category} category data structure:")
        print(structure_df.to_string(index=False))
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return

    # 2. Sample actual Auto records
    print(f"\n2. Sample {category} records...")
    sample_query = f"""
    SELECT 
        AUDIENCE,
        MERCHANT,
        CATEGORY,
        COMPARISON_POPULATION,
        PERC_AUDIENCE,
        PERC_INDEX,
        PPC,
        SPC,
        COMPOSITE_INDEX
    FROM {merchant_view}
    WHERE CATEGORY = '{category}'
    LIMIT 10
    """

    try:
        sample_df = query_to_dataframe(sample_query)
        print(f"\nSample {category} records:")
        print(sample_df.to_string(index=False))
    except Exception as e:
        print(f"❌ Error: {str(e)}")

    # 3. Check what comparison populations exist for Utah Jazz Fans
    print(f"\n3. Checking comparison populations for {team_config['team_name']} Fans...")
    comp_pop_query = f"""
    SELECT DISTINCT 
        COMPARISON_POPULATION,
        COUNT(*) as count
    FROM {merchant_view}
    WHERE AUDIENCE = '{team_config['team_name']} Fans'
    GROUP BY COMPARISON_POPULATION
    ORDER BY count DESC
    """

    try:
        comp_pop_df = query_to_dataframe(comp_pop_query)
        print(f"\nComparison populations for {team_config['team_name']} Fans:")
        print(comp_pop_df.to_string(index=False))
    except Exception as e:
        print(f"❌ Error: {str(e)}")

    # 4. Check if there's any Utah Jazz Fans + Auto combination
    print(f"\n4. Checking {team_config['team_name']} Fans + {category} combination...")
    combo_query = f"""
    SELECT 
        COUNT(*) as total_records,
        COUNT(DISTINCT MERCHANT) as unique_merchants,
        COUNT(DISTINCT COMPARISON_POPULATION) as comparison_pops
    FROM {merchant_view}
    WHERE AUDIENCE = '{team_config['team_name']} Fans'
    AND CATEGORY = '{category}'
    """

    try:
        combo_df = query_to_dataframe(combo_query)
        print(f"\n{team_config['team_name']} Fans + {category} stats:")
        print(combo_df.to_string(index=False))

        if combo_df.iloc[0]['TOTAL_RECORDS'] > 0:
            # Get sample records
            sample_combo_query = f"""
            SELECT 
                MERCHANT,
                COMPARISON_POPULATION,
                PERC_AUDIENCE,
                COMPOSITE_INDEX
            FROM {merchant_view}
            WHERE AUDIENCE = '{team_config['team_name']} Fans'
            AND CATEGORY = '{category}'
            ORDER BY PERC_AUDIENCE DESC
            LIMIT 5
            """
            sample_combo_df = query_to_dataframe(sample_combo_query)
            print("\nSample records:")
            print(sample_combo_df.to_string(index=False))
    except Exception as e:
        print(f"❌ Error: {str(e)}")

    # 5. Find which categories DO have Utah Jazz Fans data
    print(f"\n5. Finding categories with {team_config['team_name']} Fans data...")
    categories_with_data_query = f"""
    SELECT 
        CATEGORY,
        COUNT(*) as record_count,
        COUNT(DISTINCT MERCHANT) as merchant_count
    FROM {merchant_view}
    WHERE AUDIENCE = '{team_config['team_name']} Fans'
    GROUP BY CATEGORY
    ORDER BY record_count DESC
    LIMIT 10
    """

    try:
        cat_data_df = query_to_dataframe(categories_with_data_query)
        print(f"\nCategories with {team_config['team_name']} Fans data:")
        print(cat_data_df.to_string(index=False))
    except Exception as e:
        print(f"❌ Error: {str(e)}")

    # 6. Check all unique audiences in the view
    print(f"\n6. All unique audiences in the merchant view...")
    all_audiences_query = f"""
    SELECT DISTINCT 
        AUDIENCE,
        COUNT(*) as record_count,
        COUNT(DISTINCT CATEGORY) as category_count
    FROM {merchant_view}
    GROUP BY AUDIENCE
    ORDER BY record_count DESC
    """

    try:
        all_audiences_df = query_to_dataframe(all_audiences_query)
        print("\nAll audiences:")
        print(all_audiences_df.to_string(index=False))
    except Exception as e:
        print(f"❌ Error: {str(e)}")


def check_working_category(team_key: str = 'utah_jazz'):
    """Find a category that has data and test with it"""
    print(f"\n{'=' * 80}")
    print(f"FINDING WORKING CATEGORY FOR: {team_key}")
    print(f"{'=' * 80}")

    config_manager = TeamConfigManager()
    team_config = config_manager.get_team_config(team_key)
    view_prefix = team_config['view_prefix']
    merchant_view = f"{view_prefix}_MERCHANT_INDEXING_ALL_TIME"

    # Find category with most data for this team
    query = f"""
    SELECT 
        CATEGORY,
        COUNT(*) as record_count,
        COUNT(DISTINCT MERCHANT) as merchant_count,
        MIN(COMPARISON_POPULATION) as sample_comp_pop
    FROM {merchant_view}
    WHERE AUDIENCE = '{team_config['team_name']} Fans'
    AND COMPARISON_POPULATION LIKE '%Local Gen Pop%'
    GROUP BY CATEGORY
    ORDER BY record_count DESC
    LIMIT 1
    """

    try:
        result_df = query_to_dataframe(query)
        if not result_df.empty:
            category = result_df.iloc[0]['CATEGORY']
            print(f"\nBest category to test: {category}")
            print(f"Records: {result_df.iloc[0]['RECORD_COUNT']}")
            print(f"Merchants: {result_df.iloc[0]['MERCHANT_COUNT']}")
            print(f"Comparison Pop: {result_df.iloc[0]['SAMPLE_COMP_POP']}")

            # Get top 5 merchants for this category
            top_merchants_query = f"""
            SELECT 
                MERCHANT,
                PERC_AUDIENCE,
                PPC,
                SPC,
                COMPOSITE_INDEX,
                COMPARISON_POPULATION
            FROM {merchant_view}
            WHERE AUDIENCE = '{team_config['team_name']} Fans'
            AND CATEGORY = '{category}'
            AND COMPARISON_POPULATION LIKE '%Local Gen Pop%'
            ORDER BY PERC_AUDIENCE DESC
            LIMIT 5
            """

            merchants_df = query_to_dataframe(top_merchants_query)
            print(f"\nTop 5 merchants in {category}:")
            print(merchants_df.to_string(index=False))

            return category
    except Exception as e:
        print(f"❌ Error: {str(e)}")

    return None


def main():
    """Main debug function"""
    print("\n🔍 DEEP MERCHANT DATA DEBUG")
    print("=" * 80)

    # Deep debug Auto category
    deep_debug_merchant_data('utah_jazz', 'Auto')

    # Find a working category
    working_category = check_working_category('utah_jazz')

    if working_category and working_category != 'Auto':
        print(f"\n\nTesting with working category: {working_category}")
        deep_debug_merchant_data('utah_jazz', working_category)


if __name__ == "__main__":
    main()