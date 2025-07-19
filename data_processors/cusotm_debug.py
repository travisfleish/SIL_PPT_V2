#!/usr/bin/env python3
"""
Debug script to investigate why custom categories aren't being selected
FIXED: Uses COMPARISON_POPULATION instead of COMPARISON_AUDIENCE
"""

import sys
from pathlib import Path
import pandas as pd
import logging
from typing import Dict, List, Any

# Add project root to path
project_root = Path(__file__).parent.parent.parent
if project_root not in sys.path:
    sys.path.insert(0, str(project_root))

# Import required modules
from data_processors.category_analyzer import CategoryAnalyzer
from data_processors.snowflake_connector import query_to_dataframe, test_connection
from utils.team_config_manager import TeamConfigManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def debug_custom_categories(team_key: str = 'carolina_panthers'):
    """Debug why custom categories aren't being selected"""

    logger.info(f"\n{'=' * 60}")
    logger.info(f"DEBUGGING CUSTOM CATEGORIES FOR {team_key.upper()}")
    logger.info("=" * 60)

    # Load team configuration
    config_manager = TeamConfigManager()
    team_config = config_manager.get_team_config(team_key)

    # Initialize CategoryAnalyzer with comparison_population
    analyzer = CategoryAnalyzer(
        team_name=team_config['team_name'],
        team_short=team_config['team_name_short'],
        league=team_config['league'],
        comparison_population=team_config['comparison_population']
    )

    logger.info(f"\nTeam: {team_config['team_name']}")
    logger.info(f"Audience: {analyzer.audience_name}")
    logger.info(f"Comparison: {analyzer.comparison_pop}")

    # Step 1: Load and examine category data
    logger.info("\n1. LOADING CATEGORY DATA:")
    category_query = f"""
    SELECT * FROM {team_config['view_prefix']}_CATEGORY_INDEXING_ALL_TIME
    WHERE AUDIENCE = '{analyzer.audience_name}'
    AND COMPARISON_POPULATION = '{analyzer.comparison_pop}'
    """

    try:
        category_df = query_to_dataframe(category_query)
        logger.info(f"   Found {len(category_df)} category records")

        if not category_df.empty:
            # Show all categories
            logger.info("\n   All categories in database:")
            unique_categories = sorted(category_df['CATEGORY'].unique())
            for cat in unique_categories:
                cat_data = category_df[category_df['CATEGORY'] == cat].iloc[0]
                logger.info(f"     - {cat}: audience={cat_data['PERC_AUDIENCE'] * 100:.1f}%, "
                            f"composite={cat_data['COMPOSITE_INDEX']:.1f}")

    except Exception as e:
        logger.error(f"   Error loading category data: {e}")
        return

    # Step 2: Load merchant data
    logger.info("\n2. LOADING MERCHANT DATA:")
    merchant_query = f"""
    SELECT * FROM {team_config['view_prefix']}_MERCHANT_INDEXING_ALL_TIME
    WHERE AUDIENCE = '{analyzer.audience_name}'
    """

    try:
        merchant_df = query_to_dataframe(merchant_query)
        logger.info(f"   Found {len(merchant_df)} merchant records")

        # Count merchants per category
        if not merchant_df.empty:
            merchant_counts = merchant_df.groupby('CATEGORY').size().sort_values(ascending=False)
            logger.info("\n   Merchant counts by category (top 10):")
            for cat, count in merchant_counts.head(10).items():
                logger.info(f"     - {cat}: {count} merchants")

    except Exception as e:
        logger.error(f"   Error loading merchant data: {e}")
        merchant_df = pd.DataFrame()

    # Step 3: Check configuration
    logger.info("\n3. CHECKING CONFIGURATION:")
    logger.info(f"   Allowed for custom: {len(analyzer.allowed_custom)} categories")
    if analyzer.allowed_custom:
        for cat in analyzer.allowed_custom[:10]:
            logger.info(f"     - {cat}")

    logger.info(f"\n   Excluded from custom: {len(analyzer.excluded_custom)} categories")
    if analyzer.excluded_custom:
        for cat in analyzer.excluded_custom[:5]:
            logger.info(f"     - {cat}")

    # Step 4: Check fixed categories
    is_womens_team = any(indicator in team_config['team_name'].lower()
                         for indicator in ["women's", "ladies", "wnba", "nwsl"])

    fixed_categories = ['restaurants', 'athleisure', 'finance', 'gambling', 'travel', 'auto']
    if is_womens_team:
        fixed_categories.extend(['beauty', 'health'])

    logger.info(f"\n4. FIXED CATEGORIES ({len(fixed_categories)}):")
    for cat in fixed_categories:
        logger.info(f"   - {cat}")

    # Step 5: Call get_custom_categories and debug
    logger.info("\n5. CALLING GET_CUSTOM_CATEGORIES:")

    try:
        custom_categories = analyzer.get_custom_categories(
            category_df=category_df,
            merchant_df=merchant_df,
            is_womens_team=is_womens_team,
            existing_categories=fixed_categories
        )

        logger.info(f"\n   Selected {len(custom_categories)} custom categories:")
        for i, cat in enumerate(custom_categories):
            emerging_tag = " [EMERGING]" if cat.get('is_emerging', False) else " [ESTABLISHED]"
            logger.info(f"   {i + 1}. {cat['display_name']}{emerging_tag}")
            logger.info(f"      - Audience: {cat.get('audience_pct', 0) * 100:.1f}%")
            logger.info(f"      - Composite: {cat.get('composite_index', 0):.1f}")

    except Exception as e:
        logger.error(f"   Error in get_custom_categories: {e}")
        import traceback
        traceback.print_exc()

    # Step 6: Debug filters and thresholds
    logger.info("\n6. CHECKING THRESHOLDS:")

    # Check how many categories meet various thresholds
    if not category_df.empty:
        # Get categories already in fixed list
        fixed_category_names = []
        for cat_key in fixed_categories:
            if cat_key in analyzer.categories:
                fixed_category_names.extend(analyzer.categories[cat_key].get('category_names_in_data', []))

        # Filter out fixed categories, excluded, and not in allowed
        available_df = category_df[
            (~category_df['CATEGORY'].isin(fixed_category_names)) &
            (category_df['CATEGORY'].isin(analyzer.allowed_custom)) &
            (~category_df['CATEGORY'].isin(analyzer.excluded_custom))
            ].copy()

        logger.info(f"\n   Total categories: {len(category_df)}")
        logger.info(f"   After removing fixed: {len(category_df[~category_df['CATEGORY'].isin(fixed_category_names)])}")
        logger.info(
            f"   After filtering allowed_custom: {len(category_df[category_df['CATEGORY'].isin(analyzer.allowed_custom)])}")
        logger.info(f"   After all filters: {len(available_df)}")

        # Check audience thresholds
        logger.info("\n   Available categories by audience threshold:")
        for threshold in [0.40, 0.30, 0.20, 0.10, 0.05]:
            qualifying = available_df[available_df['PERC_AUDIENCE'] >= threshold]
            logger.info(f"   >= {threshold * 100:2.0f}% audience: {len(qualifying)} categories")
            if len(qualifying) > 0:
                examples = qualifying.nlargest(3, 'COMPOSITE_INDEX')['CATEGORY'].tolist()
                logger.info(f"      Examples: {', '.join(examples)}")

        # Show top available categories
        logger.info("\n   Top 10 available categories by composite index:")
        top_available = available_df.nlargest(10, 'COMPOSITE_INDEX')
        for _, row in top_available.iterrows():
            logger.info(f"     - {row['CATEGORY']}: composite={row['COMPOSITE_INDEX']:.1f}, "
                        f"audience={row['PERC_AUDIENCE'] * 100:.1f}%")

    # Step 7: Check merchant verification
    logger.info("\n7. CHECKING MERCHANT VERIFICATION:")

    if not available_df.empty and not merchant_df.empty:
        # For each potential custom category, check merchant threshold
        logger.info("\n   Checking merchant thresholds (10% audience):")

        for _, cat_row in available_df.head(10).iterrows():
            cat_name = cat_row['CATEGORY']

            # Check if merchant threshold is met
            meets_threshold = analyzer._verify_merchant_threshold(cat_name, merchant_df, 0.10)

            if meets_threshold:
                logger.info(f"   ✓ {cat_name} - has merchant(s) above 10% threshold")
            else:
                # Find max merchant audience for this category
                cat_merchants = merchant_df[
                    (merchant_df['AUDIENCE'] == analyzer.audience_name) &
                    (merchant_df['CATEGORY'].str.strip() == cat_name.strip())
                    ]
                if not cat_merchants.empty:
                    max_merch_aud = cat_merchants['PERC_AUDIENCE'].max()
                    logger.info(f"   ✗ {cat_name} - max merchant audience: {max_merch_aud * 100:.1f}%")
                else:
                    logger.info(f"   ✗ {cat_name} - no merchant data found")

    logger.info("\n" + "=" * 60)
    logger.info("DEBUG COMPLETE")
    logger.info("=" * 60)


def quick_fix_test(team_key: str = 'carolina_panthers'):
    """Quick test to see if lowering thresholds would help"""

    logger.info(f"\n{'=' * 60}")
    logger.info("TESTING WITH LOWER THRESHOLDS")
    logger.info("=" * 60)

    config_manager = TeamConfigManager()
    team_config = config_manager.get_team_config(team_key)

    # Create analyzer with lower thresholds
    analyzer = CategoryAnalyzer(
        team_name=team_config['team_name'],
        team_short=team_config['team_name_short'],
        league=team_config['league'],
        comparison_population=team_config['comparison_population']
    )

    # Override thresholds temporarily
    original_config = analyzer.config['custom_category_config']['mens_teams']['established_categories'].copy()

    # Try lower thresholds
    analyzer.config['custom_category_config']['mens_teams']['established_categories']['min_audience_pct'] = 0.10
    analyzer.config['custom_category_config']['mens_teams']['established_categories'][
        'min_merchant_audience_pct'] = 0.05

    logger.info("\nTesting with:")
    logger.info("  - Category threshold: 10% (was 20%)")
    logger.info("  - Merchant threshold: 5% (was 10%)")

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

        fixed_categories = ['restaurants', 'athleisure', 'finance', 'gambling', 'travel', 'auto']

        custom_categories = analyzer.get_custom_categories(
            category_df=category_df,
            merchant_df=merchant_df,
            is_womens_team=False,
            existing_categories=fixed_categories
        )

        logger.info(f"\nWith lower thresholds, found {len(custom_categories)} custom categories:")
        for cat in custom_categories:
            logger.info(f"  - {cat['display_name']} ({'EMERGING' if cat.get('is_emerging') else 'ESTABLISHED'})")

    except Exception as e:
        logger.error(f"Error: {e}")

    # Restore original config
    analyzer.config['custom_category_config']['mens_teams']['established_categories'] = original_config


if __name__ == "__main__":
    # Test connection
    if not test_connection():
        logger.error("Cannot connect to Snowflake!")
        sys.exit(1)

    # Debug Carolina Panthers
    debug_custom_categories('carolina_panthers')

    # Test with lower thresholds
    quick_fix_test('carolina_panthers')

    # Compare with Utah Jazz
    logger.info("\n" + "=" * 80)
    logger.info("COMPARING WITH UTAH JAZZ")
    logger.info("=" * 80)
    debug_custom_categories('utah_jazz')

    logger.info("\n✅ Debug script completed!")