#!/usr/bin/env python3
"""
Simple test script for behaviors slide
Tests the 6.5" chart with shifted positioning
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from pptx import Presentation
from data_processors.merchant_ranker import MerchantRanker
from utils.team_config_manager import TeamConfigManager
from slide_generators.behaviors_slide import BehaviorsSlide


def test_behaviors_slide(team_key='utah_jazz'):
    """Quick test of behaviors slide"""

    print(f"\n{'=' * 50}")
    print(f"Testing Behaviors Slide - {team_key}")
    print(f"{'=' * 50}\n")

    try:
        # 1. Load team config
        config_manager = TeamConfigManager()
        team_config = config_manager.get_team_config(team_key)
        print(f"✅ Team: {team_config['team_name']}")

        # 2. Load template
        template_path = Path("templates/sil_combined_template.pptx")
        if not template_path.exists():
            # Try from parent directory
            template_path = Path("../templates/sil_combined_template.pptx")
        if not template_path.exists():
            # Try from project root
            template_path = Path("../../templates/sil_combined_template.pptx")

        if template_path.exists():
            print(f"✅ Template found: {template_path}")
            presentation = Presentation(str(template_path))
        else:
            print("⚠️  No template found, creating blank presentation")
            presentation = Presentation()

        # 3. Initialize data
        ranker = MerchantRanker(team_view_prefix=team_config['view_prefix'])
        print("✅ Connected to data")

        # 4. Generate slide
        print("\nGenerating behaviors slide...")
        print("  • Community chart: 6.5\" wide")
        print("  • Fan wheel: 5.5\" diameter")
        print("  • All elements shifted up")
        print("  • Explanation text visible below chart")

        behaviors_generator = BehaviorsSlide(presentation)
        presentation = behaviors_generator.generate(ranker, team_config)

        # 5. Save
        output_file = f"{team_key}_behaviors_test.pptx"
        presentation.save(output_file)
        print(f"\n✅ Saved to: {output_file}")

        # 6. Summary
        print("\n📋 What to check:")
        print("  1. Insight text at top (0.7\" from top)")
        print("  2. Chart titles at 1.5\" from top")
        print("  3. Community chart at 1.8\" from top")
        print("  4. Explanation text at 5.4\" (visible below chart)")
        print("  5. Fan wheel centered in remaining space")

        return output_file

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    # Test Utah Jazz
    test_behaviors_slide('utah_jazz')

    # Optional: test another team
    response = input("\nTest Dallas Cowboys too? (y/n): ")
    if response.lower() == 'y':
        test_behaviors_slide('dallas_cowboys')