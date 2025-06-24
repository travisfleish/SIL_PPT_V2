# utils/__init__.py
"""
Utility functions and classes for the PowerPoint generator
"""

# Only import what's actually implemented
from .team_config_manager import TeamConfigManager

# Placeholder imports (commented out until implemented)
# from .logo_downloader import LogoDownloader
# from .ai_generators import InsightGenerator, TextEnhancer
# from .formatting import (
#     format_currency,
#     format_percentage,
#     format_number,
#     truncate_text,
#     format_merchant_name,
#     wrap_text_for_slide
# )

__all__ = [
    'TeamConfigManager',
]