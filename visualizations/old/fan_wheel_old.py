# visualizations/fan_wheel.py
"""
Fan Wheel Visualization Generator
Creates circular fan behavior visualization for sports teams
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Wedge, Circle, Polygon
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import numpy as np
from PIL import Image, ImageDraw
from pathlib import Path
import logging
from typing import Dict, Optional, List, Tuple
import pandas as pd

from .base_chart import BaseChart

logger = logging.getLogger(__name__)


class FanWheel(BaseChart):
    """Generate fan wheel visualization showing top communities and their merchants"""

    def __init__(self, team_config: Dict[str, any]):
        """
        Initialize fan wheel generator

        Args:
            team_config: Team configuration with colors and names
        """
        super().__init__()
        self.team_config = team_config
        self.team_name = team_config.get('team_name', 'Team')
        self.team_short = team_config.get('team_name_short', self.team_name.split()[-1])

        # Extract colors from team config
        colors = team_config.get('colors', {})
        self.primary_color = colors.get('primary', '#002244')
        self.secondary_color = colors.get('secondary', '#FFB612')
        self.accent_color = colors.get('accent', '#4169E1')

        # Visualization parameters
        self.outer_radius = 5.0
        self.logo_radius = 2.8
        self.inner_radius = 1.6

    def create(self, wheel_data: pd.DataFrame,
               output_path: Optional[Path] = None,
               team_logo: Optional[Image.Image] = None) -> Path:
        """
        Create fan wheel visualization

        Args:
            wheel_data: DataFrame with columns: COMMUNITY, MERCHANT, behavior, PERC_INDEX
            output_path: Where to save the visualization
            team_logo: Optional PIL Image of team logo

        Returns:
            Path to saved visualization
        """
        if output_path is None:
            output_path = Path(f'{self.team_short.lower()}_fan_wheel.png')

        # Create figure
        fig = plt.figure(figsize=(12, 12), facecolor='white')
        ax = fig.add_subplot(111, aspect='equal')
        ax.set_xlim(-6, 6)
        ax.set_ylim(-6, 6)
        ax.axis('off')

        num_items = len(wheel_data)
        if num_items == 0:
            raise ValueError("No data provided for fan wheel")

        angle_step = 360 / num_items

        # Draw wedges
        self._draw_wedges(ax, num_items, angle_step)

        # Add dividing lines
        self._add_dividing_lines(ax, num_items, angle_step)

        # Add arrows
        self._add_arrows(ax, num_items, angle_step)

        # Draw center circle
        self._draw_center_circle(ax, team_logo)

        # Add logos and text for each segment
        self._add_segment_content(ax, wheel_data, angle_step)

        # Save
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight',
                    facecolor='white', edgecolor='none')
        plt.close()

        logger.info(f"Fan wheel saved to {output_path}")
        return output_path

    def _draw_wedges(self, ax, num_items: int, angle_step: float):
        """Draw the wedge segments"""
        for i in range(num_items):
            start_angle = i * angle_step - 90
            end_angle = (i + 1) * angle_step - 90

            # Full wedge (background)
            full_wedge = Wedge((0, 0), self.outer_radius, start_angle, end_angle,
                               width=self.outer_radius,
                               facecolor=self.primary_color,
                               edgecolor='none',
                               zorder=1)
            ax.add_patch(full_wedge)

            # Outer ring (lighter color)
            outer_ring = Wedge((0, 0), self.outer_radius, start_angle, end_angle,
                               width=self.outer_radius - self.logo_radius,
                               facecolor=self.accent_color,
                               edgecolor='none',
                               zorder=2)
            ax.add_patch(outer_ring)

    def _add_dividing_lines(self, ax, num_items: int, angle_step: float):
        """Add white dividing lines between segments"""
        for i in range(num_items):
            angle = i * angle_step - 90
            angle_rad = np.deg2rad(angle)

            x_inner = self.inner_radius * np.cos(angle_rad)
            y_inner = self.inner_radius * np.sin(angle_rad)
            x_outer = self.outer_radius * np.cos(angle_rad)
            y_outer = self.outer_radius * np.sin(angle_rad)

            ax.plot([x_inner, x_outer], [y_inner, y_outer],
                    color='white', linewidth=8, zorder=15)

    def _add_arrows(self, ax, num_items: int, angle_step: float):
        """Add directional arrows between segments"""
        for i in range(num_items):
            arrow_angle_deg = i * angle_step - 90
            arrow_angle = np.deg2rad(arrow_angle_deg)

            # Arrow position
            arrow_r = 4.0
            arrow_x = arrow_r * np.cos(arrow_angle)
            arrow_y = arrow_r * np.sin(arrow_angle)

            # White circle background
            circle_bg = Circle((arrow_x, arrow_y), 0.3,
                               facecolor='white',
                               edgecolor='none',
                               zorder=16)
            ax.add_patch(circle_bg)

            # Create arrow pointing clockwise
            arrow_size = 0.15
            arrow_direction = arrow_angle - np.pi / 2

            # Arrow vertices
            tip_x = arrow_x + arrow_size * np.cos(arrow_direction)
            tip_y = arrow_y + arrow_size * np.sin(arrow_direction)

            base_center_x = arrow_x - arrow_size * 0.5 * np.cos(arrow_direction)
            base_center_y = arrow_y - arrow_size * 0.5 * np.sin(arrow_direction)

            base_offset = arrow_size * 0.4
            base1_x = base_center_x + base_offset * np.cos(arrow_direction + np.pi / 2)
            base1_y = base_center_y + base_offset * np.sin(arrow_direction + np.pi / 2)
            base2_x = base_center_x - base_offset * np.cos(arrow_direction + np.pi / 2)
            base2_y = base_center_y - base_offset * np.sin(arrow_direction + np.pi / 2)

            arrow = Polygon([(tip_x, tip_y), (base1_x, base1_y), (base2_x, base2_y)],
                            facecolor=self.secondary_color,
                            edgecolor=self.secondary_color,
                            zorder=17)
            ax.add_patch(arrow)

    def _draw_center_circle(self, ax, team_logo: Optional[Image.Image] = None):
        """Draw the center circle with team branding"""
        # Center circle
        center_circle = Circle((0, 0), self.inner_radius,
                               facecolor='black',
                               edgecolor=self.secondary_color,
                               linewidth=5,
                               zorder=20)
        ax.add_patch(center_circle)

        # For now, just show team text (no logo)
        fan_text = f"THE {self.team_short.upper()} FAN"
        ax.text(0, 0, fan_text,
                ha='center', va='center',
                fontsize=16, fontweight='bold',
                color='white', zorder=22)

    def _add_segment_content(self, ax, wheel_data: pd.DataFrame, angle_step: float):
        """Add logos and behavior text to each segment"""
        for i, (_, row) in enumerate(wheel_data.iterrows()):
            center_angle = i * angle_step + angle_step / 2 - 90
            angle_rad = np.deg2rad(center_angle)

            # Logo position
            logo_x = self.logo_radius * np.cos(angle_rad)
            logo_y = self.logo_radius * np.sin(angle_rad)

            # Add logo
            self._add_merchant_logo(ax, row['MERCHANT'], logo_x, logo_y)

            # Add behavior text
            text_radius = (self.logo_radius + self.outer_radius) / 2
            text_x = text_radius * np.cos(angle_rad)
            text_y = text_radius * np.sin(angle_rad)

            ax.text(text_x, text_y, row['behavior'],
                    ha='center', va='center',
                    fontsize=14, fontweight='bold',
                    color='white',
                    rotation=0,
                    linespacing=0.8,
                    zorder=7)

    def _add_merchant_logo(self, ax, merchant: str, x: float, y: float):
        """Add merchant logo placeholder - simple white circle"""
        # White circle placeholder
        logo_bg = Circle((x, y), 0.55,
                         facecolor='white',
                         edgecolor='#E0E0E0',  # Light gray border
                         linewidth=1,
                         zorder=5)
        ax.add_patch(logo_bg)

        # Add merchant initials as placeholder text
        initials = ''.join([word[0].upper() for word in merchant.split()[:2]])
        ax.text(x, y, initials,
                ha='center', va='center',
                fontsize=12, fontweight='bold',
                color='#888888', zorder=6)


def create_fan_wheel_from_data(merchant_ranker, team_config: Dict[str, any],
                               output_path: Optional[Path] = None) -> Path:
    """
    Convenience function to create fan wheel using MerchantRanker

    Args:
        merchant_ranker: Instance of MerchantRanker with data
        team_config: Team configuration dictionary
        output_path: Optional output path

    Returns:
        Path to generated fan wheel
    """
    # Get fan wheel data
    wheel_data = merchant_ranker.get_fan_wheel_data(
        min_audience_pct=0.20,
        top_n_communities=10
    )

    if wheel_data.empty:
        raise ValueError("No fan wheel data available")

    # Create fan wheel
    fan_wheel = FanWheel(team_config)

    # No team logo for now
    return fan_wheel.create(wheel_data, output_path, team_logo=None)