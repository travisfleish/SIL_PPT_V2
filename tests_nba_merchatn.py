#!/usr/bin/env python3
"""
Test script to verify that _get_league_comparison_subcategory correctly filters
excluded subcategories and only uses allowed subcategories for NFL comparisons.
Corrected for Carolina Panthers data structure with proper whitespace handling.
"""

import pandas as pd
import yaml
from pathlib import Path
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_processors.snowflake_connector import query_to_dataframe
from data_processors.category_analyzer import CategoryAnalyzer


def test_filtered_league_comparison_panthers():
    """Test that league comparison respects subcategory exclusion rules for Carolina Panthers"""

    # Load configs
    team_config_path = Path('config/team_config.yaml')
    with open(team_config_path, 'r') as f:
        team_config = yaml.safe_load(f)

    categories_config_path = Path('config/categories.yaml')
    with open(categories_config_path, 'r') as f:
        categories_config = yaml.safe_load(f)

    # Get Carolina Panthers config
    panthers_config = team_config['teams']['carolina_panthers']
    view_prefix = panthers_config['view_prefix']

    # Get the subcategory view name
    subcategory_view_pattern = team_config['view_patterns']['subcategory_all_time']
    subcategory_view = subcategory_view_pattern.format(prefix=view_prefix)

    # Initialize analyzer for Panthers
    analyzer = CategoryAnalyzer(
        team_name="Carolina Panthers",
        team_short="Panthers",
        league="NFL",
        comparison_population="Local Gen Pop (Excl. Carolina Panthers Fans)"
    )

    print("\n" + "=" * 80)
    print("TESTING FILTERED LEAGUE COMPARISON - CAROLINA PANTHERS")
    print("=" * 80)
    print("Verifying that excluded subcategories are not used in NFL comparisons\n")

    # Test cases
    test_cases = [
        {
            'category': 'restaurants',
            'expected_excluded': ['Restaurants - Hospitality'],
            'expected_insight_subcategory': 'QSR & Fast Casual'
        },
        {
            'category': 'travel',
            'expected_excluded': ['Travel - Retail', 'Travel - Train'],
            'expected_insight_subcategory': 'Airlines'
        },
        {
            'category': 'finance',
            'expected_excluded': ['Finance - Banks'],
            'expected_insight_subcategory': 'Investments'
        },
        {
            'category': 'auto',
            'expected_excluded': ['Auto - EV Charging', 'Auto - Motorcycle Dealers',
                                  'Auto - Oil Change', 'Auto - Tire Service'],
            'expected_insight_subcategory': 'Car Washes'
        },
        {
            'category': 'athletic',
            'expected_excluded': [],
            'expected_insight_subcategory': 'Gear'
        }
    ]

    results = []

    # First, get all available categories with their actual formatting
    all_cats_query = f"""
    SELECT DISTINCT CATEGORY 
    FROM {subcategory_view}
    WHERE AUDIENCE = 'Carolina Panthers Fans'
    """

    try:
        all_categories_df = query_to_dataframe(all_cats_query)
        # Create a mapping of stripped category names to actual category names (with whitespace)
        category_mapping = {}
        for _, row in all_categories_df.iterrows():
            actual_cat = row['CATEGORY']
            stripped_cat = actual_cat.strip().lower()
            category_mapping[stripped_cat] = actual_cat

        print(f"Found {len(category_mapping)} categories in database")
        print(f"Sample categories (showing whitespace): {list(category_mapping.values())[:5]}")
        print()

    except Exception as e:
        print(f"Error getting category list: {str(e)}")
        return

    for test_case in test_cases:
        category_key = test_case['category']
        category_config = categories_config['categories'][category_key]
        category_names = category_config.get('category_names_in_data', [])

        print(f"\nTesting: {category_config['display_name']}")
        print("-" * 60)

        # Get subcategory configuration
        subcategory_config = category_config.get('subcategories', {})
        excluded = subcategory_config.get('exclude', [])

        print(f"Excluded subcategories: {excluded if excluded else 'None'}")

        # Find matching category in database (with whitespace handling)
        actual_category = None
        for cat_name in category_names:
            stripped_name = cat_name.strip().lower()
            if stripped_name in category_mapping:
                actual_category = category_mapping[stripped_name]
                print(f"Matched config category '{cat_name}' to database category '{actual_category}'")
                break

        if not actual_category:
            print(f"WARNING: Category '{category_names}' not found in database")
            print(f"Tried to match against: {list(category_mapping.keys())[:10]}...")
            results.append({
                'category': category_config['display_name'],
                'status': 'SKIP',
                'reason': 'Category not found in data'
            })
            continue

        # Query with the actual category name (including any whitespace)
        query = f"""
        SELECT * FROM {subcategory_view}
        WHERE CATEGORY = '{actual_category}'
        AND AUDIENCE = 'Carolina Panthers Fans'
        AND COMPARISON_POPULATION = 'NFL Fans'
        ORDER BY COMPOSITE_INDEX DESC
        """

        try:
            nfl_data = query_to_dataframe(query)

            if nfl_data.empty:
                print("ERROR: No NFL comparison data found")
                results.append({
                    'category': category_config['display_name'],
                    'status': 'FAIL',
                    'reason': 'No NFL data found'
                })
                continue

            # Show all NFL comparison subcategories with their best index
            print("\nNFL comparison data (before filtering):")
            for _, row in nfl_data.iterrows():
                subcat = row['SUBCATEGORY']
                indices = {
                    'PERC': float(row.get('PERC_INDEX', 0)),
                    'SPC': float(row.get('SPC_INDEX', 0)),
                    'SPP': float(row.get('SPP_INDEX', 0)),
                    'PPC': float(row.get('PPC_INDEX', 0)),
                    'COMPOSITE': float(row.get('COMPOSITE_INDEX', 0))
                }
                best_index_name = max(indices, key=indices.get)
                best_index_value = indices[best_index_name]

                # Check if this subcategory should be excluded (strip whitespace for comparison)
                excluded_marker = ""
                for excluded_subcat in test_case['expected_excluded']:
                    if subcat.strip() == excluded_subcat.strip():
                        excluded_marker = " [SHOULD BE EXCLUDED]"
                        break

                print(f"  {subcat}: {best_index_name}_INDEX = {best_index_value:.0f}{excluded_marker}")

            # Get full subcategory data for the category
            query_full = f"""
            SELECT * FROM {subcategory_view}
            WHERE CATEGORY = '{actual_category}'
            """
            subcategory_df = query_to_dataframe(query_full)

            # Test the method
            print("\nRunning _get_league_comparison_subcategory()...")
            insight = analyzer._get_league_comparison_subcategory(subcategory_df, category_config)

            if insight:
                print(f"Generated insight: {insight}")

                # Check if excluded subcategories are used
                test_passed = True
                for excluded_subcat in test_case['expected_excluded']:
                    # Extract the subcategory name part after the dash
                    subcat_name = excluded_subcat.split(' - ')[-1].strip()
                    if subcat_name.lower() in insight.lower():
                        print(f"\nERROR: Insight uses excluded subcategory '{subcat_name}'!")
                        test_passed = False
                        results.append({
                            'category': category_config['display_name'],
                            'status': 'FAIL',
                            'reason': f'Used excluded subcategory: {subcat_name}'
                        })
                        break

                if test_passed:
                    # Check expected subcategory
                    expected = test_case['expected_insight_subcategory']
                    if expected.lower() in insight.lower():
                        print(f"SUCCESS: Correctly using '{expected}'")
                    else:
                        print(f"INFO: Expected '{expected}' but insight uses different subcategory")

                    results.append({
                        'category': category_config['display_name'],
                        'status': 'PASS',
                        'insight': insight
                    })
            else:
                print("ERROR: No insight generated")
                results.append({
                    'category': category_config['display_name'],
                    'status': 'FAIL',
                    'reason': 'No insight generated'
                })

        except Exception as e:
            print(f"ERROR: {str(e)}")
            results.append({
                'category': category_config['display_name'],
                'status': 'FAIL',
                'reason': str(e)
            })

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY - CAROLINA PANTHERS")
    print("=" * 80)

    passed = sum(1 for r in results if r['status'] == 'PASS')
    failed = sum(1 for r in results if r['status'] == 'FAIL')
    skipped = sum(1 for r in results if r['status'] == 'SKIP')

    print(f"\nTotal tests: {len(results)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Skipped: {skipped}")

    print("\nDetailed Results:")
    print("-" * 80)
    for result in results:
        if result['status'] == 'PASS':
            status = "✓"
        elif result['status'] == 'FAIL':
            status = "✗"
        else:
            status = "⚠"

        print(f"{status} {result['category']}: {result['status']}")
        if result['status'] in ['FAIL', 'SKIP']:
            print(f"  Reason: {result['reason']}")

    print("\nKey Validations for NFL/Panthers:")
    print("- Restaurants should NOT use 'Hospitality'")
    print("- Travel should NOT use 'Train'")
    print("- Finance should NOT use 'Banks'")
    print("- Athletic should still use 'Gear'")

    # Show the category mapping for debugging
    print("\n" + "=" * 80)
    print("CATEGORY MAPPING (config -> database)")
    print("=" * 80)
    for test_case in test_cases[:3]:  # Show first 3 for brevity
        category_key = test_case['category']
        category_config = categories_config['categories'][category_key]
        category_names = category_config.get('category_names_in_data', [])

        print(f"\n{category_config['display_name']}:")
        for cat_name in category_names:
            stripped_name = cat_name.strip().lower()
            if stripped_name in category_mapping:
                print(f"  '{cat_name}' -> '{category_mapping[stripped_name]}'")
            else:
                print(f"  '{cat_name}' -> NOT FOUND")


if __name__ == "__main__":
    test_filtered_league_comparison_panthers()