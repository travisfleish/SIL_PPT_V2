# visualizations/pg_subcategory_pie.py
"""
P&G Subcategory Pie Chart Visualization
Creates a pie chart with 10 equal slices, one for each subcategory
"""

import matplotlib.pyplot as plt
from matplotlib.patches import Wedge
from matplotlib.colors import LinearSegmentedColormap
import numpy as np
from pathlib import Path
import logging
from typing import Dict, Optional
import pandas as pd

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
        self.inner_radius = 0.0  # Full pie chart (no inner hole)
        self.text_radius = 3.5  # Where to place text labels

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

        # Ensure we have exactly 10 subcategories
        if len(subcategory_data) != 10:
            logger.warning(f"Expected 10 subcategories, got {len(subcategory_data)}. Using first 10.")
            subcategory_data = subcategory_data.head(10)

        # Sort by HYBRID_INDEX descending (highest first)
        subcategory_data = subcategory_data.sort_values('HYBRID_INDEX', ascending=False).reset_index(drop=True)

        num_slices = len(subcategory_data)
        angle_step = 360 / num_slices  # Each slice gets equal angle (36 degrees for 10 slices)

        # Generate gradient colors based on HYBRID_INDEX
        colors = self._generate_hybrid_index_colors(subcategory_data)

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

        # Add subcategory labels
        self._add_labels(ax, subcategory_data, num_slices, angle_step)

        # Save
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight',
                    facecolor='white', edgecolor='none',
                    pad_inches=0.05)
        plt.close()

        logger.info(f"P&G subcategory pie chart saved to {output_path}")
        return output_path

    def _generate_hybrid_index_colors(self, data: pd.DataFrame) -> list:
        """
        Generate colors based on HYBRID_INDEX values
        Green (low) to Red (high) gradient

        Args:
            data: DataFrame with HYBRID_INDEX column

        Returns:
            List of hex color strings
        """
        if 'HYBRID_INDEX' not in data.columns:
            logger.warning("HYBRID_INDEX column not found, using default colors")
            return ['#808080'] * len(data)

        hybrid_values = data['HYBRID_INDEX'].values

        # Get min and max for normalization
        min_val = hybrid_values.min()
        max_val = hybrid_values.max()

        # Normalize to 0-1 range (where 1 = highest, 0 = lowest)
        if max_val == min_val:
            # All values are the same
            normalized = np.ones(len(hybrid_values)) * 0.5
        else:
            normalized = (hybrid_values - min_val) / (max_val - min_val)

        # Create green-to-red colormap
        # Green (low) -> Yellow -> Red (high)
        colors_list = ['#00FF00', '#FFFF00', '#FF0000']  # Green, Yellow, Red
        n_bins = 256
        cmap = LinearSegmentedColormap.from_list('green_red', colors_list, N=n_bins)

        # Map normalized values to colors
        colors = []
        for norm_val in normalized:
            # Get color from colormap (norm_val is 0-1)
            rgba = cmap(norm_val)
            # Convert to hex
            hex_color = '#{:02x}{:02x}{:02x}'.format(
                int(rgba[0] * 255),
                int(rgba[1] * 255),
                int(rgba[2] * 255)
            )
            colors.append(hex_color)

        logger.info(f"Generated colors: min HYBRID_INDEX={min_val:.2f} (green), max={max_val:.2f} (red)")

        return colors

    def _draw_pie_slices(self, ax, data: pd.DataFrame, num_slices: int, angle_step: float, colors: list):
        """Draw the pie chart slices (clockwise from 12:00)"""
        for i in range(num_slices):
            # Start at 12:00 (90 degrees) and go clockwise (decreasing angles)
            start_angle = 90 - i * angle_step  # Start at 12:00, go clockwise
            end_angle = 90 - (i + 1) * angle_step
            
            # Ensure end_angle < start_angle for clockwise direction
            if end_angle > start_angle:
                end_angle = end_angle - 360

            # Draw full wedge
            wedge = Wedge((0, 0), self.outer_radius, start_angle, end_angle,
                         facecolor=colors[i],
                         edgecolor='white',
                         linewidth=3,
                         zorder=1)
            ax.add_patch(wedge)

    def _add_dividing_lines(self, ax, num_slices: int, angle_step: float):
        """Add white dividing lines between slices (clockwise)"""
        for i in range(num_slices):
            angle = 90 - i * angle_step  # Clockwise from 12:00
            angle_rad = np.deg2rad(angle)

            x = self.outer_radius * np.cos(angle_rad)
            y = self.outer_radius * np.sin(angle_rad)

            ax.plot([0, x], [0, y],
                    color='white', linewidth=3, zorder=2)

    def _add_labels(self, ax, data: pd.DataFrame, num_slices: int, angle_step: float):
        """Add subcategory labels to each slice (clockwise)"""
        for i in range(num_slices):
            # Calculate angle for label (center of slice, clockwise)
            angle = 90 - (i + 0.5) * angle_step  # Clockwise from 12:00
            angle_rad = np.deg2rad(angle)

            # Position label
            label_radius = self.text_radius
            x = label_radius * np.cos(angle_rad)
            y = label_radius * np.sin(angle_rad)

            # Get subcategory name
            subcategory = data.iloc[i]['SUBCATEGORY']

            # Add text
            ax.text(x, y, subcategory,
                   ha='center', va='center',
                   fontsize=14,
                   fontweight='bold',
                   color='white',
                   fontfamily=self.font_family,
                   zorder=10,
                   bbox=dict(boxstyle='round,pad=0.3',
                            facecolor='black',
                            alpha=0.7,
                            edgecolor='none'))
