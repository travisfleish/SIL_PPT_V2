#!/usr/bin/env python3
"""
Test script to validate that custom categories with trailing spaces now work correctly
Tests both data retrieval and slide generation
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
from data_processors.snowflake_connector import query_to_dataframe
from data_processors.category_analyzer import CategoryAnalyzer
from report_builder.pptx_builder import PowerPointBuilder
from utils.team_config_manager import TeamConfigManager

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_custom_category_data_retrieval():
    """Test that we can retrieve data for custom categories with trailing spaces"""
    logger.info("=" * 60)
    logger.info("TESTING CUSTOM CATEGORY DATA RETRIEVAL")
    logger.info("=" * 60)

    # Test teams
    test_teams = ['carolina_panthers', 'utah_jazz']

    for team_key in test_teams:
        logger.info(f"\nTesting {team_key}...")

        # Get team config
        config_manager = TeamConfigManager()
        team_config = config_manager.get_team_config(team_key)
        view_prefix = team_config['view_prefix']

        # Get custom categories
        category_query = f"SELECT * FROM {view_prefix}_CATEGORY_INDEXING_ALL_TIME"
        category_df = query_to_dataframe(category_query)

        merchant_query = f"SELECT * FROM {view_prefix}_MERCHANT_INDEXING_ALL_TIME"
        merchant_df = query_to_dataframe(merchant_query)

        # Initialize analyzer
        analyzer = CategoryAnalyzer(
            team_name=team_config['team_name'],
            team_short=team_config['team_name_short'],
            league=team_config['league'],
            comparison_population=team_config['comparison_population']
        )

        # Get custom categories
        custom_categories = analyzer.get_custom_categories(
            category_df=category_df,
            merchant_df=merchant_df,
            is_womens_team=False,
            existing_categories=['restaurants', 'athleisure', 'finance', 'gambling', 'travel', 'auto']
        )

        logger.info(f"Found {len(custom_categories)} custom categories:")

        # Test each custom category
        for i, cat in enumerate(custom_categories[:4]):
            cat_name = cat['display_name']
            logger.info(f"\n  {i + 1}. Testing '{cat_name}' (has_trailing_space: {cat_name != cat_name.strip()})")

            # Test with original name (may have spaces)
            original_query = f"""
                SELECT COUNT(*) as row_count, SUM(PERC_AUDIENCE) as total_audience
                FROM {view_prefix}_CATEGORY_INDEXING_ALL_TIME 
                WHERE TRIM(CATEGORY) = '{cat_name}'
            """
            original_result = query_to_dataframe(original_query)
            # Handle uppercase column names from Snowflake
            row_count_col = 'ROW_COUNT' if 'ROW_COUNT' in original_result.columns else 'row_count'
            logger.info(f"     Original name query: {original_result[row_count_col].iloc[0]} rows")

            # Test with stripped name
            stripped_query = f"""
                SELECT COUNT(*) as row_count, SUM(PERC_AUDIENCE) as total_audience
                FROM {view_prefix}_CATEGORY_INDEXING_ALL_TIME 
                WHERE TRIM(CATEGORY) = '{cat_name.strip()}'
            """
            stripped_result = query_to_dataframe(stripped_query)
            logger.info(f"     Stripped name query: {stripped_result[row_count_col].iloc[0]} rows")

            # Test merchant data
            merchant_test_query = f"""
                SELECT COUNT(*) as merchant_count
                FROM {view_prefix}_MERCHANT_INDEXING_ALL_TIME 
                WHERE TRIM(CATEGORY) = '{cat_name.strip()}'
                AND AUDIENCE = '{analyzer.audience_name}'
            """
            merchant_result = query_to_dataframe(merchant_test_query)
            merchant_count_col = 'MERCHANT_COUNT' if 'MERCHANT_COUNT' in merchant_result.columns else 'merchant_count'
            logger.info(f"     Merchant data: {merchant_result[merchant_count_col].iloc[0]} merchants")


def test_slide_generation():
    """Test that slides are generated correctly for custom categories"""
    logger.info("\n" + "=" * 60)
    logger.info("TESTING SLIDE GENERATION")
    logger.info("=" * 60)

    # Test Carolina Panthers specifically since it had the issue
    team_key = 'carolina_panthers'

    logger.info(f"\nCreating minimal test presentation for {team_key}...")

    try:
        # Create builder
        builder = PowerPointBuilder(team_key)

        # Get custom categories
        category_query = f"SELECT * FROM {builder.view_prefix}_CATEGORY_INDEXING_ALL_TIME"
        category_df = query_to_dataframe(category_query)

        merchant_query = f"SELECT * FROM {builder.view_prefix}_MERCHANT_INDEXING_ALL_TIME"
        merchant_df = query_to_dataframe(merchant_query)

        # Get custom categories
        custom_categories = builder.category_analyzer.get_custom_categories(
            category_df=category_df,
            merchant_df=merchant_df,
            is_womens_team=False,
            existing_categories=['restaurants', 'athleisure', 'finance', 'gambling', 'travel', 'auto']
        )

        # Test creating slides for first 2 custom categories
        logger.info("\nTesting slide creation for custom categories:")

        for i, custom_cat in enumerate(custom_categories[:2]):
            cat_name = custom_cat['display_name']
            logger.info(f"\n  Creating slide for: '{cat_name}'")

            # This simulates what happens in _create_custom_category_slides
            category_name = custom_cat['display_name'].strip()  # This is the fix

            # Verify data exists with stripped name
            test_query = f"""
                SELECT COUNT(*) as count, 
                       MAX(PERC_AUDIENCE) as max_audience,
                       MAX(COMPOSITE_INDEX) as max_index
                FROM {builder.view_prefix}_CATEGORY_INDEXING_ALL_TIME 
                WHERE TRIM(CATEGORY) = '{category_name}'
            """
            result = query_to_dataframe(test_query)

            # Handle uppercase column names
            count_col = 'COUNT' if 'COUNT' in result.columns else 'count'
            max_aud_col = 'MAX_AUDIENCE' if 'MAX_AUDIENCE' in result.columns else 'max_audience'
            max_idx_col = 'MAX_INDEX' if 'MAX_INDEX' in result.columns else 'max_index'

            logger.info(f"    Data check: {result[count_col].iloc[0]} rows, "
                        f"max_audience: {result[max_aud_col].iloc[0]:.3f}, "
                        f"max_index: {result[max_idx_col].iloc[0]:.1f}")

            # Test the actual slide creation method
            try:
                builder._create_category_slide(
                    category_key=category_name,
                    is_custom=True,
                    custom_cat_info=custom_cat
                )
                logger.info(f"    ✓ Slide created successfully")
            except Exception as e:
                logger.error(f"    ✗ Failed to create slide: {str(e)}")

        logger.info(f"\nSlides created: {len(builder.slides_created)}")

    except Exception as e:
        logger.error(f"Error in slide generation test: {str(e)}")


def test_full_report_generation():
    """Test generating a full report to ensure fix works end-to-end"""
    logger.info("\n" + "=" * 60)
    logger.info("TESTING FULL REPORT GENERATION")
    logger.info("=" * 60)

    team_key = 'carolina_panthers'

    logger.info(f"\nGenerating test report for {team_key}...")
    logger.info("This will create a complete PowerPoint to verify all custom categories work")

    try:
        from report_builder.pptx_builder import build_report

        # Generate report with custom categories
        output_path = build_report(
            team_key=team_key,
            include_custom_categories=True,
            custom_category_count=4
        )

        logger.info(f"\n✓ Report generated successfully: {output_path}")
        logger.info(f"  Please check the PowerPoint to verify custom categories have data")

        # Read the build summary
        summary_path = output_path.parent / 'build_summary.txt'
        if summary_path.exists():
            logger.info("\nBuild Summary:")
            with open(summary_path, 'r') as f:
                for line in f:
                    if 'Category Summary' in line or 'Fixed Categories' in line or 'Custom' in line:
                        logger.info(f"  {line.strip()}")

    except Exception as e:
        logger.error(f"Error generating report: {str(e)}")


def main():
    """Run all tests"""
    logger.info("Starting custom category fix validation tests...")

    # Test 1: Data retrieval
    test_custom_category_data_retrieval()

    # Test 2: Slide generation
    test_slide_generation()

    # Test 3: Full report (optional - comment out if you just want quick tests)
    user_input = input("\nGenerate full test report? This will create a complete PowerPoint. (y/n): ")
    if user_input.lower() == 'y':
        test_full_report_generation()

    logger.info("\n" + "=" * 60)
    logger.info("TEST COMPLETE")
    logger.info("=" * 60)
    logger.info("\nIf all tests passed, the fix is working correctly!")
    logger.info("Custom categories with trailing spaces should now display data properly.")


if __name__ == "__main__":
    main()