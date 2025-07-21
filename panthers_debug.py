#!/usr/bin/env python3
"""
Diagnostic script to debug Carolina Panthers data availability issues.
This will help identify the correct audience names and available data.
"""

import pandas as pd
import yaml
from pathlib import Path
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_processors.snowflake_connector import query_to_dataframe


def diagnose_panthers_data():
    """Diagnose data availability for Carolina Panthers"""

    # Load team config
    team_config_path = Path('config/team_config.yaml')
    with open(team_config_path, 'r') as f:
        team_config = yaml.safe_load(f)

    # Get Panthers config
    try:
        panthers_config = team_config['teams']['carolina_panthers']
        view_prefix = panthers_config['view_prefix']
    except KeyError:
        print("ERROR: 'carolina_panthers' not found in team_config.yaml")
        print("\nAvailable teams:")
        for team in team_config['teams'].keys():
            print(f"  - {team}")
        return

    print("=" * 80)
    print("CAROLINA PANTHERS DATA DIAGNOSTIC")
    print("=" * 80)
    print(f"\nView Prefix: {view_prefix}")

    # Check which views exist
    subcategory_view_pattern = team_config['view_patterns']['subcategory_all_time']
    subcategory_view = subcategory_view_pattern.format(prefix=view_prefix)

    print(f"\nExpected subcategory view: {subcategory_view}")

    # Test 1: Check if view exists and has data
    print("\n1. CHECKING VIEW EXISTENCE:")
    print("-" * 40)

    try:
        test_query = f"SELECT COUNT(*) as row_count FROM {subcategory_view} LIMIT 1"
        result = query_to_dataframe(test_query)
        row_count = result.iloc[0]['ROW_COUNT']
        print(f"✓ View exists with {row_count:,} rows")
    except Exception as e:
        print(f"✗ View error: {str(e)}")
        print("\nTrying to find correct view name...")

        # Try to find views with Panthers in the name
        catalog_query = """
        SELECT TABLE_NAME 
        FROM INFORMATION_SCHEMA.VIEWS 
        WHERE TABLE_SCHEMA = 'SC_TWINBRAINAI'
        AND (UPPER(TABLE_NAME) LIKE '%PANTHER%' OR UPPER(TABLE_NAME) LIKE '%CAROLINA%')
        ORDER BY TABLE_NAME
        """
        try:
            views = query_to_dataframe(catalog_query)
            if not views.empty:
                print("\nFound views containing 'PANTHER' or 'CAROLINA':")
                for _, row in views.iterrows():
                    print(f"  - {row['TABLE_NAME']}")
            else:
                print("No views found with 'PANTHER' or 'CAROLINA' in the name")
        except Exception as e2:
            print(f"Could not query catalog: {str(e2)}")
        return

    # Test 2: Check unique audiences and comparison populations
    print("\n2. CHECKING AUDIENCE NAMES:")
    print("-" * 40)

    audience_query = f"""
    SELECT DISTINCT 
        AUDIENCE,
        COMPARISON_POPULATION,
        COUNT(*) as record_count
    FROM {subcategory_view}
    GROUP BY AUDIENCE, COMPARISON_POPULATION
    ORDER BY AUDIENCE, COMPARISON_POPULATION
    """

    try:
        audiences = query_to_dataframe(audience_query)
        print(f"\nFound {len(audiences)} unique audience/comparison combinations:\n")

        panthers_audiences = []
        nfl_comparisons = []

        for _, row in audiences.iterrows():
            audience = row['AUDIENCE']
            comparison = row['COMPARISON_POPULATION']
            count = row['RECORD_COUNT']

            print(f"  Audience: '{audience}'")
            print(f"  Comparison: '{comparison}'")
            print(f"  Records: {count:,}")
            print()

            # Track Panthers-related audiences
            if 'panther' in audience.lower() or 'carolina' in audience.lower():
                panthers_audiences.append(audience)

            # Track NFL comparisons
            if 'nfl' in comparison.lower():
                nfl_comparisons.append((audience, comparison))

        if panthers_audiences:
            print(f"\nPanthers audiences found: {panthers_audiences}")
        else:
            print("\n⚠️  No Panthers-specific audiences found!")

        if nfl_comparisons:
            print(f"\nNFL comparisons found:")
            for aud, comp in nfl_comparisons:
                print(f"  - {aud} vs {comp}")
        else:
            print("\n⚠️  No NFL comparison data found!")

    except Exception as e:
        print(f"Error querying audiences: {str(e)}")

    # Test 3: Check categories available
    print("\n3. CHECKING AVAILABLE CATEGORIES:")
    print("-" * 40)

    category_query = f"""
    SELECT DISTINCT 
        CATEGORY,
        COUNT(DISTINCT SUBCATEGORY) as subcategory_count
    FROM {subcategory_view}
    WHERE AUDIENCE LIKE '%Panthers%' OR AUDIENCE LIKE '%Carolina%'
    GROUP BY CATEGORY
    ORDER BY CATEGORY
    """

    try:
        categories = query_to_dataframe(category_query)
        if not categories.empty:
            print("\nCategories available for Panthers:")
            for _, row in categories.iterrows():
                print(f"  - {row['CATEGORY']} ({row['SUBCATEGORY_COUNT']} subcategories)")
        else:
            print("No Panthers-specific category data found")

            # Try without filtering by audience
            alt_query = f"""
            SELECT DISTINCT CATEGORY
            FROM {subcategory_view}
            LIMIT 10
            """
            alt_categories = query_to_dataframe(alt_query)
            if not alt_categories.empty:
                print("\nAll available categories (sample):")
                for _, row in alt_categories.iterrows():
                    print(f"  - {row['CATEGORY']}")

    except Exception as e:
        print(f"Error querying categories: {str(e)}")

    # Test 4: Sample data for debugging
    print("\n4. SAMPLE DATA:")
    print("-" * 40)

    sample_query = f"""
    SELECT 
        AUDIENCE,
        COMPARISON_POPULATION,
        CATEGORY,
        SUBCATEGORY,
        COMPOSITE_INDEX
    FROM {subcategory_view}
    WHERE CATEGORY = 'Restaurants'
    LIMIT 10
    """

    try:
        sample = query_to_dataframe(sample_query)
        if not sample.empty:
            print("\nSample restaurant data:")
            print(sample.to_string(index=False))
        else:
            print("No restaurant data found")
    except Exception as e:
        print(f"Error getting sample: {str(e)}")

    # Test 5: Check all available views for this team
    print("\n5. CHECKING ALL PANTHERS VIEWS:")
    print("-" * 40)

    view_patterns = team_config.get('view_patterns', {})
    for view_type, pattern in view_patterns.items():
        view_name = pattern.format(prefix=view_prefix)
        try:
            check_query = f"SELECT COUNT(*) as cnt FROM {view_name} LIMIT 1"
            result = query_to_dataframe(check_query)
            print(f"✓ {view_type}: {view_name} ({result.iloc[0]['CNT']:,} rows)")
        except:
            print(f"✗ {view_type}: {view_name} (NOT FOUND)")

    print("\n" + "=" * 80)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 80)


def find_working_team_example():
    """Find a team that has working NFL comparison data"""

    print("\n" + "=" * 80)
    print("SEARCHING FOR WORKING NFL TEAM EXAMPLE")
    print("=" * 80)

    # Load team config
    team_config_path = Path('config/team_config.yaml')
    with open(team_config_path, 'r') as f:
        team_config = yaml.safe_load(f)

    # Check all NFL teams
    nfl_teams = []
    for team_key, team_data in team_config['teams'].items():
        if team_data.get('league') == 'NFL':
            nfl_teams.append((team_key, team_data))

    print(f"\nFound {len(nfl_teams)} NFL teams in config")

    for team_key, team_data in nfl_teams[:3]:  # Check first 3 NFL teams
        print(f"\nChecking {team_data['full_name']}...")

        view_prefix = team_data['view_prefix']
        subcategory_view_pattern = team_config['view_patterns']['subcategory_all_time']
        subcategory_view = subcategory_view_pattern.format(prefix=view_prefix)

        try:
            # Look for NFL comparison data
            query = f"""
            SELECT 
                AUDIENCE,
                COMPARISON_POPULATION,
                COUNT(*) as cnt
            FROM {subcategory_view}
            WHERE COMPARISON_POPULATION LIKE '%NFL%'
            GROUP BY AUDIENCE, COMPARISON_POPULATION
            LIMIT 5
            """
            result = query_to_dataframe(query)

            if not result.empty:
                print(f"✓ Found NFL comparison data!")
                for _, row in result.iterrows():
                    print(f"  - {row['AUDIENCE']} vs {row['COMPARISON_POPULATION']} ({row['CNT']} records)")
                break
            else:
                print("  No NFL comparison data")

        except Exception as e:
            print(f"  Error: {str(e)}")


if __name__ == "__main__":
    # Run diagnostics
    diagnose_panthers_data()

    # Try to find a working example
    find_working_team_example()