# slide_generators/demographics_slide.py
"""
Generate complete demographics slide for PowerPoint presentations
Clean version without circular imports
"""

from pathlib import Path
from typing import Dict, Optional, Any
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
import logging

logger = logging.getLogger(__name__)

# Default font
DEFAULT_FONT_FAMILY = "Red Hat Display"


class DemographicsSlide:
    """Generate the complete demographics slide with all charts"""

    def __init__(self, presentation: Presentation = None):
        """
        Initialize demographics slide generator

        Args:
            presentation: Existing presentation to add slide to
        """
        if presentation is None:
            self.presentation = Presentation()
            # Set 16:9 widescreen aspect ratio
            self.presentation.slide_width = Inches(13.333)
            self.presentation.slide_height = Inches(7.5)
        else:
            self.presentation = presentation

        self.default_font = DEFAULT_FONT_FAMILY
        self.team_colors = {}

        # Setup layouts
        self._setup_layouts()

    def _setup_layouts(self):
        """Setup slide layout references"""
        layout_count = len(self.presentation.slide_layouts)
        logger.info(f"Available slide layouts: {layout_count}")

        # Always keep reference to standard blank layout
        self.blank_layout = self.presentation.slide_layouts[6]  # Blank layout

        # Check if we have the SIL custom layouts (12 = white content layout)
        if layout_count >= 13:
            self.content_layout = self.presentation.slide_layouts[12]  # SIL white content
            logger.info("Using SIL white content layout")
        else:
            self.content_layout = self.blank_layout  # Fallback to blank
            logger.warning("SIL layouts not found, using blank layout")

    def add_content_slide(self):
        """Add a content slide using the appropriate layout"""
        return self.presentation.slides.add_slide(self.content_layout)

    def generate(self,
                 demographic_data: Dict[str, Any],
                 chart_dir: Path,
                 team_config: Dict[str, Any],
                 slide_index: Optional[int] = None) -> Presentation:
        """
        Generate the complete demographics slide

        Args:
            demographic_data: Processed demographic data
            chart_dir: Directory containing chart images
            team_config: Team configuration
            slide_index: Where to insert slide (None = append)

        Returns:
            Updated presentation object
        """
        # Extract team info
        team_name = team_config.get('team_name', 'Team')
        team_short = team_config.get('team_name_short', team_name.split()[-1])
        colors = team_config.get('colors', {})

        # Store team colors for legend
        self.team_colors = colors

        # Use the content layout
        slide = self.add_content_slide()
        logger.info("Added demographics slide using content layout")

        # Add header
        self._add_header(slide, team_name)

        # Add chart section headers with black backgrounds
        self._add_chart_headers(slide)

        # Add demographic charts in 2x3 grid
        self._add_charts(slide, chart_dir)

        # Add legend with colored squares (no box, no title)
        self._add_legend_box(slide, team_name, team_short, team_config.get('league', 'League'))

        logger.info(f"Generated demographics slide for {team_name}")
        return self.presentation

    def _add_header(self, slide, team_name: str):
        """Add header with title"""
        # Header background
        header_rect = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE,
            Inches(0), Inches(0),
            Inches(13.333), Inches(0.5)
        )
        header_rect.fill.solid()
        header_rect.fill.fore_color.rgb = RGBColor(240, 240, 240)
        header_rect.line.color.rgb = RGBColor(200, 200, 200)
        header_rect.line.width = Pt(0.5)

        # Team name (left)
        team_text = slide.shapes.add_textbox(
            Inches(0.2), Inches(0.1),
            Inches(3), Inches(0.3)
        )
        team_text.text_frame.text = team_name
        p = team_text.text_frame.paragraphs[0]
        p.font.name = self.default_font
        p.font.size = Pt(14)
        p.font.bold = True

        # Slide title (right)
        title_text = slide.shapes.add_textbox(
            Inches(6), Inches(0.1),
            Inches(7.133), Inches(0.3)
        )
        title_text.text_frame.text = f"FAN DEMOGRAPHICS: HOW ARE {team_name.upper()} FANS UNIQUE"
        p = title_text.text_frame.paragraphs[0]
        p.font.name = self.default_font
        p.alignment = PP_ALIGN.RIGHT
        p.font.size = Pt(14)

    def _add_chart_headers(self, slide):
        """Add black header bars for each chart section"""
        headers = [
            # Top row headers - matching right-edge aligned chart positions
            ("GENDER", 0.5, 0.95, 1.5),             # 1.5" wide
            ("HOUSEHOLD INCOME", 2.2, 0.95, 4.8),   # 4.8" wide
            ("OCCUPATION CATEGORY", 7.2, 0.95, 5.6), # 5.6" wide (ALIGNED)

            # Bottom row headers - matching alignment
            ("ETHNICITY", 0.5, 3.65, 4.5),          # 4.5" wide
            ("GENERATION", 5.2, 3.65, 4.5),         # 4.5" wide
            ("CHILDREN IN HOUSEHOLD", 9.8, 3.65, 3.0)  # 3.0" wide
        ]

        for text, left, top, width in headers:
            # Black background bar
            header_rect = slide.shapes.add_shape(
                MSO_SHAPE.RECTANGLE,
                Inches(left), Inches(top),
                Inches(width), Inches(0.25)
            )
            header_rect.fill.solid()
            header_rect.fill.fore_color.rgb = RGBColor(0, 0, 0)
            header_rect.line.fill.background()

            # White text
            text_box = slide.shapes.add_textbox(
                Inches(left + 0.1), Inches(top + 0.02),
                Inches(width - 0.2), Inches(0.2)
            )
            text_box.text_frame.text = text
            p = text_box.text_frame.paragraphs[0]
            p.font.name = self.default_font
            p.font.size = Pt(11)
            p.font.bold = True
            p.font.color.rgb = RGBColor(255, 255, 255)
            p.alignment = PP_ALIGN.CENTER

    def _add_charts(self, slide, chart_dir: Path):
        """Add all demographic charts in the correct positions"""
        chart_dir = Path(chart_dir)

        # Chart positions
        chart_positions = [
            # Top row - RIGHT-EDGE ALIGNED: Occupation right edge = Children right edge
            ('gender_chart', 0.5, 1.2, 1.5, 2.2),      # 1.5" wide
            ('income_chart', 2.2, 1.2, 4.8, 2.2),       # 4.8" wide
            ('occupation_chart', 7.2, 1.2, 5.6, 2.2),  # 5.6" wide (ALIGNED RIGHT)

            # Bottom row - Ethnicity & Generation equal, Children right-aligned
            ('ethnicity_chart', 0.5, 3.9, 4.5, 2.2),    # 4.5" wide
            ('generation_chart', 5.2, 3.9, 4.5, 2.2),   # 4.5" wide
            ('children_chart', 9.8, 3.9, 3.0, 2.2)      # 3.0" wide (RIGHT ALIGNED)
        ]

        for chart_name, left, top, width, height in chart_positions:
            # Try both regular and hires versions
            chart_path = chart_dir / f'{chart_name}_hires.png'
            if not chart_path.exists():
                chart_path = chart_dir / f'{chart_name}.png'

            if chart_path.exists():
                try:
                    slide.shapes.add_picture(
                        str(chart_path),
                        Inches(left), Inches(top),
                        width=Inches(width), height=Inches(height)
                    )
                    logger.info(f"Added {chart_name} to slide")
                except Exception as e:
                    logger.warning(f"Could not add {chart_name}: {e}")
            else:
                logger.warning(f"Chart not found: {chart_path}")
                # Add placeholder
                placeholder = slide.shapes.add_shape(
                    MSO_SHAPE.RECTANGLE,
                    Inches(left), Inches(top),
                    Inches(width), Inches(height)
                )
                placeholder.fill.solid()
                placeholder.fill.fore_color.rgb = RGBColor(245, 245, 245)
                placeholder.line.color.rgb = RGBColor(200, 200, 200)
                placeholder.line.width = Pt(1)

                # Add placeholder text
                text_box = slide.shapes.add_textbox(
                    Inches(left + 0.5), Inches(top + height / 2 - 0.2),
                    Inches(width - 1), Inches(0.4)
                )
                text_box.text_frame.text = f"{chart_name.replace('_', ' ').title()}"
                p = text_box.text_frame.paragraphs[0]
                p.font.name = self.default_font
                p.font.size = Pt(12)
                p.alignment = PP_ALIGN.CENTER

    def _add_legend_box(self, slide, team_name: str, team_short: str, league: str):
        """Add legend with colored squares in a single horizontal row, centered"""
        # Positioning for horizontal centered layout
        legend_top = Inches(6.3)  # Bottom of slide
        square_size = Inches(0.12)  # Small square size
        text_offset = Inches(0.2)  # Space between square and text
        item_gap = Inches(0.8)  # Gap between legend items

        # Get colors from team config
        team_colors = getattr(self, 'team_colors', {
            'primary': '#1f77b4',
            'secondary': '#ff7f0e',
            'accent': '#2ca02c'
        })

        # Legend items with corresponding colors and estimated text widths
        legend_items = [
            (f"{team_name} Fans", team_colors.get('primary', '#1f77b4'), 1.5),
            (
            f"{team_short} Gen Pop (state level, excluding {team_short} Fans)", team_colors.get('secondary', '#ff7f0e'),
            4.0),
            (f"{league} Fans Total (excluding {team_short} fans)", team_colors.get('accent', '#2ca02c'), 2.8)
        ]

        # Calculate total width needed for all items
        total_width = 0
        for i, (label, color, text_width) in enumerate(legend_items):
            total_width += square_size.inches + text_offset.inches + text_width
            if i < len(legend_items) - 1:  # Add gap between items (not after last)
                total_width += item_gap.inches

        # Center horizontally on slide
        slide_width = 13.333  # Standard slide width
        start_left = (slide_width - total_width) / 2

        current_left = start_left

        for i, (label, color_hex, text_width) in enumerate(legend_items):
            # Create colored square
            square = slide.shapes.add_shape(
                MSO_SHAPE.RECTANGLE,
                Inches(current_left), legend_top,
                square_size, square_size
            )
            square.fill.solid()
            square.fill.fore_color.rgb = self._hex_to_rgb(color_hex)
            square.line.fill.background()  # No border on square

            # Add text label
            text_left = current_left + square_size.inches + text_offset.inches
            text_box = slide.shapes.add_textbox(
                Inches(text_left), legend_top - Inches(0.02),
                Inches(text_width), Inches(0.2)
            )
            text_box.text_frame.text = label
            p = text_box.text_frame.paragraphs[0]
            p.font.name = self.default_font
            p.font.size = Pt(10)
            p.font.color.rgb = RGBColor(0, 0, 0)
            p.alignment = PP_ALIGN.LEFT

            # Move to next position
            current_left = text_left + text_width + item_gap.inches

    def _hex_to_rgb(self, hex_color: str) -> RGBColor:
        """Convert hex color to RGBColor"""
        hex_color = hex_color.lstrip('#')
        return RGBColor(
            int(hex_color[0:2], 16),
            int(hex_color[2:4], 16),
            int(hex_color[4:6], 16)
        )

    def save(self, output_path: Path) -> Path:
        """Save presentation"""
        output_path = Path(output_path)
        self.presentation.save(str(output_path))
        return output_path


# Convenience function
def create_demographics_slide(demographic_data: Dict[str, Any],
                              chart_dir: Path,
                              team_config: Dict[str, Any],
                              presentation: Optional[Presentation] = None) -> Presentation:
    """
    Create a demographics slide

    Args:
        demographic_data: Processed demographic data
        chart_dir: Directory with chart images
        team_config: Team configuration
        presentation: Existing presentation (creates new if None)

    Returns:
        Presentation with demographics slide
    """
    generator = DemographicsSlide(presentation)
    return generator.generate(demographic_data, chart_dir, team_config)