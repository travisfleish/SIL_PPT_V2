# visualizations/fan_wheel_standalone.py
"""
Standalone Fan Wheel Visualization Generator
Creates circular fan behavior visualization for sports teams
No dependencies on other project files
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Wedge, Circle, Polygon
import numpy as np
from pathlib import Path
import pandas as pd
from typing import Dict, Optional, Tuple


class FanWheelStandalone:
    """Generate fan wheel visualization showing top communities and their merchants"""

    def __init__(self, team_name: str = "Jazz",
                 primary_color: str = "#002B5C",
                 secondary_color: str = "#F9A01B",
                 accent_color: str = "#4169E1"):
        """
        Initialize fan wheel generator

        Args:
            team_name: Short team name (e.g., "Jazz", "Cowboys")
            primary_color: Main team color (hex)
            secondary_color: Secondary team color (hex)
            accent_color: Accent color for outer ring (hex)
        """
        self.team_name = team_name
        self.primary_color = primary_color
        self.secondary_color = secondary_color
        self.accent_color = accent_color

        # Visualization parameters
        self.outer_radius = 5.0
        self.logo_radius = 2.8
        self.inner_radius = 1.6

    def create(self, data: pd.DataFrame, output_path: str = None) -> str:
        """
        Create fan wheel visualization

        Args:
            data: DataFrame with columns: COMMUNITY, MERCHANT, behavior
            output_path: Where to save the visualization

        Returns:
            Path to saved visualization
        """
        if output_path is None:
            output_path = f'{self.team_name.lower()}_fan_wheel.png'

        # Create figure
        fig = plt.figure(figsize=(12, 12), facecolor='white')
        ax = fig.add_subplot(111, aspect='equal')
        ax.set_xlim(-6, 6)
        ax.set_ylim(-6, 6)
        ax.axis('off')

        num_items = len(data)
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
        self._draw_center_circle(ax)

        # Add logos and text for each segment
        self._add_segment_content(ax, data, angle_step)

        # Save
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight',
                    facecolor='white', edgecolor='none')
        plt.close()

        print(f"Fan wheel saved to {output_path}")
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

    def _draw_center_circle(self, ax):
        """Draw the center circle with team branding"""
        # Center circle
        center_circle = Circle((0, 0), self.inner_radius,
                               facecolor='black',
                               edgecolor=self.secondary_color,
                               linewidth=5,
                               zorder=20)
        ax.add_patch(center_circle)

        # Center text
        fan_text = f"THE {self.team_name.upper()} FAN"
        ax.text(0, 0, fan_text,
                ha='center', va='center',
                fontsize=16, fontweight='bold',
                color='white', zorder=22)

    def _add_segment_content(self, ax, data: pd.DataFrame, angle_step: float):
        """Add logos and behavior text to each segment"""
        for i, (_, row) in enumerate(data.iterrows()):
            center_angle = i * angle_step + angle_step / 2 - 90
            angle_rad = np.deg2rad(center_angle)

            # Logo position
            logo_x = self.logo_radius * np.cos(angle_rad)
            logo_y = self.logo_radius * np.sin(angle_rad)

            # Add logo placeholder
            self._add_merchant_logo(ax, row['MERCHANT'], logo_x, logo_y)

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

    def _add_merchant_logo(self, ax, merchant: str, x: float, y: float):
        """Add merchant logo placeholder - simple white circle"""
        # White circle placeholder
        logo_bg = Circle((x, y), 0.55,
                         facecolor='white',
                         edgecolor='#E0E0E0',  # Light gray border
                         linewidth=1,
                         zorder=5)
        ax.add_patch(logo_bg)

        # Add merchant initials
        initials = ''.join([word[0].upper() for word in merchant.split()[:2]])
        ax.text(x, y, initials,
                ha='center', va='center',
                fontsize=12, fontweight='bold',
                color='#888888', zorder=6)


# Test function
def test_fan_wheel_with_real_data(team_key: str = 'utah_jazz'):
    """Test fan wheel with real Snowflake data"""
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent))

    from data_processors.merchant_ranker import MerchantRanker
    from utils.team_config_manager import TeamConfigManager

    print(f"\n{'=' * 60}")
    print(f"FAN WHEEL TEST - {team_key.replace('_', ' ').title()}")
    print(f"{'=' * 60}")

    try:
        # Get team configuration
        config_manager = TeamConfigManager()
        team_config = config_manager.get_team_config(team_key)

        print(f"\nTeam: {team_config['team_name']}")
        print(f"View Prefix: {team_config['view_prefix']}")

        # Initialize merchant ranker
        ranker = MerchantRanker(team_view_prefix=team_config['view_prefix'])

        # Get fan wheel data
        print("\nFetching fan wheel data from Snowflake...")
        wheel_data = ranker.get_fan_wheel_data(
            min_audience_pct=0.20,
            top_n_communities=10
        )

        if wheel_data.empty:
            print("❌ No data found!")
            return None

        print(f"✅ Found {len(wheel_data)} communities")

        # Show data preview
        print("\nData preview:")
        print(f"{'Community':<30} {'Merchant':<25} {'Behavior':<25}")
        print("-" * 80)
        for _, row in wheel_data.head(5).iterrows():
            behavior_text = row['behavior'].replace('\n', ' ')
            print(f"{row['COMMUNITY']:<30} {row['MERCHANT']:<25} {behavior_text:<25}")

        # Create fan wheel
        print("\nGenerating fan wheel visualization...")

        colors = team_config.get('colors', {})
        fan_wheel = FanWheelStandalone(
            team_name=team_config.get('team_name_short', team_key),
            primary_color=colors.get('primary', '#002244'),
            secondary_color=colors.get('secondary', '#FFB612'),
            accent_color=colors.get('accent', '#4169E1')
        )

        output_path = f"{team_key}_fan_wheel_real_data.png"
        result = fan_wheel.create(wheel_data, output_path)

        print(f"✅ Fan wheel saved to: {result}")
        return result

    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def test_fan_wheel_with_mock_data():
    """Test fan wheel with mock data"""

    print("\n" + "=" * 60)
    print("FAN WHEEL TEST - MOCK DATA")
    print("=" * 60)

    # Create mock data
    mock_data = pd.DataFrame({
        'COMMUNITY': [
            'Live Entertainment Seekers',
            'Cost Conscious',
            'Travelers',
            'Gen Z Brand Shoppers',
            'Beauty Enthusiasts',
            'Movie Buffs',
            'Sports Streamer',
            'Gamers',
            'Pet Owners',
            'Fans of Men\'s Sports'
        ],
        'MERCHANT': [
            'Vivint Arena',
            'Dollar Tree',
            'Southwest',
            'AutoZone',
            'Ulta',
            'Megaplex',
            'ESPN Plus',
            'PlayStation',
            'Petco',
            'StubHub'
        ],
        'behavior': [
            'Attends\nVivint Arena',
            'Saves at\nDollar Tree',
            'Flies with\nSouthwest',
            'Shops at\nAutoZone',
            'Beauty at\nUlta',
            'Watches at\nMegaplex',
            'Streams\nESPN+',
            'Games on\nPlayStation',
            'Shops at\nPetco',
            'Buys at\nStubHub'
        ]
    })

    # Create fan wheel
    fan_wheel = FanWheelStandalone(
        team_name="Jazz",
        primary_color="#002B5C",  # Jazz navy
        secondary_color="#F9A01B",  # Jazz yellow
        accent_color="#00471B"  # Jazz green
    )

    output_path = fan_wheel.create(mock_data, "test_fan_wheel_mock.png")
    print(f"\n✅ Created: {output_path}")

    return output_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Generate fan wheel visualization')
    parser.add_argument('--mock', action='store_true', help='Use mock data instead of real data')
    parser.add_argument('--team', type=str, default='utah_jazz',
                        choices=['utah_jazz', 'dallas_cowboys'],
                        help='Team to generate fan wheel for')

    args = parser.parse_args()

    if args.mock:
        test_fan_wheel_with_mock_data()
    else:
        # Test with real data
        print(f"Generating fan wheel for {args.team}...")
        test_fan_wheel_with_real_data(args.team)