#!/usr/bin/env python3
"""
Debug test script for Carolina Panthers category slides with custom category testing
Tests the CategoryAnalyzer and CategorySlide with real data to diagnose issues
"""

import sys
from pathlib import Path
import pandas as pd
import logging
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from data_processors.category_analyzer import CategoryAnalyzer
from data_processors.snowflake_connector import query_to_dataframe
from utils.team_config_manager import TeamConfigManager
from slide_generators.category_slide import CategorySlide
from pptx import Presentation

# Configure logging with more detail
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def debug_panthers_category():
    """Debug Carolina Panthers category data issues"""

    logger.info("=" * 60)
    logger.info("DEBUGGING CAROLINA PANTHERS CATEGORY SLIDES")
    logger.info("=" * 60)

    # 1. Load team configuration
    config_manager = TeamConfigManager()
    team_config = config_manager.get_team_config('carolina_panthers')

    logger.info(f"\n1. TEAM CONFIGURATION:")
    logger.info(f"   Team Name: {team_config['team_name']}")
    logger.info(f"   Team Short: {team_config['team_name_short']}")
    logger.info(f"   League: {team_config['league']}")
    logger.info(f"   View Prefix: {team_config['view_prefix']}")
    logger.info(f"   Comparison Population: '{team_config['comparison_population']}'")

    # 2. Initialize CategoryAnalyzer with and without comparison_population
    logger.info(f"\n2. TESTING CATEGORYANALYZER INITIALIZATION:")

    # Test WITHOUT comparison_population (old way)
    analyzer_without = CategoryAnalyzer(
        team_name=team_config['team_name'],
        team_short=team_config['team_name_short'],
        league=team_config['league']
    )
    logger.info(f"   Without comparison_population parameter:")
    logger.info(f"     - analyzer.comparison_pop = '{analyzer_without.comparison_pop}'")

    # Test WITH comparison_population (new way)
    analyzer_with = CategoryAnalyzer(
        team_name=team_config['team_name'],
        team_short=team_config['team_name_short'],
        league=team_config['league'],
        comparison_population=team_config['comparison_population']
    )
    logger.info(f"   With comparison_population parameter:")
    logger.info(f"     - analyzer.comparison_pop = '{analyzer_with.comparison_pop}'")

    # 3. Query the database to see what comparison populations actually exist
    logger.info(f"\n3. CHECKING DATABASE FOR ACTUAL COMPARISON POPULATIONS:")

    category_view = f"{team_config['view_prefix']}_CATEGORY_INDEXING_ALL_TIME"

    # Query to get all unique comparison populations for Panthers fans
    query = f"""
    SELECT DISTINCT 
        AUDIENCE,
        COMPARISON_POPULATION,
        COUNT(*) as record_count
    FROM {category_view}
    WHERE AUDIENCE = '{analyzer_with.audience_name}'
    GROUP BY AUDIENCE, COMPARISON_POPULATION
    ORDER BY COMPARISON_POPULATION
    """

    logger.info(f"   Querying view: {category_view}")
    logger.info(f"   Looking for audience: '{analyzer_with.audience_name}'")

    try:
        comparison_df = query_to_dataframe(query)

        if not comparison_df.empty:
            logger.info(f"\n   Found {len(comparison_df)} comparison population(s):")
            for idx, row in comparison_df.iterrows():
                logger.info(f"     - '{row['COMPARISON_POPULATION']}' ({row['RECORD_COUNT']} records)")
        else:
            logger.warning("   No data found for Panthers fans!")

            # Check what audiences exist in the view
            audience_query = f"""
            SELECT DISTINCT AUDIENCE, COUNT(*) as cnt
            FROM {category_view}
            GROUP BY AUDIENCE
            ORDER BY AUDIENCE
            """
            audience_df = query_to_dataframe(audience_query)
            logger.info(f"\n   Available audiences in view:")
            for idx, row in audience_df.iterrows():
                logger.info(f"     - '{row['AUDIENCE']}' ({row['CNT']} records)")

    except Exception as e:
        logger.error(f"   Error querying database: {e}")

    # 4. Test loading category data for Restaurants
    logger.info(f"\n4. TESTING RESTAURANT CATEGORY DATA LOADING:")

    try:
        # Query for restaurant category data
        cat_query = f"""
        SELECT * 
        FROM {category_view}
        WHERE TRIM(CATEGORY) = 'Restaurants'
        AND AUDIENCE = '{analyzer_with.audience_name}'
        """

        category_df = query_to_dataframe(cat_query)

        if not category_df.empty:
            logger.info(f"   Found {len(category_df)} restaurant records")

            # Show unique comparison populations in this data
            unique_comps = category_df['COMPARISON_POPULATION'].unique()
            logger.info(f"   Unique comparison populations in restaurant data:")
            for comp in unique_comps:
                logger.info(f"     - '{comp}'")

            # Try to get metrics with each analyzer
            logger.info(f"\n   Testing metric extraction:")

            # Test with analyzer_without (wrong comparison pop)
            logger.info(f"   With analyzer_without (using '{analyzer_without.comparison_pop}'):")
            metrics1 = analyzer_without._get_category_metrics(
                category_df,
                {'display_name': 'Restaurants'}
            )
            logger.info(f"     - percent_fans: {metrics1.percent_fans}")
            logger.info(f"     - percent_likely: {metrics1.percent_likely}")

            # Test with analyzer_with (correct comparison pop)
            logger.info(f"   With analyzer_with (using '{analyzer_with.comparison_pop}'):")
            metrics2 = analyzer_with._get_category_metrics(
                category_df,
                {'display_name': 'Restaurants'}
            )
            logger.info(f"     - percent_fans: {metrics2.percent_fans}")
            logger.info(f"     - percent_likely: {metrics2.percent_likely}")

        else:
            logger.warning("   No restaurant data found for Panthers fans")

    except Exception as e:
        logger.error(f"   Error testing restaurant data: {e}")

    # 5. Test generating a slide with the correct analyzer
    logger.info(f"\n5. TESTING SLIDE GENERATION:")

    try:
        # Load all necessary data
        subcategory_query = f"""
        SELECT * 
        FROM {team_config['view_prefix']}_SUBCATEGORY_INDEXING_ALL_TIME
        WHERE TRIM(CATEGORY) = 'Restaurants'
        """
        subcategory_df = query_to_dataframe(subcategory_query)

        merchant_query = f"""
        SELECT * 
        FROM {team_config['view_prefix']}_MERCHANT_INDEXING_ALL_TIME
        WHERE TRIM(CATEGORY) = 'Restaurants'
        AND AUDIENCE = '{analyzer_with.audience_name}'
        ORDER BY PERC_AUDIENCE DESC
        LIMIT 100
        """
        merchant_df = query_to_dataframe(merchant_query)

        # Use the correct analyzer to analyze the category
        if not category_df.empty:
            results = analyzer_with.analyze_category(
                category_key='restaurants',
                category_df=category_df,
                subcategory_df=subcategory_df,
                merchant_df=merchant_df,
                validate=False
            )

            logger.info(f"   Analysis results generated:")
            logger.info(f"     - Display name: {results['display_name']}")
            logger.info(f"     - Category metrics: {results['category_metrics'].format_percent_fans()} of fans spend")
            logger.info(f"     - Insights count: {len(results['insights'])}")
            logger.info(f"     - Merchant count: {len(results['merchant_stats'][0])}")

            # Try to generate a slide
            presentation = Presentation()
            slide_gen = CategorySlide(presentation)

            presentation = slide_gen.generate(results, team_config)

            # Save test slide
            output_path = Path("test_panthers_category_debug.pptx")
            presentation.save(output_path)
            logger.info(f"\n   ✅ Test slide saved to: {output_path}")

        else:
            logger.warning("   Cannot generate slide - no category data available")

    except Exception as e:
        logger.error(f"   Error generating slide: {e}")
        import traceback
        traceback.print_exc()

    # 6. Summary and recommendations
    logger.info(f"\n6. SUMMARY AND RECOMMENDATIONS:")
    logger.info(f"   - CategoryAnalyzer without comparison_population uses: '{analyzer_without.comparison_pop}'")
    logger.info(f"   - CategoryAnalyzer with comparison_population uses: '{analyzer_with.comparison_pop}'")
    logger.info(f"   - Check if these match what's actually in the database (see section 3)")
    logger.info(f"   - Make sure pptx_builder.py passes comparison_population to CategoryAnalyzer")

    return analyzer_with, team_config


def debug_custom_categories(analyzer, team_config):
    """Debug custom category selection for Panthers"""
    logger.info("\n" + "=" * 60)
    logger.info("DEBUGGING CUSTOM CATEGORIES")
    logger.info("=" * 60)

    # 1. Check configuration
    logger.info("\n1. CUSTOM CATEGORY CONFIGURATION:")
    logger.info(
        f"   - allowed_for_custom: {analyzer.allowed_custom[:5]}..." if analyzer.allowed_custom else "   - allowed_for_custom: []")
    logger.info(
        f"   - excluded_from_custom: {analyzer.excluded_custom[:5]}..." if analyzer.excluded_custom else "   - excluded_from_custom: []")

    # 2. Load category data
    logger.info("\n2. LOADING CATEGORY DATA FOR CUSTOM SELECTION:")

    category_query = f"""
    SELECT 
        CATEGORY,
        AUDIENCE,
        COMPARISON_POPULATION,
        PERC_AUDIENCE,
        PERC_INDEX,
        COMPOSITE_INDEX,
        PPC,
        SPC
    FROM {team_config['view_prefix']}_CATEGORY_INDEXING_ALL_TIME
    WHERE AUDIENCE = '{analyzer.audience_name}'
    AND COMPARISON_POPULATION = '{analyzer.comparison_pop}'
    ORDER BY COMPOSITE_INDEX DESC
    """

    category_df = query_to_dataframe(category_query)

    if category_df.empty:
        logger.error("   ❌ No category data found!")
        return None

    logger.info(f"   ✅ Found {len(category_df)} categories")

    # 3. Show top categories by composite index
    logger.info("\n3. TOP CATEGORIES BY COMPOSITE INDEX:")
    top_10 = category_df.head(10)
    for idx, row in top_10.iterrows():
        cat_name = row['CATEGORY']
        logger.info(f"   {idx + 1}. {cat_name} (raw length: {len(cat_name)})")
        if cat_name != cat_name.strip():
            logger.warning(f"      ⚠️  HAS TRAILING/LEADING SPACES: '{cat_name}' vs '{cat_name.strip()}'")
        logger.info(f"      - PERC_AUDIENCE: {row['PERC_AUDIENCE'] * 100:.1f}%")
        logger.info(f"      - COMPOSITE_INDEX: {row['COMPOSITE_INDEX']:.1f}")
        logger.info(f"      - Allowed: {'✅' if row['CATEGORY'].strip() in analyzer.allowed_custom else '❌'}")
        logger.info(f"      - Excluded: {'❌' if row['CATEGORY'].strip() in analyzer.excluded_custom else '✅'}")

    # 4. Load merchant data for verification
    logger.info("\n4. LOADING MERCHANT DATA FOR VERIFICATION:")

    merchant_query = f"""
    SELECT 
        CATEGORY,
        MERCHANT,
        AUDIENCE,
        PERC_AUDIENCE,
        COMPOSITE_INDEX
    FROM {team_config['view_prefix']}_MERCHANT_INDEXING_ALL_TIME
    WHERE AUDIENCE = '{analyzer.audience_name}'
    ORDER BY CATEGORY, PERC_AUDIENCE DESC
    """

    merchant_df = query_to_dataframe(merchant_query)

    if merchant_df.empty:
        logger.error("   ❌ No merchant data found!")
        return None

    logger.info(f"   ✅ Found {len(merchant_df)} merchant records")

    # 5. Test get_custom_categories
    logger.info("\n5. TESTING get_custom_categories():")

    try:
        # Get fixed categories for the team
        is_womens = team_config.get('is_womens_team', False)
        fixed_categories = analyzer.config['fixed_categories']['womens_teams' if is_womens else 'mens_teams']

        logger.info(f"   - Team type: {'Womens' if is_womens else 'Mens'}")
        logger.info(f"   - Fixed categories: {fixed_categories}")

        # Call get_custom_categories
        custom_categories = analyzer.get_custom_categories(
            category_df=category_df,
            merchant_df=merchant_df,
            is_womens_team=is_womens,
            existing_categories=fixed_categories
        )

        logger.info(f"\n   RESULTS:")
        logger.info(f"   - Found {len(custom_categories)} custom categories")

        for i, cat in enumerate(custom_categories):
            logger.info(f"\n   Custom Category {i + 1}:")
            logger.info(f"     - Display Name: {cat['display_name']}")
            logger.info(f"     - Audience %: {cat['audience_pct'] * 100:.1f}%")
            logger.info(f"     - Composite Index: {cat['composite_index']:.1f}")
            logger.info(f"     - Is Emerging: {cat.get('is_emerging', False)}")

            # Check merchant verification - STRIP display_name too!
            cat_merchants = merchant_df[
                (merchant_df['CATEGORY'].str.strip() == cat['display_name'].strip()) &
                (merchant_df['AUDIENCE'] == analyzer.audience_name)
                ]

            if not cat_merchants.empty:
                top_merchant = cat_merchants.iloc[0]
                logger.info(
                    f"     - Top Merchant: {top_merchant['MERCHANT']} ({top_merchant['PERC_AUDIENCE'] * 100:.1f}%)")
            else:
                logger.info(f"     - Top Merchant: None found")

    except Exception as e:
        logger.error(f"   ❌ Error in get_custom_categories: {e}")
        import traceback
        traceback.print_exc()
        return None

    # 6. Debug why categories might be excluded
    logger.info("\n6. DEBUGGING CATEGORY EXCLUSIONS:")

    # Check categories that meet thresholds but aren't selected
    high_audience_cats = category_df[category_df['PERC_AUDIENCE'] >= 0.10]

    logger.info(f"   Categories with >=10% audience:")
    for idx, row in high_audience_cats.iterrows():
        cat_name = row['CATEGORY'].strip()

        # Check various exclusion reasons
        reasons = []

        if cat_name not in analyzer.allowed_custom:
            reasons.append("Not in allowed_for_custom")

        if cat_name in analyzer.excluded_custom:
            reasons.append("In excluded_from_custom")

        # Check if it's a fixed category
        for fixed_key in fixed_categories:
            if fixed_key in analyzer.categories:
                fixed_cat_names = analyzer.categories[fixed_key].get('category_names_in_data', [])
                if cat_name in fixed_cat_names:
                    reasons.append(f"Already in fixed category: {fixed_key}")

        # Check merchant threshold
        cat_merchants = merchant_df[
            (merchant_df['CATEGORY'].str.strip() == cat_name) &
            (merchant_df['AUDIENCE'] == analyzer.audience_name)
            ]

        if not cat_merchants.empty:
            max_merchant_pct = cat_merchants['PERC_AUDIENCE'].max()
            if max_merchant_pct < 0.10:
                reasons.append(f"No merchant >=10% (max: {max_merchant_pct * 100:.1f}%)")
        else:
            reasons.append("No merchant data")

        logger.info(f"\n   - {cat_name} ({row['PERC_AUDIENCE'] * 100:.1f}% audience)")
        if reasons:
            for reason in reasons:
                logger.info(f"     ❌ {reason}")
        else:
            logger.info(f"     ✅ Should be selectable")

    # 7. Test analyzing a custom category
    if custom_categories:
        logger.info("\n7. TESTING CUSTOM CATEGORY ANALYSIS:")

        test_cat = custom_categories[0]
        logger.info(f"   Testing category: {test_cat['display_name']}")

        try:
            # Create config for the custom category
            custom_config = analyzer.create_custom_category_config(test_cat['display_name'])

            # Load data for this category - USE STRIPPED NAME!
            category_name_stripped = test_cat['display_name'].strip()

            cat_data_query = f"""
            SELECT * 
            FROM {team_config['view_prefix']}_CATEGORY_INDEXING_ALL_TIME
            WHERE TRIM(CATEGORY) = '{category_name_stripped}'
            AND AUDIENCE = '{analyzer.audience_name}'
            """
            cat_data = query_to_dataframe(cat_data_query)

            subcat_data_query = f"""
            SELECT * 
            FROM {team_config['view_prefix']}_SUBCATEGORY_INDEXING_ALL_TIME
            WHERE TRIM(CATEGORY) = '{category_name_stripped}'
            """
            subcat_data = query_to_dataframe(subcat_data_query)

            merch_data_query = f"""
            SELECT * 
            FROM {team_config['view_prefix']}_MERCHANT_INDEXING_ALL_TIME
            WHERE TRIM(CATEGORY) = '{category_name_stripped}'
            """
            merch_data = query_to_dataframe(merch_data_query)

            # Analyze the category
            logger.info(f"   Calling analyze_category with:")
            logger.info(f"      - category_key: '{test_cat['category_key']}'")
            logger.info(f"      - display_name: '{test_cat['display_name']}'")
            logger.info(f"      - category data rows: {len(cat_data)}")
            logger.info(f"      - subcategory data rows: {len(subcat_data)}")
            logger.info(f"      - merchant data rows: {len(merch_data)}")

            # Check if category_key exists in analyzer.categories
            if test_cat['category_key'] not in analyzer.categories:
                logger.warning(f"   ⚠️  Category key '{test_cat['category_key']}' not found in analyzer.categories")
                logger.info(f"      Available keys: {list(analyzer.categories.keys())[:10]}...")

                # Since it's a custom category, we need to add it to the analyzer's categories
                analyzer.categories[test_cat['category_key']] = custom_config

            results = analyzer.analyze_category(
                category_key=test_cat['category_key'],
                category_df=cat_data,
                subcategory_df=subcat_data,
                merchant_df=merch_data,
                validate=False
            )

            logger.info(f"   ✅ Analysis successful:")
            logger.info(f"      - Insights: {len(results['insights'])}")
            logger.info(f"      - Subcategories: {len(results['subcategory_stats'])}")
            logger.info(f"      - Merchants: {len(results['merchant_stats'][0])}")

            # Test slide generation
            presentation = Presentation()
            slide_gen = CategorySlide(presentation)

            # Mark as emerging if applicable
            results['is_emerging'] = test_cat.get('is_emerging', False)

            presentation = slide_gen.generate(results, team_config)
            presentation = slide_gen.generate_brand_slide(results, team_config)

            output_path = Path(f"test_panthers_custom_{test_cat['category_key']}.pptx")
            presentation.save(output_path)
            logger.info(f"   ✅ Test slides saved to: {output_path.absolute()}")

        except Exception as e:
            logger.error(f"   ❌ Error analyzing custom category: {e}")
            import traceback
            traceback.print_exc()

    return custom_categories


def check_all_teams_comparison_populations():
    """Check comparison populations for all configured teams"""
    logger.info("\n" + "=" * 60)
    logger.info("CHECKING ALL TEAMS COMPARISON POPULATIONS")
    logger.info("=" * 60)

    config_manager = TeamConfigManager()
    teams = config_manager.list_teams()

    for team_key in teams:
        team_config = config_manager.get_team_config(team_key)
        logger.info(f"\n{team_config['team_name']}:")
        logger.info(f"  Config comparison_population: '{team_config['comparison_population']}'")

        # Check what's in the database
        view_name = f"{team_config['view_prefix']}_CATEGORY_INDEXING_ALL_TIME"
        query = f"""
        SELECT DISTINCT COMPARISON_POPULATION
        FROM {view_name}
        WHERE AUDIENCE = '{team_config['team_name']} Fans'
        LIMIT 5
        """

        try:
            df = query_to_dataframe(query)
            if not df.empty:
                logger.info(f"  Database comparison populations:")
                for comp in df['COMPARISON_POPULATION'].unique():
                    logger.info(f"    - '{comp}'")
                    if comp != team_config['comparison_population']:
                        logger.warning(f"    ⚠️  MISMATCH! Config has different value")
            else:
                logger.warning(f"  No data found for {team_config['team_name']} Fans")
        except Exception as e:
            logger.error(f"  Error checking database: {e}")


if __name__ == "__main__":
    # Run the debugging
    try:
        # First check all teams to see the pattern
        check_all_teams_comparison_populations()

        # Then debug Panthers specifically
        analyzer, team_config = debug_panthers_category()

        # NEW: Debug custom categories
        custom_categories = debug_custom_categories(analyzer, team_config)

        logger.info("\n✅ Debug test completed!")

    except Exception as e:
        logger.error(f"\n❌ Debug test failed: {e}")
        import traceback

        traceback.print_exc()