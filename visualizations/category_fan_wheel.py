# visualizations/category_fan_wheel.py
"""
Category-based Fan Wheel Visualization
Shows top categories by PERC_INDEX instead of merchants from communities
"""

import matplotlib.pyplot as plt
from matplotlib.patches import Wedge, Circle
from matplotlib.colors import LinearSegmentedColormap
import numpy as np
from pathlib import Path
import logging
from typing import Dict, Optional
import pandas as pd
from PIL import Image
from textwrap import wrap

from .fan_wheel import FanWheel
from utils.font_manager import font_manager

logger = logging.getLogger(__name__)

# Try to import LAB color space conversion
try:
    from skimage.color import rgb2lab, lab2rgb
    HAS_SKIMAGE = True
    HAS_COLORMATH = False
except ImportError:
    try:
        from colormath.color_objects import LabColor, sRGBColor
        from colormath.color_conversions import convert_color
        HAS_COLORMATH = True
        HAS_SKIMAGE = False
    except ImportError:
        HAS_SKIMAGE = False
        HAS_COLORMATH = False
        logger.warning("Neither skimage nor colormath available, using perceptual brightness approximation")


class CategoryFanWheel(FanWheel):
    """Fan wheel showing top categories by PERC_INDEX"""
    
    def __init__(self, team_config: Dict, enable_logos: bool = False, logo_dir: Optional[Path] = None):
        """
        Initialize category fan wheel generator
        
        Args:
            team_config: Team configuration with colors and names
            enable_logos: Whether to enable logo loading (default: False for categories)
            logo_dir: Optional custom logo directory path
        """
        super().__init__(team_config, enable_logos, logo_dir)
        
        # Get primary color from team config
        colors = team_config.get('colors', {})
        self.primary_color = colors.get('primary', '#002244')
        
        # Create red colormap for heat map inner ring
        self._create_red_colormap()
    
    def _rgb_to_lab(self, rgb):
        """Convert RGB to LAB color space (perceptual brightness)"""
        if HAS_SKIMAGE:
            rgb_array = np.array([[rgb]])
            lab_array = rgb2lab(rgb_array)
            return lab_array[0, 0], lab_array[0, 1], lab_array[0, 2]
        elif HAS_COLORMATH:
            rgb_obj = sRGBColor(rgb[0], rgb[1], rgb[2], is_upscaled=False)
            lab_obj = convert_color(rgb_obj, LabColor)
            return lab_obj.lab_l, lab_obj.lab_a, lab_obj.lab_b
        else:
            # Perceptual brightness approximation using relative luminance
            # This approximates LAB L* (lightness) component
            r, g, b = rgb
            # Linearize sRGB values
            def linearize(c):
                return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
            r_lin = linearize(r)
            g_lin = linearize(g)
            b_lin = linearize(b)
            # Relative luminance (Y in XYZ color space)
            y = 0.2126 * r_lin + 0.7152 * g_lin + 0.0722 * b_lin
            # Approximate LAB L* from Y (perceptual lightness)
            # L* = 116 * f(Y/Yn) - 16, where f(t) = t^(1/3) if t > (6/29)^3, else (1/3)*((29/6)^2)*t + 4/29
            # For D65 white point, Yn = 1.0
            if y > 0.008856:
                lab_l = 116 * (y ** (1/3)) - 16
            else:
                lab_l = 903.3 * y
            # For red hue, approximate a* and b* (red has positive a*, near-zero b*)
            # These are rough approximations but maintain red hue
            lab_a = 50 + (r - 0.5) * 30  # Red hue component
            lab_b = 20 + (g - 0.1) * 10  # Slight yellow tint
            return lab_l, lab_a, lab_b
    
    def _lab_to_rgb(self, l, a, b):
        """Convert LAB to RGB color space (perceptual brightness)"""
        if HAS_SKIMAGE:
            lab_array = np.array([[[l, a, b]]])
            rgb_array = lab2rgb(lab_array)
            return tuple(rgb_array[0, 0])
        elif HAS_COLORMATH:
            lab_obj = LabColor(lab_l=l, lab_a=a, lab_b=b)
            rgb_obj = convert_color(lab_obj, sRGBColor)
            return (rgb_obj.rgb_r, rgb_obj.rgb_g, rgb_obj.rgb_b)
        else:
            # Approximate LAB to RGB conversion
            # Convert L* back to Y (luminance)
            l_norm = (l + 16) / 116
            if l_norm > 0.206897:
                y = l_norm ** 3
            else:
                y = (l_norm - 16/116) / 7.787
            
            # For red hue, reconstruct RGB maintaining red color
            # Use a* to determine red intensity, keep hue red
            # Simplified: maintain red hue while varying brightness
            red_intensity = min(1.0, max(0.0, (a - 20) / 50))  # Normalize a* to red intensity
            
            # Calculate RGB from luminance and red hue
            # For red, we want high R, low G, very low B
            # Adjust based on luminance (y) and red intensity
            r = min(1.0, max(0.0, y * (1.0 + red_intensity * 0.5)))
            g = min(1.0, max(0.0, y * 0.3 * (1 - red_intensity * 0.7)))
            b = min(1.0, max(0.0, y * 0.1 * (1 - red_intensity * 0.9)))
            
            # Gamma correction (inverse of linearization)
            def gamma_correct(c):
                return 12.92 * c if c <= 0.0031308 else 1.055 * (c ** (1/2.4)) - 0.055
            
            r = gamma_correct(r)
            g = gamma_correct(g)
            b = gamma_correct(b)
            
            return (r, g, b)
    
    def _create_red_colormap(self):
        """
        Create a perceptually uniform colormap using LAB color space
        Low PERC_INDEX = dark red (low L*)
        High PERC_INDEX = very light red (high L*)
        Hue fixed at red, only brightness (L*) varies
        """
        # Convert primary red to LAB to get the red hue (a*, b*)
        hex_color = self.primary_color.lstrip('#')
        r = int(hex_color[0:2], 16) / 255.0
        g = int(hex_color[2:4], 16) / 255.0
        b = int(hex_color[4:6], 16) / 255.0
        
        primary_rgb = (r, g, b)
        lab_l_primary, lab_a_primary, lab_b_primary = self._rgb_to_lab(primary_rgb)
        
        # Create gradient by varying only L* (lightness) in LAB space
        # Low PERC_INDEX: dark red (L* = 20-30)
        # High PERC_INDEX: very light red (L* = 85-95)
        # Keep a* and b* constant to maintain red hue
        
        colors = []
        n_steps = 256
        
        for i in range(n_steps):
            t = i / (n_steps - 1)
            # Interpolate L* from dark (20) to very light (90)
            # Large spread for visibility on dark background
            lab_l = 20 + t * 70  # 20 (dark) to 90 (very light)
            # Keep a* and b* constant for red hue
            lab_a = lab_a_primary
            lab_b = lab_b_primary
            
            # Convert back to RGB
            rgb = self._lab_to_rgb(lab_l, lab_a, lab_b)
            colors.append(rgb)
        
        # Create colormap
        self.red_colormap = LinearSegmentedColormap.from_list(
            'perceptual_red_heatmap',
            colors,
            N=n_steps
        )
        
        logger.info(f"Created perceptual LAB-based colormap: dark red (L*=20) -> light red (L*=90)")
        logger.info(f"Red hue: a*={lab_a_primary:.1f}, b*={lab_b_primary:.1f}")
    
    def _add_segment_content(self, ax, wheel_data: pd.DataFrame, angle_step: float):
        """
        Add category text to each segment in outer ring only (no indexes)
        Uses same text positioning and wrapping as original fan wheel
        
        Args:
            ax: Matplotlib axis
            wheel_data: DataFrame with CATEGORY column
            angle_step: Angle step between segments
        """
        num_items = len(wheel_data)
        
        for i, (_, row) in enumerate(wheel_data.iterrows()):
            category = row['CATEGORY']
            
            # Calculate angle for this segment (center of segment)
            center_angle = i * angle_step + angle_step / 2 - 90
            angle_rad = np.deg2rad(center_angle)
            
            # Position for category name in outer ring - inset more than original
            text_radius = self.outer_radius - 1.1  # More inset to keep text within segments
            text_x = text_radius * np.cos(angle_rad)
            text_y = text_radius * np.sin(angle_rad)
            
            # Wrap the category text to fit in the wedge - same logic as original
            word_count = len(category.split())
            
            if word_count >= 4 or len(category) > 20:
                # 4+ words or long text should wrap to 3 lines
                # Use width=10 to force more aggressive wrapping
                wrapped_text = '\n'.join(wrap(category,
                                              width=10,
                                              break_long_words=False))
            elif word_count == 3 or len(category) > 12:
                # 3 words or medium text should wrap to 2-3 lines
                # Use width=11 for moderate wrapping
                wrapped_text = '\n'.join(wrap(category,
                                              width=11,
                                              break_long_words=False))
            else:
                # 1-2 words or very short text can stay on one line
                wrapped_text = category
            
            # Additional check: if we still only got 2 lines but text is long,
            # try again with tighter width
            lines = wrapped_text.split('\n')
            if len(lines) == 2 and len(category) > 18:
                wrapped_text = '\n'.join(wrap(category,
                                              width=9,
                                              break_long_words=False))
            
            # Add category text - same parameters as original fan wheel
            ax.text(text_x, text_y, wrapped_text,
                    ha='center', va='center',
                    fontsize=22,  # Match original fan wheel fontsize
                    fontweight='bold',
                    fontfamily=self.font_family,
                    color='white',
                    rotation=0,
                    linespacing=0.9,  # Match original fan wheel line spacing
                    zorder=7)
    
    def _split_category_text(self, text: str, max_chars_per_line: int = 15) -> list:
        """
        Split category text into lines, trying to break at word boundaries
        
        Args:
            text: Category name to split
            max_chars_per_line: Maximum characters per line
            
        Returns:
            List of text lines (1-3 lines)
        """
        if len(text) <= max_chars_per_line:
            return [text]
        
        # Try to split at word boundaries
        words = text.split()
        if len(words) == 1:
            # Single long word - split in middle
            mid = len(text) // 2
            return [text[:mid], text[mid:]]
        
        # Find best split points for 2-3 lines
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
        
        remaining_words = words[len(line1_words):]
        
        # If remaining text is short, just use 2 lines
        remaining_text = ' '.join(remaining_words)
        if len(remaining_text) <= max_chars_per_line:
            return [' '.join(line1_words), remaining_text]
        
        # Need 3 lines - split remaining text
        line2_words = []
        line2_length = 0
        
        for word in remaining_words:
            test_length = line2_length + len(word) + (1 if line2_words else 0)
            if test_length <= max_chars_per_line:
                line2_words.append(word)
                line2_length = test_length
            else:
                break
        
        if not line2_words:
            # Second word is too long, split it
            second_word = remaining_words[0]
            mid = len(second_word) // 2
            return [
                ' '.join(line1_words),
                second_word[:mid],
                second_word[mid:] + ' ' + ' '.join(remaining_words[1:])
            ]
        
        line1 = ' '.join(line1_words)
        line2 = ' '.join(line2_words)
        line3 = ' '.join(remaining_words[len(line2_words):])
        
        return [line1, line2, line3]
    
    def _draw_wedges_with_heatmap(self, ax, wheel_data: pd.DataFrame, num_items: int, angle_step: float):
        """
        Draw wedge segments with heat map inner ring based on PERC_INDEX
        Higher PERC_INDEX = darker red, Lower PERC_INDEX = lighter red
        
        Args:
            ax: Matplotlib axis
            wheel_data: DataFrame with PERC_INDEX column
            num_items: Number of segments
            angle_step: Angle step between segments
        """
        # Get PERC_INDEX values
        if 'PERC_INDEX' not in wheel_data.columns:
            logger.warning("PERC_INDEX not found, using uniform color for inner ring")
            perc_indices = np.ones(num_items) * 100  # Default value
        else:
            perc_indices = wheel_data['PERC_INDEX'].values
        
        # Normalize PERC_INDEX to 0-1 range (higher index = higher normalized value)
        min_index = perc_indices.min()
        max_index = perc_indices.max()
        
        if max_index == min_index:
            # All values are the same, use uniform color
            normalized_indices = np.ones(num_items) * 0.5
        else:
            # Normalize: higher PERC_INDEX = higher normalized value (for darker color)
            normalized_indices = (perc_indices - min_index) / (max_index - min_index)
        
        logger.info(f"PERC_INDEX range: min={min_index:.2f}, max={max_index:.2f}")
        logger.info(f"Normalized range: {normalized_indices.min():.3f} - {normalized_indices.max():.3f}")
        
        for i in range(num_items):
            start_angle = i * angle_step - 90
            end_angle = (i + 1) * angle_step - 90

            # Full wedge (background) - full radius
            full_wedge = Wedge((0, 0), self.outer_radius, start_angle, end_angle,
                               width=self.outer_radius,
                               facecolor=self.primary_color,
                               edgecolor='none',
                               zorder=1)
            ax.add_patch(full_wedge)

            # Heat map ring extending full length (from inner_radius to outer_radius)
            # Get color for this segment based on PERC_INDEX
            color_value = float(normalized_indices[i])
            color_rgba = self.red_colormap(color_value)
            
            # Debug: log first few to verify mapping
            if i < 3:
                category_name = wheel_data.iloc[i]['CATEGORY'] if 'CATEGORY' in wheel_data.columns else f"Segment {i}"
                perc_idx = wheel_data.iloc[i]['PERC_INDEX'] if 'PERC_INDEX' in wheel_data.columns else 0
                logger.info(f"Segment {i}: {category_name} - PERC_INDEX: {perc_idx:.2f}, Normalized: {color_value:.3f}, RGB: {color_rgba}")
            
            # Convert RGBA to hex color string
            if hasattr(color_rgba, '__iter__') and len(color_rgba) >= 3:
                r_val = int(float(color_rgba[0]) * 255)
                g_val = int(float(color_rgba[1]) * 255)
                b_val = int(float(color_rgba[2]) * 255)
                heatmap_color = f'#{r_val:02x}{g_val:02x}{b_val:02x}'
            else:
                heatmap_color = self.primary_color  # Fallback
            
            # Heat map ring extending from inner_radius all the way to outer_radius (full length)
            heatmap_ring = Wedge((0, 0), self.outer_radius, start_angle, end_angle,
                                 width=self.outer_radius - self.inner_radius,
                                 facecolor=heatmap_color,
                                 edgecolor='none',
                                 zorder=2)
            ax.add_patch(heatmap_ring)
    
    def create(self, wheel_data: pd.DataFrame,
               output_path: Optional[Path] = None,
               team_logo: Optional[Image.Image] = None) -> Path:
        """
        Create category fan wheel visualization
        
        Args:
            wheel_data: DataFrame with columns: CATEGORY, PERC_INDEX
            output_path: Where to save the visualization
            team_logo: Optional PIL Image of team logo
            
        Returns:
            Path to saved visualization
        """
        if output_path is None:
            output_path = Path(f'{self.team_short.lower()}_category_fan_wheel.png')
        
        # Validate required columns
        required_cols = ['CATEGORY']
        missing_cols = [col for col in required_cols if col not in wheel_data.columns]
        if missing_cols:
            raise ValueError(f"wheel_data missing required columns: {missing_cols}")
        
        # Sort by PERC_INDEX descending (highest first)
        if 'PERC_INDEX' in wheel_data.columns:
            wheel_data = wheel_data.sort_values('PERC_INDEX', ascending=False).reset_index(drop=True)
            logger.info("Sorted data by PERC_INDEX descending")
        
        # Rotate so Collectibles (highest) is at position 1 (12 o'clock is position 0)
        # After sorting: Collectibles=0, Live Entertainment=1, ..., Business Services=9
        # We want descending order going clockwise from Collectibles
        # So: Collectibles at pos 1, then Live Entertainment, Cannabis & Vaping, etc. clockwise
        # Since data is already in descending order, we just need to rotate by -1
        # to move Collectibles from index 0 to position 1
        num_items = len(wheel_data)
        if num_items > 0:
            # Rotate by -1 (counter-clockwise by 1) to move Collectibles from index 0 to position 1
            # This keeps descending order: Collectibles (pos 1) → Live Entertainment (pos 2) → ...
            wheel_data = wheel_data.reindex(np.roll(wheel_data.index, -1)).reset_index(drop=True)
            logger.info("Rotated by 1 position: Collectibles at position 1, descending clockwise")
        
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
        
        num_items = len(wheel_data)
        if num_items == 0:
            raise ValueError("No data provided for fan wheel")
        
        angle_step = 360 / num_items
        
        # Draw wedges with heat map inner ring
        self._draw_wedges_with_heatmap(ax, wheel_data, num_items, angle_step)
        
        # Add dividing lines
        self._add_dividing_lines(ax, num_items, angle_step)
        
        # Add arrows
        self._add_arrows(ax, num_items, angle_step)
        
        # Draw center circle
        self._draw_center_circle(ax, team_logo)
        
        # Add category text to each segment
        self._add_segment_content(ax, wheel_data, angle_step)
        
        # Save
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight',
                    facecolor='white', edgecolor='none',
                    pad_inches=0.05)
        plt.close()
        
        logger.info(f"Category fan wheel saved to {output_path}")
        return output_path

