# test_demographics_two_slides.py
"""
Test script for the two-slide demographics implementation
"""

import sys
from pathlib import Path
from typing import Dict, Any

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from pptx import Presentation
from data_processors.demographic_processor import DemographicsProcessor
from data_processors.snowflake_connector import query_to_dataframe
from visualizations.demographic_charts import DemographicCharts
from slide_generators.demographics_slide1 import DemographicsSlide1
from slide_generators.demographics_slide2 import DemographicsSlide2
from utils.team_config_manager import TeamConfigManager


def test_two_slide_demographics(team_key: str = 'utah_jazz'):
    """Test the two-slide demographics implementation"""

    print("\n" + "=" * 60)
    print("TWO-SLIDE DEMOGRAPHICS TEST")
    print("=" * 60)

    try:
        # 1. Setup
        print("\n1. Setting up...")
        config_manager = TeamConfigManager()
        team_config = config_manager.get_team_config(team_key)
        team_name = team_config['team_name']
        print(f"   Team: {team_name}")

        # 2. Fetch and process data
        print("\n2. Fetching demographic data...")
        demographics_view = config_manager.get_view_name(team_key, 'demographics')
        query = f"SELECT * FROM {demographics_view}"
        df = query_to_dataframe(query)
        print(f"   ✅ Loaded {len(df):,} rows")

        # 3. Process demographics
        print("\n3. Processing demographics...")
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

        # 4. Generate charts
        print("\n4. Generating charts...")
        output_dir = Path(f"{team_key}_two_slide_test")
        output_dir.mkdir(exist_ok=True)

        charter = DemographicCharts(team_colors=team_config.get('colors'))
        charts = charter.create_all_demographic_charts(
            demographic_data,
            output_dir=output_dir
        )

        print(f"   ✅ Generated {len(charts)} charts")

        # 5. Create PowerPoint with two slides
        print("\n5. Creating PowerPoint with two demographics slides...")
        presentation = Presentation()

        # Create demographics slide 1
        print("   Creating slide 1 (Gender, Ethnicity, Generation)...")
        demo_generator1 = DemographicsSlide1(presentation)
        presentation = demo_generator1.generate(
            demographic_data=demographic_data,
            chart_dir=output_dir,
            team_config=team_config
        )

        # Create demographics slide 2
        print("   Creating slide 2 (Income, Children, Occupation)...")
        demo_generator2 = DemographicsSlide2(presentation)
        presentation = demo_generator2.generate(
            demographic_data=demographic_data,
            chart_dir=output_dir,
            team_config=team_config
        )

        # Save presentation
        output_file = f"{team_key}_demographics_two_slides_test.pptx"
        presentation.save(output_file)
        print(f"   ✅ Saved to: {output_file}")

        print("\n✅ Test complete!")
        print(f"\nGenerated files:")
        print(f"  - PowerPoint: {output_file}")
        print(f"  - Charts: {output_dir}/")
        print(f"\nThe presentation contains 2 slides:")
        print(f"  - Slide 1: Gender, Ethnicity, Generation")
        print(f"  - Slide 2: Income, Children, Occupation")

        return True

    except Exception as e:
        print(f"\n❌ ERROR: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def compare_single_vs_two_slides(team_key: str = 'utah_jazz'):
    """Create both single-slide and two-slide versions for comparison"""

    print("\n" + "=" * 60)
    print("COMPARING SINGLE VS TWO-SLIDE DEMOGRAPHICS")
    print("=" * 60)

    # Import the original single slide version
    from slide_generators.demographics_slide import DemographicsSlide

    try:
        # Setup (same for both)
        config_manager = TeamConfigManager()
        team_config = config_manager.get_team_config(team_key)

        # Get data and process
        demographics_view = config_manager.get_view_name(team_key, 'demographics')
        df = query_to_dataframe(f"SELECT * FROM {demographics_view}")

        processor = DemographicsProcessor(
            data_source=df,
            team_name=team_config['team_name'],
            league=team_config['league']
        )
        demographic_data = processor.process_all_demographics()

        # Generate charts
        output_dir = Path(f"{team_key}_comparison_test")
        output_dir.mkdir(exist_ok=True)

        charter = DemographicCharts(team_colors=team_config.get('colors'))
        charts = charter.create_all_demographic_charts(demographic_data, output_dir=output_dir)

        # Create single-slide version
        print("\n1. Creating single-slide version...")
        pres1 = Presentation()
        demo_gen = DemographicsSlide(pres1)
        pres1 = demo_gen.generate(demographic_data, output_dir, team_config)
        pres1.save(f"{team_key}_single_slide.pptx")
        print("   ✅ Saved single-slide version")

        # Create two-slide version
        print("\n2. Creating two-slide version...")
        pres2 = Presentation()

        demo_gen1 = DemographicsSlide1(pres2)
        pres2 = demo_gen1.generate(demographic_data, output_dir, team_config)

        demo_gen2 = DemographicsSlide2(pres2)
        pres2 = demo_gen2.generate(demographic_data, output_dir, team_config)

        pres2.save(f"{team_key}_two_slides.pptx")
        print("   ✅ Saved two-slide version")

        print("\n✅ Comparison complete! Check both files to compare layouts.")

    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()


def main():
    """Main test function"""
    print("\n🎯 DEMOGRAPHICS TWO-SLIDE TEST")

    # Test two-slide implementation
    success = test_two_slide_demographics('utah_jazz')

    if success:
        # Compare with single slide
        user_input = input("\n\nCreate comparison with single-slide version? (y/n): ")
        if user_input.lower() == 'y':
            compare_single_vs_two_slides('utah_jazz')

        # Test with Dallas Cowboys
        user_input = input("\n\nTest with Dallas Cowboys too? (y/n): ")
        if user_input.lower() == 'y':
            test_two_slide_demographics('dallas_cowboys')


if __name__ == "__main__":
    main()