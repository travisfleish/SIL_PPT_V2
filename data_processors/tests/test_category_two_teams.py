#!/usr/bin/env python3
"""
Test script to verify CategoryAnalyzer can find data for multiple teams
Tests teams defined in config/team_config.yaml
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

from data_processors.category_analyzer import CategoryAnalyzer
from data_processors.snowflake_connector import get_connection

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


class TeamDataTester:
    """Test data availability for multiple teams using team_config.yaml"""

    def __init__(self, config_path: Path = None):
        """Initialize the tester with Snowflake connection and team config"""
        self.connection = None

        # Load team configuration
        if config_path is None:
            # Go up two levels from tests folder to project root, then to config
            config_path = Path(__file__).parent.parent.parent / 'config' / 'team_config.yaml'

            # If that doesn't exist, try from current working directory
            if not config_path.exists():
                config_path = Path.cwd() / 'config' / 'team_config.yaml'

        if not config_path.exists():
            raise FileNotFoundError(f"Could not find team_config.yaml. Looked in:\n"
                                    f"  - {Path(__file__).parent.parent.parent / 'config' / 'team_config.yaml'}\n"
                                    f"  - {Path.cwd() / 'config' / 'team_config.yaml'}")

        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        self.teams = self.config['teams']
        self.view_patterns = self.config['view_patterns']

    def connect(self):
        """Establish Snowflake connection"""
        try:
            self.connection = get_connection()
            logger.info("✅ Connected to Snowflake")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to connect to Snowflake: {e}")
            return False

    def test_team_views(self, team_key: str):
        """Test if views exist for a specific team"""
        team_config = self.teams[team_key]
        team_name = team_config['team_name']

        logger.info(f"\n{'=' * 60}")
        logger.info(f"Testing data availability for: {team_name}")
        logger.info(f"{'=' * 60}")
        logger.info(f"View prefix: {team_config['view_prefix']}")
        logger.info(f"Audience: {team_config['audience_name']}")
        logger.info(f"Comparison: {team_config['comparison_population']}")

        # Test key view types
        view_tests = {
            'category_all_time': 'CATEGORY ALL TIME',
            'subcategory_all_time': 'SUBCATEGORY ALL TIME',
            'merchant_all_time': 'MERCHANT ALL TIME',
            'demographics': 'DEMOGRAPHICS',
            'community_all_time': 'COMMUNITY ALL TIME',
            'category_last_full_year': 'CATEGORY LAST YEAR',
            'subcategory_last_full_year': 'SUBCATEGORY LAST YEAR',
            'merchant_last_full_year': 'MERCHANT LAST YEAR'
        }

        found_views = {}
        missing_views = []

        for pattern_key, display_name in view_tests.items():
            # Generate view name from pattern
            view_pattern = self.view_patterns.get(pattern_key)
            if not view_pattern:
                logger.warning(f"  ⚠️  No pattern defined for {pattern_key}")
                continue

            view_name = view_pattern.format(prefix=team_config['view_prefix'])

            query = f"""
            SELECT COUNT(*) as row_count
            FROM SIL__TB_OTT_TEST.SC_TWINBRAINAI.{view_name}
            LIMIT 1
            """

            try:
                result = pd.read_sql(query, self.connection)
                row_count = result['ROW_COUNT'].iloc[0]
                found_views[pattern_key] = {
                    'name': view_name,
                    'rows': row_count,
                    'display': display_name
                }
                logger.info(f"  ✅ {display_name}: Found ({row_count:,} rows)")
            except Exception as e:
                missing_views.append(pattern_key)
                error_msg = str(e).split('\n')[0]  # Get first line of error
                logger.warning(f"  ❌ {display_name}: Not found")
                logger.debug(f"     View name tried: {view_name}")

        return {
            'team': team_name,
            'team_key': team_key,
            'found': found_views,
            'missing': missing_views,
            'success': len(missing_views) == 0
        }

    def test_category_analyzer(self, team_key: str):
        """Test CategoryAnalyzer initialization and basic functionality"""
        team_config = self.teams[team_key]
        logger.info(f"\n📊 Testing CategoryAnalyzer for {team_config['team_name']}")

        try:
            # Initialize CategoryAnalyzer
            analyzer = CategoryAnalyzer(
                team_name=team_config['team_name'],
                team_short=team_config['team_name_short'],
                league=team_config['league'],
                comparison_population=team_config['comparison_population']
            )

            logger.info(f"  ✅ CategoryAnalyzer initialized successfully")
            logger.info(f"     - Audience: {analyzer.audience_name}")
            logger.info(f"     - Comparison: {analyzer.comparison_pop}")
            logger.info(f"     - League fans: {analyzer.league_fans}")

            # Test loading a sample category data
            view_name = self.view_patterns['category_all_time'].format(
                prefix=team_config['view_prefix']
            )

            # First check what audiences exist
            audience_query = f"""
            SELECT DISTINCT AUDIENCE
            FROM SIL__TB_OTT_TEST.SC_TWINBRAINAI.{view_name}
            LIMIT 10
            """

            audiences_df = pd.read_sql(audience_query, self.connection)
            logger.info(f"  📋 Available audiences: {', '.join(audiences_df['AUDIENCE'].tolist())}")

            # Now query for the team's audience
            query = f"""
            SELECT *
            FROM SIL__TB_OTT_TEST.SC_TWINBRAINAI.{view_name}
            WHERE AUDIENCE = '{team_config['audience_name']}'
            LIMIT 5
            """

            sample_data = pd.read_sql(query, self.connection)

            if not sample_data.empty:
                logger.info(f"  ✅ Found {len(sample_data)} sample category records")
                categories = sample_data['CATEGORY'].unique()[:5]
                logger.info(f"     Sample categories: {', '.join(categories)}")

                # Show a sample row
                row = sample_data.iloc[0]
                logger.info(f"     Sample metrics:")
                logger.info(f"       - Category: {row['CATEGORY']}")
                logger.info(f"       - PERC_AUDIENCE: {row.get('PERC_AUDIENCE', 'N/A')}")
                logger.info(f"       - COMPOSITE_INDEX: {row.get('COMPOSITE_INDEX', 'N/A')}")
            else:
                logger.warning(f"  ⚠️  No data found for audience: {team_config['audience_name']}")

            return True

        except Exception as e:
            logger.error(f"  ❌ CategoryAnalyzer test failed: {e}")
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
        results = []
        for team_key in team_keys:
            # Test views
            view_result = self.test_team_views(team_key)
            results.append(view_result)

            # Test CategoryAnalyzer if at least some views exist
            if len(view_result['found']) > 0:
                self.test_category_analyzer(team_key)
            else:
                logger.warning(f"⚠️  Skipping CategoryAnalyzer test - no views found")

        # Summary
        self._print_summary(results)

        # Close connection
        if self.connection:
            self.connection.close()
            logger.info("\n✅ Snowflake connection closed")

    def test_all_teams(self):
        """Test all teams defined in the config"""
        team_keys = list(self.teams.keys())
        logger.info(f"Testing all {len(team_keys)} teams from config...")
        self.test_specific_teams(team_keys)

    def _print_summary(self, results):
        """Print a summary of test results"""
        logger.info(f"\n{'=' * 60}")
        logger.info("SUMMARY")
        logger.info(f"{'=' * 60}")

        for result in results:
            status = "✅ PASS" if result['success'] else "⚠️  PARTIAL" if result['found'] else "❌ FAIL"
            logger.info(f"{status} {result['team']}: "
                        f"{len(result['found'])} views found, "
                        f"{len(result['missing'])} missing")

            if result['found']:
                logger.info(f"     Found: {', '.join([v['display'] for v in result['found'].values()])}")

            if result['missing']:
                missing_names = [
                    self.view_patterns.get(m, m).format(prefix=self.teams[result['team_key']]['view_prefix'])
                    for m in result['missing']]
                logger.info(f"     Missing views:")
                for view_name in missing_names:
                    logger.info(f"       - {view_name}")


def main():
    """Main test function"""
    import argparse

    parser = argparse.ArgumentParser(description='Test CategoryAnalyzer for multiple teams')
    parser.add_argument('--teams', nargs='+', help='Specific team keys to test (e.g., utah_jazz carolina_panthers)')
    parser.add_argument('--all', action='store_true', help='Test all teams in config')

    args = parser.parse_args()

    logger.info("Starting CategoryAnalyzer multi-team test...")
    logger.info(f"Timestamp: {datetime.now().isoformat()}")

    tester = TeamDataTester()

    if args.all:
        tester.test_all_teams()
    else:
        # Default to Jazz and Panthers, or use specified teams
        teams_to_test = args.teams if args.teams else ['utah_jazz', 'carolina_panthers']
        tester.test_specific_teams(teams_to_test)

    logger.info("\nTest complete!")


if __name__ == "__main__":
    main()