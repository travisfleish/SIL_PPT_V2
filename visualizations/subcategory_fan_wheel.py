# visualizations/subcategory_fan_wheel.py
"""
Subcategory-based Fan Wheel Visualization
Shows top subcategory from each of the top 10 categories
"""

import matplotlib.pyplot as plt
from matplotlib.patches import Wedge, Circle
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from matplotlib.colors import LinearSegmentedColormap
import numpy as np
from PIL import Image
from pathlib import Path
import logging
from typing import Dict, Optional, List
import pandas as pd

from .fan_wheel import FanWheel
from utils.font_manager import font_manager

logger = logging.getLogger(__name__)


class SubcategoryFanWheel(FanWheel):
    """Fan wheel showing top subcategories from top categories"""
    
    def __init__(self, team_config: Dict, enable_logos: bool = True, logo_dir: Optional[Path] = None):
        """
        Initialize subcategory fan wheel generator
        
        Args:
            team_config: Team configuration with colors and names
            enable_logos: Whether to enable logo loading (default: True)
            logo_dir: Optional custom logo directory path
        """
        super().__init__(team_config, enable_logos, logo_dir)
        
        # Get primary color (red) from team config
        colors = team_config.get('colors', {})
        self.primary_color = colors.get('primary', '#E10600')  # F1 Red default
        
        # Heatmap parameters (set before creating colormap)
        # Much wider range for highly visible contrast
        self.heatmap_min_intensity = 0.10  # Very dark red for higher indices (lower intensity = darker)
        self.heatmap_max_intensity = 1.0   # Full brightness red for lower indices (higher intensity = lighter)
        
        # Create red-based colormap for heatmap
        self._create_red_colormap()
    
    def _create_red_colormap(self):
        """Create a custom red-based colormap for the heatmap"""
        hex_color = self.primary_color.lstrip('#')
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        
        # Create colormap from lighter red to darker red
        colors_list = [
            (r/255.0 * self.heatmap_max_intensity, g/255.0 * self.heatmap_max_intensity, b/255.0 * self.heatmap_max_intensity, 1.0),  # Lighter (lower index)
            (r/255.0 * self.heatmap_min_intensity, g/255.0 * self.heatmap_min_intensity, b/255.0 * self.heatmap_min_intensity, 1.0),  # Darker (higher index)
        ]
        
        n_bins = 256
        self.red_cmap = LinearSegmentedColormap.from_list('red_heatmap', colors_list, N=n_bins)
    
    def _add_segment_content(self, ax, wheel_data: pd.DataFrame, angle_step: float):
        """
        Add subcategory text to each segment in the outer ring (no logos for subcategories)
        
        Args:
            ax: Matplotlib axis
            wheel_data: DataFrame with SUBCATEGORY column
            angle_step: Angle step between segments
        """
        num_items = len(wheel_data)
        
        for i, (_, row) in enumerate(wheel_data.iterrows()):
            subcategory = row['SUBCATEGORY']
            
            # Calculate angle for this segment (center of segment)
            # Start at 12:00 (90°) and go clockwise
            angle_center = 90 - (i * angle_step + angle_step / 2)
            
            # Convert to radians
            angle_rad = np.radians(angle_center)
            
            # Position for text in outer ring (between logo radius and outer radius)
            text_radius = (self.logo_radius + self.outer_radius) / 2
            
            # Calculate position
            x = text_radius * np.cos(angle_rad)
            y = text_radius * np.sin(angle_rad)
            
            # Format subcategory name (remove category prefix if present)
            display_name = self._format_subcategory_name(subcategory)
            
            # Split text into two lines if needed
            lines = self._split_text_into_lines(display_name, max_chars_per_line=15)
            
            # Add text in outer ring - always horizontal, larger font, bold, two lines
            for line_idx, line in enumerate(lines):
                line_y_offset = (len(lines) - 1) * 0.15 - line_idx * 0.3  # Space lines vertically
                ax.text(x, y + line_y_offset, line,
                       ha='center', va='center',
                       fontsize=18,  # Increased font size
                       fontfamily=self.font_family,
                       fontweight='bold',  # Bold text
                       color='white',
                       rotation=0)  # Always horizontal
    
    def _format_subcategory_name(self, subcategory: str) -> str:
        """
        Format subcategory name for display
        Removes category prefix if it's redundant (e.g., "Apparel - Luxury" -> "Luxury")
        
        Args:
            subcategory: Full subcategory name
            
        Returns:
            Formatted name for display
        """
        # If subcategory contains " - ", split and take the part after the dash
        if ' - ' in subcategory:
            parts = subcategory.split(' - ', 1)
            if len(parts) == 2:
                return parts[1].strip()
        
        return subcategory
    
    def _split_text_into_lines(self, text: str, max_chars_per_line: int = 15) -> List[str]:
        """
        Split text into two lines, trying to break at word boundaries
        
        Args:
            text: Text to split
            max_chars_per_line: Maximum characters per line
            
        Returns:
            List of text lines (1 or 2 lines)
        """
        if len(text) <= max_chars_per_line:
            return [text]
        
        # Try to split at word boundaries
        words = text.split()
        if len(words) == 1:
            # Single long word - split in middle
            mid = len(text) // 2
            return [text[:mid], text[mid:]]
        
        # Find best split point
        line1_words = []
        line1_length = 0
        
        for word in words:
            test_length = line1_length + len(word) + (1 if line1_words else 0)
            if test_length <= max_chars_per_line:
                line1_words.append(word)
                line1_length = test_length
            else:
                break
        
        if not line1_words:
            # First word is too long, split first word
            first_word = words[0]
            mid = len(first_word) // 2
            return [first_word[:mid], first_word[mid:] + ' ' + ' '.join(words[1:])]
        
        line1 = ' '.join(line1_words)
        line2 = ' '.join(words[len(line1_words):])
        
        return [line1, line2]
    
    def _draw_heatmap_wheel(self, ax, wheel_data: pd.DataFrame, num_items: int, angle_step: float):
        """
        Draw entire wheel as heatmap based on blended indices
        Lower indices = lighter red, higher indices = darker red
        Starts at 12:00 (top) with highest index
        
        Args:
            ax: Matplotlib axis
            wheel_data: DataFrame with BLENDED_INDEX column (already sorted descending)
            num_items: Number of segments
            angle_step: Angle step between segments
        """
        if 'BLENDED_INDEX' not in wheel_data.columns:
            logger.warning("BLENDED_INDEX not found in wheel_data, using uniform color")
            # Draw uniform red wedges
            for i in range(num_items):
                start_angle = 90 - i * angle_step  # Start at 12:00 (top) and go clockwise
                end_angle = 90 - (i + 1) * angle_step
                full_wedge = Wedge((0, 0), self.outer_radius, start_angle, end_angle,
                                  width=self.outer_radius,
                                  facecolor=self.primary_color,
                                  edgecolor='none',
                                  zorder=1)
                ax.add_patch(full_wedge)
            return
        
        # Get blended index values
        blended_indices = wheel_data['BLENDED_INDEX'].values
        
        # Normalize to 0-1 range (invert so higher = darker)
        min_index = blended_indices.min()
        max_index = blended_indices.max()
        
        if max_index == min_index:
            # All values are the same, use uniform color
            normalized_indices = np.ones(num_items) * 0.5
        else:
            # Normalize: higher index = higher normalized value (for darker color)
            # Colormap: position 0 = lighter, position 1 = darker
            # So higher blended index should map to position 1 (darker)
            normalized_indices = (blended_indices - min_index) / (max_index - min_index)
        
        logger.info(f"Blended index range: min={min_index:.2f}, max={max_index:.2f}")
        logger.info(f"Normalized range: {normalized_indices.min():.3f} - {normalized_indices.max():.3f}")
        
        # Draw entire wheel as heatmap wedges (from inner_radius to outer_radius)
        for i in range(num_items):
            start_angle = 90 - i * angle_step  # Start at 12:00 (top) and go clockwise
            end_angle = 90 - (i + 1) * angle_step
            
            # Get color for this segment based on normalized index
            color_value = float(normalized_indices[i])  # Ensure it's a Python float
            color_rgba = self.red_cmap(color_value)
            
            # Convert RGBA to hex color string (more reliable for matplotlib)
            if hasattr(color_rgba, '__iter__') and len(color_rgba) >= 3:
                r_val = int(float(color_rgba[0]) * 255)
                g_val = int(float(color_rgba[1]) * 255)
                b_val = int(float(color_rgba[2]) * 255)
                color = f'#{r_val:02x}{g_val:02x}{b_val:02x}'
            else:
                color = self.primary_color  # Fallback
            
            logger.info(f"Segment {i}: blended_index={blended_indices[i]:.2f}, normalized={color_value:.3f}, color={color}")
            
            # Draw full wedge (entire segment from inner to outer)
            full_wedge = Wedge((0, 0), self.outer_radius, start_angle, end_angle,
                              width=self.outer_radius - self.inner_radius,
                              facecolor=color,
                              edgecolor='none',
                              zorder=1)
            ax.add_patch(full_wedge)
    
    def _add_dividing_lines_corrected(self, ax, num_items: int, angle_step: float):
        """Add white dividing lines between segments (starting at 12:00)"""
        for i in range(num_items):
            angle = 90 - i * angle_step  # Start at 12:00 and go clockwise
            angle_rad = np.deg2rad(angle)

            x_inner = self.inner_radius * np.cos(angle_rad)
            y_inner = self.inner_radius * np.sin(angle_rad)
            x_outer = self.outer_radius * np.cos(angle_rad)
            y_outer = self.outer_radius * np.sin(angle_rad)

            ax.plot([x_inner, x_outer], [y_inner, y_outer],
                    color='white', linewidth=8, zorder=15)
    
    def create(self, wheel_data: pd.DataFrame,
               output_path: Optional[Path] = None,
               team_logo: Optional[Image.Image] = None) -> Path:
        """
        Create subcategory fan wheel visualization
        
        Args:
            wheel_data: DataFrame with columns: CATEGORY, SUBCATEGORY, BLENDED_INDEX, PERC_INDEX, SPC_INDEX
            output_path: Where to save the visualization
            team_logo: Optional PIL Image of team logo
            
        Returns:
            Path to saved visualization
        """
        if output_path is None:
            output_path = Path(f'{self.team_short.lower()}_subcategory_fan_wheel.png')
        
        # Validate required columns
        required_cols = ['SUBCATEGORY']
        missing_cols = [col for col in required_cols if col not in wheel_data.columns]
        if missing_cols:
            raise ValueError(f"wheel_data missing required columns: {missing_cols}")
        
        # Create figure
        dpi = 150 if self.enable_logos else 100
        fig = plt.figure(figsize=(12, 12), facecolor='white', dpi=dpi)
        ax = fig.add_subplot(111, aspect='equal')
        
        # Set limits
        margin = 0.3
        limit = self.outer_radius + margin
        ax.set_xlim(-limit, limit)
        ax.set_ylim(-limit, limit)
        ax.axis('off')
        
        # Sort by blended index descending (highest first) to start at 12:00
        if 'BLENDED_INDEX' in wheel_data.columns:
            wheel_data = wheel_data.sort_values('BLENDED_INDEX', ascending=False).reset_index(drop=True)
            logger.info("Sorted data by BLENDED_INDEX descending (highest at 12:00)")
        
        num_items = len(wheel_data)
        if num_items == 0:
            raise ValueError("No data provided for fan wheel")
        
        angle_step = 360 / num_items
        
        # Draw entire wheel as heatmap (no separate inner/outer rings)
        self._draw_heatmap_wheel(ax, wheel_data, num_items, angle_step)
        
        # Add dividing lines (with corrected angles for 12:00 start)
        self._add_dividing_lines_corrected(ax, num_items, angle_step)
        
        # Add arrows
        self._add_arrows(ax, num_items, angle_step)
        
        # Draw center circle
        self._draw_center_circle(ax, team_logo)
        
        # Add subcategory text to each segment
        self._add_segment_content(ax, wheel_data, angle_step)
        
        # Save
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight',
                    facecolor='white', edgecolor='none',
                    pad_inches=0.05)
        plt.close()
        
        logger.info(f"Subcategory fan wheel saved to {output_path}")
        return output_path

