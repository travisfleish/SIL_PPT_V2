# visualizations/base_chart.py
"""
Base class for all chart/visualization components
"""

import matplotlib.pyplot as plt
from pathlib import Path
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class BaseChart:
    """Base class for all visualizations"""

    def __init__(self):
        """Initialize base chart settings"""
        # Set default matplotlib parameters for consistent styling
        plt.style.use('default')
        plt.rcParams['figure.facecolor'] = 'white'
        plt.rcParams['axes.facecolor'] = 'white'
        plt.rcParams['axes.edgecolor'] = 'black'
        plt.rcParams['grid.alpha'] = 0.3
        plt.rcParams['font.size'] = 10
        plt.rcParams['font.family'] = 'sans-serif'

        # Default figure settings
        self.fig_dpi = 300
        self.default_figsize = (10, 6)

    def save_figure(self, fig: plt.Figure, output_path: Path,
                    dpi: Optional[int] = None, bbox_inches: str = 'tight') -> Path:
        """
        Save figure with consistent settings

        Args:
            fig: Matplotlib figure to save
            output_path: Where to save the figure
            dpi: DPI for output (uses self.fig_dpi if not specified)
            bbox_inches: How to handle the bounding box

        Returns:
            Path to saved figure
        """
        if dpi is None:
            dpi = self.fig_dpi

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        fig.savefig(output_path, dpi=dpi, bbox_inches=bbox_inches,
                    facecolor='white', edgecolor='none')

        logger.info(f"Chart saved to {output_path}")
        return output_path

    def create_figure(self, figsize: Optional[tuple] = None, **kwargs) -> tuple:
        """
        Create a new figure with consistent settings

        Args:
            figsize: Figure size (width, height) in inches
            **kwargs: Additional arguments for plt.figure()

        Returns:
            fig, ax tuple
        """
        if figsize is None:
            figsize = self.default_figsize

        fig, ax = plt.subplots(figsize=figsize, **kwargs)
        fig.patch.set_facecolor('white')

        return fig, ax

    def apply_team_colors(self, team_config: Dict[str, Any]) -> Dict[str, str]:
        """
        Extract and return team colors from config

        Args:
            team_config: Team configuration dictionary

        Returns:
            Dictionary of color values
        """
        colors = team_config.get('colors', {})
        return {
            'primary': colors.get('primary', '#002244'),
            'secondary': colors.get('secondary', '#FFB612'),
            'accent': colors.get('accent', '#8B8B8B')
        }

    def format_currency(self, value: float) -> str:
        """Format currency values consistently"""
        if value >= 1_000_000:
            return f"${value / 1_000_000:.1f}M"
        elif value >= 1_000:
            return f"${value / 1_000:.0f}K"
        else:
            return f"${value:.0f}"

    def format_percentage(self, value: float, decimal_places: int = 0) -> str:
        """Format percentage values consistently"""
        return f"{value:.{decimal_places}f}%"

    def cleanup(self):
        """Clean up matplotlib resources"""
        plt.close('all')