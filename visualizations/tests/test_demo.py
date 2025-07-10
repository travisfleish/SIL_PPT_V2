# test_demographics_fixed.py
"""
Test script for the fixed demographics slide and charts
Tests the removal of redundant titles, legends, and fixes the KEY text visibility
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
import pandas as pd  # Add this import for the hotfix

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

        # HOTFIX: Check communities and data types
        print("\n   🔧 HOTFIX: Diagnosing community and data type issues...")

        # Check what communities are actually in the data
        actual_communities = df['COMMUNITY'].unique().tolist()
        print(f"   Actual communities in data: {actual_communities}")
        print(f"   Number of communities: {len(actual_communities)}")

        # Check data types
        if 'CUSTOMER_COUNT' in df.columns:
            original_dtype = df['CUSTOMER_COUNT'].dtype
            print(f"   CUSTOMER_COUNT dtype: {original_dtype}")

            # Show sample values for debugging
            sample_values = df['CUSTOMER_COUNT'].head(5).tolist()
            print(f"   Sample CUSTOMER_COUNT values: {sample_values}")

            # Ensure it's numeric if needed
            if df['CUSTOMER_COUNT'].dtype == 'object':
                print("   Converting CUSTOMER_COUNT to numeric...")
                df['CUSTOMER_COUNT'] = pd.to_numeric(
                    df['CUSTOMER_COUNT'].astype(str).str.replace(',', '').str.replace('$', '').str.strip(),
                    errors='coerce'
                ).fillna(0).astype('int64')
                print(f"   ✅ Converted to: {df['CUSTOMER_COUNT'].dtype}")

            # Final verification
            total_customers = df['CUSTOMER_COUNT'].sum()
            print(f"   Total customers: {total_customers:,}")

        # Check for ethnicity data specifically
        if 'ETHNIC_GROUP' in df.columns:
            unique_groups = df['ETHNIC_GROUP'].dropna().unique()
            print(f"   Ethnic groups found: {list(unique_groups)}")
            print(f"   Number of ethnic groups: {len(unique_groups)}")

            # Test a simple groupby to see if it works
            try:
                test_group = df.groupby(['COMMUNITY', 'ETHNIC_GROUP'])['CUSTOMER_COUNT'].sum()
                print(f"   ✅ Test groupby successful, result type: {type(test_group)}")
                print(f"   Test groupby dtype: {test_group.dtype}")

                # Show a few sample grouped results
                sample_results = test_group.head(3)
                print(f"   Sample grouped results: {sample_results.tolist()}")

            except Exception as e:
                print(f"   ❌ Test groupby failed: {e}")
        else:
            print("   ⚠️  No ETHNIC_GROUP column found")

        # 4. Process demographics (this should now work)
        print("\n3. Processing demographics...")

        # Debug: Check what communities the processor will expect
        expected_communities = [
            f'{team_name} Fans',
            f'Local Gen Pop (Excl. {team_name.split()[-1]})',
            f'{team_config["league"]} Fans'
        ]
        print(f"   Expected communities by processor: {expected_communities}")
        print(f"   Actual communities in data: {actual_communities}")

        # Check for mismatches
        missing_expected = set(expected_communities) - set(actual_communities)
        unexpected_actual = set(actual_communities) - set(expected_communities)

        if missing_expected:
            print(f"   ⚠️  Missing expected communities: {missing_expected}")
        if unexpected_actual:
            print(f"   ⚠️  Unexpected communities in data: {unexpected_actual}")
        if not missing_expected and not unexpected_actual:
            print("   ✅ Community names match perfectly")

        # Create processor and immediately check its internal data types
        processor = DemographicsProcessor(
            data_source=df,
            team_name=team_name,
            league=team_config['league']
        )

        # DIAGNOSTIC: Check processor's internal data types
        print(f"   🔍 Processor's internal CUSTOMER_COUNT dtype: {processor.data['CUSTOMER_COUNT'].dtype}")
        print(f"   🔍 Processor's internal data shape: {processor.data.shape}")

        # Test processor's internal groupby
        try:
            internal_test = processor.data.groupby(['COMMUNITY', 'ETHNIC_GROUP'])['CUSTOMER_COUNT'].sum()
            print(f"   🔍 Processor internal groupby dtype: {internal_test.dtype}")
        except Exception as e:
            print(f"   ❌ Processor internal groupby failed: {e}")

        demographic_data = processor.process_all_demographics()

        # Show what demographics were processed
        print("   Demographics processed:")
        for demo_type, demo_info in demographic_data['demographics'].items():
            chart_type = demo_info.get('chart_type', 'unknown')
            print(f"   - {demo_type}: {chart_type}")

        # Specifically check if ethnicity was processed
        if 'ethnicity' in demographic_data['demographics']:
            print("   ✅ Ethnicity data successfully processed!")
            ethnicity_data = demographic_data['demographics']['ethnicity']
            print(f"   Ethnicity categories: {ethnicity_data.get('categories', [])}")
        else:
            print("   ⚠️  No ethnicity data found")

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
        print(
            f"Ethnicity processing: {'✅ SUCCESS' if 'ethnicity' in demographic_data['demographics'] else '❌ NO DATA'}")

        if not save_charts_only:
            print(f"PowerPoint file: {output_file}")
            print("\nWhat to check in PowerPoint:")
            print("1. Open the presentation")
            print("2. Verify charts have clean appearance (no titles/legends)")
            print("3. Check that KEY box text is visible (black on white)")
            print("4. Confirm black header bars provide chart context")
            print("5. Look for ethnicity chart (if data was available)")

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


if __name__ == "__main__":
    # Default behavior - run full test
    print("🎯 DEMOGRAPHICS FIXES TEST WITH HOTFIX")
    print("Run with --help for options")

    # Run default test
    test_fixed_demographics_slide('utah_jazz')