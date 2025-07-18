"""
Test script for tiered custom category selection
Demonstrates the logic with detailed logging
"""

import pandas as pd
import logging
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path if running from scripts folder
sys.path.append(str(Path(__file__).parent.parent))

from data_processors.category_analyzer import CategoryAnalyzer
from data_processors.snowflake_connector import get_connection, query_to_dataframe

# Configure logging to show detailed output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f'custom_category_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    ]
)

logger = logging.getLogger(__name__)


def create_test_data():
    """Create mock data for testing if you don't want to connect to Snowflake"""

    # Mock category data with various audience percentages
    category_data = pd.DataFrame([
        # Established category candidates (>20% audience)
        {'CATEGORY': 'Electronics', 'AUDIENCE': 'Utah Jazz Fans',
         'COMPARISON_POPULATION': 'Local Gen Pop (Excl. Jazz)',
         'PERC_AUDIENCE': 0.35, 'COMPOSITE_INDEX': 450, 'PERC_INDEX': 280},

        {'CATEGORY': 'Home', 'AUDIENCE': 'Utah Jazz Fans',
         'COMPARISON_POPULATION': 'Local Gen Pop (Excl. Jazz)',
         'PERC_AUDIENCE': 0.28, 'COMPOSITE_INDEX': 380, 'PERC_INDEX': 250},

        {'CATEGORY': 'Streaming', 'AUDIENCE': 'Utah Jazz Fans',
         'COMPARISON_POPULATION': 'Local Gen Pop (Excl. Jazz)',
         'PERC_AUDIENCE': 0.42, 'COMPOSITE_INDEX': 520, 'PERC_INDEX': 310},

        {'CATEGORY': 'Gaming', 'AUDIENCE': 'Utah Jazz Fans',
         'COMPARISON_POPULATION': 'Local Gen Pop (Excl. Jazz)',
         'PERC_AUDIENCE': 0.25, 'COMPOSITE_INDEX': 320, 'PERC_INDEX': 220},

        # Emerging category candidates (10-20% audience)
        {'CATEGORY': 'Pets', 'AUDIENCE': 'Utah Jazz Fans',
         'COMPARISON_POPULATION': 'Local Gen Pop (Excl. Jazz)',
         'PERC_AUDIENCE': 0.15, 'COMPOSITE_INDEX': 280, 'PERC_INDEX': 180},

        {'CATEGORY': 'Dating', 'AUDIENCE': 'Utah Jazz Fans',
         'COMPARISON_POPULATION': 'Local Gen Pop (Excl. Jazz)',
         'PERC_AUDIENCE': 0.12, 'COMPOSITE_INDEX': 250, 'PERC_INDEX': 160},

        # Category with low audience (<10%)
        {'CATEGORY': 'Baby', 'AUDIENCE': 'Utah Jazz Fans',
         'COMPARISON_POPULATION': 'Local Gen Pop (Excl. Jazz)',
         'PERC_AUDIENCE': 0.08, 'COMPOSITE_INDEX': 180, 'PERC_INDEX': 140},
    ])

    # Mock merchant data with various penetration levels
    merchant_data = pd.DataFrame([
        # Electronics - has strong merchants (will pass)
        {'CATEGORY': 'Electronics', 'MERCHANT': 'Best Buy', 'AUDIENCE': 'Utah Jazz Fans',
         'PERC_AUDIENCE': 0.18, 'COMPOSITE_INDEX': 320},
        {'CATEGORY': 'Electronics', 'MERCHANT': 'Apple', 'AUDIENCE': 'Utah Jazz Fans',
         'PERC_AUDIENCE': 0.15, 'COMPOSITE_INDEX': 290},

        # Home - has one merchant just above threshold (will pass)
        {'CATEGORY': 'Home', 'MERCHANT': 'Home Depot', 'AUDIENCE': 'Utah Jazz Fans',
         'PERC_AUDIENCE': 0.11, 'COMPOSITE_INDEX': 250},
        {'CATEGORY': 'Home', 'MERCHANT': 'Lowes', 'AUDIENCE': 'Utah Jazz Fans',
         'PERC_AUDIENCE': 0.08, 'COMPOSITE_INDEX': 220},

        # Streaming - all merchants below 10% (will fail established, good for emerging)
        {'CATEGORY': 'Streaming', 'MERCHANT': 'Netflix', 'AUDIENCE': 'Utah Jazz Fans',
         'PERC_AUDIENCE': 0.09, 'COMPOSITE_INDEX': 280},
        {'CATEGORY': 'Streaming', 'MERCHANT': 'Hulu', 'AUDIENCE': 'Utah Jazz Fans',
         'PERC_AUDIENCE': 0.07, 'COMPOSITE_INDEX': 240},
        {'CATEGORY': 'Streaming', 'MERCHANT': 'Disney+', 'AUDIENCE': 'Utah Jazz Fans',
         'PERC_AUDIENCE': 0.06, 'COMPOSITE_INDEX': 210},

        # Gaming - no merchant above 10% (will fail established)
        {'CATEGORY': 'Gaming', 'MERCHANT': 'GameStop', 'AUDIENCE': 'Utah Jazz Fans',
         'PERC_AUDIENCE': 0.08, 'COMPOSITE_INDEX': 200},
        {'CATEGORY': 'Gaming', 'MERCHANT': 'Steam', 'AUDIENCE': 'Utah Jazz Fans',
         'PERC_AUDIENCE': 0.05, 'COMPOSITE_INDEX': 180},

        # Pets - fragmented (good emerging candidate)
        {'CATEGORY': 'Pets', 'MERCHANT': 'Petco', 'AUDIENCE': 'Utah Jazz Fans',
         'PERC_AUDIENCE': 0.04, 'COMPOSITE_INDEX': 150},
        {'CATEGORY': 'Pets', 'MERCHANT': 'PetSmart', 'AUDIENCE': 'Utah Jazz Fans',
         'PERC_AUDIENCE': 0.03, 'COMPOSITE_INDEX': 140},

        # Dating - very fragmented
        {'CATEGORY': 'Dating', 'MERCHANT': 'Match', 'AUDIENCE': 'Utah Jazz Fans',
         'PERC_AUDIENCE': 0.02, 'COMPOSITE_INDEX': 120},
    ])

    return category_data, merchant_data


def test_with_mock_data():
    """Test using mock data"""
    logger.info("=" * 80)
    logger.info("TESTING TIERED CUSTOM CATEGORY SELECTION WITH MOCK DATA")
    logger.info("=" * 80)

    # Initialize analyzer
    analyzer = CategoryAnalyzer(
        team_name="Utah Jazz",
        team_short="Jazz",
        league="NBA"
    )

    # Create mock data
    category_df, merchant_df = create_test_data()

    logger.info(f"\nTest Data Summary:")
    logger.info(f"  - Categories: {len(category_df)}")
    logger.info(f"  - Merchants: {len(merchant_df)}")

    # Test men's team (4 slots: 3 established + 1 emerging)
    logger.info("\n" + "="*60)
    logger.info("TEST 1: Men's Team (3 established + 1 emerging)")
    logger.info("="*60)

    custom_categories = analyzer.get_custom_categories(
        category_df=category_df,
        merchant_df=merchant_df,
        is_womens_team=False,
        existing_categories=['restaurants', 'athleisure', 'finance', 'gambling', 'travel', 'auto']
    )

    logger.info(f"\nRESULTS:")
    for i, cat in enumerate(custom_categories, 1):
        cat_type = "EMERGING" if cat.get('is_emerging') else "ESTABLISHED"
        logger.info(f"\n{i}. {cat['display_name']} ({cat_type})")
        logger.info(f"   - Composite Index: {cat['composite_index']:.1f}")
        logger.info(f"   - Audience %: {cat['audience_pct']*100:.1f}%")
        logger.info(f"   - Category Key: {cat['category_key']}")

    # Test women's team (2 established only)
    logger.info("\n" + "="*60)
    logger.info("TEST 2: Women's Team (2 established only)")
    logger.info("="*60)

    custom_categories_women = analyzer.get_custom_categories(
        category_df=category_df,
        merchant_df=merchant_df,
        is_womens_team=True,
        existing_categories=['restaurants', 'athleisure', 'finance', 'gambling', 'travel', 'auto', 'beauty', 'health']
    )

    logger.info(f"\nRESULTS:")
    for i, cat in enumerate(custom_categories_women, 1):
        cat_type = "EMERGING" if cat.get('is_emerging') else "ESTABLISHED"
        logger.info(f"\n{i}. {cat['display_name']} ({cat_type})")
        logger.info(f"   - Composite Index: {cat['composite_index']:.1f}")
        logger.info(f"   - Audience %: {cat['audience_pct']*100:.1f}%")


def test_with_snowflake(team_code: str = "utah_jazz"):
    """Test using real Snowflake data"""
    logger.info("=" * 80)
    logger.info("TESTING TIERED CUSTOM CATEGORY SELECTION WITH SNOWFLAKE DATA")
    logger.info("=" * 80)

    # Load configuration
    import yaml
    # Navigate from test file location to project root, then to config
    # If we're in data_processors/tests/, go up twice to get to root
    current_file = Path(__file__).resolve()
    if 'tests' in current_file.parts:
        # We're in a tests subdirectory
        project_root = current_file.parent.parent.parent
    else:
        # We're in data_processors directly
        project_root = current_file.parent.parent

    config_path = project_root / 'config' / 'categories.yaml'
    logger.info(f"Looking for config at: {config_path}")

    if not config_path.exists():
        logger.error(f"Config file not found at {config_path}")
        raise FileNotFoundError(f"Could not find categories.yaml at {config_path}")

    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    # Define team configurations
    TEAM_CONFIGS = {
        'utah_jazz': {
            'full_name': 'Utah Jazz',
            'short_name': 'Jazz',
            'league': 'NBA',
            'view_prefix': 'V_UTAH_JAZZ_SIL_',
            'is_womens_team': False
        },
        'dallas_cowboys': {
            'full_name': 'Dallas Cowboys',
            'short_name': 'Cowboys',
            'league': 'NFL',
            'view_prefix': 'V_DALLAS_COWBOYS_',
            'is_womens_team': False
        }
    }

    team_config = TEAM_CONFIGS.get(team_code)

    if not team_config:
        logger.error(f"No config found for team: {team_code}")
        return

    # Initialize analyzer
    analyzer = CategoryAnalyzer(
        team_name=team_config['full_name'],
        team_short=team_config['short_name'],
        league=team_config['league']
    )

    # Load data
    logger.info(f"\nLoading data for {team_config['full_name']}...")

    # Category data
    category_view = f"{team_config['view_prefix']}CATEGORY_INDEXING_ALL_TIME"
    category_query = f"SELECT * FROM {category_view}"
    logger.info(f"  - Querying: {category_view}")
    category_df = query_to_dataframe(category_query)

    # Merchant data
    merchant_view = f"{team_config['view_prefix']}MERCHANT_INDEXING_ALL_TIME"
    merchant_query = f"SELECT * FROM {merchant_view}"
    logger.info(f"  - Querying: {merchant_view}")
    merchant_df = query_to_dataframe(merchant_query)

    logger.info(f"  - Loaded {len(category_df)} category records")
    logger.info(f"  - Loaded {len(merchant_df)} merchant records")

    # Get existing categories from config
    is_womens = team_config.get('is_womens_team', False)
    existing_categories = config['fixed_categories']['womens_teams' if is_womens else 'mens_teams']

    # Run selection
    logger.info(f"\nRunning custom category selection...")
    custom_categories = analyzer.get_custom_categories(
        category_df=category_df,
        merchant_df=merchant_df,
        is_womens_team=is_womens,
        existing_categories=existing_categories
    )

    logger.info(f"\n{'='*60}")
    logger.info(f"FINAL RESULTS FOR {team_config['full_name'].upper()}")
    logger.info(f"{'='*60}")

    for i, cat in enumerate(custom_categories, 1):
        cat_type = "EMERGING" if cat.get('is_emerging') else "ESTABLISHED"
        logger.info(f"\n{i}. {cat['display_name']} ({cat_type})")
        logger.info(f"   - Composite Index: {cat['composite_index']:.1f}")
        logger.info(f"   - Audience %: {cat['audience_pct']*100:.1f}%")
        logger.info(f"   - Perc Index: {cat['perc_index']:.1f}")

        # Show top merchants for this category
        cat_merchants = merchant_df[
            (merchant_df['AUDIENCE'] == analyzer.audience_name) &
            (merchant_df['CATEGORY'] == cat['display_name'])
        ].nlargest(3, 'PERC_AUDIENCE')

        if not cat_merchants.empty:
            logger.info(f"   - Top Merchants:")
            for _, merch in cat_merchants.iterrows():
                logger.info(f"     • {merch['MERCHANT']}: {merch['PERC_AUDIENCE']*100:.1f}%")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Test tiered custom category selection')
    parser.add_argument('--mock', action='store_true', help='Use mock data instead of Snowflake')
    parser.add_argument('--team', default='utah_jazz', help='Team code for Snowflake test')

    args = parser.parse_args()

    if args.mock:
        test_with_mock_data()
    else:
        test_with_snowflake(args.team)

    logger.info("\n" + "="*80)
    logger.info("TEST COMPLETE")
    logger.info("="*80)