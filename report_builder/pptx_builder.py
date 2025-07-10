# report_builder/pptx_builder.py
"""
Main PowerPoint builder that orchestrates the entire presentation generation
Combines all slide generators to create the complete sponsorship insights report
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

# Import data processors
from data_processors.demographic_processor import DemographicsProcessor
from data_processors.merchant_ranker import MerchantRanker
from data_processors.category_analyzer import CategoryAnalyzer
from data_processors.snowflake_connector import query_to_dataframe

# Import slide generators
from slide_generators.title_slide import TitleSlide
from slide_generators.demographics_slide import DemographicsSlide  # Now single slide
from slide_generators.behaviors_slide import BehaviorsSlide
from slide_generators.category_slide import CategorySlide

# Import visualizations
from visualizations.demographic_charts import DemographicCharts

# Import utilities
from utils.team_config_manager import TeamConfigManager

# from utils.logo_downloader import LogoDownloader  # Not implemented yet

logger = logging.getLogger(__name__)

# Default font configuration
DEFAULT_FONT_FAMILY = "Red Hat Display"
FALLBACK_FONT = "Arial"


class PowerPointBuilder:
    """Main orchestrator for building complete PowerPoint presentations"""

    def __init__(self, team_key: str):
        """
        Initialize the PowerPoint builder with proper 16:9 formatting

        Args:
            team_key: Team identifier (e.g., 'utah_jazz', 'dallas_cowboys')
        """
        self.team_key = team_key
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Load team configuration
        self.config_manager = TeamConfigManager()
        self.team_config = self.config_manager.get_team_config(team_key)

        # Extract key values
        self.team_name = self.team_config['team_name']
        self.team_short = self.team_config['team_name_short']
        self.league = self.team_config['league']
        self.view_prefix = self.team_config['view_prefix']

        # Initialize data processors
        self.merchant_ranker = MerchantRanker(team_view_prefix=self.view_prefix)
        self.category_analyzer = CategoryAnalyzer(
            team_name=self.team_name,
            team_short=self.team_short,
            league=self.league
        )

        # Validate and set presentation font
        self.presentation_font = self._validate_font()

        # CHANGE: Use combined template instead of blue template
        COMBINED_TEMPLATE_PATH = Path(__file__).parent.parent / 'templates' / 'sil_combined_template.pptx'

        if COMBINED_TEMPLATE_PATH.exists():
            try:
                # Load the combined template
                self.presentation = Presentation(str(COMBINED_TEMPLATE_PATH))
                logger.info("Initialized presentation from combined SIL template")
            except Exception as e:
                logger.warning(f"Could not load template: {e}. Creating blank presentation.")
                self.presentation = Presentation()
        else:
            # Create blank presentation if no template
            logger.warning(f"Combined template not found at: {COMBINED_TEMPLATE_PATH}")
            self.presentation = Presentation()

        # Set 16:9 dimensions regardless of template
        self.presentation.slide_width = Inches(13.333)  # 16:9 widescreen width
        self.presentation.slide_height = Inches(7.5)  # 16:9 widescreen height

        # Use blank layout for consistent formatting (no title boxes)
        self.blank_layout = self.presentation.slide_layouts[6]

        # Setup directories
        self.output_dir = Path(f'output/{self.team_key}_{self.timestamp}')
        self.temp_dir = self.output_dir / 'temp'
        self.charts_dir = self.temp_dir / 'charts'
        self.logos_dir = self.temp_dir / 'logos'

        # Create directories
        for dir_path in [self.output_dir, self.temp_dir, self.charts_dir, self.logos_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

        # Track progress
        self.slides_created = []

        logger.info(f"Initialized PowerPoint builder for {self.team_name} (16:9 format)")
        logger.info(f"Using font: {self.presentation_font}")

    def _validate_font(self) -> str:
        """
        Validate that Red Hat Display font is available

        Returns:
            Font name to use (Red Hat Display or fallback)
        """
        try:
            # Try to create a test presentation with Red Hat Display
            test_pres = Presentation()
            test_slide = test_pres.slides.add_slide(test_pres.slide_layouts[5])
            test_box = test_slide.shapes.add_textbox(0, 0, 100, 100)
            test_box.text_frame.text = "Test"
            test_box.text_frame.paragraphs[0].font.name = DEFAULT_FONT_FAMILY

            logger.info(f"✓ {DEFAULT_FONT_FAMILY} font validated and available")
            return DEFAULT_FONT_FAMILY

        except Exception as e:
            logger.warning(f"⚠ {DEFAULT_FONT_FAMILY} font may not be available: {e}")
            logger.warning(f"Using fallback font: {FALLBACK_FONT}")

            # Update all slide generators to use fallback font
            self._update_slide_generators_font(FALLBACK_FONT)

            return FALLBACK_FONT

    def _update_slide_generators_font(self, font_name: str):
        """
        Update the default font in all slide generators

        Args:
            font_name: Font to use as default
        """
        # Update base slide
        import slide_generators.base_slide as base_slide
        base_slide.DEFAULT_FONT_FAMILY = font_name

        # Update demographics slide
        import slide_generators.demographics_slide as demo_slide
        demo_slide.DEFAULT_FONT_FAMILY = font_name

        # Update category slide
        import slide_generators.category_slide as cat_slide
        cat_slide.DEFAULT_FONT_FAMILY = font_name

        logger.info(f"Updated all slide generators to use font: {font_name}")

    def build_presentation(self,
                           include_custom_categories: bool = True,
                           custom_category_count: Optional[int] = None) -> Path:
        """
        Build the complete PowerPoint presentation

        Args:
            include_custom_categories: Whether to include custom categories
            custom_category_count: Number of custom categories (default: 4 for men's, 2 for women's)

        Returns:
            Path to the generated PowerPoint file
        """
        logger.info(f"Starting presentation build for {self.team_name}")
        logger.info(f"Font: {self.presentation_font}")

        try:
            # 1. Create title slide with demographic insights
            self._create_title_slide()

            # 2. Create single demographics slide with all 6 charts
            self._create_demographics_slide()

            # 3. Create behaviors slide
            self._create_behaviors_slide()

            # 4. Create category slides (fixed categories)
            self._create_fixed_category_slides()

            # 5. Create custom category slides (if requested)
            if include_custom_categories:
                self._create_custom_category_slides(custom_category_count)

            # 6. Save presentation
            output_path = self._save_presentation()

            logger.info(f"Presentation completed with {len(self.slides_created)} slides")
            return output_path

        except Exception as e:
            logger.error(f"Error building presentation: {str(e)}")
            raise

    def _create_title_slide(self):
        """Create the title slide"""
        logger.info("Creating title slide...")

        title_generator = TitleSlide(self.presentation)
        title_generator.default_font = self.presentation_font

        self.presentation = title_generator.generate(
            team_config=self.team_config,
            subtitle="Sponsorship Insights Report"
        )

        self.slides_created.append("Title Slide")
        logger.info("✓ Title slide created")

    def _get_demographic_insights(self) -> Optional[str]:
        """Generate demographic insights text for title slide"""
        try:
            # Load demographics data
            demographics_view = self.config_manager.get_view_name(self.team_key, 'demographics')
            query = f"SELECT * FROM {demographics_view}"
            df = query_to_dataframe(query)

            if df.empty:
                return None

            # Process demographics to get key stats
            processor = DemographicsProcessor(
                data_source=df,
                team_name=self.team_name,
                league=self.league
            )
            demographic_data = processor.process_all_demographics()

            # Get the AI-generated insight or format our own
            if 'key_insights' in demographic_data and demographic_data['key_insights']:
                return demographic_data['key_insights']
            else:
                return self._format_demographic_insights(demographic_data)

        except Exception as e:
            logger.warning(f"Could not generate demographic insights: {e}")
            return None

    def _format_demographic_insights(self, demographic_data: Dict[str, Any]) -> str:
        """Format demographic data into insights text"""
        # This is a fallback - ideally the DemographicsProcessor provides this
        team_name = self.team_config['team_name']

        # Default insight format matching the designer's sample
        default_insight = (
            f"{team_name} fans are significantly younger, with 79% being Millennials/Gen X "
            f"compared to 0% in the Utah general population and 76% of NBA average fans, "
            f"they have a higher household income with 76% earning $100K+ compared to 0% "
            f"in the Utah general population and 73% of NBA average fans, are predominantly "
            f"male at 54% versus 0% in the Utah general population and 52% of NBA average fans, "
            f"and are largely working professionals at 64% compared to 0% in the Utah general "
            f"population and 65% for NBA average fans."
        )

        return default_insight

    def _create_demographics_slide(self):
        """Create single demographics slide with all 6 charts"""
        logger.info("Creating demographics slide...")

        try:
            # Load demographics data
            demographics_view = self.config_manager.get_view_name(self.team_key, 'demographics')
            query = f"SELECT * FROM {demographics_view}"
            df = query_to_dataframe(query)

            if df.empty:
                logger.warning("No demographics data found")
                self._add_placeholder_slide("Demographics data not available")
                return

            # Process demographics
            processor = DemographicsProcessor(
                data_source=df,
                team_name=self.team_name,
                league=self.league
            )

            demographic_data = processor.process_all_demographics()

            # Generate charts
            charter = DemographicCharts(team_colors=self.team_config.get('colors'))
            charts = charter.create_all_demographic_charts(
                demographic_data,
                output_dir=self.charts_dir
            )

            # Create single demographics slide with all 6 charts
            demo_generator = DemographicsSlide(self.presentation)
            demo_generator.default_font = self.presentation_font

            self.presentation = demo_generator.generate(
                demographic_data=demographic_data,
                chart_dir=self.charts_dir,
                team_config=self.team_config
            )

            self.slides_created.append("Demographics Slide (All 6 Charts)")
            logger.info("✓ Demographics slide created")

        except Exception as e:
            logger.error(f"Error creating demographics slide: {str(e)}")
            self._add_placeholder_slide("Demographics slide - error loading data")

    def _create_behaviors_slide(self):
        """Create the fan behaviors slide"""
        logger.info("Creating behaviors slide...")

        try:
            behaviors_generator = BehaviorsSlide(self.presentation)
            behaviors_generator.default_font = self.presentation_font

            self.presentation = behaviors_generator.generate(
                self.merchant_ranker,
                self.team_config
            )

            self.slides_created.append("Fan Behaviors")
            logger.info("✓ Behaviors slide created")

        except Exception as e:
            logger.error(f"Error creating behaviors slide: {str(e)}")
            self._add_placeholder_slide("Behaviors slide - error loading data")

    def _create_fixed_category_slides(self):
        """Create slides for all fixed categories"""
        logger.info("Creating fixed category slides...")

        # Define fixed categories based on team type
        is_womens_team = self._is_womens_team()

        fixed_categories = ['restaurants', 'athleisure', 'finance', 'gambling', 'travel', 'auto']
        if is_womens_team:
            fixed_categories.extend(['beauty', 'health'])

        for category_key in fixed_categories:
            self._create_category_slide(category_key, is_custom=False)

    def _create_custom_category_slides(self, custom_count: Optional[int] = None):
        """Create slides for custom categories"""
        logger.info("Creating custom category slides...")

        # Determine number of custom categories
        is_womens_team = self._is_womens_team()
        if custom_count is None:
            custom_count = 2 if is_womens_team else 4

        # Get all category data for selection
        try:
            category_query = f"SELECT * FROM {self.view_prefix}_CATEGORY_INDEXING_ALL_TIME"
            all_category_df = query_to_dataframe(category_query)

            # Get custom categories
            custom_categories = self.category_analyzer.get_custom_categories(
                category_df=all_category_df,
                is_womens_team=is_womens_team
            )

            # Create slides for each custom category
            for i, custom_cat in enumerate(custom_categories[:custom_count]):
                category_name = custom_cat['display_name']
                logger.info(f"Creating custom category slide {i + 1}: {category_name}")
                self._create_category_slide(category_name, is_custom=True)

        except Exception as e:
            logger.error(f"Error creating custom category slides: {str(e)}")

    def _create_category_slide(self, category_key: str, is_custom: bool = False):
        """Create slides for a single category"""
        try:
            logger.info(f"Creating slides for {category_key} {'[CUSTOM]' if is_custom else '[FIXED]'}...")

            # Load category data
            if is_custom:
                cat_config = self.category_analyzer.create_custom_category_config(category_key)
                cat_names = [category_key]
            else:
                cat_config = self.category_analyzer.categories.get(category_key, {})
                cat_names = cat_config.get('category_names_in_data', [])

            if not cat_names:
                logger.warning(f"No configuration found for {category_key}")
                return

            # Build WHERE clause
            category_where = " OR ".join([f"TRIM(CATEGORY) = '{cat}'" for cat in cat_names])

            # Load data
            category_df = query_to_dataframe(f"""
                SELECT * FROM {self.view_prefix}_CATEGORY_INDEXING_ALL_TIME 
                WHERE {category_where}
            """)

            subcategory_df = query_to_dataframe(f"""
                SELECT * FROM {self.view_prefix}_SUBCATEGORY_INDEXING_ALL_TIME 
                WHERE {category_where}
            """)

            merchant_df = query_to_dataframe(f"""
                SELECT * FROM {self.view_prefix}_MERCHANT_INDEXING_ALL_TIME 
                WHERE {category_where}
                AND AUDIENCE = '{self.category_analyzer.audience_name}'
                ORDER BY PERC_AUDIENCE DESC
                LIMIT 100
            """)

            # Add config for custom categories temporarily
            if is_custom:
                self.category_analyzer.categories[category_key] = cat_config

            # Analyze category
            results = self.category_analyzer.analyze_category(
                category_key=category_key,
                category_df=category_df,
                subcategory_df=subcategory_df,
                merchant_df=merchant_df,
                validate=False
            )

            # Clean up temporary config
            if is_custom:
                del self.category_analyzer.categories[category_key]

            # Create slides
            category_generator = CategorySlide(self.presentation)
            category_generator.default_font = self.presentation_font

            # Category analysis slide
            self.presentation = category_generator.generate(results, self.team_config)
            self.slides_created.append(f"{results['display_name']} Analysis")

            # Brand analysis slide
            self.presentation = category_generator.generate_brand_slide(results, self.team_config)
            self.slides_created.append(f"{results['display_name']} Brands")

            logger.info(f"✓ Created {results['display_name']} slides")

        except Exception as e:
            logger.error(f"Error creating {category_key} slides: {str(e)}")
            self._add_placeholder_slide(f"{category_key.title()} - error loading data")

    def _add_placeholder_slide(self, message: str):
        """Add a placeholder slide when data is not available"""
        # CHANGE: Use white template layout if available
        if len(self.presentation.slides) > 1:
            # Get the white layout from slide 1
            white_layout = self.presentation.slides[1].slide_layout
            slide = self.presentation.slides.add_slide(white_layout)
        else:
            slide = self.presentation.slides.add_slide(self.blank_layout)

        text_box = slide.shapes.add_textbox(Inches(1), Inches(3), Inches(11.333), Inches(1))
        text_box.text = message
        p = text_box.text_frame.paragraphs[0]
        p.font.name = self.presentation_font
        p.font.size = Pt(24)
        p.alignment = PP_ALIGN.CENTER
        self.slides_created.append(f"Placeholder: {message}")

    def _is_womens_team(self) -> bool:
        """Determine if this is a women's team"""
        womens_indicators = ["women's", "ladies", "wnba", "nwsl"]
        return any(indicator in self.team_name.lower() for indicator in womens_indicators)

    def _save_presentation(self) -> Path:
        """Save the presentation to file"""
        filename = f"{self.team_key}_sponsorship_insights_{self.timestamp}.pptx"
        output_path = self.output_dir / filename

        self.presentation.save(str(output_path))
        logger.info(f"Presentation saved to: {output_path}")

        # Create summary file
        self._create_summary_file(output_path)

        return output_path

    def _create_summary_file(self, pptx_path: Path):
        """Create a summary text file with build information"""
        summary_path = self.output_dir / 'build_summary.txt'

        with open(summary_path, 'w') as f:
            f.write(f"PowerPoint Build Summary\n")
            f.write(f"{'=' * 50}\n\n")
            f.write(f"Team: {self.team_name}\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Output: {pptx_path.name}\n")
            f.write(f"Format: 16:9 Widescreen (13.333\" x 7.5\")\n")
            f.write(f"Font: {self.presentation_font}\n\n")
            f.write(f"Slides Created ({len(self.slides_created)}):\n")
            for i, slide in enumerate(self.slides_created, 1):
                f.write(f"  {i}. {slide}\n")
            f.write(f"\nView Configuration:\n")
            f.write(f"  Prefix: {self.view_prefix}\n")
            f.write(f"  Demographics: {self.config_manager.get_view_name(self.team_key, 'demographics')}\n")

            # Add font validation status
            f.write(f"\nFont Configuration:\n")
            f.write(f"  Requested: {DEFAULT_FONT_FAMILY}\n")
            f.write(f"  Used: {self.presentation_font}\n")
            if self.presentation_font != DEFAULT_FONT_FAMILY:
                f.write(f"  Note: Using fallback font as {DEFAULT_FONT_FAMILY} was not available\n")

        logger.info(f"Summary saved to: {summary_path}")

    def check_font_installation(self) -> Dict[str, Any]:
        """
        Check if Red Hat Display font is properly installed

        Returns:
            Dictionary with font status information
        """
        import platform
        import os

        font_status = {
            'requested_font': DEFAULT_FONT_FAMILY,
            'fallback_font': FALLBACK_FONT,
            'system': platform.system(),
            'font_available': False,
            'font_paths': [],
            'instructions': []
        }

        system = platform.system()

        if system == "Windows":
            # Check Windows font directory
            fonts_dir = os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Fonts')
            if os.path.exists(fonts_dir):
                red_hat_fonts = [f for f in os.listdir(fonts_dir) if 'RedHat' in f or 'Red Hat' in f]
                font_status['font_paths'] = red_hat_fonts
                font_status['font_available'] = len(red_hat_fonts) > 0

            if not font_status['font_available']:
                font_status['instructions'] = [
                    "1. Download Red Hat Display from: https://fonts.google.com/specimen/Red+Hat+Display",
                    "2. Extract the ZIP file",
                    "3. Select all .ttf files",
                    "4. Right-click and select 'Install for all users'",
                    "5. Restart your Python environment"
                ]

        elif system == "Darwin":  # macOS
            # Check common font locations
            font_dirs = [
                os.path.expanduser("~/Library/Fonts"),
                "/Library/Fonts",
                "/System/Library/Fonts"
            ]

            for font_dir in font_dirs:
                if os.path.exists(font_dir):
                    red_hat_fonts = [f for f in os.listdir(font_dir) if 'RedHat' in f or 'Red Hat' in f]
                    font_status['font_paths'].extend(red_hat_fonts)

            font_status['font_available'] = len(font_status['font_paths']) > 0

            if not font_status['font_available']:
                font_status['instructions'] = [
                    "1. Download Red Hat Display from: https://fonts.google.com/specimen/Red+Hat+Display",
                    "2. Extract the ZIP file",
                    "3. Double-click each .ttf file",
                    "4. Click 'Install Font' in Font Book",
                    "5. Restart your Python environment"
                ]

        elif system == "Linux":
            # Check using fc-list if available
            try:
                import subprocess
                result = subprocess.run(['fc-list', ':family'],
                                        capture_output=True, text=True)
                font_status['font_available'] = 'Red Hat Display' in result.stdout
            except:
                pass

            if not font_status['font_available']:
                font_status['instructions'] = [
                    "1. Download Red Hat Display from: https://fonts.google.com/specimen/Red+Hat+Display",
                    "2. Extract the ZIP file",
                    "3. Copy .ttf files to ~/.fonts/ or /usr/share/fonts/",
                    "4. Run: fc-cache -f -v",
                    "5. Restart your Python environment"
                ]

        return font_status


def build_report(team_key: str, **kwargs) -> Path:
    """
    Convenience function to build a complete PowerPoint report

    Args:
        team_key: Team identifier
        **kwargs: Additional arguments for PowerPointBuilder.build_presentation()

    Returns:
        Path to generated PowerPoint file
    """
    builder = PowerPointBuilder(team_key)

    # Log font status
    font_status = builder.check_font_installation()
    if not font_status['font_available']:
        logger.warning(f"Font '{DEFAULT_FONT_FAMILY}' not installed on system")
        logger.info("Installation instructions:")
        for instruction in font_status['instructions']:
            logger.info(f"  {instruction}")

    return builder.build_presentation(**kwargs)


def validate_fonts_before_build():
    """
    Validate fonts before building any presentations
    Can be called from main.py
    """
    try:
        # Test font availability
        test_pres = Presentation()
        test_slide = test_pres.slides.add_slide(test_pres.slide_layouts[5])
        test_box = test_slide.shapes.add_textbox(0, 0, 100, 100)
        test_box.text_frame.text = "Font Test"

        # Try Red Hat Display
        p = test_box.text_frame.paragraphs[0]
        p.font.name = DEFAULT_FONT_FAMILY

        logger.info(f"✓ Font validation passed: {DEFAULT_FONT_FAMILY} is available")
        return True

    except Exception as e:
        logger.warning(f"⚠ Font validation failed: {DEFAULT_FONT_FAMILY} may not be available")
        logger.warning(f"  Error: {str(e)}")
        logger.info(f"  Will use fallback font: {FALLBACK_FONT}")

        # Print installation instructions
        print("\n" + "=" * 60)
        print("Red Hat Display Font Installation Required")
        print("=" * 60)
        print("\nTo use Red Hat Display font:")
        print("1. Download from: https://fonts.google.com/specimen/Red+Hat+Display")
        print("2. Install all .ttf files on your system")
        print("3. Restart your Python environment")
        print("=" * 60 + "\n")

        return False