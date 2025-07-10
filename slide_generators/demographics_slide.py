# slide_generators/demographics_slide.py
"""
Generate complete demographics slide for PowerPoint presentations
Includes all charts arranged according to the reference layout
"""

from pathlib import Path
from typing import Dict, Optional, Any
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
import logging

from .base_slide import BaseSlide

logger = logging.getLogger(__name__)

# Default font
DEFAULT_FONT_FAMILY = "Red Hat Display"


class DemographicsSlide(BaseSlide):
    """Generate the complete demographics slide with all charts"""

    def __init__(self, presentation: Presentation = None):
        """
        Initialize demographics slide generator

        Args:
            presentation: Existing presentation to add slide to
        """
        super().__init__(presentation)

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

        # Use the content layout (SIL white layout #12)
        slide = self.add_content_slide()
        logger.info("Added demographics slide using SIL white layout")

        # Add header
        self._add_header(slide, team_name)

        # Add chart section headers with black backgrounds
        self._add_chart_headers(slide)

        # Add demographic charts in 2x3 grid
        self._add_charts(slide, chart_dir)

        # Add KEY/legend box at bottom left
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
            # Top row - adjusted for new layout
            ('GENDER', 0.5, 0.9, 3.5),  # Narrower for stacked gender
            ('HOUSEHOLD INCOME', 4.2, 0.9, 5.0),  # Wider
            ('OCCUPATION CATEGORY', 9.4, 0.9, 3.8),

            # Bottom row
            ('ETHNICITY', 0.5, 3.6, 3.5),
            ('GENERATION', 4.2, 3.6, 5.0),  # Wider
            ('CHILDREN IN HOUSEHOLD', 9.4, 3.6, 3.8)
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

        # Chart positions matching designer layout with stacked gender charts
        chart_positions = [
            # Top row - Gender takes left column with stacked pie charts, more room for other charts
            ('gender_chart', 0.5, 1.2, 3.5, 2.2),  # Left column (narrower for stacked pies)
            ('income_chart', 4.2, 1.2, 5.0, 2.2),  # Middle column (wider)
            ('occupation_chart', 9.4, 1.2, 3.8, 2.2),  # Right column

            # Bottom row
            ('ethnicity_chart', 0.5, 3.9, 3.5, 2.2),  # Left column
            ('generation_chart', 4.2, 3.9, 5.0, 2.2),  # Middle column (wider)
            ('children_chart', 9.4, 3.9, 3.8, 2.2)  # Right column
        ]

        for chart_name, left, top, width, height in chart_positions:
            # Try both regular and hires versions
            chart_path = chart_dir / f'{chart_name}_hires.png'
            if not chart_path.exists():
                chart_path = chart_dir / f'{chart_name}.png'

            if chart_path.exists():
                try:
                    # For gender chart, we need special handling if it's stacked
                    if chart_name == 'gender_chart':
                        # The gender chart should be generated as a taller image with stacked pies
                        # Adjust height to accommodate stacked layout
                        slide.shapes.add_picture(
                            str(chart_path),
                            Inches(left), Inches(top),
                            width=Inches(width), height=Inches(height)
                        )
                    else:
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
        """Add KEY legend box at bottom left"""
        # Box position - bottom left as in designer's version
        left = Inches(0.5)
        top = Inches(6.3)
        width = Inches(5.5)
        height = Inches(0.85)

        # Create box
        box = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE,
            left, top, width, height
        )
        box.fill.solid()
        box.fill.fore_color.rgb = RGBColor(255, 255, 255)
        box.line.color.rgb = RGBColor(0, 0, 0)
        box.line.width = Pt(1)

        # Add KEY text
        text_frame = box.text_frame
        text_frame.clear()
        text_frame.margin_left = Inches(0.1)
        text_frame.margin_top = Inches(0.08)
        text_frame.margin_bottom = Inches(0.08)

        # KEY title
        p = text_frame.add_paragraph()
        p.text = "KEY"
        p.font.name = self.default_font
        p.font.size = Pt(11)
        p.font.bold = True
        p.space_after = Pt(6)

        # Legend items
        items = [
            f"- {team_name} Fans",
            f"- {team_short} Gen Pop (state level, excluding {team_short} Fans)",
            f"- {league} Fans Total (excluding {team_short} fans)"
        ]

        for i, item in enumerate(items):
            if i > 0:
                p = text_frame.add_paragraph()
            else:
                p = text_frame.add_paragraph()
            p.text = item
            p.font.name = self.default_font
            p.font.size = Pt(10)
            p.level = 0
            p.space_before = Pt(2)
            p.space_after = Pt(2)

    def _hex_to_rgb(self, hex_color: str) -> RGBColor:
        """Convert hex color to RGBColor"""
        return self.hex_to_rgb(hex_color)

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