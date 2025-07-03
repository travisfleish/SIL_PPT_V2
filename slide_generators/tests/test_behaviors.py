# test_behaviors_slide_updated.py
"""
Test script for the updated behaviors slide with titles and explanation
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from pptx import Presentation
from data_processors.merchant_ranker import MerchantRanker
from utils.team_config_manager import TeamConfigManager
from slide_generators.behaviors_slide import BehaviorsSlide
import logging

logging.basicConfig(level=logging.INFO)


def test_behaviors_slide(team_key: str = 'utah_jazz', save_intermediate: bool = True):
    """
    Test the updated behaviors slide

    Args:
        team_key: Team to test with
        save_intermediate: Whether to save the chart images separately
    """
    print(f"\n{'=' * 60}")
    print(f"TESTING UPDATED BEHAVIORS SLIDE - {team_key.upper()}")
    print(f"{'=' * 60}\n")

    try:
        # 1. Setup
        print("1. Loading configuration...")
        config_manager = TeamConfigManager()
        team_config = config_manager.get_team_config(team_key)
        print(f"   ✅ Team: {team_config['team_name']}")

        # 2. Initialize data
        print("\n2. Connecting to data source...")
        ranker = MerchantRanker(team_view_prefix=team_config['view_prefix'])

        # Quick data check
        communities = ranker.get_top_communities(min_audience_pct=0.20, top_n=3)
        if communities.empty:
            print("   ❌ No community data found!")
            return None
        print(f"   ✅ Found {len(communities)} communities")

        # 3. Create presentation
        print("\n3. Creating presentation...")
        presentation = Presentation()

        # 4. Generate behaviors slide
        print("\n4. Generating behaviors slide...")
        print("   • Creating fan wheel visualization")
        print("   • Creating community index chart")
        print("   • Adding chart titles:")
        print("     - 'Top Community Fan Purchases'")
        print("     - 'Top Ten [Team] Fan Communities'")
        print("   • Adding explanation text")
        print("   • Adding insight text")

        behaviors_generator = BehaviorsSlide(presentation)
        presentation = behaviors_generator.generate(ranker, team_config)

        # 5. Save presentation
        output_path = Path(f"{team_key}_behaviors_updated.pptx")
        presentation.save(str(output_path))

        print(f"\n✅ SUCCESS! Presentation saved to: {output_path.absolute()}")

        # 6. Verify what was added
        print("\n📋 Slide should contain:")
        print("   • Header: Team name + 'Fan Behaviors: How Are [Team] Fans Unique'")
        print("   • Fan wheel (left) with title 'Top Community Fan Purchases'")
        print("   • Bar chart (right) with title 'Top Ten [Team] Fan Communities'")
        print("   • Legend showing '% Team Fans' and 'Team Fan Index'")
        print("   • X-axis labeled 'Percent Fan Audience'")
        print("   • Explanation text below bar chart")
        print("   • Insight text below fan wheel")

        # Check if intermediate files exist
        if save_intermediate:
            print("\n📁 Intermediate files:")
            for file in ['temp_fan_wheel.png', 'temp_community_chart.png']:
                if Path(file).exists():
                    print(f"   ✅ {file}")
                else:
                    print(f"   ❌ {file} (missing)")

        return output_path

    except Exception as e:
        print(f"\n❌ ERROR: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def compare_slides(team_key: str = 'utah_jazz'):
    """
    Generate before/after comparison if you have the old version
    """
    print("\n🔄 COMPARISON TEST")
    print("This will generate two versions to compare the changes\n")

    # Test with updated version
    result = test_behaviors_slide(team_key)

    if result:
        print("\n💡 TIP: Open the PowerPoint and verify:")
        print("   1. Both charts have titles above them")
        print("   2. Bar chart shows '% Team Fans' and 'Team Fan Index' in legend")
        print("   3. X-axis says 'Percent Fan Audience'")
        print("   4. Explanation text appears below the bar chart")


def test_multiple_teams():
    """Test with multiple teams to ensure consistency"""
    teams = ['utah_jazz', 'dallas_cowboys']
    results = []

    for team in teams:
        print(f"\n{'=' * 40}")
        print(f"Testing {team}")
        print(f"{'=' * 40}")

        result = test_behaviors_slide(team, save_intermediate=False)
        if result:
            results.append((team, result))

    print("\n📊 SUMMARY")
    print(f"Successfully generated {len(results)} presentations:")
    for team, path in results:
        print(f"   • {team}: {path}")


def main():
    """Main test function"""
    print("\n🎯 BEHAVIORS SLIDE UPDATE TEST")
    print("This will test the updated behaviors slide with:")
    print("  • Chart titles")
    print("  • Updated legend labels")
    print("  • Explanation text")
    print("  • Correct x-axis label")

    # Single team test
    test_behaviors_slide('utah_jazz')

    # Ask if user wants to test more
    user_input = input("\n\nTest Dallas Cowboys too? (y/n): ")
    if user_input.lower() == 'y':
        test_behaviors_slide('dallas_cowboys')

    user_input = input("\nRun comparison test? (y/n): ")
    if user_input.lower() == 'y':
        compare_slides()


if __name__ == "__main__":
    main()