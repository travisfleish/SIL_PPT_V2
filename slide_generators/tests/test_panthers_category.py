#!/usr/bin/env python3
"""
Debug test script for Carolina Panthers category slides
Tests the CategoryAnalyzer and CategorySlide with real data to diagnose the comparison population issue
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

        logger.info("\n✅ Debug test completed!")

    except Exception as e:
        logger.error(f"\n❌ Debug test failed: {e}")
        import traceback

        traceback.print_exc()