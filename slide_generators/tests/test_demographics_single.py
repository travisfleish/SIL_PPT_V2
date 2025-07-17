# test_demographics_fixed.py
"""
Test script for the fixed demographics slide and charts
Tests the removal of redundant titles, legends, and fixes the KEY text visibility
ENHANCED: Added comprehensive font debugging
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

# Import matplotlib for debugging
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm


def debug_font_system():
    """Debug the font system and available fonts"""
    print("\n" + "=" * 70)
    print("FONT SYSTEM DEBUG")
    print("=" * 70)

    # 1. Check matplotlib version
    print(f"\n1. Matplotlib version: {matplotlib.__version__}")

    # 2. Check current font settings
    print("\n2. Current matplotlib font settings:")
    font_settings = [
        'font.family', 'font.weight', 'font.size',
        'axes.labelweight', 'axes.titleweight',
        'figure.titleweight', 'figure.labelweight'
    ]
    for setting in font_settings:
        value = matplotlib.rcParams.get(setting, 'NOT SET')
        print(f"   {setting}: {value}")

    # 3. Check available Overpass fonts
    print("\n3. Available Overpass fonts:")
    overpass_fonts = []
    for font in fm.fontManager.ttflist:
        if 'overpass' in font.name.lower():
            overpass_fonts.append({
                'name': font.name,
                'weight': font.weight,
                'style': font.style,
                'variant': font.variant,
                'stretch': font.stretch,
                'fname': font.fname
            })

    if overpass_fonts:
        for font in sorted(overpass_fonts, key=lambda x: x['weight'], reverse=True):
            print(f"   - {font['name']}")
            print(f"     Weight: {font['weight']} ({'bold' if font['weight'] >= 700 else 'regular'})")
            print(f"     Style: {font['style']}")
            print(f"     Path: {font['fname']}")
    else:
        print("   ❌ No Overpass fonts found!")

    # 4. Check available bold fonts
    print("\n4. Available bold fonts (weight >= 700):")
    bold_fonts = []
    for font in fm.fontManager.ttflist:
        if font.weight >= 700:
            bold_fonts.append(f"{font.name} (weight: {font.weight})")

    # Show first 10 bold fonts
    for font in sorted(bold_fonts)[:10]:
        print(f"   - {font}")

    # 5. Test if Arial Black is available
    print("\n5. Checking for Arial Black:")
    arial_black_found = False
    for font in fm.fontManager.ttflist:
        if 'arial black' in font.name.lower():
            print(f"   ✅ Found: {font.name} (weight: {font.weight})")
            arial_black_found = True
    if not arial_black_found:
        print("   ❌ Arial Black not found")

    # 6. Font cache location
    print("\n6. Font cache info:")
    cache_dir = Path.home() / '.matplotlib'
    if cache_dir.exists():
        cache_files = list(cache_dir.glob('fontlist-*.json'))
        if cache_files:
            for cache_file in cache_files:
                print(f"   - {cache_file}")
                print(f"     Size: {cache_file.stat().st_size / 1024:.1f} KB")
                print(f"     Modified: {datetime.fromtimestamp(cache_file.stat().st_mtime)}")
        else:
            print("   No font cache files found")
    else:
        print("   Cache directory does not exist")

    return overpass_fonts, bold_fonts


def create_font_test_chart(output_dir: Path):
    """Create a test chart to verify font rendering"""
    print("\n7. Creating font test chart...")

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 6))

    # Test different font specifications
    test_configs = [
        {'family': 'Overpass', 'weight': 'bold', 'label': 'Overpass Bold'},
        {'family': 'Overpass', 'weight': 'normal', 'label': 'Overpass Normal'},
        {'family': 'Arial', 'weight': 'bold', 'label': 'Arial Bold'},
        {'family': 'Arial Black', 'weight': 'normal', 'label': 'Arial Black'},
    ]

    # Test on first axis
    ax1.set_title('Font Weight Test', fontsize=14, fontweight='bold')
    y_pos = 0.8
    for config in test_configs:
        try:
            ax1.text(0.1, y_pos, config['label'] + ':',
                     fontfamily=config['family'], fontweight='normal', fontsize=12)
            ax1.text(0.5, y_pos, 'Sample Text 123',
                     fontfamily=config['family'], fontweight=config['weight'], fontsize=12)
            y_pos -= 0.2
        except:
            ax1.text(0.5, y_pos, f"Failed to render {config['family']}",
                     fontsize=10, color='red')
            y_pos -= 0.2

    ax1.set_xlim(0, 1)
    ax1.set_ylim(0, 1)
    ax1.axis('off')

    # Test current matplotlib settings
    ax2.set_title('Current Settings Test', fontsize=14, fontweight='bold')
    ax2.text(0.5, 0.8, 'Default Text (should be bold)', ha='center', fontsize=12)
    ax2.text(0.5, 0.6, f"Font: {plt.rcParams['font.family']}", ha='center', fontsize=10)
    ax2.text(0.5, 0.4, f"Weight: {plt.rcParams['font.weight']}", ha='center', fontsize=10)

    # Add sample bar chart
    ax2_inset = fig.add_axes([0.2, 0.05, 0.6, 0.25])
    ax2_inset.bar(['A', 'B', 'C'], [10, 20, 15])
    ax2_inset.set_ylabel('Values')
    ax2_inset.set_title('Sample Bar Chart')

    ax2.set_xlim(0, 1)
    ax2.set_ylim(0, 1)
    ax2.axis('off')

    # Save test chart
    test_path = output_dir / 'font_test_chart.png'
    fig.savefig(test_path, dpi=150, bbox_inches='tight')
    plt.close(fig)

    print(f"   ✅ Font test chart saved: {test_path}")
    return test_path


def inspect_generated_chart(fig, chart_name: str):
    """Inspect a generated chart for font properties"""
    print(f"\n   Inspecting {chart_name} chart:")

    axes = fig.get_axes()
    for i, ax in enumerate(axes):
        print(f"   Axis {i}:")

        # Check title
        title = ax.get_title()
        if title:
            print(f"     Title: '{title}' (weight: {ax.title.get_weight()})")

        # Check axis labels
        xlabel = ax.get_xlabel()
        ylabel = ax.get_ylabel()
        if xlabel:
            print(f"     X-label: '{xlabel}' (weight: {ax.xaxis.label.get_weight()})")
        if ylabel:
            print(f"     Y-label: '{ylabel}' (weight: {ax.yaxis.label.get_weight()})")

        # Check tick labels
        xtick_labels = ax.get_xticklabels()
        if xtick_labels:
            first_label = xtick_labels[0] if xtick_labels else None
            if first_label:
                print(f"     X-tick weight: {first_label.get_weight()}")
                print(f"     X-tick font: {first_label.get_fontfamily()}")

        # Check text objects
        texts = ax.texts
        if texts:
            print(f"     Text objects: {len(texts)}")
            for j, text in enumerate(texts[:3]):  # First 3 texts
                print(f"       Text {j}: '{text.get_text()[:20]}...' (weight: {text.get_weight()})")


def test_fixed_demographics_slide(team_key: str = 'utah_jazz', save_charts_only: bool = False):
    """
    Test the fixed demographics implementation with enhanced font debugging

    Args:
        team_key: Team to test with
        save_charts_only: If True, only generate charts without PowerPoint
    """

    print("\n" + "=" * 70)
    print("FIXED DEMOGRAPHICS SLIDE TEST - WITH FONT DEBUGGING")
    print("=" * 70)
    print("Testing fixes for:")
    print("  ✓ Removed redundant chart titles")
    print("  ✓ Removed individual chart legends")
    print("  ✓ Fixed KEY text visibility (black on white)")
    print("  🔍 ENHANCED: Font weight debugging")
    print("=" * 70)

    # Run font system debug first
    overpass_fonts, bold_fonts = debug_font_system()

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

        # Create font test chart
        create_font_test_chart(output_dir)

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
        print("   - DEBUGGING: Font weights")

        # Check matplotlib settings before chart creation
        print("\n   Matplotlib settings before chart creation:")
        print(f"   - font.family: {matplotlib.rcParams['font.family']}")
        print(f"   - font.weight: {matplotlib.rcParams['font.weight']}")

        charter = DemographicCharts(team_colors=team_config.get('colors'))

        # Check what font the charter is using
        print(f"\n   DemographicCharts font settings:")
        print(f"   - font_family: {charter.font_family}")
        print(f"   - matplotlib font.family: {plt.rcParams['font.family']}")
        print(f"   - matplotlib font.weight: {plt.rcParams['font.weight']}")

        charts = charter.create_all_demographic_charts(
            demographic_data,
            output_dir=output_dir
        )

        print(f"\n   ✅ Generated {len(charts)} charts")
        print("   Charts created:")
        for chart_name, fig in charts.items():
            regular_path = output_dir / f'{chart_name}_chart.png'
            hires_path = output_dir / f'{chart_name}_chart_hires.png'
            print(f"   - {chart_name}")

            # Inspect the chart for font properties
            inspect_generated_chart(fig, chart_name)

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
            print("5. CHECK font_test_chart.png for font rendering")

        print("\nFiles created:")
        for file in sorted(output_dir.glob('*')):
            print(f"  - {file.name}")

        # Final font recommendation
        print("\n" + "=" * 70)
        print("FONT RECOMMENDATIONS")
        print("=" * 70)
        if not overpass_fonts or all(f['weight'] < 700 for f in overpass_fonts):
            print("⚠️  No bold Overpass variant found!")
            print("Recommendations:")
            print("1. Install Overpass Bold from: https://fonts.google.com/specimen/Overpass")
            print("2. Or use Arial Black for guaranteed bold text")
            print("3. Or use Helvetica Neue Bold on macOS")
        else:
            print("✅ Bold Overpass variants found - ensure matplotlib is using them")

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
        print("🔍 Check font_test_chart.png for font debugging")
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
    print("🎯 DEMOGRAPHICS FIXES TEST - ENHANCED WITH FONT DEBUGGING")
    print("Run with --help for options")

    # Run default test
    test_fixed_demographics_slide('utah_jazz')