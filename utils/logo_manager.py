# utils/logo_manager.py
"""
Enhanced Logo Manager for Fan Wheel Integration
Handles local logo files with fallback strategies
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Tuple
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import re

logger = logging.getLogger(__name__)


class LogoManager:
    """Manage local logo files with intelligent fallbacks"""

    def __init__(self, logo_dir: Optional[Path] = None):
        """
        Initialize logo manager

        Args:
            logo_dir: Path to logo directory (defaults to assets/logos/merchants)
        """
        # Set default logo directory
        if logo_dir is None:
            logo_dir = Path(__file__).parent.parent / 'assets' / 'logos' / 'merchants'

        self.logo_dir = Path(logo_dir)
        self.logo_dir.mkdir(parents=True, exist_ok=True)

        # Cache for loaded logos
        self._logo_cache: Dict[str, Optional[Image.Image]] = {}

        # Supported image formats
        self.supported_formats = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff'}

        logger.info(f"LogoManager initialized with directory: {self.logo_dir}")

    def get_logo(self, merchant_name: str, size: Tuple[int, int] = (120, 120)) -> Optional[Image.Image]:
        """
        Get logo for merchant with intelligent fallback

        Args:
            merchant_name: Name of the merchant
            size: Desired logo size (width, height)

        Returns:
            PIL Image or None if not found
        """
        # Check cache first
        cache_key = f"{merchant_name}_{size[0]}x{size[1]}"
        if cache_key in self._logo_cache:
            return self._logo_cache[cache_key]

        # Try to find logo file
        logo_path = self._find_logo_file(merchant_name)

        if logo_path:
            try:
                # Load and resize logo
                logo = Image.open(logo_path)
                logo = self._prepare_logo(logo, size)

                # Cache the result
                self._logo_cache[cache_key] = logo
                logger.debug(f"Loaded logo for {merchant_name} from {logo_path}")
                return logo

            except Exception as e:
                logger.warning(f"Failed to load logo for {merchant_name}: {e}")

        # Logo not found - cache None to avoid repeated lookups
        self._logo_cache[cache_key] = None
        logger.debug(f"No logo found for {merchant_name}")
        return None

    def _find_logo_file(self, merchant_name: str) -> Optional[Path]:
        """
        Find logo file using various naming strategies

        Args:
            merchant_name: Name of the merchant

        Returns:
            Path to logo file or None
        """
        # Generate possible filename variations
        search_names = self._generate_search_names(merchant_name)

        # Search for files with any supported extension
        for search_name in search_names:
            for ext in self.supported_formats:
                logo_path = self.logo_dir / f"{search_name}{ext}"
                if logo_path.exists():
                    return logo_path

        return None

    def _generate_search_names(self, merchant_name: str) -> list[str]:
        """
        Generate possible filename variations for merchant

        Args:
            merchant_name: Original merchant name

        Returns:
            List of possible filenames (without extension)
        """
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
            'wayfair': ['wayfair']
        }

        merchant_lower = merchant_name.lower()
        for key, aliases in name_mapping.items():
            if key in merchant_lower:
                variations.extend(aliases)

        # Remove duplicates while preserving order
        return list(dict.fromkeys(variations))

    def _prepare_logo(self, logo: Image.Image, size: Tuple[int, int]) -> Image.Image:
        """
        Prepare logo for use in fan wheel (resize, ensure RGBA)

        Args:
            logo: Original logo image
            size: Target size

        Returns:
            Prepared logo image
        """
        # Convert to RGBA if not already
        if logo.mode != 'RGBA':
            logo = logo.convert('RGBA')

        # Resize maintaining aspect ratio
        logo.thumbnail(size, Image.Resampling.LANCZOS)

        # Create new image with exact size and transparent background
        final_logo = Image.new('RGBA', size, (255, 255, 255, 0))

        # Center the logo
        x = (size[0] - logo.width) // 2
        y = (size[1] - logo.height) // 2
        final_logo.paste(logo, (x, y), logo if logo.mode == 'RGBA' else None)

        return final_logo

    def create_fallback_logo(self, merchant_name: str, size: Tuple[int, int] = (120, 120),
                             bg_color: str = 'white', text_color: str = '#888888') -> Image.Image:
        """
        Create a fallback logo with merchant initials

        Args:
            merchant_name: Merchant name
            size: Logo size
            bg_color: Background color
            text_color: Text color

        Returns:
            Generated fallback logo
        """
        # Create background
        logo = Image.new('RGBA', size, bg_color)
        draw = ImageDraw.Draw(logo)

        # Add border
        border_width = 2
        draw.ellipse([border_width, border_width,
                      size[0] - border_width, size[1] - border_width],
                     outline='#E0E0E0', width=border_width)

        # Generate initials
        initials = ''.join([word[0].upper() for word in merchant_name.split()[:2]])

        # Calculate font size to fit
        font_size = min(size) // 3
        try:
            # Try to use a nice font
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            # Fall back to default font
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
        """
        List all available logo files

        Returns:
            List of merchant names (based on filenames)
        """
        logos = []
        for ext in self.supported_formats:
            for logo_file in self.logo_dir.glob(f"*{ext}"):
                logos.append(logo_file.stem)

        return sorted(set(logos))

    def add_missing_logos_report(self, merchant_names: list[str]) -> Dict[str, bool]:
        """
        Generate report of which merchants have/don't have logos

        Args:
            merchant_names: List of merchant names to check

        Returns:
            Dict mapping merchant name to whether logo exists
        """
        report = {}
        for merchant in merchant_names:
            logo_path = self._find_logo_file(merchant)
            report[merchant] = logo_path is not None

        return report