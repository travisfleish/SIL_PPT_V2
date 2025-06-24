# test_demographics_only.py
"""
Test script to verify demographics slide works independently
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from pptx import Presentation
from slide_generators.demographics_slide import DemographicsSlide
from utils.team_config_manager import TeamConfigManager


def test_demographics_slide():
    """Test demographics slide with existing charts"""

    print("\n🔍 DEMOGRAPHICS SLIDE TEST")
    print("=" * 50)

    # Get team config
    config_manager = TeamConfigManager()
    team_config = config_manager.get_team_config('utah_jazz')

    # Path to existing charts
    chart_dir = Path('utah_jazz_temp_charts')

    if not chart_dir.exists():
        print(f"❌ Chart directory not found: {chart_dir}")
        return

    # List available charts
    print(f"\n📊 Found charts in {chart_dir}:")
    for chart in chart_dir.glob('*.png'):
        print(f"   - {chart.name}")

    # Create mock demographic data
    demographic_data = {
        'key_insights': 'Jazz fans are younger, and more likely to be parents who are working professionals versus the Jazz gen pop.'
    }

    # Create presentation with demographics slide
    print("\n🎨 Creating demographics slide...")

    try:
        # Create new presentation
        pres = Presentation()

        # Create demographics slide generator
        demo_generator = DemographicsSlide(pres)

        # Generate the slide
        pres = demo_generator.generate(
            demographic_data=demographic_data,
            chart_dir=chart_dir,
            team_config=team_config
        )

        # Save
        output_path = 'test_demographics_only.pptx'
        pres.save(output_path)

        print(f"\n✅ Success! Slide saved to: {output_path}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_demographics_slide()