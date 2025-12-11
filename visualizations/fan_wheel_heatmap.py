# visualizations/fan_wheel_heatmap.py
"""
Fan Wheel with Heat Map Inner Ring
Creates a fan wheel visualization where the inner ring is a heat map gradient
weighted by the merchant's composite index
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Wedge, Circle, Polygon
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import logging
from typing import Dict, Optional, List, Tuple
import pandas as pd
from textwrap import wrap

from .fan_wheel import FanWheel
from utils.logo_manager import LogoManager
from utils.font_manager import font_manager

logger = logging.getLogger(__name__)


class FanWheelHeatmap(FanWheel):
    """
    Extended Fan Wheel with heat map inner ring
    The inner ring (between center circle and logo radius) displays a gradient
    heat map where intensity is weighted by the merchant's composite index
    """

    def __init__(self, team_config: Dict[str, any], enable_logos: bool = True, logo_dir: Optional[Path] = None):
        """
        Initialize fan wheel with heat map

        Args:
            team_config: Team configuration with colors and names
            enable_logos: Whether to enable logo loading (default: True)
            logo_dir: Optional custom logo directory path
        """
        super().__init__(team_config, enable_logos, logo_dir)
        
        # Get primary color (red) from team config
        colors = team_config.get('colors', {})
        self.primary_color = colors.get('primary', '#E10600')  # F1 Red default
        
        # Heat map parameters - using red-based gradient
        self.heatmap_colormap = None  # Will use custom red colormap
        # Inverted: darker = higher composite index
        # Lighter range: darker red is lighter, lighter red is also lighter
        self.heatmap_min_intensity = 0.35  # Lighter dark red (for highest composite index)
        self.heatmap_max_intensity = 0.85  # Lighter bright red (for lowest composite index)
        
        # Create custom red-based colormap
        self._create_red_colormap()

    def create(self, wheel_data: pd.DataFrame,
               output_path: Optional[Path] = None,
               team_logo: Optional[Image.Image] = None) -> Path:
        """
        Create fan wheel visualization with heat map inner ring

        Args:
            wheel_data: DataFrame with columns: COMMUNITY, MERCHANT, behavior, PERC_INDEX, COMPOSITE_INDEX
            output_path: Where to save the visualization
            team_logo: Optional PIL Image of team logo

        Returns:
            Path to saved visualization
        """
        if output_path is None:
            output_path = Path(f'{self.team_short.lower()}_fan_wheel_heatmap.png')

        # Validate that COMPOSITE_INDEX exists in the data
        # Check for various possible column names - prefer merchant-level index over community-level
        wheel_data = wheel_data.copy()
        if 'COMPOSITE_INDEX' not in wheel_data.columns:
            # Try PERC_INDEX first (merchant-level, more relevant for individual merchants)
            if 'PERC_INDEX' in wheel_data.columns:
                logger.info("Using PERC_INDEX (merchant-level) for rose diagram bars")
                wheel_data['COMPOSITE_INDEX'] = wheel_data['PERC_INDEX']
            # Fall back to community-level if merchant-level not available
            elif 'COMMUNITY_COMPOSITE_INDEX' in wheel_data.columns:
                logger.info("Using COMMUNITY_COMPOSITE_INDEX (community-level) for rose diagram")
                wheel_data['COMPOSITE_INDEX'] = wheel_data['COMMUNITY_COMPOSITE_INDEX']
            else:
                raise ValueError("wheel_data must contain COMPOSITE_INDEX, PERC_INDEX, or COMMUNITY_COMPOSITE_INDEX")

        # Create figure with higher DPI if logos are enabled
        dpi = 150 if self.enable_logos else 100
        fig = plt.figure(figsize=(12, 12), facecolor='white', dpi=dpi)
        ax = fig.add_subplot(111, aspect='equal')

        # Reduce whitespace by setting limits closer to actual wheel size
        margin = 0.3
        limit = self.outer_radius + margin
        ax.set_xlim(-limit, limit)
        ax.set_ylim(-limit, limit)
        ax.axis('off')

        num_items = len(wheel_data)
        if num_items == 0:
            raise ValueError("No data provided for fan wheel")

        angle_step = 360 / num_items

        # Draw wedges (background only, no inner ring)
        self._draw_wedges_without_inner_ring(ax, num_items, angle_step)

        # Draw rose diagram bars (replaces the inner ring)
        self._draw_rose_diagram_bars(ax, wheel_data, num_items, angle_step)

        # Add dividing lines
        self._add_dividing_lines(ax, num_items, angle_step)

        # Add arrows
        self._add_arrows(ax, num_items, angle_step)

        # Draw center circle
        self._draw_center_circle(ax, team_logo)

        # Add logos and text for each segment
        self._add_segment_content(ax, wheel_data, angle_step)

        # Save with improved bbox settings to minimize whitespace
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight',
                    facecolor='white', edgecolor='none',
                    pad_inches=0.05)
        plt.close()

        logger.info(f"Fan wheel with heat map saved to {output_path}")
        return output_path

    def _draw_rose_diagram_bars(self, ax, wheel_data: pd.DataFrame, num_items: int, angle_step: float):
        """
        Draw rose diagram bars (polar bar chart) where bar length represents composite index
        
        Args:
            ax: Matplotlib axis
            wheel_data: DataFrame with COMPOSITE_INDEX column
            num_items: Number of segments
            angle_step: Angle step between segments
        """
        # Get composite index values
        composite_indices = wheel_data['COMPOSITE_INDEX'].values
        
        logger.info(f"Composite index values: min={composite_indices.min():.2f}, max={composite_indices.max():.2f}, "
                   f"mean={composite_indices.mean():.2f}, std={composite_indices.std():.2f}")
        
        # Normalize composite indices to bar length range
        min_index = composite_indices.min()
        max_index = composite_indices.max()
        
        # Bar parameters
        bar_start_radius = self.inner_radius  # Start from inner circle edge
        bar_max_length = self.logo_radius - self.inner_radius  # Maximum bar length (to logo radius)
        bar_width_degrees = angle_step * 0.8  # Bar width (80% of segment to leave gaps)
        
        # Use a lighter/brighter shade of red for bars to stand out from background
        # Convert hex to RGB and lighten it
        hex_color = self.primary_color.lstrip('#')
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        # Lighten by blending with white (70% original, 30% white)
        r_light = int(r * 0.7 + 255 * 0.3)
        g_light = int(g * 0.7 + 255 * 0.3)
        b_light = int(b * 0.7 + 255 * 0.3)
        bar_color = f"#{r_light:02x}{g_light:02x}{b_light:02x}"
        
        if max_index == min_index:
            # All values are the same, use uniform bar length
            logger.warning("All composite indices are the same - using uniform bar lengths")
            bar_lengths = np.ones(num_items) * (bar_max_length * 0.7)
        else:
            # Normalize to 0-1 range, then scale to bar length
            normalized_indices = (composite_indices - min_index) / (max_index - min_index)
            logger.info(f"Normalized indices range: {normalized_indices.min():.3f} - {normalized_indices.max():.3f}")
            # Scale to bar length (use 0.3 to 1.0 of max length for better visibility)
            bar_lengths = normalized_indices * (bar_max_length * 0.7) + (bar_max_length * 0.3)
            logger.info(f"Bar lengths range: {bar_lengths.min():.3f} - {bar_lengths.max():.3f}")
        
        # Draw bars for each segment
        for i in range(num_items):
            # Calculate center angle for this segment
            center_angle = i * angle_step + angle_step / 2 - 90
            center_angle_rad = np.deg2rad(center_angle)
            
            # Bar length for this segment
            bar_length = bar_lengths[i]
            
            # Calculate end radius (start radius + bar length)
            end_radius = bar_start_radius + bar_length
            
            # Calculate bar width in radians
            bar_width_rad = np.deg2rad(bar_width_degrees)
            half_width_rad = bar_width_rad / 2
            
            # Calculate the four corners of the bar (rectangle extending from inner radius)
            # Start angle (inner edge)
            start_angle_inner = center_angle_rad - half_width_rad
            start_angle_outer = center_angle_rad + half_width_rad
            
            # Corner points (going counter-clockwise)
            corners = [
                (bar_start_radius * np.cos(start_angle_inner),   # Inner corner, left side
                 bar_start_radius * np.sin(start_angle_inner)),
                (end_radius * np.cos(start_angle_inner),         # Outer corner, left side
                 end_radius * np.sin(start_angle_inner)),
                (end_radius * np.cos(start_angle_outer),         # Outer corner, right side
                 end_radius * np.sin(start_angle_outer)),
                (bar_start_radius * np.cos(start_angle_outer),   # Inner corner, right side
                 bar_start_radius * np.sin(start_angle_outer))
            ]
            
            # Draw bar as polygon - filled with lighter red color and white edge for visibility
            bar = Polygon(corners, 
                         facecolor=bar_color,  # Filled with lighter red
                         edgecolor='white',    # White edge for contrast
                         linewidth=2,          # Visible edge
                         zorder=3)  # Above background wedges (zorder=1) but below dividing lines (zorder=15)
            ax.add_patch(bar)
            
            # Debug: log first few bars
            if i < 3:
                community = wheel_data.iloc[i]['COMMUNITY'] if 'COMMUNITY' in wheel_data.columns else f"Segment {i}"
                composite_idx = wheel_data.iloc[i]['COMPOSITE_INDEX']
                logger.info(f"Bar {i}: {community} - Composite Index: {composite_idx:.2f}, Bar Length: {bar_length:.3f}, End Radius: {end_radius:.3f}")
        
        logger.info(f"Rose diagram bars drawn with length range: "
                   f"{bar_lengths.min():.2f} - {bar_lengths.max():.2f} "
                   f"(composite index range: {min_index:.2f} - {max_index:.2f})")

    def _draw_wedges_without_inner_ring(self, ax, num_items: int, angle_step: float):
        """
        Draw the wedge segments without the inner ring (bars will replace it)
        
        Args:
            ax: Matplotlib axis
            num_items: Number of segments
            angle_step: Angle step between segments
        """
        for i in range(num_items):
            start_angle = i * angle_step - 90
            end_angle = (i + 1) * angle_step - 90

            # Full wedge (background only - no inner ring)
            full_wedge = Wedge((0, 0), self.outer_radius, start_angle, end_angle,
                               width=self.outer_radius,
                               facecolor=self.primary_color,
                               edgecolor='none',
                               zorder=1)
            ax.add_patch(full_wedge)

    def _create_red_colormap(self):
        """
        Create a custom colormap using different shades/intensities of the primary red color
        Goes from darker red (low intensity) to full primary red (high intensity)
        """
        # Convert hex color to RGB (0-1 range)
        hex_color = self.primary_color.lstrip('#')
        r = int(hex_color[0:2], 16) / 255.0
        g = int(hex_color[2:4], 16) / 255.0
        b = int(hex_color[4:6], 16) / 255.0
        
        # Create gradient from lighter dark red to lighter bright red
        # Adjusted range: 0.35 (lighter dark) to 0.85 (lighter bright) for more subtle contrast
        colors = [
            (r * 0.35, g * 0.35, b * 0.35),  # Lighter dark red (for highest composite index)
            (r * 0.45, g * 0.45, b * 0.45),  # Medium-dark red
            (r * 0.55, g * 0.55, b * 0.55),  # Medium red
            (r * 0.65, g * 0.65, b * 0.65),  # Medium-bright red
            (r * 0.75, g * 0.75, b * 0.75),  # Bright red
            (r * 0.85, g * 0.85, b * 0.85)   # Lighter bright red (for lowest composite index)
        ]
        
        # Create colormap
        n_bins = 256
        self.red_colormap = LinearSegmentedColormap.from_list(
            'red_heatmap',
            colors,
            N=n_bins
        )
        
        logger.info(f"Created custom red colormap based on {self.primary_color}")

    def set_heatmap_colormap(self, colormap: str):
        """
        Set the colormap for the heat map (deprecated - now uses red-based colormap)
        This method is kept for compatibility but will recreate the red colormap
        
        Args:
            colormap: Name of matplotlib colormap (ignored, uses red-based gradient)
        """
        # Recreate red colormap (ignoring the parameter)
        self._create_red_colormap()
        logger.info(f"Heat map uses red-based gradient from {self.primary_color}")

    def set_heatmap_intensity_range(self, min_intensity: float = 0.35, max_intensity: float = 0.85):
        """
        Set the intensity range for the heat map
        
        Args:
            min_intensity: Minimum intensity (0-1) - darker red for HIGHEST composite index (inverted)
            max_intensity: Maximum intensity (0-1) - brighter red for LOWEST composite index (inverted)
        """
        self.heatmap_min_intensity = max(0.0, min(1.0, min_intensity))
        self.heatmap_max_intensity = max(0.0, min(1.0, max_intensity))
        # Recreate colormap with new range
        self._create_red_colormap()
        logger.info(f"Heat map intensity range set to: {self.heatmap_min_intensity} - {self.heatmap_max_intensity} (inverted: darker = higher composite index)")

