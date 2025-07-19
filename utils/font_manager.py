# backend/utils/font_manager.py
import os
import logging
from pathlib import Path
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt

logger = logging.getLogger(__name__)


class FontManager:
    """Manages custom font loading and fallback strategies"""

    def __init__(self):
        self.fonts_loaded = False
        self.font_paths = {}
        self.default_font_family = 'DejaVu Sans'  # Matplotlib default
        self._loading = False  # Prevent concurrent loading

    def load_custom_fonts(self, fonts_dir: str = None):
        """Load custom fonts from directory"""
        if self.fonts_loaded or self._loading:
            return

        self._loading = True

        if fonts_dir is None:
            # Try multiple possible locations
            possible_locations = [
                # Your mentioned location - interpreting "root-backend-assets-fonts"
                Path.cwd() / 'backend' / 'assets' / 'fonts',
                # Alternative interpretation if it's at root level
                Path.cwd() / 'assets' / 'fonts',
                # Original relative path
                Path(__file__).parent.parent / 'assets' / 'fonts',
                # If running from backend directory
                Path.cwd() / 'assets' / 'fonts' if 'backend' in str(Path.cwd()) else None,
                # Absolute path to project root
                Path('/Users/travisfleisher/PycharmProjects/PPT_Generator_SIL/backend/assets/fonts'),
            ]

            # Filter out None values and check which path exists
            fonts_dir = None
            for loc in filter(None, possible_locations):
                logger.debug(f"Checking font location: {loc}")
                if loc.exists():
                    fonts_dir = loc
                    logger.info(f"Found fonts directory at: {fonts_dir}")
                    break

            if fonts_dir is None:
                logger.error("Could not find fonts directory. Tried locations:")
                for loc in filter(None, possible_locations):
                    logger.error(f"  - {loc}")
                logger.info(f"Current working directory: {Path.cwd()}")
                logger.info(f"Script location: {Path(__file__).parent}")
                return
        else:
            fonts_dir = Path(fonts_dir)

        if not fonts_dir.exists():
            logger.warning(f"Fonts directory not found: {fonts_dir}")
            return

        try:
            # Find all TTF/OTF files
            font_files = list(fonts_dir.glob('*.ttf')) + list(fonts_dir.glob('*.otf'))

            if not font_files:
                logger.warning(f"No font files found in {fonts_dir}")
                return

            for font_file in font_files:
                try:
                    # Add font to matplotlib's font manager
                    fm.fontManager.addfont(str(font_file))
                    logger.info(f"Loaded font: {font_file.name}")

                    # Extract font properties for reference
                    prop = fm.FontProperties(fname=str(font_file))
                    family_name = prop.get_family()[0]
                    self.font_paths[family_name] = str(font_file)

                except Exception as e:
                    logger.error(f"Failed to load font {font_file}: {e}")

            # Rebuild font cache - handle different matplotlib versions
            try:
                # Try the private method first (older versions)
                if hasattr(fm, '_rebuild'):
                    fm._rebuild()
                # Try the public method (newer versions)
                elif hasattr(fm.fontManager, 'ttflist'):
                    # In newer versions, the font list is automatically updated
                    # when using addfont(), so we just need to clear any cache
                    fm.fontManager.ttflist = fm.fontManager.ttflist
                    if hasattr(fm, 'get_font'):
                        # Clear the font cache if it exists
                        fm.get_font.cache_clear()
            except Exception as e:
                # Log but don't fail - fonts are still loaded
                logger.debug(f"Font cache rebuild not needed or failed: {e}")

            self.fonts_loaded = True
            logger.info(f"Successfully loaded {len(font_files)} custom fonts")

        except Exception as e:
            logger.error(f"Error loading custom fonts: {e}")
        finally:
            self._loading = False

    def get_font_family(self, preferred_family: str = 'Red Hat Display'):
        """Get font family with fallback"""
        # Ensure fonts are loaded
        if not self.fonts_loaded:
            self.load_custom_fonts()

        # Check if preferred font is available
        available_fonts = [f.name for f in fm.fontManager.ttflist]

        if preferred_family in available_fonts:
            return preferred_family

        # Try variations
        variations = [
            preferred_family.replace(' ', ''),  # RedHatDisplay
            preferred_family.replace(' ', '-'),  # Red-Hat-Display
            preferred_family.lower(),
            preferred_family.upper()
        ]

        for variation in variations:
            matching_fonts = [font for font in available_fonts if variation.lower() in font.lower()]
            if matching_fonts:
                logger.info(f"Using font variation: {matching_fonts[0]}")
                return matching_fonts[0]

        logger.warning(f"Font '{preferred_family}' not found, using fallback: {self.default_font_family}")
        logger.warning(f"Available fonts sample: {available_fonts[:10]}...")  # Show first 10 for debugging
        return self.default_font_family

    def configure_matplotlib(self):
        """Configure matplotlib with custom fonts"""
        self.load_custom_fonts()

        # Set default font
        font_family = self.get_font_family()

        plt.rcParams.update({
            'font.family': font_family,
            'font.sans-serif': [font_family, self.default_font_family],
            'axes.unicode_minus': False  # Fix minus sign rendering
        })

        logger.info(f"Matplotlib configured with font family: {font_family}")

    def set_fonts_directory(self, fonts_dir: str):
        """Manually set the fonts directory path"""
        self.fonts_loaded = False  # Reset to allow reloading
        self.load_custom_fonts(fonts_dir)


# Global font manager instance
font_manager = FontManager()