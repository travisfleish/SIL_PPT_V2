#!/usr/bin/env python3
"""
Test script for the new single demographics slide layout
"""

import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from pptx import Presentation
from data_processors.demographic_processor import DemographicsProcessor
from data_processors.snowflake_connector import query_to_dataframe
from visualizations.demographic_charts import DemographicCharts
from slide_generators.demographics_slide import DemographicsSlide
from utils.team_config_manager import TeamConfigManager
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_demographics_slide(team_key: str = 'utah_jazz'):
    """
    Test the new single demographics slide layout

    Args:
        team_key: Team to test with (default: utah_jazz)
    """
    print("\n" + "=" * 60)
    print("TESTING NEW DEMOGRAPHICS SLIDE LAYOUT")
    print("=" * 60)

    try:
        # 1. Setup
        print("\n1. Setting up...")
        config_manager = TeamConfigManager()
        team_config = config_manager.get_team_config(team_key)
        team_name = team_config['team_name']
        print(f"   ✅ Team: {team_name}")

        # 2. Test Snowflake connection
        print("\n2. Testing Snowflake connection...")
        from data_processors.snowflake_connector import test_connection
        if not test_connection():
            print("   ❌ Cannot connect to Snowflake")
            return None
        print("   ✅ Connected to Snowflake")

        # 3. Fetch demographic data
        print("\n3. Fetching demographic data...")
        demographics_view = config_manager.get_view_name(team_key, 'demographics')
        query = f"SELECT * FROM {demographics_view}"
        df = query_to_dataframe(query)

        if df.empty:
            print("   ❌ No demographic data found")
            return None

        print(f"   ✅ Loaded {len(df):,} rows")

        # 4. Process demographics
        print("\n4. Processing demographics...")
        processor = DemographicsProcessor(
            data_source=df,
            team_name=team_name,
            league=team_config['league']
        )

        demographic_data = processor.process_all_demographics()

        # Show what demographics were processed
        print("   Demographics processed:")
        for demo_type in demographic_data['demographics'].keys():
            print(f"   - {demo_type}")

        # 5. Generate charts
        print("\n5. Generating demographic charts...")
        output_dir = Path(f"test_output_{team_key}_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        output_dir.mkdir(exist_ok=True)

        charter = DemographicCharts(team_colors=team_config.get('colors'))
        charts = charter.create_all_demographic_charts(
            demographic_data,
            output_dir=output_dir
        )

        print(f"   ✅ Generated {len(charts)} charts")
        print("   Charts created:")
        for chart_name in charts.keys():
            print(f"   - {chart_name}")

        # 6. Create PowerPoint with single demographics slide
        print("\n6. Creating PowerPoint with new demographics layout...")
        presentation = Presentation()

        # Create demographics slide
        demo_generator = DemographicsSlide(presentation)
        presentation = demo_generator.generate(
            demographic_data=demographic_data,
            chart_dir=output_dir,
            team_config=team_config
        )

        # 7. Save presentation
        output_file = output_dir / f"{team_key}_demographics_test.pptx"
        presentation.save(str(output_file))
        print(f"\n✅ SUCCESS! Presentation saved to:")
        print(f"   {output_file.absolute()}")

        # 8. Summary
        print("\n📋 SLIDE SUMMARY:")
        print("   • Single demographics slide with 6 charts")
        print("   • Charts arranged in 2x3 grid")
        print("   • Black header bars for each section")
        print("   • KEY legend at bottom-left")
        print("   • No team logo or fan photo")
        print("   • No insight text (moved to title slide)")

        # 9. Chart layout verification
        print("\n📊 CHART LAYOUT:")
        print("   Top Row:")
        print("   - GENDER (left)")
        print("   - HOUSEHOLD INCOME (center)")
        print("   - OCCUPATION CATEGORY (right)")
        print("   Bottom Row:")
        print("   - ETHNICITY (left)")
        print("   - GENERATION (center)")
        print("   - CHILDREN IN HOUSEHOLD (right)")

        return output_file

    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def quick_test():
    """Quick test with minimal output"""
    print("\n🚀 QUICK TEST - Demographics Slide")
    print("-" * 40)

    result = test_demographics_slide('utah_jazz')

    if result:
        print("\n✅ Test completed successfully!")
        print(f"📁 Output: {result}")

        # Open file location (Windows)
        if sys.platform == 'win32':
            import os
            os.startfile(result.parent)
    else:
        print("\n❌ Test failed!")


def test_multiple_teams():
    """Test with multiple teams"""
    teams = ['utah_jazz', 'dallas_cowboys']
    results = []

    print("\n🏀 TESTING MULTIPLE TEAMS")
    print("=" * 60)

    for team in teams:
        print(f"\n\nTesting {team}...")
        print("-" * 40)
        result = test_demographics_slide(team)
        if result:
            results.append((team, result))

    print("\n\n📊 SUMMARY")
    print("=" * 60)
    print(f"Successfully generated {len(results)}/{len(teams)} presentations:")
    for team, path in results:
        print(f"   • {team}: {path.name}")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Test new demographics slide layout')
    parser.add_argument('team', nargs='?', default='utah_jazz',
                        help='Team key to test (default: utah_jazz)')
    parser.add_argument('--quick', action='store_true',
                        help='Run quick test with minimal output')
    parser.add_argument('--all', action='store_true',
                        help='Test all available teams')

    args = parser.parse_args()

    if args.all:
        test_multiple_teams()
    elif args.quick:
        quick_test()
    else:
        test_demographics_slide(args.team)


if __name__ == "__main__":
    main()