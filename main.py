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
from typing import Optional, List, Dict
from pptx import Presentation
from pptx.util import Inches

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


def generate_single_slide(team_key: str,
                         slide_type: str,
                         output_dir: Optional[Path] = None) -> Path:
    """
    Generate a single slide for testing/preview

    Args:
        team_key: Team identifier
        slide_type: Type of slide (demographics, behaviors, category:NAME)
        output_dir: Optional output directory

    Returns:
        Path to generated PowerPoint file
    """
    print(f"\n{'=' * 60}")
    print(f"GENERATING SINGLE SLIDE: {slide_type.upper()}")
    print(f"{'=' * 60}")

    # Get team info
    config_manager = TeamConfigManager()
    team_config = config_manager.get_team_config(team_key)

    print(f"\nTeam: {team_config['team_name']}")
    print(f"Slide Type: {slide_type}")

    # Test connection
    print("\n🔍 Testing Snowflake connection...")
    if not test_connection():
        raise Exception("Failed to connect to Snowflake")
    print("✅ Connected to Snowflake")

    # Create presentation with SIL template
    print("\n📊 Creating presentation...")

    # Load the SIL template
    TEMPLATE_PATH = Path(__file__).parent / 'templates' / 'sil_combined_template.pptx'
    if TEMPLATE_PATH.exists():
        pres = Presentation(str(TEMPLATE_PATH))
        logging.info("Loaded SIL template")
    else:
        pres = Presentation()
        logging.warning("Template not found, using blank presentation")

    # Set 16:9 dimensions
    pres.slide_width = Inches(13.333)
    pres.slide_height = Inches(7.5)

    # Create output directory
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_base = output_dir or Path('output')
    slide_output_dir = output_base / f'single_slides/{team_key}_{timestamp}'
    slide_output_dir.mkdir(parents=True, exist_ok=True)

    # Generate the specific slide
    if slide_type == 'demographics':
        from slide_generators.demographics_slide import DemographicsSlide
        from data_processors.demographic_processor import DemographicsProcessor
        from data_processors.snowflake_connector import query_to_dataframe
        from visualizations.demographic_charts import DemographicCharts

        print("\n📈 Processing demographics data...")

        # Get demographics view name using TeamConfigManager
        demographics_view = config_manager.get_view_name(team_key, 'demographics')
        query = f"SELECT * FROM {demographics_view}"
        print(f"   • Querying view: {demographics_view}")

        df = query_to_dataframe(query)
        print(f"   • Fetched {len(df):,} records")

        # Process with DemographicsProcessor
        processor = DemographicsProcessor(
            data_source=df,
            team_name=team_config['team_name'],
            league=team_config['league'],
            comparison_population=team_config.get('comparison_population')
        )
        data = processor.process_all_demographics()

        # Generate charts
        chart_dir = slide_output_dir / 'charts'
        chart_dir.mkdir(exist_ok=True)

        print("\n📊 Generating demographic charts...")
        charter = DemographicCharts(
            team_colors=team_config.get('colors'),
            team_config=team_config
        )
        charts = charter.create_all_demographic_charts(
            data,
            output_dir=chart_dir
        )
        print(f"   • Generated {len(charts)} charts")

        generator = DemographicsSlide(pres)
        pres = generator.generate(data, chart_dir, team_config)

    elif slide_type == 'behaviors':
        from slide_generators.behaviors_slide import BehaviorsSlide
        from data_processors.merchant_ranker import MerchantRanker

        print("\n🎯 Processing behaviors data...")
        ranker = MerchantRanker(
            team_view_prefix=team_config['view_prefix'],
            comparison_population=team_config.get('comparison_population')
        )

        generator = BehaviorsSlide(pres)
        pres = generator.generate(ranker, team_config)

    elif slide_type.startswith('category:'):
        from slide_generators.category_slide import CategorySlide
        from data_processors.category_analyzer import CategoryAnalyzer
        from data_processors.snowflake_connector import query_to_dataframe

        category_name = slide_type.split(':', 1)[1]
        print(f"\n📊 Processing category: {category_name}")

        analyzer = CategoryAnalyzer(
            team_name=team_config['team_name'],
            team_short=team_config['team_name_short'],
            league=team_config['league'],
            comparison_population=team_config['comparison_population'],
            audience_name=team_config.get('audience_name')
        )
        
        # Fetch the required data for the category
        view_prefix = team_config['view_prefix']
        
        # Get category configuration to find the category names in data
        category_config = analyzer.categories.get(category_name.lower(), {})
        cat_names = category_config.get('category_names_in_data', [category_name])
        
        if not cat_names:
            raise ValueError(f"No configuration found for category: {category_name}")
        
        # Build WHERE clause
        category_where = " OR ".join([f"TRIM(CATEGORY) = '{cat.strip()}'" for cat in cat_names])
        
        # Load data
        category_df = query_to_dataframe(f"""
            SELECT * FROM {view_prefix}_CATEGORY_INDEXING_ALL_TIME 
            WHERE {category_where}
        """)
        
        subcategory_df = query_to_dataframe(f"""
            SELECT * FROM {view_prefix}_SUBCATEGORY_INDEXING_ALL_TIME 
            WHERE {category_where}
        """)
        
        merchant_df = query_to_dataframe(f"""
            SELECT * FROM {view_prefix}_MERCHANT_INDEXING_ALL_TIME 
            WHERE {category_where}
            AND AUDIENCE = '{analyzer.audience_name}'
            ORDER BY PERC_AUDIENCE DESC
        """)
        
        # Load LAST_FULL_YEAR data for specific insights
        subcategory_last_year_df = query_to_dataframe(f"""
            SELECT * FROM {view_prefix}_SUBCATEGORY_INDEXING_LAST_FULL_YEAR 
            WHERE {category_where}
        """)
        
        merchant_last_year_df = query_to_dataframe(f"""
            SELECT * FROM {view_prefix}_MERCHANT_INDEXING_LAST_FULL_YEAR 
            WHERE {category_where}
            AND AUDIENCE = '{analyzer.audience_name}'
            ORDER BY PERC_AUDIENCE DESC
        """)
        
        # Analyze category with the fetched data
        analysis = analyzer.analyze_category(
            category_key=category_name.lower(),
            category_df=category_df,
            subcategory_df=subcategory_df,
            merchant_df=merchant_df,
            subcategory_last_year_df=subcategory_last_year_df,
            merchant_last_year_df=merchant_last_year_df,
            validate=False
        )

        if not analysis:
            raise ValueError(f"Category '{category_name}' not found or has no data")

        generator = CategorySlide(pres)
        pres = generator.generate(analysis, team_config, 0)

    else:
        raise ValueError(f"Unknown slide type: {slide_type}")

    # Save the presentation
    output_file = slide_output_dir / f'{team_key}_{slide_type.replace(":", "_")}_{timestamp}.pptx'
    pres.save(str(output_file))

    print(f"\n✅ SUCCESS! Slide generated:")
    print(f"📁 {output_file}")

    return output_file


def generate_report(team_key: str,
                    skip_custom: bool = False,
                    custom_count: Optional[int] = None,
                    output_dir: Optional[Path] = None,
                    category_mode: Optional[str] = None,
                    custom_categories: Optional[List[str]] = None) -> Path:
    """
    Generate PowerPoint report for a team

    Args:
        team_key: Team identifier
        skip_custom: Whether to skip custom categories
        custom_count: Number of custom categories to include
        output_dir: Optional output directory
        category_mode: Override category mode ('standard' or 'custom')
        custom_categories: List of custom categories for custom mode

    Returns:
        Path to generated PowerPoint file
    """
    print(f"\n{'=' * 60}")
    print(f"GENERATING POWERPOINT REPORT")
    print(f"{'=' * 60}")

    # Get team info
    config_manager = TeamConfigManager()
    team_config = config_manager.get_team_config(team_key)

    # Override category mode if specified via command line
    if category_mode:
        print(f"\n🔄 Overriding category mode: {category_mode}")
        team_config = team_config.copy()  # Create a copy to avoid modifying original
        team_config['category_mode'] = category_mode
        
        if category_mode == 'custom' and custom_categories:
            team_config['custom_categories'] = {
                'count': len(custom_categories),
                'selected_categories': custom_categories,
                'thresholds': {
                    'min_audience_pct': 0.20,  # Default thresholds
                    'min_merchant_audience_pct': 0.10
                }
            }
            print(f"   • Custom categories: {', '.join(custom_categories)}")
        elif category_mode == 'standard':
            # Remove custom category config if switching to standard
            if 'custom_categories' in team_config:
                del team_config['custom_categories']

    print(f"\nTeam: {team_config['team_name']}")
    print(f"League: {team_config['league']}")
    print(f"View Prefix: {team_config['view_prefix']}")
    print(f"Category Mode: {team_config.get('category_mode', 'standard')}")

    # Test Snowflake connection
    print("\n🔍 Testing Snowflake connection...")
    if not test_connection():
        raise Exception("Failed to connect to Snowflake")
    print("✅ Connected to Snowflake")

    # Build presentation
    print("\n📊 Building presentation...")
    print("This may take several minutes...")

    try:
        # Create a custom TeamConfigManager that returns our modified config
        class OverrideTeamConfigManager(TeamConfigManager):
            def __init__(self, override_config):
                self.override_config = override_config
                super().__init__()
            
            def get_team_config(self, team_key):
                return self.override_config
        
        # Create builder with overridden config
        builder = PowerPointBuilder(team_key)
        
        # Override the team config in the builder
        builder.team_config = team_config
        builder.config_manager = OverrideTeamConfigManager(team_config)

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


def generate_multiple_reports(teams: List[str],
                            skip_custom: bool = False,
                            custom_count: Optional[int] = None,
                            output_dir: Optional[Path] = None,
                            category_mode: Optional[str] = None,
                            custom_categories: Optional[List[str]] = None) -> Dict[str, Dict]:
    """
    Generate reports for multiple teams

    Args:
        teams: List of team keys
        skip_custom: Whether to skip custom categories
        custom_count: Number of custom categories to include
        output_dir: Optional output directory
        category_mode: Override category mode ('standard' or 'custom')
        custom_categories: List of custom categories for custom mode

    Returns:
        Dictionary with results for each team
    """
    results = {}
    total_teams = len(teams)

    print(f"\n{'='*60}")
    print(f"BATCH MODE: Processing {total_teams} teams")
    print(f"{'='*60}")

    # Create shared output directory with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    batch_output_dir = output_dir or Path('output') / f'batch_{timestamp}'
    batch_output_dir.mkdir(parents=True, exist_ok=True)

    for i, team_key in enumerate(teams, 1):
        print(f"\n[{i}/{total_teams}] Processing {team_key}")
        print("-" * 40)

        try:
            start_time = datetime.now()

            # Generate report for this team
            pptx_path = generate_report(
                team_key=team_key,
                skip_custom=skip_custom,
                custom_count=custom_count,
                output_dir=batch_output_dir,
                category_mode=category_mode,
                custom_categories=custom_categories
            )

            duration = datetime.now() - start_time

            results[team_key] = {
                'success': True,
                'path': str(pptx_path),
                'duration': duration.total_seconds()
            }

        except Exception as e:
            results[team_key] = {
                'success': False,
                'error': str(e),
                'duration': 0
            }
            logging.error(f"Failed to generate report for {team_key}: {str(e)}")

    # Print summary
    print(f"\n{'='*60}")
    print(f"BATCH SUMMARY")
    print(f"{'='*60}")

    successful = sum(1 for r in results.values() if r['success'])
    failed = total_teams - successful

    print(f"\nTotal teams: {total_teams}")
    print(f"✅ Successful: {successful}")
    print(f"❌ Failed: {failed}")

    # Show individual results
    print(f"\nResults:")
    for team_key, result in results.items():
        if result['success']:
            print(f"  ✅ {team_key} - {result['duration']:.1f}s")
        else:
            print(f"  ❌ {team_key} - Error: {result['error']}")

    print(f"\n📂 Output directory: {batch_output_dir}")

    return results


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Generate PowerPoint sponsorship insights reports for sports teams',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py utah_jazz                        # Single team
  python main.py utah_jazz dallas_cowboys         # Multiple teams (space-separated)
  python main.py utah_jazz,dallas_cowboys         # Multiple teams (comma-separated)
  python main.py utah_jazz demographics           # Single slide for a team
  python main.py utah_jazz behaviors              # Behaviors slide only
  python main.py utah_jazz category:Restaurants  # Specific category slide
  
  # Category mode overrides:
  python main.py utah_jazz --category-mode custom --custom-categories "Restaurants,Athleisure,Finance"
  python main.py utah_jazz --category-mode standard
  
  python main.py --list-teams                     # List all available teams
  python main.py --list-slides                    # List available slide types
        """
    )

    # Arguments - support both teams and slide type
    parser.add_argument('teams', nargs='*', help='Team key(s) - space or comma-separated, optionally followed by slide type')
    parser.add_argument('--slide', help='Generate single slide type (demographics, behaviors, category:NAME)')
    parser.add_argument('--list-teams', action='store_true', help='List all available teams')
    parser.add_argument('--list-slides', action='store_true', help='List available slide types')
    parser.add_argument('--no-custom', dest='skip_custom', action='store_true',
                        help='Skip custom category slides')
    parser.add_argument('--custom-count', type=int, help='Number of custom categories to include')
    parser.add_argument('--category-mode', choices=['standard', 'custom'], 
                        help='Override category mode: standard (6+4) or custom (selected categories)')
    parser.add_argument('--custom-categories', type=str, 
                        help='Comma-separated list of categories for custom mode (e.g., "Restaurants,Athleisure,Finance")')
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

        # List slides
        if args.list_slides:
            print("\n📋 Available slide types:")
            print("   • demographics    - Fan demographic analysis")
            print("   • behaviors       - Fan behavior wheel and community indices")
            print("   • category:NAME   - Specific category analysis (e.g., category:Restaurants)")
            print("\n   Fixed categories:")
            print("     - Restaurants, Athleisure, Finance, Gambling, Travel, Auto")
            print("   \n   For custom categories, generate a full report first to see available options.")
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

        # Check if teams were provided
        if not args.teams:
            parser.print_help()
            return 1

        # Check if this is a single slide request
        # Pattern: team_name slide_type (e.g., "utah_jazz demographics")
        if len(args.teams) == 2 and not ',' in args.teams[0] and args.teams[1] in ['demographics', 'behaviors'] or (len(args.teams) == 2 and args.teams[1].startswith('category:')):
            # Single slide generation
            team_key = args.teams[0]
            slide_type = args.teams[1]

            # Validate team
            if not validate_team(team_key):
                return 1

            # Generate single slide
            start_time = datetime.now()

            slide_path = generate_single_slide(
                team_key=team_key,
                slide_type=slide_type,
                output_dir=args.output_dir
            )

            # Calculate duration
            duration = datetime.now() - start_time
            seconds = int(duration.total_seconds())

            print(f"\n⏱️  Generation time: {seconds}s")
            print(f"📝 Log file: {log_file}")

            return 0

        # Check if --slide option is used
        if args.slide:
            # Using --slide option with team(s)
            teams_to_process = []
            for team_arg in args.teams:
                if ',' in team_arg:
                    teams_to_process.extend([t.strip() for t in team_arg.split(',')])
                else:
                    teams_to_process.append(team_arg.strip())

            # Generate single slide for each team
            for team_key in teams_to_process:
                if not validate_team(team_key):
                    continue

                print(f"\nGenerating {args.slide} slide for {team_key}...")
                generate_single_slide(
                    team_key=team_key,
                    slide_type=args.slide,
                    output_dir=args.output_dir
                )

            return 0

        # Parse teams - could be space-separated or comma-separated
        teams_to_process = []
        for team_arg in args.teams:
            if ',' in team_arg:
                # Split comma-separated teams
                teams_to_process.extend([t.strip() for t in team_arg.split(',')])
            else:
                teams_to_process.append(team_arg.strip())

        # Remove empty strings and duplicates
        teams_to_process = list(filter(None, teams_to_process))
        teams_to_process = list(dict.fromkeys(teams_to_process))  # Remove duplicates while preserving order

        # Check if multiple teams
        if len(teams_to_process) > 1:
            # Validate all teams
            invalid_teams = []
            for team_key in teams_to_process:
                if not validate_team(team_key):
                    invalid_teams.append(team_key)

            if invalid_teams:
                print(f"\n❌ Invalid teams: {', '.join(invalid_teams)}")
                return 1

            # Generate reports for all teams
            start_time = datetime.now()

            results = generate_multiple_reports(
                teams=teams_to_process,
                skip_custom=args.skip_custom,
                custom_count=args.custom_count,
                output_dir=args.output_dir,
                category_mode=args.category_mode,
                custom_categories=args.custom_categories.split(',') if args.custom_categories else None
            )

            # Check if any failed
            failed_count = sum(1 for r in results.values() if not r['success'])

            # Calculate total duration
            duration = datetime.now() - start_time
            minutes = int(duration.total_seconds() / 60)
            seconds = int(duration.total_seconds() % 60)

            print(f"\n⏱️  Total generation time: {minutes}m {seconds}s")
            print(f"📝 Log file: {log_file}")

            # Return error code if any failed
            return 1 if failed_count > 0 else 0

        else:
            # Single team processing
            team_key = teams_to_process[0]

            # Validate team
            if not validate_team(team_key):
                return 1

            # Generate report
            start_time = datetime.now()

            pptx_path = generate_report(
                team_key=team_key,
                skip_custom=args.skip_custom,
                custom_count=args.custom_count,
                output_dir=args.output_dir,
                category_mode=args.category_mode,
                custom_categories=args.custom_categories.split(',') if args.custom_categories else None
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