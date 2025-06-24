# slide_generators/title_slide.py
"""
Generate title slide for PowerPoint presentations
Creates the opening slide with team branding and report title
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


class TitleSlide(BaseSlide):
    """Generate the title slide for the presentation"""

    def __init__(self, presentation: Presentation = None):
        """
        Initialize title slide generator

        Args:
            presentation: Existing presentation to add slide to
        """
        super().__init__(presentation)

    def generate(self,
                 team_config: Dict[str, Any],
                 subtitle: str = "Sponsorship Insights Report",
                 slide_index: Optional[int] = None) -> Presentation:
        """
        Generate the title slide

        Args:
            team_config: Team configuration with name and colors
            subtitle: Subtitle for the presentation
            slide_index: Where to insert slide (None = append)

        Returns:
            Updated presentation object
        """
        # Extract team info
        team_name = team_config.get('team_name', 'Team')
        team_colors = team_config.get('colors', {})

        # FIX 2: Use blank layout (no automatic title placeholder)
        slide = self.presentation.slides.add_slide(self.blank_layout)

        # Add background color
        background = slide.background
        fill = background.fill
        fill.solid()
        fill.fore_color.rgb = RGBColor(255, 255, 255)  # White background

        # Add team logo circle (placeholder)
        self._add_team_logo_circle(slide, team_name, team_colors)

        # Add title manually (no automatic placeholder)
        self._add_title_text(slide, team_name)

        # Add subtitle manually
        self._add_subtitle_text(slide, subtitle)

        # Add decorative elements (optional)
        self._add_decorative_elements(slide, team_colors)

        logger.info(f"Generated title slide for {team_name}")
        return self.presentation

    def _add_team_logo_circle(self, slide, team_name: str, team_colors: Dict[str, str]):
        """Add team logo placeholder circle"""
        # Position for logo
        left = Inches(5.5)
        top = Inches(1.5)
        size = Inches(2)

        # Outer circle (secondary color)
        if 'secondary' in team_colors:
            outer_circle = slide.shapes.add_shape(
                MSO_SHAPE.OVAL,
                left - Inches(0.1), top - Inches(0.1),
                size + Inches(0.2), size + Inches(0.2)
            )
            outer_circle.fill.solid()
            outer_circle.fill.fore_color.rgb = self.hex_to_rgb(team_colors['secondary'])
            outer_circle.line.fill.background()

        # Inner circle (primary color)
        inner_circle = slide.shapes.add_shape(
            MSO_SHAPE.OVAL,
            left, top,
            size, size
        )
        inner_circle.fill.solid()
        inner_circle.fill.fore_color.rgb = self.hex_to_rgb(
            team_colors.get('primary', '#002244')
        )
        inner_circle.line.fill.background()

        # Team initials or short name
        text_box = slide.shapes.add_textbox(
            left, top + Inches(0.7),
            size, Inches(0.6)
        )
        text_frame = text_box.text_frame
        text_frame.text = team_name.split()[-1][:4].upper()  # e.g., "JAZZ" or "COWB"

        p = text_frame.paragraphs[0]
        p.font.size = Pt(36)
        p.font.bold = True
        p.font.color.rgb = RGBColor(255, 255, 255)
        p.alignment = PP_ALIGN.CENTER

    def _add_title_text(self, slide, team_name: str):
        """Add main title text manually"""
        title_box = slide.shapes.add_textbox(
            Inches(1), Inches(4),
            Inches(11.333), Inches(1)  # Adjusted for 16:9 width
        )

        text_frame = title_box.text_frame
        text_frame.text = team_name
        text_frame.word_wrap = True

        p = text_frame.paragraphs[0]
        p.font.size = Pt(44)
        p.font.bold = True
        p.font.color.rgb = RGBColor(51, 51, 51)
        p.alignment = PP_ALIGN.CENTER

    def _add_subtitle_text(self, slide, subtitle: str):
        """Add subtitle text manually"""
        subtitle_box = slide.shapes.add_textbox(
            Inches(1), Inches(5),
            Inches(11.333), Inches(0.8)  # Adjusted for 16:9 width
        )

        text_frame = subtitle_box.text_frame
        text_frame.text = subtitle

        p = text_frame.paragraphs[0]
        p.font.size = Pt(28)
        p.font.bold = False
        p.font.color.rgb = RGBColor(89, 89, 89)
        p.alignment = PP_ALIGN.CENTER

    def _add_decorative_elements(self, slide, team_colors: Dict[str, str]):
        """Add optional decorative elements"""
        # Add a subtle line below the subtitle
        if 'accent' in team_colors:
            line_y = Inches(5.8)
            line = slide.shapes.add_shape(
                MSO_SHAPE.RECTANGLE,
                Inches(4), line_y,
                Inches(5.333), Pt(3)  # Adjusted for 16:9 width
            )
            line.fill.solid()
            line.fill.fore_color.rgb = self.hex_to_rgb(team_colors['accent'])
            line.line.fill.background()

        # Add date in bottom right
        date_box = slide.shapes.add_textbox(
            Inches(8.833), Inches(6.8),  # Adjusted for 16:9 width
            Inches(4), Inches(0.3)
        )

        from datetime import datetime
        date_text = datetime.now().strftime("%B %Y")

        text_frame = date_box.text_frame
        text_frame.text = date_text

        p = text_frame.paragraphs[0]
        p.font.size = Pt(12)
        p.font.color.rgb = RGBColor(150, 150, 150)
        p.alignment = PP_ALIGN.RIGHT


# Convenience function
def create_title_slide(team_config: Dict[str, Any],
                       presentation: Optional[Presentation] = None,
                       subtitle: str = "Sponsorship Insights Report") -> Presentation:
    """
    Create a title slide for the presentation

    Args:
        team_config: Team configuration
        presentation: Existing presentation (creates new if None)
        subtitle: Subtitle text

    Returns:
        Presentation with title slide
    """
    generator = TitleSlide(presentation)
    return generator.generate(team_config, subtitle)