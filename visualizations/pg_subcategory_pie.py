# visualizations/pg_subcategory_pie.py
"""
P&G Subcategory Pie Chart Visualization
Creates a pie chart with 10 equal slices, one for each subcategory
"""

import matplotlib.pyplot as plt
from matplotlib.patches import Wedge, Circle
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import numpy as np
from pathlib import Path
import logging
from typing import Dict, Optional
import pandas as pd
from PIL import Image

from .base_chart import BaseChart
from utils.font_manager import font_manager

logger = logging.getLogger(__name__)


class PGSubcategoryPie(BaseChart):
    """Generate pie chart visualization with 10 equal slices for P&G subcategories"""

    def __init__(self, team_config: Dict[str, any]):
        """
        Initialize pie chart generator

        Args:
            team_config: Team configuration with colors and names
        """
        super().__init__()
        self.team_config = team_config
        self.team_name = team_config.get('team_name', 'Team')
        self.team_short = team_config.get('team_name_short', self.team_name.split()[-1])

        # Extract colors from team config
        colors = team_config.get('colors', {})
        self.primary_color = colors.get('primary', '#E10600')  # F1 Red
        self.secondary_color = colors.get('secondary', '#1E1E1E')  # F1 Black
        self.accent_color = colors.get('accent', '#666666')  # Dark gray

        # Visualization parameters
        self.outer_radius = 5.0
        self.inner_ring_outer_radius = 2.5  # Outer radius of inner ring
        self.inner_ring_inner_radius = 1.5  # Inner radius of inner ring (creates ring thickness)
        self.inner_ring_radius = 2.0  # Radius for text in inner ring (center of ring)
        self.center_circle_radius = 1.5  # Radius of center black circle (extends to inner border of inner ring)
        self.text_radius = 3.75  # Where to place text labels

        # Get font family from font manager
        self.font_family = font_manager.get_font_family('Red Hat Display')
        logger.info(f"Using font family: {self.font_family}")

    def create(self, subcategory_data: pd.DataFrame,
               output_path: Optional[Path] = None) -> Path:
        """
        Create pie chart visualization with 10 equal slices

        Args:
            subcategory_data: DataFrame with columns: SUBCATEGORY, PERC_INDEX, PPC_INDEX, HYBRID_INDEX
            output_path: Where to save the visualization

        Returns:
            Path to saved visualization
        """
        if output_path is None:
            output_path = Path(f'{self.team_short.lower()}_pg_subcategory_pie.png')

        # Ensure we have exactly 12 items (10 subcategories + 2 categories)
        if len(subcategory_data) != 12:
            logger.warning(f"Expected 12 items (10 subcategories + 2 categories), got {len(subcategory_data)}. Using all available.")
            if len(subcategory_data) > 12:
                subcategory_data = subcategory_data.head(12)

        # Sort by HYBRID_INDEX descending (highest first)
        subcategory_data = subcategory_data.sort_values(
            'HYBRID_INDEX', ascending=False
        ).reset_index(drop=True)

        num_slices = len(subcategory_data)
        angle_step = 360 / num_slices  # Each slice gets equal angle (36 degrees for 10 slices)

        # All slices the same gray color
        colors = ['#808080'] * num_slices

        # Create figure
        fig = plt.figure(figsize=(12, 12), facecolor='white', dpi=150)
        ax = fig.add_subplot(111, aspect='equal')

        # Set limits
        margin = 0.5
        limit = self.outer_radius + margin
        ax.set_xlim(-limit, limit)
        ax.set_ylim(-limit, limit)
        ax.axis('off')

        # Draw pie slices
        self._draw_pie_slices(ax, subcategory_data, num_slices, angle_step, colors)

        # Add dividing lines
        self._add_dividing_lines(ax, num_slices, angle_step)

        # Add inner ring with HYBRID_INDEX values
        self._add_inner_ring(ax, subcategory_data, num_slices, angle_step)

        # Add center circle with molly.png and "The F1 Fan" text
        self._draw_center_circle(ax)

        # Add subcategory labels with rank (1., 2., etc.)
        self._add_labels(ax, subcategory_data, num_slices, angle_step)

        # Save
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight',
                    facecolor='white', edgecolor='none',
                    pad_inches=0.05)
        plt.close()

        logger.info(f"P&G subcategory pie chart saved to {output_path}")
        return output_path

    def _draw_pie_slices(self, ax, data: pd.DataFrame,
                         num_slices: int, angle_step: float, colors: list):
        """
        Draw the pie chart slices (clockwise).

        Slice 0 (highest HYBRID_INDEX) is centered at 12:00 (90°).
        Slices proceed clockwise in descending HYBRID_INDEX.
        """
        center_top = 90.0  # 12 o'clock

        for i in range(num_slices):
            center_angle = center_top - i * angle_step  # clockwise from top
            start_angle = center_angle + angle_step / 2.0
            end_angle = center_angle - angle_step / 2.0

            if end_angle > start_angle:
                end_angle -= 360

            wedge = Wedge(
                (0, 0),
                self.outer_radius,
                start_angle,
                end_angle,
                facecolor=colors[i],
                edgecolor='white',
                linewidth=3,
                zorder=1
            )
            ax.add_patch(wedge)

    def _add_dividing_lines(self, ax, num_slices: int, angle_step: float):
        """Add white dividing lines between slices (clockwise), starting at black circle edge, through inner ring, to outer border"""
        center_top = 90.0

        for i in range(num_slices):
            # boundary between slice i-1 and slice i
            angle = center_top + angle_step / 2.0 - i * angle_step
            angle_rad = np.deg2rad(angle)

            # Start point at edge of black circle (center_circle_radius)
            x_start = self.center_circle_radius * np.cos(angle_rad)
            y_start = self.center_circle_radius * np.sin(angle_rad)

            # End point at outer edge
            x_end = self.outer_radius * np.cos(angle_rad)
            y_end = self.outer_radius * np.sin(angle_rad)

            # Draw line from black circle edge to outer edge
            # zorder=4 to be above inner ring (zorder=3) but below text (zorder=10)
            ax.plot(
                [x_start, x_end], [y_start, y_end],
                color='white',
                linewidth=3,
                zorder=4
            )

    def _add_inner_ring(self, ax, data: pd.DataFrame, num_slices: int, angle_step: float):
        """
        Add inner ring (like fan wheel) with red F1 color containing HYBRID_INDEX values
        formatted as 2.1X, 1.9X, etc.
        """
        center_top = 90.0

        for i in range(num_slices):
            center_angle = center_top - i * angle_step  # same center as slice
            start_angle = center_angle + angle_step / 2.0
            end_angle = center_angle - angle_step / 2.0

            if end_angle > start_angle:
                end_angle -= 360

            # Draw inner ring wedge with F1 red color
            inner_wedge = Wedge(
                (0, 0),
                self.inner_ring_outer_radius,
                start_angle,
                end_angle,
                width=self.inner_ring_outer_radius - self.inner_ring_inner_radius,
                facecolor=self.primary_color,  # F1 Red
                edgecolor='white',
                linewidth=2,
                zorder=3
            )
            ax.add_patch(inner_wedge)

            # Position for text in center of inner ring
            angle_rad = np.deg2rad(center_angle)
            x = self.inner_ring_radius * np.cos(angle_rad)
            y = self.inner_ring_radius * np.sin(angle_rad)

            # Get HYBRID_INDEX and format it (divide by 100, one decimal, add X)
            hybrid_index = data.iloc[i]['HYBRID_INDEX']
            formatted_value = f"{hybrid_index / 100:.1f}X"

            # Add text in inner ring
            ax.text(
                x, y, formatted_value,
                ha='center', va='center',
                fontsize=18,
                fontweight='bold',
                color='white',
                fontfamily=self.font_family,
                zorder=10
            )

    def _split_text_into_two_lines(self, text: str) -> str:
        """
        Split text into two lines, trying to balance words
        
        Args:
            text: Text to split
            
        Returns:
            Text with newline character for two-line display
        """
        words = text.split()
        if len(words) <= 1:
            return text
        
        # Try to split roughly in the middle
        mid_point = len(words) // 2
        line1 = ' '.join(words[:mid_point])
        line2 = ' '.join(words[mid_point:])
        
        return f"{line1}\n{line2}"

    def _add_labels(self, ax, data: pd.DataFrame,
                    num_slices: int, angle_step: float):
        """
        Add subcategory labels to each slice (clockwise),
        as 'rank. SUBCATEGORY' on two lines, e.g. '1. AI\nUsers'
        """
        center_top = 90.0

        for i in range(num_slices):
            center_angle = center_top - i * angle_step  # same center as slice
            angle_rad = np.deg2rad(center_angle)

            label_radius = self.text_radius
            x = label_radius * np.cos(angle_rad)
            y = label_radius * np.sin(angle_rad)

            subcategory = data.iloc[i]['SUBCATEGORY']
            rank = i + 1  # 1-based rank from highest HYBRID_INDEX

            # Split subcategory into two lines, with rank on first line
            words = subcategory.split()
            if len(words) <= 1:
                # Single word - just add rank
                label_text = f"{rank}. {subcategory}"
            else:
                # Split roughly in the middle
                mid_point = len(words) // 2
                line1 = ' '.join(words[:mid_point])
                line2 = ' '.join(words[mid_point:])
                label_text = f"{rank}. {line1}\n{line2}"

            ax.text(
                x, y, label_text,
                ha='center', va='center',
                fontsize=20,
                fontweight='bold',
                color='white',
                fontfamily=self.font_family,
                zorder=10
                # Removed bbox to eliminate black background
            )

    def _draw_center_circle(self, ax):
        """Draw the center circle with black background, molly.png image, and 'The F1 Fan' text"""
        # Draw the black background circle
        center_circle = Circle(
            (0, 0),
            self.center_circle_radius,
            facecolor='black',
            edgecolor=self.secondary_color,
            linewidth=5,
            zorder=20
        )
        ax.add_patch(center_circle)

        # Try to load molly.png
        team_logo = None
        try:
            # Get the project root more reliably
            current_file = Path(__file__).resolve()

            # Try multiple potential paths for the logo
            logo_paths = [
                # Primary location - where the file actually is
                current_file.parent.parent / 'assets' / 'logos' / 'general' / 'molly.png',
                Path.cwd() / 'assets' / 'logos' / 'general' / 'molly.png',

                # Also check without 'general' subdirectory
                current_file.parent.parent / 'assets' / 'logos' / 'molly.png',
                current_file.parent.parent / 'assets' / 'molly.png',
                current_file.parent.parent / 'molly.png',
                Path.cwd() / 'assets' / 'logos' / 'molly.png',
                Path.cwd() / 'assets' / 'molly.png',
                Path.cwd() / 'molly.png',
            ]

            for logo_path in logo_paths:
                if logo_path.exists():
                    team_logo = Image.open(logo_path)
                    logger.info(f"Successfully loaded molly.png from {logo_path}")
                    break
            else:
                logger.warning("Could not find molly.png in any expected location")
        except Exception as e:
            logger.error(f"Failed to load molly.png: {e}", exc_info=True)

        if team_logo is not None:
            try:
                # Prepare the logo for display
                if team_logo.mode != 'RGBA':
                    team_logo = team_logo.convert('RGBA')

                # Calculate size to fit within the inner circle with room for text
                # The logo should take up about 60% of the circle diameter to leave room for text
                logo_size_pixels = int(self.center_circle_radius * 1.4 * 100)

                # Create a copy to avoid modifying the original
                logo_copy = team_logo.copy()
                logo_copy.thumbnail((logo_size_pixels, logo_size_pixels), Image.Resampling.LANCZOS)

                logger.info(f"Logo resized to: {logo_copy.size}")

                # Convert to numpy array for matplotlib
                logo_array = np.array(logo_copy)

                # Create OffsetImage with appropriate zoom
                # Zoom factor to ensure it fits within the circle
                zoom_factor = 0.5
                imagebox = OffsetImage(logo_array, zoom=zoom_factor)

                # Position logo in upper portion of circle to leave room for text
                logo_y_offset = 0.4  # Position in upper part of circle
                ab = AnnotationBbox(imagebox, (0, logo_y_offset),
                                    frameon=False,
                                    pad=0,
                                    zorder=22)
                ax.add_artist(ab)

                # Add team text in lower portion of circle
                fan_text = "THE F1\nFAN"

                # Position text in lower part of circle
                text_y_position = -0.8  # Lower in the circle
                ax.text(0, text_y_position, fan_text,
                        ha='center', va='center',
                        fontsize=28,
                        fontweight='bold',
                        fontfamily=self.font_family,
                        color='white',
                        zorder=23,
                        linespacing=0.8)

                logger.info("Logo and text added successfully within circle bounds")
            except Exception as e:
                logger.error(f"Error adding logo to plot: {e}", exc_info=True)
                # Fall back to text-only version
                self._add_text_only_center(ax)
        else:
            # Fallback to text-only version
            self._add_text_only_center(ax)

    def _add_text_only_center(self, ax):
        """Add text-only center when logo is not available"""
        fan_text = "THE F1 FAN"
        ax.text(0, 0, fan_text,
                ha='center', va='center',
                fontsize=20,
                fontweight='bold',
                fontfamily=self.font_family,
                color='white',
                zorder=23)
