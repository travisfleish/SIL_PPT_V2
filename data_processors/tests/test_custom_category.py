#!/usr/bin/env python3
"""
Test script to identify custom categories selected by the CategoryAnalyzer
Uses actual Snowflake data and the new allowed_for_custom list
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

    # 1. Initialize CategoryAnalyzer with correct config path
    config_manager = TeamConfigManager()
    team_config = config_manager.get_team_config(team_key)

    # Explicitly set the config path to categories.yaml
    config_path = Path(__file__).parent.parent.parent / 'config' / 'categories.yaml'

    analyzer = CategoryAnalyzer(
        team_name=team_config['team_name'],
        team_short=team_config['team_name_short'],
        league=team_config['league'],
        config_path=config_path
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

    # 3. Show allowed and excluded lists
    print("\n📋 CATEGORY CONFIGURATION:")
    print("-" * 80)
    print(f"Allowed categories for custom selection: {len(analyzer.allowed_custom)}")
    print(f"Excluded categories: {len(analyzer.excluded_custom)}")
    print(f"\nExcluded list: {', '.join(analyzer.excluded_custom)}")

    # 4. Show all categories ranked by composite index
    print("\n📊 ALL CATEGORIES BY COMPOSITE INDEX:")
    print("-" * 90)
    print(f"{'Rank':<6} {'Category':<35} {'Composite':<10} {'Aud %':<8} {'Index':<8} {'Status':<20}")
    print("-" * 90)

    # Get fixed category names
    fixed_categories = ['restaurants', 'athleisure', 'finance', 'gambling', 'travel', 'auto']
    if team_config.get('gender') == 'womens':
        fixed_categories.extend(['beauty', 'health'])

    fixed_names = set()
    for cat_key in fixed_categories:
        if cat_key in analyzer.categories:
            fixed_names.update(analyzer.categories[cat_key]['category_names_in_data'])

    for i, (_, row) in enumerate(category_df.head(25).iterrows(), 1):
        cat_name = row['CATEGORY']

        # Determine status
        if cat_name in fixed_names:
            status = "Fixed"
        elif cat_name not in analyzer.allowed_custom:
            status = "Not Allowed"
        elif cat_name in analyzer.excluded_custom:
            status = "Excluded"
        elif row['PERC_AUDIENCE'] < 0.20:
            status = "Below 20%"
        else:
            status = "✅ Eligible"

        print(f"{i:<6} {cat_name:<35} {row['COMPOSITE_INDEX']:<10.1f} "
              f"{row['PERC_AUDIENCE'] * 100:<7.1f}% {row['PERC_INDEX']:<8.0f} {status:<20}")

    if len(category_df) > 25:
        print(f"... and {len(category_df) - 25} more categories")

    # 5. Get custom categories
    print("\n\n🎯 CUSTOM CATEGORY SELECTION:")
    print("-" * 80)

    print(f"Fixed categories: {', '.join(fixed_categories)}")
    print(f"Minimum audience threshold: 20%")

    # Determine custom category count
    if team_config.get('gender') == 'womens':
        custom_count_text = "2 (women's team)"
    else:
        custom_count_text = "4 (men's team)"
    print(f"Number of custom categories to select: {custom_count_text}")

    custom_categories = analyzer.get_custom_categories(
        category_df=category_df,
        is_womens_team=(team_config.get('gender') == 'womens')
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

    # 6. Show excluded categories and reasons
    print("\n❌ EXCLUDED CATEGORIES AND REASONS:")
    print("-" * 80)

    # Get selected custom category names
    selected_names = {cat['display_name'] for cat in custom_categories}

    # Check all categories
    all_categories = category_df['CATEGORY'].unique()

    exclusion_summary = {
        'Fixed category': [],
        'Not in allowed list': [],
        'In exclusion list': [],
        'Below 20% threshold': [],
        'Not in top N': []
    }

    for cat in all_categories:
        if cat not in selected_names and cat not in fixed_names:
            cat_data = category_df[category_df['CATEGORY'] == cat].iloc[0]

            if cat not in analyzer.allowed_custom:
                reason = 'Not in allowed list'
            elif cat in analyzer.excluded_custom:
                reason = 'In exclusion list'
            elif cat_data['PERC_AUDIENCE'] < 0.20:
                reason = 'Below 20% threshold'
            else:
                reason = 'Not in top N'

            exclusion_summary[reason].append({
                'name': cat,
                'composite': cat_data['COMPOSITE_INDEX'],
                'audience': cat_data['PERC_AUDIENCE'] * 100
            })

    # Display exclusions by reason
    for reason, categories in exclusion_summary.items():
        if categories:
            print(f"\n{reason} ({len(categories)} categories):")
            # Sort by composite index
            categories.sort(key=lambda x: x['composite'], reverse=True)
            for cat in categories[:5]:  # Show top 5 in each category
                print(f"  - {cat['name']:<35} (index: {cat['composite']:.0f}, audience: {cat['audience']:.1f}%)")
            if len(categories) > 5:
                print(f"  ... and {len(categories) - 5} more")

    # 7. Show eligible categories that weren't selected
    print("\n\n📊 ELIGIBLE BUT NOT SELECTED (lower composite index):")
    print("-" * 80)

    # Find all eligible categories
    eligible_but_not_selected = []
    for _, row in category_df.iterrows():
        cat_name = row['CATEGORY']
        if (cat_name in analyzer.allowed_custom and
                cat_name not in analyzer.excluded_custom and
                cat_name not in fixed_names and
                cat_name not in selected_names and
                row['PERC_AUDIENCE'] >= 0.20):
            eligible_but_not_selected.append({
                'name': cat_name,
                'composite': row['COMPOSITE_INDEX'],
                'audience': row['PERC_AUDIENCE'] * 100
            })

    if eligible_but_not_selected:
        eligible_but_not_selected.sort(key=lambda x: x['composite'], reverse=True)
        for cat in eligible_but_not_selected[:10]:
            print(f"  - {cat['name']:<35} (index: {cat['composite']:.0f}, audience: {cat['audience']:.1f}%)")
        if len(eligible_but_not_selected) > 10:
            print(f"  ... and {len(eligible_but_not_selected) - 10} more")
    else:
        print("  None - all eligible categories were selected")

    # 8. Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total categories in data: {len(all_categories)}")
    print(f"Categories in allowed list: {len(analyzer.allowed_custom)}")
    print(f"Categories meeting all criteria: {len(custom_categories) + len(eligible_but_not_selected)}")
    print(f"Fixed categories: {len(fixed_categories)}")
    print(f"Custom categories selected: {len(custom_categories)}")
    print(f"Total categories for report: {len(fixed_categories) + len(custom_categories)}")

    # Show final category list
    print("\n📋 FINAL CATEGORY LIST FOR POWERPOINT:")
    all_report_categories = fixed_categories + [cat['category_key'] for cat in custom_categories]
    for i, cat in enumerate(all_report_categories, 1):
        print(f"  {i}. {cat}")

    return custom_categories


def analyze_allowed_list_impact():
    """Analyze the impact of the allowed_for_custom list"""
    print("\n" + "=" * 80)
    print("ANALYZING IMPACT OF ALLOWED_FOR_CUSTOM LIST")
    print("=" * 80)

    # Initialize analyzer to get config with correct path
    config_path = Path(__file__).parent.parent.parent / 'config' / 'categories.yaml'

    analyzer = CategoryAnalyzer(
        team_name="Test Team",
        team_short="Test",
        league="NBA",
        config_path=config_path
    )

    print(f"\nAllowed list contains {len(analyzer.allowed_custom)} categories:")
    for i, cat in enumerate(sorted(analyzer.allowed_custom), 1):
        print(f"  {i:2d}. {cat}")

    print(f"\n\nExcluded list contains {len(analyzer.excluded_custom)} categories:")
    for i, cat in enumerate(analyzer.excluded_custom, 1):
        print(f"  {i}. {cat}")

    # Check for overlaps
    overlap = set(analyzer.allowed_custom) & set(analyzer.excluded_custom)
    if overlap:
        print(f"\n⚠️  Categories in BOTH allowed and excluded lists: {', '.join(overlap)}")
        print("   These will be excluded (exclusion takes precedence)")


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

        # Find common categories
        jazz_cats = {cat['display_name'] for cat in results.get('utah_jazz', [])}
        cowboys_cats = {cat['display_name'] for cat in results.get('dallas_cowboys', [])}

        common = jazz_cats & cowboys_cats
        if common:
            print(f"\n\nCommon custom categories: {', '.join(sorted(common))}")

        jazz_only = jazz_cats - cowboys_cats
        if jazz_only:
            print(f"\nUtah Jazz only: {', '.join(sorted(jazz_only))}")

        cowboys_only = cowboys_cats - jazz_cats
        if cowboys_only:
            print(f"\nDallas Cowboys only: {', '.join(sorted(cowboys_only))}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Test custom category selection with Snowflake data')
    parser.add_argument('--team', type=str, default='utah_jazz',
                        choices=['utah_jazz', 'dallas_cowboys'],
                        help='Team to test (default: utah_jazz)')
    parser.add_argument('--compare', action='store_true',
                        help='Compare custom categories between all teams')
    parser.add_argument('--analyze-allowed', action='store_true',
                        help='Analyze the allowed_for_custom list configuration')

    args = parser.parse_args()

    if args.analyze_allowed:
        analyze_allowed_list_impact()
    elif args.compare:
        compare_teams()
    else:
        test_custom_category_selection(args.team)