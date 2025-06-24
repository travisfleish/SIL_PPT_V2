#!/usr/bin/env python3
"""
Test script to identify custom categories selected by the CategoryAnalyzer
Uses actual Snowflake data
"""

import pandas as pd
from pathlib import Path
import sys

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from data_processors.category_analyzer import CategoryAnalyzer
from data_processors.snowflake_connector import query_to_dataframe, test_connection
from utils.team_config_manager import TeamConfigManager


def test_custom_category_selection(team_key: str = 'utah_jazz'):
    """Test and display custom category selection using real Snowflake data"""

    print("\n" + "=" * 80)
    print(f"CUSTOM CATEGORY SELECTION TEST - {team_key.replace('_', ' ').title()}")
    print("=" * 80)

    # Test connection first
    print("\nTesting Snowflake connection...")
    if not test_connection():
        print("❌ Failed to connect to Snowflake")
        return
    print("✅ Connected to Snowflake")

    # 1. Initialize CategoryAnalyzer
    config_manager = TeamConfigManager()
    team_config = config_manager.get_team_config(team_key)

    analyzer = CategoryAnalyzer(
        team_name=team_config['team_name'],
        team_short=team_config['team_name_short'],
        league=team_config['league']
    )

    print(f"\nTeam: {team_config['team_name']}")
    print(f"League: {team_config['league']}")
    print(f"Audience: {analyzer.audience_name}")
    print(f"Comparison: {analyzer.comparison_pop}")

    # 2. Load category data from Snowflake
    view_prefix = team_config['view_prefix']
    view_name = f"{view_prefix}_CATEGORY_INDEXING_ALL_TIME"

    print(f"\nLoading data from: {view_name}")

    query = f"""
    SELECT * FROM {view_name}
    WHERE AUDIENCE = '{analyzer.audience_name}'
    AND COMPARISON_POPULATION = '{analyzer.comparison_pop}'
    ORDER BY COMPOSITE_INDEX DESC
    """

    try:
        category_df = query_to_dataframe(query)
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        return

    if category_df.empty:
        print("❌ No data found!")
        return

    print(f"✅ Loaded {len(category_df)} category records")

    # 3. Show all categories ranked by composite index
    print("\n📊 ALL CATEGORIES BY COMPOSITE INDEX:")
    print("-" * 90)
    print(f"{'Rank':<6} {'Category':<40} {'Composite':<12} {'Audience %':<12} {'Index':<8}")
    print("-" * 90)

    for i, (_, row) in enumerate(category_df.head(20).iterrows(), 1):
        print(f"{i:<6} {row['CATEGORY']:<40} {row['COMPOSITE_INDEX']:<12.1f} "
              f"{row['PERC_AUDIENCE'] * 100:<11.1f}% {row['PERC_INDEX']:<8.0f}")

    if len(category_df) > 20:
        print(f"... and {len(category_df) - 20} more categories")

    # 4. Get custom categories
    print("\n\n🎯 CUSTOM CATEGORY SELECTION:")
    print("-" * 80)

    # Get fixed categories
    fixed_categories = ['restaurants', 'athleisure', 'finance', 'gambling', 'travel', 'auto']
    print(f"Fixed categories: {', '.join(fixed_categories)}")
    print(f"Minimum audience threshold: 20%")
    print(f"Number of custom categories to select: 4")

    custom_categories = analyzer.get_custom_categories(
        category_df=category_df,
        is_womens_team=False  # Change to True for women's teams
    )

    if not custom_categories:
        print("\n❌ No custom categories selected!")
        return

    print(f"\n✅ Selected {len(custom_categories)} custom categories:\n")

    for i, cat in enumerate(custom_categories, 1):
        print(f"{i}. {cat['display_name']}")
        print(f"   - Composite Index: {cat['composite_index']:.1f}")
        print(f"   - Audience %: {cat['audience_pct'] * 100:.1f}%")
        print(f"   - Index vs Gen Pop: {cat['perc_index']:.0f}")
        print(f"   - Category Key: {cat['category_key']}")
        print()

    # 5. Show excluded categories and reasons
    print("\n❌ EXCLUDED CATEGORIES AND REASONS:")
    print("-" * 80)

    # Get fixed category names from config
    fixed_names = set()
    for cat_key in fixed_categories:
        if cat_key in analyzer.categories:
            fixed_names.update(analyzer.categories[cat_key]['category_names_in_data'])

    # Get selected custom category names
    selected_names = {cat['display_name'] for cat in custom_categories}

    # Check all categories
    all_categories = category_df['CATEGORY'].unique()

    exclusion_summary = {
        'Fixed category': [],
        'In exclusion list': [],
        'Below 20% threshold': [],
        'Not in top 4': [],
        'Women\'s only': []
    }

    for cat in all_categories:
        if cat not in selected_names:
            cat_data = category_df[category_df['CATEGORY'] == cat].iloc[0]

            if cat in fixed_names:
                reason = 'Fixed category'
            elif cat in analyzer.excluded_custom:
                reason = 'In exclusion list'
            elif cat in ['Beauty', 'Health']:
                reason = 'Women\'s only'
            elif cat_data['PERC_AUDIENCE'] < 0.20:
                reason = 'Below 20% threshold'
            else:
                reason = 'Not in top 4'

            exclusion_summary[reason].append({
                'name': cat,
                'composite': cat_data['COMPOSITE_INDEX'],
                'audience': cat_data['PERC_AUDIENCE'] * 100
            })

    # Display exclusions by reason
    for reason, categories in exclusion_summary.items():
        if categories:
            print(f"\n{reason}:")
            # Sort by composite index
            categories.sort(key=lambda x: x['composite'], reverse=True)
            for cat in categories[:5]:  # Show top 5 in each category
                print(f"  - {cat['name']:<35} (index: {cat['composite']:.0f}, audience: {cat['audience']:.1f}%)")
            if len(categories) > 5:
                print(f"  ... and {len(categories) - 5} more")

    # 6. Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total categories in data: {len(all_categories)}")
    print(f"Fixed categories: {len(fixed_categories)}")
    print(f"Custom categories selected: {len(custom_categories)}")
    print(f"Total categories for report: {len(fixed_categories) + len(custom_categories)}")

    # Show final category list
    print("\n📋 FINAL CATEGORY LIST FOR POWERPOINT:")
    all_report_categories = fixed_categories + [cat['category_key'] for cat in custom_categories]
    for i, cat in enumerate(all_report_categories, 1):
        print(f"  {i}. {cat}")

    return custom_categories


def compare_teams():
    """Compare custom category selection between teams"""
    print("\n" + "=" * 80)
    print("COMPARING CUSTOM CATEGORIES BETWEEN TEAMS")
    print("=" * 80)

    teams = ['utah_jazz', 'dallas_cowboys']
    results = {}

    for team in teams:
        print(f"\n\nAnalyzing {team.replace('_', ' ').title()}...")
        custom_cats = test_custom_category_selection(team)
        if custom_cats:
            results[team] = custom_cats

    # Compare results
    if len(results) == 2:
        print("\n\n" + "=" * 80)
        print("COMPARISON SUMMARY")
        print("=" * 80)

        for team, cats in results.items():
            print(f"\n{team.replace('_', ' ').title()} Custom Categories:")
            for i, cat in enumerate(cats, 1):
                print(f"  {i}. {cat['display_name']} (index: {cat['composite_index']:.0f})")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Test custom category selection with Snowflake data')
    parser.add_argument('--team', type=str, default='utah_jazz',
                        choices=['utah_jazz', 'dallas_cowboys'],
                        help='Team to test (default: utah_jazz)')
    parser.add_argument('--compare', action='store_true',
                        help='Compare custom categories between all teams')

    args = parser.parse_args()

    if args.compare:
        compare_teams()
    else:
        test_custom_category_selection(args.team)