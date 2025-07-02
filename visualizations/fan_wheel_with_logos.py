# visualizations/fan_wheel_with_logos.py
"""
Enhanced Fan Wheel Visualization with Logo Integration
Creates circular fan behavior visualization using local logo files
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
from utils.logo_manager import LogoManager

logger = logging.getLogger(__name__)


class EnhancedFanWheel(BaseChart):
    """Generate fan wheel visualization with integrated logo support"""

    def __init__(self, team_config: Dict[str, any], logo_dir: Optional[Path] = None):
        """
        Initialize enhanced fan wheel generator

        Args:
            team_config: Team configuration with colors and names
            logo_dir: Optional path to logo directory
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

        # Logo settings
        self.logo_size = (110, 110)  # Size for logos in pixels
        self.logo_circle_radius = 0.55  # Radius of logo background circle

        # Initialize logo manager
        self.logo_manager = LogoManager(logo_dir)

    def create(self, wheel_data: pd.DataFrame,
               output_path: Optional[Path] = None,
               team_logo: Optional[Image.Image] = None,
               use_fallback_for_missing: bool = True) -> Path:
        """
        Create enhanced fan wheel visualization with logos

        Args:
            wheel_data: DataFrame with columns: COMMUNITY, MERCHANT, behavior, PERC_INDEX
            output_path: Where to save the visualization
            team_logo: Optional PIL Image of team logo
            use_fallback_for_missing: Whether to create fallback logos for missing ones

        Returns:
            Path to saved visualization
        """
        if output_path is None:
            output_path = Path(f'{self.team_short.lower()}_fan_wheel_enhanced.png')

        # Create figure with high DPI for crisp logos
        fig = plt.figure(figsize=(12, 12), facecolor='white', dpi=150)
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
        self._add_segment_content_with_logos(ax, wheel_data, angle_step, use_fallback_for_missing)

        # Save with high quality
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight',
                    facecolor='white', edgecolor='none',
                    pil_kwargs={'quality': 95})
        plt.close()

        logger.info(f"Enhanced fan wheel saved to {output_path}")
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
                               alpha=0.7,
                               zorder=2)
            ax.add_patch(outer_ring)

    def _add_dividing_lines(self, ax, num_items: int, angle_step: float):
        """Add dividing lines between segments"""
        for i in range(num_items):
            angle = i * angle_step - 90
            angle_rad = np.deg2rad(angle)

            # Line from center to outer edge
            x1, y1 = 0, 0
            x2 = self.outer_radius * np.cos(angle_rad)
            y2 = self.outer_radius * np.sin(angle_rad)

            ax.plot([x1, x2], [y1, y2], color='white', linewidth=3, zorder=10)

    def _add_arrows(self, ax, num_items: int, angle_step: float):
        """Add directional arrows"""
        for i in range(num_items):
            center_angle = i * angle_step + angle_step / 2 - 90
            angle_rad = np.deg2rad(center_angle)

            # Arrow position (between logo radius and outer radius)
            arrow_radius = (self.logo_radius + self.outer_radius) / 2 + 0.3
            arrow_x = arrow_radius * np.cos(angle_rad)
            arrow_y = arrow_radius * np.sin(angle_rad)

            # Arrow direction (pointing outward)
            arrow_direction = angle_rad

            # Arrow geometry
            arrow_length = 0.3
            tip_x = arrow_x + arrow_length * np.cos(arrow_direction)
            tip_y = arrow_y + arrow_length * np.sin(arrow_direction)

            base_offset = 0.15
            base_center_x = arrow_x - (arrow_length * 0.4) * np.cos(arrow_direction)
            base_center_y = arrow_y - (arrow_length * 0.4) * np.sin(arrow_direction)

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

        # Team text (could be enhanced with actual logo later)
        fan_text = f"THE {self.team_short.upper()} FAN"
        ax.text(0, 0, fan_text,
                ha='center', va='center',
                fontsize=16, fontweight='bold',
                color='white', zorder=22)

    def _add_segment_content_with_logos(self, ax, wheel_data: pd.DataFrame,
                                        angle_step: float, use_fallback: bool = True):
        """Add logos and behavior text to each segment"""
        missing_logos = []

        for i, (_, row) in enumerate(wheel_data.iterrows()):
            center_angle = i * angle_step + angle_step / 2 - 90
            angle_rad = np.deg2rad(center_angle)

            # Logo position
            logo_x = self.logo_radius * np.cos(angle_rad)
            logo_y = self.logo_radius * np.sin(angle_rad)

            # Try to add actual logo
            merchant_name = row['MERCHANT']
            logo_added = self._add_merchant_logo_enhanced(ax, merchant_name, logo_x, logo_y, use_fallback)

            if not logo_added:
                missing_logos.append(merchant_name)

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

        # Log missing logos for debugging
        if missing_logos:
            logger.info(f"Missing logos for: {', '.join(missing_logos)}")

    def _add_merchant_logo_enhanced(self, ax, merchant: str, x: float, y: float,
                                    use_fallback: bool = True) -> bool:
        """
        Add merchant logo with enhanced loading capabilities

        Args:
            ax: Matplotlib axis
            merchant: Merchant name
            x, y: Position coordinates
            use_fallback: Whether to use fallback if logo not found

        Returns:
            True if logo was added (real or fallback), False otherwise
        """
        # Try to get actual logo
        logo_img = self.logo_manager.get_logo(merchant, self.logo_size)

        if logo_img is not None:
            # Add actual logo
            self._add_logo_to_plot(ax, logo_img, x, y)
            return True
        elif use_fallback:
            # Create and add fallback logo
            fallback_logo = self.logo_manager.create_fallback_logo(
                merchant, self.logo_size, 'white', '#888888'
            )
            self._add_logo_to_plot(ax, fallback_logo, x, y)
            return True
        else:
            # No logo added
            return False

    def _add_logo_to_plot(self, ax, logo_img: Image.Image, x: float, y: float):
        """
        Add PIL Image logo to matplotlib plot

        Args:
            ax: Matplotlib axis
            logo_img: PIL Image
            x, y: Position coordinates
        """
        # Convert PIL to numpy array for matplotlib
        logo_array = np.array(logo_img)

        # Create OffsetImage
        imagebox = OffsetImage(logo_array, zoom=0.5)  # Adjust zoom as needed

        # Create AnnotationBbox
        ab = AnnotationBbox(imagebox, (x, y),
                            frameon=False,  # No frame around logo
                            pad=0,  # No padding
                            zorder=15)  # High z-order to appear on top

        # Add to plot
        ax.add_artist(ab)

    def generate_logo_report(self, wheel_data: pd.DataFrame) -> Dict[str, any]:
        """
        Generate report on logo availability for merchants in wheel data

        Args:
            wheel_data: DataFrame with MERCHANT column

        Returns:
            Dictionary with logo availability statistics
        """
        merchants = wheel_data['MERCHANT'].unique().tolist()
        logo_report = self.logo_manager.add_missing_logos_report(merchants)

        total_merchants = len(merchants)
        with_logos = sum(logo_report.values())
        missing_logos = total_merchants - with_logos

        return {
            'total_merchants': total_merchants,
            'with_logos': with_logos,
            'missing_logos': missing_logos,
            'coverage_percentage': (with_logos / total_merchants) * 100 if total_merchants > 0 else 0,
            'detailed_report': logo_report,
            'missing_list': [merchant for merchant, has_logo in logo_report.items() if not has_logo]
        }


def create_enhanced_fan_wheel_from_data(merchant_ranker, team_config: Dict[str, any],
                                        output_path: Optional[Path] = None,
                                        logo_dir: Optional[Path] = None) -> Tuple[Path, Dict]:
    """
    Convenience function to create enhanced fan wheel using MerchantRanker

    Args:
        merchant_ranker: Instance of MerchantRanker with data
        team_config: Team configuration dictionary
        output_path: Optional output path
        logo_dir: Optional logo directory path

    Returns:
        Tuple of (Path to generated fan wheel, logo report dictionary)
    """
    # Get fan wheel data
    wheel_data = merchant_ranker.get_fan_wheel_data(
        min_audience_pct=0.20,
        top_n_communities=10
    )

    if wheel_data.empty:
        raise ValueError("No fan wheel data available")

    # Create enhanced fan wheel
    fan_wheel = EnhancedFanWheel(team_config, logo_dir)

    # Generate logo report
    logo_report = fan_wheel.generate_logo_report(wheel_data)

    # Create visualization
    wheel_path = fan_wheel.create(wheel_data, output_path, team_logo=None)

    return wheel_path, logo_report