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
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import logging
from typing import Dict, Optional, List, Tuple
import pandas as pd
import re

from .base_chart import BaseChart

logger = logging.getLogger(__name__)


class LogoManager:
    """Manage local logo files with intelligent fallbacks"""

    def __init__(self, logo_dir: Optional[Path] = None):
        """Initialize logo manager"""
        if logo_dir is None:
            # Find project root (look for PPT_Generator_SIL directory)
            current_path = Path(__file__).resolve()
            project_root = None

            # Walk up the directory tree to find the project root
            for parent in current_path.parents:
                if parent.name == 'PPT_Generator_SIL':
                    project_root = parent
                    break

            if project_root is None:
                # Fallback: assume we're somewhere in the project
                project_root = current_path.parent
                while project_root.parent != project_root and not (project_root / 'assets').exists():
                    project_root = project_root.parent

            logo_dir = project_root / 'assets' / 'logos' / 'merchants'

        self.logo_dir = Path(logo_dir)
        self.logo_dir.mkdir(parents=True, exist_ok=True)

        # Cache for loaded logos
        self._logo_cache: Dict[str, Optional[Image.Image]] = {}

        # Supported image formats
        self.supported_formats = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff'}

        logger.debug(f"LogoManager initialized with directory: {self.logo_dir}")

    def get_logo(self, merchant_name: str, size: Tuple[int, int] = (120, 120)) -> Optional[Image.Image]:
        """Get logo for merchant with intelligent fallback"""
        cache_key = f"{merchant_name}_{size[0]}x{size[1]}"
        if cache_key in self._logo_cache:
            return self._logo_cache[cache_key]

        # Try to find logo file
        logo_path = self._find_logo_file(merchant_name)

        if logo_path:
            try:
                logo = Image.open(logo_path)
                logo = self._prepare_logo(logo, size)
                self._logo_cache[cache_key] = logo
                logger.debug(f"Loaded logo for {merchant_name} from {logo_path}")
                return logo
            except Exception as e:
                logger.warning(f"Failed to load logo for {merchant_name}: {e}")

        self._logo_cache[cache_key] = None
        return None

    def _find_logo_file(self, merchant_name: str) -> Optional[Path]:
        """Find logo file using various naming strategies"""
        search_names = self._generate_search_names(merchant_name)

        for search_name in search_names:
            for ext in self.supported_formats:
                logo_path = self.logo_dir / f"{search_name}{ext}"
                if logo_path.exists():
                    return logo_path
        return None

    def _generate_search_names(self, merchant_name: str) -> list[str]:
        """Generate possible filename variations for merchant"""
        variations = []

        # Original name
        variations.append(merchant_name)

        # Lowercase
        variations.append(merchant_name.lower())

        # Replace spaces with underscores
        variations.append(merchant_name.lower().replace(' ', '_'))

        # Replace spaces with hyphens
        variations.append(merchant_name.lower().replace(' ', '-'))

        # Remove special characters and spaces
        clean_name = re.sub(r'[^a-zA-Z0-9]', '', merchant_name.lower())
        variations.append(clean_name)

        # Common abbreviations/variations
        name_mapping = {
            'mcdonalds': ['mcdonalds', 'mcd', 'mcdonald'],
            'taco bell': ['tacobell', 'taco_bell'],
            'kwik trip': ['kwiktrip', 'kwik_trip'],
            'auto zone': ['autozone', 'auto_zone'],
            'krispy kreme': ['krispykreme', 'krispy_kreme', 'kk'],
            'jewel osco': ['jewelosco', 'jewel_osco', 'jewel'],
            'binny\'s': ['binnys', 'binny', 'binnys_beverage'],
            'ulta': ['ulta', 'ulta_beauty'],
            'grubhub': ['grubhub', 'grub_hub'],
            'wayfair': ['wayfair'],
            'lululemon': ['lululemon', 'lulu']
        }

        merchant_lower = merchant_name.lower()
        for key, aliases in name_mapping.items():
            if key in merchant_lower:
                variations.extend(aliases)

        return list(dict.fromkeys(variations))  # Remove duplicates

    def _prepare_logo(self, logo: Image.Image, size: Tuple[int, int]) -> Image.Image:
        """Prepare logo for use in fan wheel (resize, ensure RGBA)"""
        if logo.mode != 'RGBA':
            logo = logo.convert('RGBA')

        logo.thumbnail(size, Image.Resampling.LANCZOS)

        final_logo = Image.new('RGBA', size, (255, 255, 255, 0))

        x = (size[0] - logo.width) // 2
        y = (size[1] - logo.height) // 2
        final_logo.paste(logo, (x, y), logo if logo.mode == 'RGBA' else None)

        return final_logo

    def create_fallback_logo(self, merchant_name: str, size: Tuple[int, int] = (120, 120),
                             bg_color: str = 'white', text_color: str = '#888888') -> Image.Image:
        """Create a fallback logo with merchant initials"""
        logo = Image.new('RGBA', size, bg_color)
        draw = ImageDraw.Draw(logo)

        # Add border
        border_width = 2
        draw.ellipse([border_width, border_width,
                      size[0] - border_width, size[1] - border_width],
                     outline='#E0E0E0', width=border_width)

        # Generate initials
        initials = ''.join([word[0].upper() for word in merchant_name.split()[:2]])

        # Calculate font size
        font_size = min(size) // 3
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            font = ImageFont.load_default()

        # Center text
        bbox = draw.textbbox((0, 0), initials, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        x = (size[0] - text_width) // 2
        y = (size[1] - text_height) // 2

        draw.text((x, y), initials, fill=text_color, font=font)

        return logo

    def list_available_logos(self) -> list[str]:
        """List all available logo files"""
        logos = []
        for ext in self.supported_formats:
            for logo_file in self.logo_dir.glob(f"*{ext}"):
                logos.append(logo_file.stem)
        return sorted(set(logos))


class FanWheel(BaseChart):
    """Generate fan wheel visualization showing top communities and their merchants"""

    def __init__(self, team_config: Dict[str, any], enable_logos: bool = True, logo_dir: Optional[Path] = None):
        """
        Initialize fan wheel generator

        Args:
            team_config: Team configuration with colors and names
            enable_logos: Whether to enable logo loading (default: True)
            logo_dir: Optional custom logo directory path
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
        self.enable_logos = enable_logos
        self.logo_size = (110, 110)  # Size for logos in pixels

        # Initialize logo manager if enabled
        self.logo_manager = LogoManager(logo_dir) if enable_logos else None

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

        # Create figure with higher DPI if logos are enabled
        dpi = 150 if self.enable_logos else 100
        fig = plt.figure(figsize=(12, 12), facecolor='white', dpi=dpi)
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
        # Draw the black background circle
        center_circle = Circle((0, 0), self.inner_radius,
                               facecolor='black',
                               edgecolor=self.secondary_color,
                               linewidth=5,
                               zorder=20)
        ax.add_patch(center_circle)

        # If no team logo provided, try to load molly.png
        if team_logo is None:
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
                logo_size_pixels = int(self.inner_radius * 1.4 * 100)  # Much smaller than before

                # Create a copy to avoid modifying the original
                logo_copy = team_logo.copy()
                logo_copy.thumbnail((logo_size_pixels, logo_size_pixels), Image.Resampling.LANCZOS)

                logger.info(f"Logo resized to: {logo_copy.size}")

                # Convert to numpy array for matplotlib
                logo_array = np.array(logo_copy)

                # Create OffsetImage with appropriate zoom
                # Zoom factor to ensure it fits within the circle
                zoom_factor = 0.5  # Reduced from 1.2 to make it smaller
                imagebox = OffsetImage(logo_array, zoom=zoom_factor)

                # Position logo in upper portion of circle to leave room for text
                logo_y_offset = 0.4  # Position in upper part of circle
                ab = AnnotationBbox(imagebox, (0, logo_y_offset),
                                    frameon=False,
                                    pad=0,
                                    zorder=22)
                ax.add_artist(ab)

                # Add team text in lower portion of circle
                fan_text = f"THE {self.team_short.upper()}\nFAN"

                # Position text in lower part of circle
                text_y_position = -.8  # Lower in the circle
                ax.text(0, text_y_position, fan_text,
                        ha='center', va='center',
                        fontsize=24,  # Smaller font to fit better
                        fontweight='bold',
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
        fan_text = f"THE {self.team_short.upper()} FAN"
        ax.text(0, 0, fan_text,
                ha='center', va='center',
                fontsize=16, fontweight='bold',
                color='white', zorder=22)

    def _add_segment_content(self, ax, wheel_data: pd.DataFrame, angle_step: float):
        """Add logos and behavior text to each segment"""
        missing_logos = []

        for i, (_, row) in enumerate(wheel_data.iterrows()):
            center_angle = i * angle_step + angle_step / 2 - 90
            angle_rad = np.deg2rad(center_angle)

            # Logo position
            logo_x = self.logo_radius * np.cos(angle_rad)
            logo_y = self.logo_radius * np.sin(angle_rad)

            # Add logo (enhanced with logo loading)
            merchant_name = row['MERCHANT']
            logo_added = self._add_merchant_logo(ax, merchant_name, logo_x, logo_y)

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
        if missing_logos and self.enable_logos:
            logger.debug(f"Missing logos for: {', '.join(missing_logos)}")

    def _add_merchant_logo(self, ax, merchant: str, x: float, y: float) -> bool:
        """
        Add merchant logo with enhanced loading capabilities

        Args:
            ax: Matplotlib axis
            merchant: Merchant name
            x, y: Position coordinates

        Returns:
            True if logo was added (real or fallback), False if using old placeholder
        """
        # Try to load actual logo if logo manager is available
        if self.logo_manager:
            logo_img = self.logo_manager.get_logo(merchant, self.logo_size)

            if logo_img is not None:
                # Add actual logo
                self._add_logo_to_plot(ax, logo_img, x, y)
                return True
            else:
                # Create and add enhanced fallback logo
                fallback_logo = self.logo_manager.create_fallback_logo(
                    merchant, self.logo_size, 'white', '#888888'
                )
                self._add_logo_to_plot(ax, fallback_logo, x, y)
                return True

        # Fallback to original placeholder method
        self._add_placeholder_logo(ax, merchant, x, y)
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

    def _add_placeholder_logo(self, ax, merchant: str, x: float, y: float):
        """Add merchant logo placeholder - simple white circle (original method)"""
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

    def generate_logo_report(self, wheel_data: pd.DataFrame) -> Dict[str, any]:
        """
        Generate report on logo availability for merchants in wheel data

        Args:
            wheel_data: DataFrame with MERCHANT column

        Returns:
            Dictionary with logo availability statistics
        """
        if not self.logo_manager:
            return {
                'total_merchants': 0,
                'with_logos': 0,
                'missing_logos': 0,
                'coverage_percentage': 0,
                'message': 'Logo functionality disabled'
            }

        merchants = wheel_data['MERCHANT'].unique().tolist()
        logo_report = {}

        for merchant in merchants:
            logo = self.logo_manager.get_logo(merchant)
            logo_report[merchant] = logo is not None

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


def create_fan_wheel_from_data(merchant_ranker, team_config: Dict[str, any],
                               output_path: Optional[Path] = None,
                               enable_logos: bool = True) -> Path:
    """
    Convenience function to create fan wheel using MerchantRanker

    Args:
        merchant_ranker: Instance of MerchantRanker with data
        team_config: Team configuration dictionary
        output_path: Optional output path
        enable_logos: Whether to enable logo loading (default: True)

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

    # Create fan wheel with logo support
    fan_wheel = FanWheel(team_config, enable_logos=enable_logos)

    # No team logo for now
    return fan_wheel.create(wheel_data, output_path, team_logo=None)