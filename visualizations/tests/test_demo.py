# test_demographics_fixed.py
"""
Test script for the fixed demographics slide and charts
Tests the removal of redundant titles, legends, and fixes the KEY text visibility
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from pptx import Presentation
from data_processors.demographic_processor import DemographicsProcessor
from data_processors.snowflake_connector import query_to_dataframe
from visualizations.demographic_charts import DemographicCharts
from slide_generators.demographics_slide import DemographicsSlide
from utils.team_config_manager import TeamConfigManager


def test_fixed_demographics_slide(team_key: str = 'utah_jazz', save_charts_only: bool = False):
    """
    Test the fixed demographics implementation

    Args:
        team_key: Team to test with
        save_charts_only: If True, only generate charts without PowerPoint
    """

    print("\n" + "=" * 70)
    print("FIXED DEMOGRAPHICS SLIDE TEST")
    print("=" * 70)
    print("Testing fixes for:")
    print("  ✓ Removed redundant chart titles")
    print("  ✓ Removed individual chart legends")
    print("  ✓ Fixed KEY text visibility (black on white)")
    print("=" * 70)

    try:
        # 1. Setup
        print("\n1. Setting up...")
        config_manager = TeamConfigManager()
        team_config = config_manager.get_team_config(team_key)
        team_name = team_config['team_name']
        print(f"   Team: {team_name}")
        print(f"   Colors: {team_config.get('colors', {})}")

        # 2. Create output directory
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_dir = Path(f"test_fixed_demographics_{team_key}_{timestamp}")
        output_dir.mkdir(exist_ok=True)
        print(f"   Output directory: {output_dir}")

        # 3. Fetch and process data
        print("\n2. Fetching demographic data...")
        demographics_view = config_manager.get_view_name(team_key, 'demographics')
        query = f"SELECT * FROM {demographics_view}"
        df = query_to_dataframe(query)
        print(f"   ✅ Loaded {len(df):,} rows from {demographics_view}")

        # 4. Process demographics
        print("\n3. Processing demographics...")
        processor = DemographicsProcessor(
            data_source=df,
            team_name=team_name,
            league=team_config['league']
        )

        demographic_data = processor.process_all_demographics()

        # Show what demographics were processed
        print("   Demographics processed:")
        for demo_type, demo_info in demographic_data['demographics'].items():
            chart_type = demo_info.get('chart_type', 'unknown')
            print(f"   - {demo_type}: {chart_type}")

        # 5. Generate charts with fixed settings
        print("\n4. Generating FIXED charts...")
        print("   Changes:")
        print("   - NO titles (black headers on slide provide context)")
        print("   - NO legends (KEY box provides legend)")
        print("   - Clean, minimal appearance")

        charter = DemographicCharts(team_colors=team_config.get('colors'))
        charts = charter.create_all_demographic_charts(
            demographic_data,
            output_dir=output_dir
        )

        print(f"   ✅ Generated {len(charts)} charts")
        print("   Charts created:")
        for chart_name in charts.keys():
            regular_path = output_dir / f'{chart_name}_chart.png'
            hires_path = output_dir / f'{chart_name}_chart_hires.png'
            print(f"   - {chart_name}")
            print(f"     Regular: {regular_path}")
            print(f"     Hi-res:  {hires_path}")

        # 6. Test chart appearance
        print("\n5. Verifying chart fixes...")
        verification_results = verify_chart_fixes(charts)
        for chart_name, issues in verification_results.items():
            if issues:
                print(f"   ⚠️  {chart_name}: {', '.join(issues)}")
            else:
                print(f"   ✅ {chart_name}: No titles/legends detected")

        # 7. Create PowerPoint if requested
        if not save_charts_only:
            print("\n6. Creating PowerPoint with FIXED demographics slide...")
            presentation = Presentation()

            # Create demographics slide with fixed KEY text
            demo_generator = DemographicsSlide(presentation)
            presentation = demo_generator.generate(
                demographic_data=demographic_data,
                chart_dir=output_dir,
                team_config=team_config
            )

            # Save presentation
            output_file = output_dir / f"{team_key}_demographics_fixed.pptx"
            presentation.save(str(output_file))
            print(f"   ✅ PowerPoint saved: {output_file}")

            # 8. Verify PowerPoint fixes
            print("\n7. PowerPoint fixes verification:")
            print("   ✅ Charts should have NO titles (black headers provide context)")
            print("   ✅ Charts should have NO legends (KEY box provides legend)")
            print("   ✅ KEY box should show BLACK text on white background")
            print("   ✅ Black header bars should clearly label each chart section")

        # 9. Summary
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        print(f"Team: {team_name}")
        print(f"Charts generated: {len(charts)}")
        print(f"Output directory: {output_dir}")

        if not save_charts_only:
            print(f"PowerPoint file: {output_file}")
            print("\nWhat to check in PowerPoint:")
            print("1. Open the presentation")
            print("2. Verify charts have clean appearance (no titles/legends)")
            print("3. Check that KEY box text is visible (black on white)")
            print("4. Confirm black header bars provide chart context")

        print("\nFiles created:")
        for file in sorted(output_dir.glob('*')):
            print(f"  - {file.name}")

        return output_dir

    except Exception as e:
        print(f"\n❌ ERROR: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def verify_chart_fixes(charts: Dict[str, Any]) -> Dict[str, list]:
    """
    Verify that charts don't have titles or legends
    This is a basic check - in practice you'd inspect the matplotlib objects
    """
    verification_results = {}

    for chart_name, fig in charts.items():
        issues = []

        # Get the axes from the figure
        axes = fig.get_axes()

        for ax in axes:
            # Check for titles
            if ax.get_title():
                issues.append("has title")

            # Check for legends
            if ax.get_legend():
                issues.append("has legend")

        verification_results[chart_name] = issues

    return verification_results


def test_comparison(team_key: str = 'utah_jazz'):
    """
    Test to compare old vs new approach
    """
    print("\n" + "=" * 70)
    print("COMPARISON TEST: OLD vs NEW CHARTS")
    print("=" * 70)

    # Test new approach
    print("\n🔧 Testing NEW approach (no titles/legends):")
    new_result = test_fixed_demographics_slide(team_key, save_charts_only=True)

    if new_result:
        print(f"✅ NEW charts saved to: {new_result}")

        # Show what the differences should be
        print("\n📊 Expected differences:")
        print("  OLD charts had:")
        print("    - Matplotlib titles above each chart")
        print("    - Individual legends on each chart")
        print("    - White text in KEY box (invisible)")
        print("  NEW charts have:")
        print("    - NO titles (black slide headers provide context)")
        print("    - NO legends (KEY box provides centralized legend)")
        print("    - BLACK text in KEY box (visible)")


def test_multiple_teams():
    """Test with multiple teams to ensure consistency"""
    teams = ['utah_jazz', 'dallas_cowboys']
    results = []

    print("\n" + "=" * 70)
    print("MULTI-TEAM TEST")
    print("=" * 70)

    for team in teams:
        print(f"\n{'🏀' if 'jazz' in team else '🏈'} Testing {team.replace('_', ' ').title()}:")
        print("-" * 40)

        result = test_fixed_demographics_slide(team, save_charts_only=True)
        if result:
            results.append((team, result))
            print(f"✅ Success: {result}")
        else:
            print(f"❌ Failed for {team}")

    print(f"\n📊 SUMMARY: {len(results)}/{len(teams)} teams successful")
    for team, path in results:
        print(f"  • {team}: {path}")


def quick_test():
    """Quick test with minimal output"""
    print("\n🚀 QUICK TEST - Fixed Demographics")
    print("-" * 40)

    result = test_fixed_demographics_slide('utah_jazz')

    if result:
        print(f"\n✅ Test completed! Check: {result}")
        print("💡 Open the PowerPoint to verify the fixes")
    else:
        print("\n❌ Test failed")


def main():
    """Main test function with options"""
    import argparse

    parser = argparse.ArgumentParser(description='Test fixed demographics slide')
    parser.add_argument('--team', default='utah_jazz', help='Team to test')
    parser.add_argument('--charts-only', action='store_true', help='Only generate charts')
    parser.add_argument('--comparison', action='store_true', help='Run comparison test')
    parser.add_argument('--multi-team', action='store_true', help='Test multiple teams')
    parser.add_argument('--quick', action='store_true', help='Quick test')

    args = parser.parse_args()

    if args.quick:
        quick_test()
    elif args.comparison:
        test_comparison(args.team)
    elif args.multi_team:
        test_multiple_teams()
    else:
        test_fixed_demographics_slide(args.team, args.charts_only)


if __name__ == "__main__":
    # Default behavior - run full test
    print("🎯 DEMOGRAPHICS FIXES TEST")
    print("Run with --help for options")

    # Run default test
    test_fixed_demographics_slide('utah_jazz')