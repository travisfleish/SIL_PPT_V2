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

        # Create figure
        fig, ax = plt.subplots(figsize=(10, 6))
        fig.patch.set_facecolor('white')
        ax.set_facecolor('white')

        # Set up the plot
        y_positions = np.arange(len(data))
        max_value = 700  # Fixed scale as shown in reference

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
                            label='% Team Fans')  # Changed from '% Audience'

        # Draw blue bars representing the Team Fan Index - as thin lines
        blue_bars = ax.barh(y_positions,
                            data['Composite_Index'],
                            color=self.bar_color,
                            height=0.08,  # Very thin height for line effect
                            label='Team Fan Index')  # Changed from '% Audience Index'

        # Add percentage labels in yellow boxes at the end of gray bars
        for i, (idx, row) in enumerate(data.iterrows()):
            # Convert to percentage if needed
            if data['Audience_Pct'].max() <= 1.0:
                pct_value = row['Audience_Pct'] * 100
            else:
                pct_value = row['Audience_Pct']

            # Position for the yellow box - at the end of the gray bar (% Team Fans)
            x_pos = pct_value * (max_value / 100)  # Scale to match x-axis
            y_pos = y_positions[i]

            # Create yellow box
            box_width = 60
            box_height = 0.5

            # Add yellow rectangle
            rect = Rectangle((x_pos - 5, y_pos - box_height / 2),
                             box_width, box_height,
                             facecolor=self.highlight_color,
                             edgecolor='none',
                             zorder=10)
            ax.add_patch(rect)

            # Add percentage text - show PERC_AUDIENCE
            ax.text(x_pos + box_width / 2 - 5, y_pos,
                    f"{pct_value:.1f}%",
                    ha='center', va='center',
                    fontweight='bold', fontsize=11,
                    zorder=11)

        # Customize the plot
        ax.set_yticks(y_positions)
        ax.set_yticklabels(data['Community'], fontsize=13)  # Increased from 11 to 13
        ax.set_xlabel('Percent Fan Audience', fontsize=13, fontweight='bold')  # Changed from '% Audience Index', matched fontsize
        ax.set_xlim(0, max_value)

        # Add x-axis labels at specific intervals with bold font
        ax.set_xticks([0, 100, 200, 300, 400, 500, 600, 700])
        ax.tick_params(axis='x', labelsize=12, labelbottom=True)
        for label in ax.get_xticklabels():
            label.set_fontweight('bold')

        # Remove top and right spines
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_visible(True)
        ax.spines['bottom'].set_visible(True)

        # Add grid
        ax.grid(True, axis='x', alpha=0.3, linestyle='-', linewidth=0.5)
        ax.set_axisbelow(True)

        # Add title if provided
        if title:
            ax.set_title(title, fontsize=14, fontweight='bold', pad=20)

        # Add legend at bottom with more space and matched font size
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor=self.background_color, alpha=0.8, label='% Team Fans'),  # Changed from '% Audience'
            Patch(facecolor=self.bar_color, label='Team Fan Index')  # Changed from '% Audience Index'
        ]
        ax.legend(handles=legend_elements,
                  loc='lower center',
                  bbox_to_anchor=(0.5, -0.25),  # Changed from -0.15 to -0.20 for more space
                  ncol=2,
                  frameon=True,
                  fancybox=True,
                  shadow=False,
                  fontsize=13)  # Added fontsize to match

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
                        help='Team to generate chart for')

    args = parser.parse_args()

    if args.mock:
        test_community_index_chart()
    else:
        test_with_real_data(args.team)