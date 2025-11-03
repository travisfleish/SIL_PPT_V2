# visualizations/community_index_chart.py
"""
Community Index Chart Visualization
Creates horizontal bar chart showing audience index for top communities
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Rectangle
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Optional, List, Tuple
import matplotlib.font_manager as fm
import os

from utils.font_manager import font_manager  # Added font manager import
from typing import Union


class CommunityIndexChart:
    """Generate community index bar chart visualization"""

    def __init__(self, team_colors: Optional[Dict[str, str]] = None):
        """
        Initialize chart generator

        Args:
            team_colors: Dictionary with 'primary', 'secondary' color values
        """
        if team_colors:
            self.bar_color = team_colors.get('primary', '#4472C4')
            self.highlight_color = team_colors.get('secondary', '#FFC000')
        else:
            self.bar_color = '#4472C4'  # Default blue
            self.highlight_color = '#FFC000'  # Default yellow

        self.background_color = '#C5C5C5'  # Gray for background bars

        # Use font manager to get the appropriate font family
        self.font_family = font_manager.get_font_family('Red Hat Display')

    def create(self, data: pd.DataFrame,
               output_path: Optional[Path] = None,
               title: Optional[str] = None) -> Path:
        """
        Create community index chart

        Args:
            data: DataFrame with columns 'Community', 'Audience_Pct', and 'Composite_Index'
            output_path: Where to save the chart
            title: Optional title for the chart

        Returns:
            Path to saved chart
        """
        if output_path is None:
            output_path = Path('community_index_chart.png')

        # Sort data by Audience_Pct descending
        data = data.sort_values('Audience_Pct', ascending=True)  # Ascending for bottom-to-top display

        # Create figure with dual x-axes
        fig, ax = plt.subplots(figsize=(10, 6))
        fig.patch.set_facecolor('white')
        ax.set_facecolor('white')

        # Create top axis for percentage
        ax2 = ax.twiny()

        # Set up the plot
        y_positions = np.arange(len(data))
        max_value = 700  # Fixed scale for bottom axis

        # Draw gray bars representing the % Team Fans (PERC_AUDIENCE)
        # Check if values are in decimal format (0-1) or percentage format (0-100)
        if data['Audience_Pct'].max() <= 1.0:
            # Convert from decimal to percentage
            audience_pct_display = data['Audience_Pct'] * 100
        else:
            audience_pct_display = data['Audience_Pct']

        # Scale to match the x-axis (since PERC_AUDIENCE is 0-100 and x-axis is 0-700)
        gray_bars_scaled = audience_pct_display * (max_value / 100)
        gray_bars = ax.barh(y_positions,
                            gray_bars_scaled,
                            color=self.background_color,
                            height=0.6,
                            alpha=0.8,
                            label='% Team Fans')

        # Draw blue bars representing the Team Fan Index - as thin lines
        blue_bars = ax.barh(y_positions,
                            data['Composite_Index'],
                            color=self.bar_color,
                            height=0.08,  # Very thin height for line effect
                            label='Team Fan Index')

        # Add vertical reference line at x=100 (where index = 1.0)
        ax.axvline(x=100, color='#808080', linestyle='-', linewidth=1.5, alpha=0.6, zorder=1)

        # Customize the bottom plot (Index) with blue color
        ax.set_yticks(y_positions)
        ax.set_yticklabels(data['Community'], fontsize=15, fontweight='bold', fontfamily=self.font_family)
        ax.set_xlabel('Likelihood To Be In Community (Index vs. Local Gen Pop)',
                      fontsize=13, fontweight='bold', fontfamily=self.font_family, color=self.bar_color)
        ax.set_xlim(0, max_value)

        # Set bottom x-axis ticks and labels with blue color
        ax.set_xticks([0, 100, 200, 300, 400, 500, 600, 700])
        ax.tick_params(axis='x', labelsize=15, labelbottom=True, colors=self.bar_color)
        for label in ax.get_xticklabels():
            label.set_fontweight('bold')
            label.set_fontfamily(self.font_family)
            label.set_color(self.bar_color)

        # Color the bottom x-axis spine blue
        ax.spines['bottom'].set_color(self.bar_color)
        ax.spines['bottom'].set_linewidth(2)

        # Configure top axis for percentage with gray color
        ax2.set_xlim(0, 100)
        ax2.set_xticks([0, 20, 40, 60, 80, 100])
        ax2.set_xticklabels(['0%', '20%', '40%', '60%', '80%', '100%'])
        ax2.tick_params(axis='x', labelsize=15, colors=self.background_color)
        for label in ax2.get_xticklabels():
            label.set_fontweight('bold')
            label.set_fontfamily(self.font_family)
            label.set_color(self.background_color)

        # Color the top x-axis spine gray
        ax2.spines['top'].set_color(self.background_color)
        ax2.spines['top'].set_linewidth(2)

        # Remove other spines
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax2.spines['right'].set_visible(False)
        ax2.spines['bottom'].set_visible(False)
        ax2.spines['left'].set_visible(False)
        ax.spines['left'].set_visible(True)

        # Add grid on bottom axis
        ax.grid(True, axis='x', alpha=0.3, linestyle='-', linewidth=0.5)
        ax.set_axisbelow(True)

        # Add title if provided with font
        if title:
            ax.set_title(title, fontsize=14, fontweight='bold', pad=20, fontfamily=self.font_family)

        # Add legend at bottom with more space and matched font size
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor=self.background_color, alpha=0.8, label='% Fans'),
            Patch(facecolor=self.bar_color, label='Index vs. Local Gen Pop')
        ]
        legend = ax.legend(handles=legend_elements,
                           loc='lower center',
                           bbox_to_anchor=(0.5, -0.25),
                           ncol=2,
                           frameon=True,
                           fancybox=True,
                           shadow=False,
                           prop={'family': self.font_family, 'weight': 'bold', 'size': 15})

        # Adjust layout
        plt.tight_layout()

        # Save
        plt.savefig(output_path, dpi=300, bbox_inches='tight',
                    facecolor='white', edgecolor='none')
        plt.close()

        return output_path


def create_community_chart_from_ranker(merchant_ranker,
                                       team_colors: Optional[Dict[str, str]] = None,
                                       output_path: Optional[Path] = None) -> Path:
    """
    Convenience function to create chart using MerchantRanker

    Args:
        merchant_ranker: Instance of MerchantRanker
        team_colors: Optional team colors dictionary
        output_path: Optional output path

    Returns:
        Path to generated chart
    """
    # Get the raw community data which includes COMPOSITE_INDEX
    communities_df = merchant_ranker.get_top_communities(
        min_audience_pct=0.20,
        top_n=10
    )

    if communities_df.empty:
        raise ValueError("No community data available")

    # Rename columns to match what the chart expects
    data = communities_df.rename(columns={
        'COMMUNITY': 'Community',
        'PERC_AUDIENCE': 'Audience_Pct',
        'COMPOSITE_INDEX': 'Composite_Index'
    })

    # Create chart
    chart = CommunityIndexChart(team_colors)
    return chart.create(data, output_path)


# ------------------------------
# Offline CSV utilities
# ------------------------------
def _normalize_min_audience_threshold(min_audience_pct: Optional[float]) -> Optional[float]:
    """Return a threshold expressed as a 0-1 decimal or None.

    Accepts values in either 0-1 or 0-100 scale and normalizes to 0-1.
    """
    if min_audience_pct is None:
        return None
    # If value looks like a whole percent (e.g. 20 for 20%), convert to decimal
    return min_audience_pct / 100.0 if min_audience_pct > 1.0 else min_audience_pct


def load_community_data_from_csv(
    community_csv_path: Union[str, Path],
    audience: str = 'Seattle Reign FC',
    comparison_population: str = 'Local Gen Pop (Excl. Seattle Reign Fans)',
    top_n: int = 10,
    min_audience_pct: Optional[float] = None,
) -> pd.DataFrame:
    """
    Load and prepare community data from a local CSV export (offline mode).

    Args:
        community_csv_path: Path to seattle_reign_community.csv
        audience: Value to match in 'AUDIENCE' column
        comparison_population: Value to match in 'COMPARISON_POPULATION' column
        top_n: Number of communities to return (by highest COMPOSITE_INDEX)
        min_audience_pct: Optional threshold for 'PERC_AUDIENCE' (accepts 0-1 or 0-100)

    Returns:
        DataFrame with columns: 'Community', 'Audience_Pct', 'Composite_Index'
    """
    community_csv_path = Path(community_csv_path)
    if not community_csv_path.exists():
        raise FileNotFoundError(f"Community CSV not found: {community_csv_path}")

    df = pd.read_csv(community_csv_path)

    # Basic column validation
    required_cols = {'AUDIENCE', 'COMPARISON_POPULATION', 'COMMUNITY', 'PERC_AUDIENCE', 'COMPOSITE_INDEX'}
    missing = required_cols.difference(df.columns)
    if missing:
        raise ValueError(f"Missing required columns in {community_csv_path}: {sorted(missing)}")

    # Filter to the requested slice
    filtered = df[
        (df['AUDIENCE'] == audience) &
        (df['COMPARISON_POPULATION'] == comparison_population)
    ].copy()

    if filtered.empty:
        raise ValueError(
            "No rows matched the provided filters. "
            f"audience='{audience}', comparison='{comparison_population}'"
        )

    # Normalize threshold and filter on audience percentage if specified
    threshold = _normalize_min_audience_threshold(min_audience_pct)
    if threshold is not None:
        filtered = filtered[filtered['PERC_AUDIENCE'] >= threshold]

    # Clean and sort
    filtered = filtered.dropna(subset=['COMMUNITY', 'PERC_AUDIENCE', 'COMPOSITE_INDEX'])
    filtered = filtered.sort_values('COMPOSITE_INDEX', ascending=False)

    # Take top N and rename to chart schema
    top = filtered.head(top_n).copy()
    top = top.rename(columns={
        'COMMUNITY': 'Community',
        'PERC_AUDIENCE': 'Audience_Pct',
        'COMPOSITE_INDEX': 'Composite_Index',
    })

    # Ensure only expected columns are returned
    return top[['Community', 'Audience_Pct', 'Composite_Index']]


def create_community_chart_from_csvs(
    community_csv_path: Union[str, Path] = None,
    audience: str = 'Seattle Reign FC',
    comparison_population: str = 'Local Gen Pop (Excl. Seattle Reign Fans)',
    top_n: int = 10,
    min_audience_pct: Optional[float] = None,
    team_colors: Optional[Dict[str, str]] = None,
    output_path: Optional[Path] = None,
) -> Path:
    """
    Convenience function to create chart using local CSV exports (offline mode).

    By default, reads 'seattle_reign_community.csv' in the repository root.

    Args:
        community_csv_path: CSV path; defaults to repo-root/seattle_reign_community.csv
        audience: Audience filter (e.g., 'Seattle Reign FC')
        comparison_population: Comparison population filter (e.g., 'Local Gen Pop (Excl. Seattle Reign Fans)')
        top_n: Number of communities to display
        min_audience_pct: Optional threshold for PERC_AUDIENCE (0-1 or 0-100)
        team_colors: Optional color dict {'primary', 'secondary'}
        output_path: Optional output path for the PNG

    Returns:
        Path to generated chart image
    """
    # Default to repository root CSV if not provided
    if community_csv_path is None:
        # visualizations/community_index_chart.py -> project root
        repo_root = Path(__file__).resolve().parent.parent
        community_csv_path = repo_root / 'seattle_reign_community.csv'

    data = load_community_data_from_csv(
        community_csv_path=community_csv_path,
        audience=audience,
        comparison_population=comparison_population,
        top_n=top_n,
        min_audience_pct=min_audience_pct,
    )

    chart = CommunityIndexChart(team_colors)
    return chart.create(data, output_path)


# Standalone test function
def test_community_index_chart():
    """Test with mock data matching the reference image"""

    # Create mock data matching the reference
    # Composite Index is typically PERC_AUDIENCE * PERC_INDEX / 100
    mock_data = pd.DataFrame({
        'Community': [
            'Live Entertainment Seekers',
            'Sports Merchandise Shopper',
            'College Sports',
            'Youth Sports',
            'Trend Setters',
            'Gambler',
            'Theme Parkers',
            'Fitness Enthusiasts',
            'Casual Outdoor Enthusiasts',
            'Movie Buffs'
        ],
        'Audience_Pct': [71, 44, 36, 30, 28, 28, 27, 24, 22, 22],  # PERC_AUDIENCE
        'Composite_Index': [798, 444, 364, 303, 287, 283, 270, 246, 224, 221]  # From reference
    })

    # Create chart with Jazz colors
    team_colors = {
        'primary': '#4472C4',  # Blue from reference
        'secondary': '#FFC000'  # Yellow from reference
    }

    chart = CommunityIndexChart(team_colors)
    output_path = chart.create(mock_data, 'test_community_index_chart.png')

    print(f"Created test chart: {output_path}")
    return output_path


# Test with real data
def test_with_real_data(team_key: str = 'utah_jazz'):
    """Test with real Snowflake data"""
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent))

    from data_processors.merchant_ranker import MerchantRanker
    from utils.team_config_manager import TeamConfigManager

    try:
        # Get team configuration
        config_manager = TeamConfigManager()
        team_config = config_manager.get_team_config(team_key)

        # Initialize merchant ranker
        ranker = MerchantRanker(team_view_prefix=team_config['view_prefix'])

        # Use the correct function that returns COMPOSITE_INDEX
        communities_df = ranker.get_top_communities(
            min_audience_pct=0.20,
            top_n=10
        )

        if communities_df.empty:
            print("No data found!")
            return None

        print(f"Found {len(communities_df)} communities")
        print("\nData preview:")
        print(communities_df.head())

        # Rename columns to match what the chart expects
        data = communities_df.rename(columns={
            'COMMUNITY': 'Community',
            'PERC_AUDIENCE': 'Audience_Pct',
            'COMPOSITE_INDEX': 'Composite_Index'
        })

        # Create chart
        chart = CommunityIndexChart(team_config.get('colors'))
        output_path = chart.create(data, f'{team_key}_community_index_chart.png')

        print(f"\nChart saved to: {output_path}")
        return output_path

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Generate community index chart')
    parser.add_argument('--mock', action='store_true', help='Use mock data')
    parser.add_argument('--team', type=str, default='utah_jazz',
                        choices=['utah_jazz', 'dallas_cowboys'],
                        help='Team to generate chart for (Snowflake mode)')
    parser.add_argument('--offline', action='store_true', help='Use local CSVs (offline)')
    parser.add_argument('--community-csv', type=str, default=None,
                        help='Path to seattle_reign_community.csv (defaults to repo root)')
    parser.add_argument('--audience', type=str, default='Seattle Reign FC',
                        help="AUDIENCE value to filter (offline)")
    parser.add_argument('--comparison', type=str, default='Local Gen Pop (Excl. Seattle Reign Fans)',
                        help="COMPARISON_POPULATION value to filter (offline)")
    parser.add_argument('--top-n', type=int, default=10, help='Number of communities (offline)')
    parser.add_argument('--min-audience', type=float, default=None,
                        help='Minimum PERC_AUDIENCE threshold (0-1 or 0-100, offline)')
    parser.add_argument('--output', type=str, default='community_index_chart.png',
                        help='Output image path')

    args = parser.parse_args()

    if args.mock:
        test_community_index_chart()
    elif args.offline:
        out = create_community_chart_from_csvs(
            community_csv_path=args.community_csv,
            audience=args.audience,
            comparison_population=args.comparison,
            top_n=args.top_n,
            min_audience_pct=args.min_audience,
            team_colors=None,
            output_path=Path(args.output),
        )
        print(f"Chart saved to: {out}")
    else:
        test_with_real_data(args.team)