#!/usr/bin/env python3
"""
Quick start script to test PowerPoint generation
Simplified interface for rapid testing and development
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import List, Optional

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from report_builder.pptx_builder import PowerPointBuilder
from data_processors.snowflake_connector import test_connection
from utils.team_config_manager import TeamConfigManager


def quick_generate(team_key: str = 'utah_jazz', categories_only: Optional[List[str]] = None):
    """
    Quick generation with minimal configuration

    Args:
        team_key: Team to generate for
        categories_only: Optional list of specific categories to generate
    """
    print(f"\n🚀 QUICK START - PowerPoint Generator for {team_key}")
    print("=" * 50)

    # Test connection
    print("\nChecking Snowflake connection...")
    if not test_connection():
        print("❌ Cannot connect to Snowflake")
        return None
    print("✅ Connected!")

    # Get team info
    config = TeamConfigManager()
    team_config = config.get_team_config(team_key)
    print(f"\n📊 Generating for: {team_config['team_name']}")

    # Create builder
    builder = PowerPointBuilder(team_key)

    # If specific categories requested, modify the builder
    if categories_only:
        print(f"📌 Generating only: {', '.join(categories_only)}")
        # This would require modifying the builder to support selective generation
        # For now, we'll generate all

    # Generate
    print("\n⏳ Generating presentation...")
    print("   • Demographics slide")
    print("   • Fan behaviors slide")
    print("   • Category analysis slides")
    print("\nThis will take 2-3 minutes...")

    try:
        output_path = builder.build_presentation(
            include_custom_categories=True,
            custom_category_count=4  # Reduced for faster testing
        )

        print(f"\n✅ Success! Generated: {output_path.name}")
        print(f"📁 Location: {output_path.parent}")

        # Open file location (Windows)
        if sys.platform == 'win32':
            import os
            os.startfile(output_path.parent)

        return output_path

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def quick_generate_multiple(team_keys: List[str], categories_only: Optional[List[str]] = None):
    """
    Generate reports for multiple teams in sequence

    Args:
        team_keys: List of team keys to generate for
        categories_only: Optional list of specific categories to generate
    """
    print(f"\n🚀 MULTI-TEAM GENERATION - {len(team_keys)} teams")
    print("=" * 50)

    results = {}
    successful = 0
    failed = 0

    for i, team_key in enumerate(team_keys, 1):
        print(f"\n\n{'=' * 50}")
        print(f"📊 Team {i}/{len(team_keys)}: {team_key.upper()}")
        print(f"{'=' * 50}")

        result = quick_generate(team_key, categories_only)
        results[team_key] = result

        if result:
            successful += 1
        else:
            failed += 1

    # Summary
    print(f"\n\n{'=' * 50}")
    print("📈 GENERATION SUMMARY")
    print(f"{'=' * 50}")
    print(f"✅ Successful: {successful}")
    print(f"❌ Failed: {failed}")
    print(f"\nResults:")
    for team, path in results.items():
        status = "✅" if path else "❌"
        team_name = team.replace('_', ' ').title()
        if path:
            print(f"  {status} {team_name}: {path.name}")
        else:
            print(f"  {status} {team_name}: Generation failed")

    return results


def generate_jazz_and_panthers():
    """
    Convenience function to generate for Utah Jazz and Carolina Panthers
    """
    print("\n🏀🏈 Generating for Utah Jazz and Carolina Panthers")
    return quick_generate_multiple(['utah_jazz', 'carolina_panthers'])


def test_single_slide(slide_type: str, team_key: str = 'utah_jazz'):
    """
    Test generation of a single slide type

    Args:
        slide_type: Type of slide to generate (demographics, behaviors, category)
        team_key: Team to use
    """
    print(f"\n🧪 Testing {slide_type} slide generation")
    print("=" * 50)

    from pptx import Presentation

    # Get team config
    config = TeamConfigManager()
    team_config = config.get_team_config(team_key)

    # Create presentation
    pres = Presentation()

    if slide_type == 'demographics':
        from slide_generators.demographics_slide import DemographicsSlide
        from data_processors.demographic_processor import DemographicsProcessor
        from data_processors.snowflake_connector import query_to_dataframe

        # Load data
        view = config.get_view_name(team_key, 'demographics')
        df = query_to_dataframe(f"SELECT * FROM {view}")

        # Process
        processor = DemographicsProcessor(df, team_config['team_name'], team_config['league'])
        data = processor.process_all_demographics()

        # Generate charts (mock)
        chart_dir = Path('temp_charts')
        chart_dir.mkdir(exist_ok=True)

        # Create slide
        generator = DemographicsSlide(pres)
        pres = generator.generate(data, chart_dir, team_config)

    elif slide_type == 'behaviors':
        from slide_generators.behaviors_slide import BehaviorsSlide
        from data_processors.merchant_ranker import MerchantRanker

        # Create slide
        ranker = MerchantRanker(team_view_prefix=team_config['view_prefix'])
        generator = BehaviorsSlide(pres)
        pres = generator.generate(ranker, team_config)

    elif slide_type.startswith('category:'):
        from slide_generators.category_slide import CategorySlide
        from data_processors.category_analyzer import CategoryAnalyzer

        category_name = slide_type.split(':')[1]

        # Would need to load and analyze category data here
        print(f"Category slide generation for '{category_name}' not fully implemented in test mode")
        return None

    # Save
    output_file = f"test_{slide_type}_{team_key}.pptx"
    pres.save(output_file)
    print(f"\n✅ Test slide saved: {output_file}")

    return output_file


def interactive_mode():
    """Interactive mode for testing"""
    print("\n🎮 INTERACTIVE MODE")
    print("=" * 50)

    while True:
        print("\nOptions:")
        print("1. Generate full report (Utah Jazz)")
        print("2. Generate full report (Dallas Cowboys)")
        print("3. Generate full report (Carolina Panthers)")
        print("4. Generate for Jazz AND Panthers")
        print("5. Generate for all configured teams")
        print("6. Test single slide")
        print("7. List available teams")
        print("8. Test connection only")
        print("0. Exit")

        choice = input("\nSelect option: ").strip()

        if choice == '0':
            break

        elif choice == '1':
            quick_generate('utah_jazz')

        elif choice == '2':
            quick_generate('dallas_cowboys')

        elif choice == '3':
            quick_generate('carolina_panthers')

        elif choice == '4':
            generate_jazz_and_panthers()

        elif choice == '5':
            config = TeamConfigManager()
            all_teams = config.list_teams()
            print(f"\nGenerating for all {len(all_teams)} configured teams...")
            quick_generate_multiple(all_teams)

        elif choice == '6':
            slide_type = input("Slide type (demographics/behaviors/category:NAME): ").strip()
            team_key = input("Team key (utah_jazz/dallas_cowboys/carolina_panthers): ").strip()
            test_single_slide(slide_type, team_key)

        elif choice == '7':
            config = TeamConfigManager()
            teams = config.list_teams()
            print("\nAvailable teams:")
            for team in teams:
                team_config = config.get_team_config(team)
                print(f"  • {team}: {team_config['team_name']} ({team_config['league']})")

        elif choice == '8':
            if test_connection():
                print("✅ Connection successful!")
            else:
                print("❌ Connection failed!")

        else:
            print("Invalid option")

        input("\nPress Enter to continue...")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Quick PowerPoint generation for testing')
    parser.add_argument('team', nargs='?', help='Team key(s) - can be comma-separated for multiple teams')
    parser.add_argument('--interactive', '-i', action='store_true', help='Interactive mode')
    parser.add_argument('--slide', help='Test single slide type')
    parser.add_argument('--categories', nargs='+', help='Specific categories to generate')
    parser.add_argument('--jazz-panthers', action='store_true', help='Generate for Utah Jazz and Carolina Panthers')
    parser.add_argument('--all', action='store_true', help='Generate for all configured teams')

    args = parser.parse_args()

    if args.interactive:
        interactive_mode()
    elif args.jazz_panthers:
        generate_jazz_and_panthers()
    elif args.all:
        config = TeamConfigManager()
        all_teams = config.list_teams()
        quick_generate_multiple(all_teams)
    elif args.slide:
        team_key = args.team if args.team else 'utah_jazz'
        test_single_slide(args.slide, team_key)
    elif args.team:
        # Check if multiple teams specified
        if ',' in args.team:
            teams = [t.strip() for t in args.team.split(',')]
            quick_generate_multiple(teams, args.categories)
        else:
            quick_generate(args.team, args.categories)
    else:
        # Default: run for both Jazz and Panthers
        generate_jazz_and_panthers()