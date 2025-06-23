# slide_generators/base_slide.py
"""
Base class for all slide generators
Provides common functionality for creating PowerPoint slides
"""

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pathlib import Path
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class BaseSlide:
    """Base class for all slide generators"""

    def __init__(self, presentation: Optional[Presentation] = None):
        """
        Initialize base slide generator

        Args:
            presentation: Existing presentation to add slides to
        """
        if presentation is None:
            self.presentation = Presentation()
        else:
            self.presentation = presentation

        # Get blank slide layout
        self.blank_layout = self.presentation.slide_layouts[5]  # Blank layout

    def hex_to_rgb(self, hex_color: str) -> RGBColor:
        """
        Convert hex color to RGBColor

        Args:
            hex_color: Hex color string (e.g., '#FF0000' or 'FF0000')

        Returns:
            RGBColor object
        """
        # Remove # if present
        hex_color = hex_color.lstrip('#')

        # Convert to RGB
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)

        return RGBColor(r, g, b)

    def add_text_box(self, slide, text: str,
                     left: float, top: float,
                     width: float, height: float,
                     font_size: int = 14,
                     bold: bool = False,
                     alignment: PP_ALIGN = PP_ALIGN.LEFT) -> None:
        """
        Add a text box to slide with common formatting

        Args:
            slide: Slide object
            text: Text content
            left, top, width, height: Position and size in inches
            font_size: Font size in points
            bold: Whether text should be bold
            alignment: Text alignment
        """
        text_box = slide.shapes.add_textbox(
            Inches(left), Inches(top),
            Inches(width), Inches(height)
        )

        text_frame = text_box.text_frame
        text_frame.text = text
        text_frame.word_wrap = True

        p = text_frame.paragraphs[0]
        p.font.size = Pt(font_size)
        p.font.bold = bold
        p.alignment = alignment

    def add_image(self, slide, image_path: Path,
                  left: float, top: float,
                  width: Optional[float] = None,
                  height: Optional[float] = None) -> None:
        """
        Add an image to slide

        Args:
            slide: Slide object
            image_path: Path to image file
            left, top: Position in inches
            width, height: Size in inches (maintains aspect if only one specified)
        """
        if width and height:
            slide.shapes.add_picture(
                str(image_path),
                Inches(left), Inches(top),
                width=Inches(width), height=Inches(height)
            )
        elif width:
            slide.shapes.add_picture(
                str(image_path),
                Inches(left), Inches(top),
                width=Inches(width)
            )
        elif height:
            slide.shapes.add_picture(
                str(image_path),
                Inches(left), Inches(top),
                height=Inches(height)
            )
        else:
            slide.shapes.add_picture(
                str(image_path),
                Inches(left), Inches(top)
            )

    def save(self, output_path: Path) -> Path:
        """
        Save presentation to file

        Args:
            output_path: Where to save the presentation

        Returns:
            Path to saved file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        self.presentation.save(str(output_path))
        logger.info(f"Presentation saved to {output_path}")

        return output_path

    def get_slide_dimensions(self) -> Tuple[float, float]:
        """
        Get slide dimensions in inches

        Returns:
            (width, height) in inches
        """
        width = self.presentation.slide_width / 914400  # EMUs to inches
        height = self.presentation.slide_height / 914400

        return width, height