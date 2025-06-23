# slide_generators/demographics_slide.py
"""
Generate complete demographics slide for PowerPoint presentations
Includes all elements: charts, text, images, and formatting
"""

from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Circle, FancyBboxPatch
from PIL import Image
import numpy as np
from typing import Dict, Optional, Any
from .base_slide import BaseSlide


class DemographicsSlide(BaseSlide):
    """Generate the complete demographics slide with all elements"""

    def __init__(self,
                 demographic_data: Dict[str, Any],
                 chart_dir: Path,
                 team_config: Dict[str, Any],
                 team_logo_path: Optional[Path] = None):
        """
        Initialize demographics slide generator

        Args:
            demographic_data: Processed demographic data from DemographicsProcessor
            chart_dir: Directory containing individual chart images
            team_config: Team configuration including colors and names
            team_logo_path: Optional path to team logo/photo
        """
        super().__init__()
        self.demographic_data = demographic_data
        self.chart_dir = Path(chart_dir)
        self.team_config = team_config
        self.team_logo_path = team_logo_path

        # Extract team info
        self.team_name = team_config.get('team_name', 'Team')
        self.team_short = team_config.get('team_name_short', self.team_name.split()[-1])
        self.colors = team_config.get('colors', {
            'primary': '#002244',
            'secondary': '#FFB612',
            'accent': '#8B8B8B'
        })

    def generate(self, output_path: Optional[Path] = None) -> Path:
        """
        Generate the complete demographics slide

        Args:
            output_path: Where to save the slide image

        Returns:
            Path to the generated slide image
        """
        if output_path is None:
            output_path = self.chart_dir / f'{self.team_name.lower().replace(" ", "_")}_demographics_slide.png'

        # Create figure with PowerPoint slide dimensions
        fig = plt.figure(figsize=(13.33, 7.5), dpi=300)
        fig.patch.set_facecolor('white')

        # Create main layout grid
        gs = fig.add_gridspec(10, 12, left=0.02, right=0.98, top=0.94, bottom=0.02,
                              wspace=0.02, hspace=0.02)

        # 1. Add team logo/photo (left side)
        self._add_team_logo(fig, gs[1:5, 0:3])

        # 2. Add insight text below logo
        self._add_insight_text(fig, gs[5:9, 0:3])

        # 3. Add title
        self._add_title(fig)

        # 4. Add demographic charts
        self._add_charts(fig, gs)

        # 5. Add KEY/legend box
        self._add_legend_box(fig, gs[8:10, 3:8])

        # 6. Add Ethnicity section
        self._add_ethnicity_section(fig, gs[8:10, 8:12])

        # Save the slide
        plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close(fig)

        # Also save high-res version
        hires_path = output_path.with_name(output_path.stem + '_hires.png')
        fig = self._regenerate_figure()  # Regenerate for high-res
        plt.savefig(hires_path, dpi=600, bbox_inches='tight', facecolor='white')
        plt.close(fig)

        print(f"Generated demographics slide: {output_path}")
        return output_path

    def _add_team_logo(self, fig, gridspec):
        """Add team logo or photo in circular frame"""
        ax = fig.add_subplot(gridspec)
        ax.axis('off')

        if self.team_logo_path and self.team_logo_path.exists():
            # Load and display team image
            img = Image.open(self.team_logo_path)

            # Create circular mask
            height, width = img.size
            lum_img = Image.new('L', (width, height), 0)
            draw = ImageDraw.Draw(lum_img)
            draw.pieslice([(0, 0), (width, height)], 0, 360, fill=255)

            # Apply mask
            img_array = np.array(img)
            mask = np.array(lum_img)

            ax.imshow(img_array)

            # Add circular border
            circle = Circle((0.5, 0.5), 0.48, transform=ax.transAxes,
                            fill=False, edgecolor=self.colors['secondary'],
                            linewidth=5)
            ax.add_patch(circle)
        else:
            # Placeholder circle if no logo
            circle = Circle((0.5, 0.5), 0.4, transform=ax.transAxes,
                            facecolor=self.colors['primary'],
                            edgecolor=self.colors['secondary'], linewidth=5)
            ax.add_patch(circle)
            ax.text(0.5, 0.5, self.team_short, transform=ax.transAxes,
                    ha='center', va='center', fontsize=24, color='white',
                    fontweight='bold')

    def _add_insight_text(self, fig, gridspec):
        """Add the key insight text"""
        ax = fig.add_subplot(gridspec)
        ax.axis('off')

        # Get insight from demographic data or use default
        insight = self.demographic_data.get('key_insights',
                                            f"{self.team_short} fans are younger, and more likely to be parents "
                                            f"who are working professionals versus the {self.team_short} gen pop.")

        # Add text with proper formatting
        ax.text(0.05, 0.5, insight, transform=ax.transAxes,
                ha='left', va='center', fontsize=14,
                fontweight='bold', wrap=True,
                color=self.colors['primary'])

    def _add_title(self, fig):
        """Add slide title"""
        title = f"Fan Demographics: How Are {self.team_name} Fans Unique"
        fig.text(0.5, 0.97, title, ha='center', va='top',
                 fontsize=20, fontweight='bold')

    def _add_charts(self, fig, gs):
        """Add all demographic charts"""
        # Chart positions in the grid
        chart_positions = {
            'generation': gs[1:5, 3:6],  # Top left
            'income': gs[1:5, 6:10],  # Top middle
            'gender': gs[1:5, 10:12],  # Top right
            'occupation': gs[5:8, 3:8],  # Bottom left
            'children': gs[5:8, 8:11]  # Bottom right
        }

        for chart_type, gridspec in chart_positions.items():
            ax = fig.add_subplot(gridspec)
            ax.axis('off')

            # Try to load hires version first
            chart_path = self.chart_dir / f'{chart_type}_chart_hires.png'
            if not chart_path.exists():
                chart_path = self.chart_dir / f'{chart_type}_chart.png'

            if chart_path.exists():
                img = Image.open(chart_path)
                ax.imshow(img)

    def _add_legend_box(self, fig, gridspec):
        """Add the KEY legend box"""
        ax = fig.add_subplot(gridspec)
        ax.axis('off')

        # Create box
        box = FancyBboxPatch((0.05, 0.1), 0.9, 0.8,
                             boxstyle="round,pad=0.05",
                             facecolor='white',
                             edgecolor='black',
                             linewidth=2,
                             transform=ax.transAxes)
        ax.add_patch(box)

        # Add KEY text
        ax.text(0.1, 0.7, "KEY", transform=ax.transAxes,
                fontweight='bold', fontsize=12)

        # Add legend items
        legend_items = [
            (f"-{self.team_name} Fans", self.colors['primary']),
            (f"- {self.team_short} Gen Pop (state level, excluding {self.team_short} Fans)",
             self.colors['secondary']),
            (f"- {self.team_config['league']} Fans Total (excluding {self.team_short} fans)",
             self.colors['accent'])
        ]

        y_pos = 0.5
        for text, color in legend_items:
            ax.text(0.1, y_pos, text, transform=ax.transAxes,
                    fontsize=10, color=color)
            y_pos -= 0.15

    def _add_ethnicity_section(self, fig, gridspec):
        """Add ethnicity section (placeholder for now)"""
        ax = fig.add_subplot(gridspec)
        ax.axis('off')

        # Create box
        box = FancyBboxPatch((0.05, 0.1), 0.9, 0.8,
                             boxstyle="round,pad=0.05",
                             facecolor='#f0f0f0',
                             edgecolor='black',
                             linewidth=2,
                             transform=ax.transAxes)
        ax.add_patch(box)

        # Add title
        ax.text(0.5, 0.5, "Ethnicity", transform=ax.transAxes,
                ha='center', va='center', fontsize=16)

    def _regenerate_figure(self):
        """Regenerate the figure for high-res saving"""
        # This is a simplified version - in practice, you'd refactor
        # the generation code to be reusable
        return self.generate(output_path=None)


def create_demographics_slide(demographic_data: Dict[str, Any],
                              chart_dir: Path,
                              team_key: str = 'utah_jazz',
                              output_dir: Optional[Path] = None) -> Path:
    """
    Convenience function to create a demographics slide

    Args:
        demographic_data: Output from DemographicsProcessor
        chart_dir: Directory containing individual chart images
        team_key: Team identifier for configuration
        output_dir: Optional output directory

    Returns:
        Path to generated slide
    """
    from utils.team_config_manager import TeamConfigManager

    # Get team configuration
    config_manager = TeamConfigManager()
    team_config = config_manager.get_team_config(team_key)

    # Create slide generator
    slide = DemographicsSlide(
        demographic_data=demographic_data,
        chart_dir=chart_dir,
        team_config=team_config
    )

    # Generate slide
    if output_dir:
        output_path = output_dir / f'{team_key}_demographics_slide.png'
    else:
        output_path = None

    return slide.generate(output_path)


if __name__ == "__main__":
    # Test with mock data
    from pathlib import Path

    mock_data = {
        'team_name': 'Utah Jazz',
        'key_insights': 'Jazz fans are younger, and more likely to be parents who are working professionals versus the Utah gen pop.'
    }

    chart_dir = Path('mock_demographic_charts')

    if chart_dir.exists():
        print("Creating complete demographics slide...")

        # Need to import or mock team config
        team_config = {
            'team_name': 'Utah Jazz',
            'team_name_short': 'Jazz',
            'league': 'NBA',
            'colors': {
                'primary': '#002B5C',
                'secondary': '#F9A01B',
                'accent': '#00471B'
            }
        }

        slide = DemographicsSlide(
            demographic_data=mock_data,
            chart_dir=chart_dir,
            team_config=team_config
        )

        output_path = slide.generate()
        print(f"Slide saved to: {output_path}")
    else:
        print("Chart directory not found. Run test_demographic_charts.py first.")