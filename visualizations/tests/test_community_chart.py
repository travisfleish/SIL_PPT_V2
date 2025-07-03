# test_community_chart_standalone.py
"""
Simple standalone test for the community index chart
"""

import pandas as pd
from pathlib import Path
import sys

# Add parent directory to path if running from a subdirectory
sys.path.append(str(Path(__file__).parent.parent))

from visualizations.community_index_chart import CommunityIndexChart


def test_chart():
    """Create a test chart with mock data"""

    # Create mock data matching the reference image
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
        'Audience_Pct': [71, 44, 36, 30, 28, 28, 27, 24, 22, 22],  # % of fans
        'Composite_Index': [798, 444, 364, 303, 287, 283, 270, 246, 224, 221]  # Index values
    })

    # Define team colors (Utah Jazz example)
    team_colors = {
        'primary': '#4472C4',  # Blue
        'secondary': '#FFC000'  # Yellow/Gold
    }

    # Create the chart
    print("Creating community index chart...")
    chart = CommunityIndexChart(team_colors)
    output_path = chart.create(mock_data, Path('test_community_chart.png'))

    # Convert to Path object if it's a string
    if isinstance(output_path, str):
        output_path = Path(output_path)

    print(f"✅ Chart saved to: {output_path.absolute()}")
    print("\nChart should show:")
    print("- Gray bars labeled '% Team Fans'")
    print("- Blue lines labeled 'Team Fan Index'")
    print("- X-axis labeled 'Percent Fan Audience'")
    print("- Yellow boxes with percentages at the end of gray bars")

    return output_path


if __name__ == "__main__":
    test_chart()