#!/usr/bin/env python3
"""
Test script to verify the trailing whitespace fix for Carolina Panthers custom categories
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from data_processors.category_analyzer import CategoryAnalyzer
from data_processors.snowflake_connector import query_to_dataframe
from utils.team_config_manager import TeamConfigManager
from report_builder.pptx_builder import PowerPointBuilder
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_custom_categories_fix():
    """Test that Carolina Panthers now gets custom categories"""

    print("\n" + "=" * 80)
    print("TESTING CUSTOM CATEGORIES FIX FOR CAROLINA PANTHERS")
    print("=" * 80)

    # Initialize
    config_manager = TeamConfigManager()
    team_config = config_manager.get_team_config('carolina_panthers')

    analyzer = CategoryAnalyzer(
        team_name=team_config['team_name'],
        team_short=team_config['team_name_short'],
        league=team_config['league'],
        comparison_population=team_config['comparison_population']
    )

    print(f"\nTeam: {team_config['team_name']}")
    print(f"Comparison: {analyzer.comparison_pop}")

    # Load data
    category_query = f"""
    SELECT * FROM {team_config['view_prefix']}_CATEGORY_INDEXING_ALL_TIME
    WHERE AUDIENCE = '{analyzer.audience_name}'
    AND COMPARISON_POPULATION = '{analyzer.comparison_pop}'
    """

    merchant_query = f"""
    SELECT * FROM {team_config['view_prefix']}_MERCHANT_INDEXING_ALL_TIME
    WHERE AUDIENCE = '{analyzer.audience_name}'
    """

    try:
        category_df = query_to_dataframe(category_query)
        merchant_df = query_to_dataframe(merchant_query)

        print(f"\nLoaded {len(category_df)} categories")
        print(f"Loaded {len(merchant_df)} merchant records")

        # Check for whitespace
        categories_with_space = category_df[category_df['CATEGORY'] != category_df['CATEGORY'].str.strip()]
        print(f"\nCategories with trailing whitespace: {len(categories_with_space)}")

        # Get custom categories
        print("\n" + "-" * 60)
        print("GETTING CUSTOM CATEGORIES...")
        print("-" * 60)

        custom_categories = analyzer.get_custom_categories(
            category_df=category_df,
            merchant_df=merchant_df,
            is_womens_team=False,
            existing_categories=['restaurants', 'athleisure', 'finance', 'gambling', 'travel', 'auto']
        )

        print(f"\n✅ RESULTS: Found {len(custom_categories)} custom categories!")

        if custom_categories:
            print("\nSelected categories:")
            for i, cat in enumerate(custom_categories, 1):
                cat_type = "EMERGING" if cat.get('is_emerging', False) else "ESTABLISHED"
                print(f"\n{i}. {cat['display_name']} [{cat_type}]")
                print(f"   - Composite Index: {cat['composite_index']:.1f}")
                print(f"   - Audience: {cat['audience_pct'] * 100:.1f}%")

                # Show top merchant
                cat_merchants = merchant_df[
                    (merchant_df['CATEGORY'].str.strip() == cat['display_name']) &
                    (merchant_df['AUDIENCE'] == analyzer.audience_name)
                    ].nlargest(1, 'PERC_AUDIENCE')

                if not cat_merchants.empty:
                    top_merchant = cat_merchants.iloc[0]
                    print(f"   - Top Merchant: {top_merchant['MERCHANT']} ({top_merchant['PERC_AUDIENCE'] * 100:.1f}%)")

            print("\n✅ SUCCESS! The fix is working correctly.")
            print("\nExpected categories like:")
            print("  - Apparel (80.2% audience)")
            print("  - Specialty Food & Gifts (68.0% audience)")
            print("  - Athletic (57.8% audience)")
            print("  - Sportstainment (18.2% audience) [EMERGING]")

        else:
            print("\n❌ FAILED! No custom categories found.")
            print("The fix may not have been applied correctly.")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


def test_full_presentation_generation():
    """Test generating a full presentation to ensure everything works end-to-end"""

    print("\n" + "=" * 80)
    print("TESTING FULL PRESENTATION GENERATION")
    print("=" * 80)

    try:
        print("\nGenerating Carolina Panthers presentation...")
        print("This will test the complete pipeline including custom categories...")

        # Use the PowerPointBuilder
        builder = PowerPointBuilder('carolina_panthers')

        # Check that custom categories will be included
        print(f"\nCategory Analyzer initialized with:")
        print(f"  - Comparison population: {builder.category_analyzer.comparison_pop}")
        print(f"  - Allowed custom categories: {len(builder.category_analyzer.allowed_custom)}")

        # Build presentation (this will take a minute)
        output_path = builder.build_presentation(
            include_custom_categories=True,
            custom_category_count=4  # Force 4 custom categories
        )

        print(f"\n✅ Presentation generated successfully!")
        print(f"   Output: {output_path}")

        # Check what was created
        if builder.slides_created:
            print(f"\n   Total slides: {len(builder.slides_created)}")

            # Count custom category slides
            custom_slides = [s for s in builder.slides_created if any(
                cat in s for cat in ['Apparel', 'Athletic', 'Specialty Food', 'Sportstainment',
                                     'Beauty', 'Electronics', 'Entertainment', 'Pets']
            )]

            if custom_slides:
                print(f"   Custom category slides found: {len(custom_slides)}")
                for slide in custom_slides:
                    print(f"     - {slide}")
            else:
                print("   ⚠️  No custom category slides found!")

    except Exception as e:
        print(f"\n❌ Error generating presentation: {e}")
        import traceback
        traceback.print_exc()


def compare_before_after():
    """Compare Jazz vs Panthers to ensure both work correctly"""

    print("\n" + "=" * 80)
    print("COMPARING JAZZ VS PANTHERS")
    print("=" * 80)

    config_manager = TeamConfigManager()

    for team_key in ['utah_jazz', 'carolina_panthers']:
        print(f"\n{team_key.replace('_', ' ').title()}:")
        print("-" * 40)

        team_config = config_manager.get_team_config(team_key)

        analyzer = CategoryAnalyzer(
            team_name=team_config['team_name'],
            team_short=team_config['team_name_short'],
            league=team_config['league'],
            comparison_population=team_config['comparison_population']
        )

        # Load data
        category_query = f"""
        SELECT * FROM {team_config['view_prefix']}_CATEGORY_INDEXING_ALL_TIME
        WHERE AUDIENCE = '{analyzer.audience_name}'
        AND COMPARISON_POPULATION = '{analyzer.comparison_pop}'
        """

        merchant_query = f"""
        SELECT * FROM {team_config['view_prefix']}_MERCHANT_INDEXING_ALL_TIME
        WHERE AUDIENCE = '{analyzer.audience_name}'
        """

        try:
            category_df = query_to_dataframe(category_query)
            merchant_df = query_to_dataframe(merchant_query)

            custom_categories = analyzer.get_custom_categories(
                category_df=category_df,
                merchant_df=merchant_df,
                is_womens_team=False,
                existing_categories=['restaurants', 'athleisure', 'finance', 'gambling', 'travel', 'auto']
            )

            print(f"  Custom categories found: {len(custom_categories)}")
            for cat in custom_categories:
                cat_type = "[E]" if cat.get('is_emerging', False) else "[S]"
                print(f"    - {cat['display_name']} {cat_type}")

        except Exception as e:
            print(f"  Error: {e}")

    print("\n✅ Both teams should now have custom categories!")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Test custom categories fix')
    parser.add_argument('--full', action='store_true',
                        help='Test full presentation generation (takes longer)')
    parser.add_argument('--compare', action='store_true',
                        help='Compare Jazz and Panthers')

    args = parser.parse_args()

    # Always run the basic test
    test_custom_categories_fix()

    if args.compare:
        compare_before_after()

    if args.full:
        test_full_presentation_generation()
    else:
        print("\n💡 Tip: Use --full to test complete presentation generation")
        print("   Use --compare to compare Jazz and Panthers")