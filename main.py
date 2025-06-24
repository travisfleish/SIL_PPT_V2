# main.py
"""
Main script to generate PowerPoint sponsorship insights reports
Entry point for the Sports Innovation Lab PowerPoint generator
"""

import argparse
import logging
import sys
from pathlib import Path
from datetime import datetime
import traceback

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from report_builder.pptx_builder import PowerPointBuilder, build_report
from data_processors.snowflake_connector import test_connection
from utils.team_config_manager import TeamConfigManager


# Setup logging
def setup_logging(verbose: bool = False):
    """Setup logging configuration"""
    log_level = logging.DEBUG if verbose else logging.INFO
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    # Create logs directory
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)

    # Log file with timestamp
    log_file = log_dir / f'pptx_generator_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'

    # Configure logging
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )

    # Set specific loggers
    logging.getLogger('pptx').setLevel(logging.WARNING)  # Reduce noise from python-pptx

    return log_file


def validate_team(team_key: str) -> bool:
    """Validate that team configuration exists"""
    try:
        config_manager = TeamConfigManager()
        available_teams = config_manager.list_teams()

        if team_key not in available_teams:
            print(f"\n❌ Error: Team '{team_key}' not found")
            print(f"Available teams: {', '.join(available_teams)}")
            return False

        return True

    except Exception as e:
        print(f"\n❌ Error validating team: {str(e)}")
        return False


def generate_report(team_key: str,
                    skip_custom: bool = False,
                    custom_count: Optional[int] = None,
                    output_dir: Optional[Path] = None) -> Path:
    """
    Generate PowerPoint report for a team

    Args:
        team_key: Team identifier
        skip_custom: Whether to skip custom categories
        custom_count: Number of custom categories to include
        output_dir: Optional output directory

    Returns:
        Path to generated PowerPoint file
    """
    print(f"\n{'=' * 60}")
    print(f"GENERATING POWERPOINT REPORT")
    print(f"{'=' * 60}")

    # Get team info
    config_manager = TeamConfigManager()
    team_config = config_manager.get_team_config(team_key)

    print(f"\nTeam: {team_config['team_name']}")
    print(f"League: {team_config['league']}")
    print(f"View Prefix: {team_config['view_prefix']}")

    # Test Snowflake connection
    print("\n🔍 Testing Snowflake connection...")
    if not test_connection():
        raise Exception("Failed to connect to Snowflake")
    print("✅ Connected to Snowflake")

    # Build presentation
    print("\n📊 Building presentation...")
    print("This may take several minutes...")

    try:
        builder = PowerPointBuilder(team_key)

        # Override output directory if specified
        if output_dir:
            builder.output_dir = output_dir / f'{team_key}_{builder.timestamp}'
            builder.output_dir.mkdir(parents=True, exist_ok=True)

        # Build the presentation
        pptx_path = builder.build_presentation(
            include_custom_categories=not skip_custom,
            custom_category_count=custom_count
        )

        print(f"\n✅ SUCCESS! PowerPoint generated:")
        print(f"📁 {pptx_path}")

        # Print summary
        print(f"\n📋 Presentation Summary:")
        print(f"   • Total slides: {len(builder.slides_created)}")
        print(f"   • Fixed categories: 6" + (" + 2 (women's)" if "women" in team_config['team_name'].lower() else ""))
        if not skip_custom:
            print(
                f"   • Custom categories: {custom_count or (2 if 'women' in team_config['team_name'].lower() else 4)}")

        print(f"\n📂 Output directory: {builder.output_dir}")

        return pptx_path

    except Exception as e:
        print(f"\n❌ ERROR: Failed to generate PowerPoint")
        print(f"Error: {str(e)}")
        logging.error(traceback.format_exc())
        raise


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Generate PowerPoint sponsorship insights reports for sports teams',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py utah_jazz                    # Generate report for Utah Jazz
  python main.py dallas_cowboys --no-custom   # Generate without custom categories
  python main.py utah_jazz --custom-count 2   # Generate with only 2 custom categories
  python main.py --list-teams                 # List all available teams
        """
    )

    # Arguments
    parser.add_argument('team', nargs='?', help='Team key (e.g., utah_jazz, dallas_cowboys)')
    parser.add_argument('--list-teams', action='store_true', help='List all available teams')
    parser.add_argument('--no-custom', dest='skip_custom', action='store_true',
                        help='Skip custom category slides')
    parser.add_argument('--custom-count', type=int, help='Number of custom categories to include')
    parser.add_argument('--output-dir', type=Path, help='Output directory for generated files')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    parser.add_argument('--test-connection', action='store_true', help='Test Snowflake connection only')

    args = parser.parse_args()

    # Setup logging
    log_file = setup_logging(args.verbose)

    print("\n🏀 Sports Innovation Lab - PowerPoint Generator")
    print("=" * 50)

    try:
        # List teams
        if args.list_teams:
            config_manager = TeamConfigManager()
            teams = config_manager.list_teams()

            print("\n📋 Available teams:")
            for team in teams:
                team_config = config_manager.get_team_config(team)
                print(f"   • {team:<20} - {team_config['team_name']}")

            return 0

        # Test connection
        if args.test_connection:
            print("\n🔍 Testing Snowflake connection...")
            if test_connection():
                print("✅ Connection successful!")
                return 0
            else:
                print("❌ Connection failed!")
                return 1

        # Check if team was provided
        if not args.team:
            parser.print_help()
            return 1

        # Validate team
        if not validate_team(args.team):
            return 1

        # Generate report
        start_time = datetime.now()

        pptx_path = generate_report(
            team_key=args.team,
            skip_custom=args.skip_custom,
            custom_count=args.custom_count,
            output_dir=args.output_dir
        )

        # Calculate duration
        duration = datetime.now() - start_time
        minutes = int(duration.total_seconds() / 60)
        seconds = int(duration.total_seconds() % 60)

        print(f"\n⏱️  Generation time: {minutes}m {seconds}s")
        print(f"📝 Log file: {log_file}")

        return 0

    except KeyboardInterrupt:
        print("\n\n⚠️  Generation cancelled by user")
        return 130

    except Exception as e:
        print(f"\n\n❌ Fatal error: {str(e)}")
        logging.error(traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main())