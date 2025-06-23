# test_behaviors_slide.py
"""
Test script for generating the Fan Behaviors PowerPoint slide
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from slide_generators.behaviors_slide import create_behaviors_slide
from data_processors.merchant_ranker import MerchantRanker
from utils.team_config_manager import TeamConfigManager
import logging

logging.basicConfig(level=logging.INFO)


def test_behaviors_slide(team_key: str = 'utah_jazz'):
    """
    Test behaviors slide generation

    Args:
        team_key: Team identifier (utah_jazz or dallas_cowboys)
    """
    print(f"\n{'=' * 60}")
    print(f"BEHAVIORS SLIDE TEST - {team_key.replace('_', ' ').title()}")
    print(f"{'=' * 60}")

    try:
        # 1. Get team configuration
        print("\n1. Loading team configuration...")
        config_manager = TeamConfigManager()
        team_config = config_manager.get_team_config(team_key)
        print(f"   ✅ Team: {team_config['team_name']}")
        print(f"   ✅ Colors: {team_config['colors']}")

        # 2. Initialize data source
        print("\n2. Initializing data source...")
        ranker = MerchantRanker(team_view_prefix=team_config['view_prefix'])
        print(f"   ✅ Connected to Snowflake views")

        # 3. Test data availability
        print("\n3. Checking data availability...")
        communities = ranker.get_top_communities(min_audience_pct=0.20, top_n=3)
        if communities.empty:
            print("   ❌ No community data found!")
            return
        print(f"   ✅ Found {len(communities)} top communities")
        print(f"      Top 3: {', '.join(communities['COMMUNITY'].tolist())}")

        # 4. Generate slide
        print("\n4. Generating behaviors slide...")
        print("   - Creating fan wheel visualization...")
        print("   - Creating community index chart...")
        print("   - Building PowerPoint slide...")

        presentation = create_behaviors_slide(ranker, team_config)

        # 5. Save presentation
        output_path = Path(f"{team_key}_behaviors_slide.pptx")
        presentation.save(str(output_path))

        print(f"\n✅ SUCCESS! Slide saved to: {output_path.absolute()}")

        # Also save the intermediate images for inspection
        print("\n📁 Check these temporary files:")
        print("   - temp_fan_wheel.png")
        print("   - temp_community_chart.png")

        return output_path

    except Exception as e:
        print(f"\n❌ ERROR: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Main test function"""
    print("\n🎯 FAN BEHAVIORS SLIDE GENERATOR TEST")
    print("This will create a PowerPoint slide with:")
    print("  • Fan wheel visualization (left)")
    print("  • Community index chart (right)")
    print("  • Insight text below the fan wheel")

    # Test with Utah Jazz
    jazz_result = test_behaviors_slide('utah_jazz')

    if jazz_result:
        # Ask if user wants to test Dallas Cowboys too
        user_input = input("\n\nAlso test Dallas Cowboys? (y/n): ")
        if user_input.lower() == 'y':
            cowboys_result = test_behaviors_slide('dallas_cowboys')

    print("\n✨ Test complete!")


if __name__ == "__main__":
    main()