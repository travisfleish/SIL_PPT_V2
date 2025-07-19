#!/usr/bin/env python3
"""
Test script to verify MerchantRanker functionality for multiple teams
Tests: Utah Jazz (NBA) and Carolina Panthers (NFL)
"""

import os
import sys
from pathlib import Path
import pandas as pd
from datetime import datetime
import logging
from dotenv import load_dotenv
import yaml

# Add the parent directory to sys.path to import project modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from data_processors.merchant_ranker import MerchantRanker
from data_processors.snowflake_connector import get_connection

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


class MerchantRankerTester:
    """Test MerchantRanker functionality for multiple teams"""

    def __init__(self, config_path: Path = None):
        """Initialize the tester with team config"""
        self.connection = None

        # Load team configuration
        if config_path is None:
            # Go up two levels from tests folder to project root, then to config
            config_path = Path(__file__).parent.parent.parent / 'config' / 'team_config.yaml'

            # If that doesn't exist, try from current working directory
            if not config_path.exists():
                config_path = Path.cwd() / 'config' / 'team_config.yaml'

        if not config_path.exists():
            raise FileNotFoundError(f"Could not find team_config.yaml")

        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        self.teams = self.config['teams']

    def connect(self):
        """Establish Snowflake connection"""
        try:
            self.connection = get_connection()
            logger.info("✅ Connected to Snowflake")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to connect to Snowflake: {e}")
            return False

    def test_merchant_ranker(self, team_key: str):
        """Test MerchantRanker functionality for a specific team"""
        team_config = self.teams[team_key]
        team_name = team_config['team_name']

        logger.info(f"\n{'=' * 60}")
        logger.info(f"Testing MerchantRanker for: {team_name}")
        logger.info(f"{'=' * 60}")

        try:
            # Initialize MerchantRanker
            ranker = MerchantRanker(
                team_view_prefix=team_config['view_prefix'],
                comparison_population=team_config['comparison_population']
            )

            logger.info(f"✅ MerchantRanker initialized")
            logger.info(f"   View prefix: {team_config['view_prefix']}")
            logger.info(f"   Comparison: {team_config['comparison_population']}")

            # Test 1: Get top communities
            logger.info(f"\n📊 Test 1: Getting top communities...")
            try:
                communities_df = ranker.get_top_communities(
                    min_audience_pct=0.20,
                    top_n=5
                )

                if not communities_df.empty:
                    logger.info(f"✅ Found {len(communities_df)} communities")
                    for idx, row in communities_df.iterrows():
                        logger.info(f"   {idx + 1}. {row['COMMUNITY']} - "
                                    f"Index: {row['COMPOSITE_INDEX']:.1f}, "
                                    f"Audience: {row['PERC_AUDIENCE'] * 100:.1f}%")
                else:
                    logger.warning("⚠️  No communities found")

            except Exception as e:
                logger.error(f"❌ Failed to get communities: {str(e)}")
                communities_df = pd.DataFrame()

            # Test 2: Get top merchants for communities
            if not communities_df.empty:
                logger.info(f"\n📊 Test 2: Getting top merchants for communities...")
                try:
                    top_communities = communities_df['COMMUNITY'].head(3).tolist()
                    merchants_df = ranker.get_top_merchants_for_communities(
                        communities=top_communities,
                        top_n_per_community=2
                    )

                    if not merchants_df.empty:
                        logger.info(f"✅ Found {len(merchants_df)} merchant-community pairs")

                        # Check if standardization worked
                        if 'MERCHANT_ORIGINAL' in merchants_df.columns:
                            logger.info("✅ Merchant name standardization applied")

                            # Show some examples
                            standardized = merchants_df[
                                merchants_df['MERCHANT'] != merchants_df['MERCHANT_ORIGINAL']
                                ].head(3)

                            if not standardized.empty:
                                logger.info("   Examples of standardized names:")
                                for _, row in standardized.iterrows():
                                    logger.info(f"     '{row['MERCHANT_ORIGINAL']}' → '{row['MERCHANT']}'")

                        # Group by community to show merchants
                        for community in top_communities[:2]:
                            comm_merchants = merchants_df[merchants_df['COMMUNITY'] == community]
                            if not comm_merchants.empty:
                                logger.info(f"\n   {community}:")
                                for _, row in comm_merchants.iterrows():
                                    logger.info(f"     - {row['MERCHANT']} "
                                                f"(Category: {row['CATEGORY']}, "
                                                f"Audience: {row['PERC_AUDIENCE'] * 100:.1f}%)")
                    else:
                        logger.warning("⚠️  No merchants found")

                except Exception as e:
                    logger.error(f"❌ Failed to get merchants: {str(e)}")

            # Test 3: Get fan wheel data
            logger.info(f"\n📊 Test 3: Getting fan wheel data...")
            try:
                fan_wheel_df = ranker.get_fan_wheel_data(
                    min_audience_pct=0.20,
                    top_n_communities=5
                )

                if not fan_wheel_df.empty:
                    logger.info(f"✅ Generated fan wheel data for {len(fan_wheel_df)} communities")
                    logger.info("   Sample behaviors:")
                    for idx, row in fan_wheel_df.head(3).iterrows():
                        logger.info(f"     - {row['COMMUNITY']}: {row['behavior'].replace(chr(10), ' ')}")
                else:
                    logger.warning("⚠️  No fan wheel data generated")

            except Exception as e:
                logger.error(f"❌ Failed to get fan wheel data: {str(e)}")

            # Test 4: Get community index data for chart
            logger.info(f"\n📊 Test 4: Getting community index chart data...")
            try:
                chart_df = ranker.get_community_index_data(
                    min_audience_pct=0.20,
                    top_n=5
                )

                if not chart_df.empty:
                    logger.info(f"✅ Generated chart data for {len(chart_df)} communities")
                    logger.info(f"   Top community: {chart_df.iloc[0]['Community']} "
                                f"(Index: {chart_df.iloc[0]['Audience_Index']:.1f})")
                else:
                    logger.warning("⚠️  No chart data generated")

            except Exception as e:
                logger.error(f"❌ Failed to get chart data: {str(e)}")

            # Test 5: Test category-specific merchant ranking
            logger.info(f"\n📊 Test 5: Testing category-specific merchant ranking...")
            try:
                restaurant_merchants = ranker.get_standardized_merchant_ranking(
                    category_filter="Restaurant",
                    top_n=5
                )

                if not restaurant_merchants.empty:
                    logger.info(f"✅ Found {len(restaurant_merchants)} restaurant merchants")
                    logger.info("   Top restaurants:")
                    for idx, row in restaurant_merchants.head(3).iterrows():
                        logger.info(f"     - {row['MERCHANT']} "
                                    f"(Audience: {row['PERC_AUDIENCE'] * 100:.1f}%)")
                else:
                    logger.warning("⚠️  No restaurant merchants found")

            except Exception as e:
                logger.error(f"❌ Failed to get restaurant merchants: {str(e)}")

            return True

        except Exception as e:
            logger.error(f"❌ MerchantRanker initialization failed: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return False

    def test_specific_teams(self, team_keys: list = None):
        """Test specific teams from the config"""
        # Default to testing Jazz and Panthers if not specified
        if team_keys is None:
            team_keys = ['utah_jazz', 'carolina_panthers']

        # Validate team keys
        for team_key in team_keys:
            if team_key not in self.teams:
                logger.error(f"❌ Team '{team_key}' not found in config!")
                logger.info(f"   Available teams: {', '.join(self.teams.keys())}")
                return

        # Connect to Snowflake
        if not self.connect():
            return

        # Test each team
        results = {}
        for team_key in team_keys:
            success = self.test_merchant_ranker(team_key)
            results[team_key] = success

        # Summary
        logger.info(f"\n{'=' * 60}")
        logger.info("SUMMARY")
        logger.info(f"{'=' * 60}")

        for team_key, success in results.items():
            team_name = self.teams[team_key]['team_name']
            status = "✅ PASS" if success else "❌ FAIL"
            logger.info(f"{status} {team_name}")

        # Close connection
        if self.connection:
            self.connection.close()
            logger.info("\n✅ Snowflake connection closed")


def main():
    """Main test function"""
    import argparse

    parser = argparse.ArgumentParser(description='Test MerchantRanker for multiple teams')
    parser.add_argument('--teams', nargs='+', help='Specific team keys to test (e.g., utah_jazz carolina_panthers)')
    parser.add_argument('--all', action='store_true', help='Test all teams in config')

    args = parser.parse_args()

    logger.info("Starting MerchantRanker test...")
    logger.info(f"Timestamp: {datetime.now().isoformat()}")

    tester = MerchantRankerTester()

    if args.all:
        teams_to_test = list(tester.teams.keys())
        tester.test_specific_teams(teams_to_test)
    else:
        # Default to Jazz and Panthers, or use specified teams
        teams_to_test = args.teams if args.teams else ['utah_jazz', 'carolina_panthers']
        tester.test_specific_teams(teams_to_test)

    logger.info("\nTest complete!")


if __name__ == "__main__":
    main()