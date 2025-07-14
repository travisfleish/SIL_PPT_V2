#!/usr/bin/env python3
"""
Test script for Community Index Chart formatting
Run this to quickly test different formatting options
"""

import pandas as pd
import sys
from pathlib import Path

# Add the parent directory to the path so we can import the visualization module
sys.path.append(str(Path(__file__).parent.parent))

from visualizations.community_index_chart import CommunityIndexChart


def test_chart_formatting():
    """Test chart with different formatting options"""

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
        'Audience_Pct': [71, 44, 36, 30, 28, 28, 27, 24, 22, 22],  # PERC_AUDIENCE
        'Composite_Index': [798, 444, 364, 303, 287, 283, 270, 246, 224, 221]  # Team Fan Index
    })

    # Test 1: Default Utah Jazz colors
    print("Generating chart with Utah Jazz colors...")
    jazz_colors = {
        'primary': '#002B5C',  # Jazz navy blue
        'secondary': '#F9A01B'  # Jazz gold
    }

    chart = CommunityIndexChart(jazz_colors)
    output_path = chart.create(mock_data, 'test_jazz_community_chart.png')
    print(f"✓ Created: {output_path}")

    # Test 2: Dallas Cowboys colors
    print("\nGenerating chart with Dallas Cowboys colors...")
    cowboys_colors = {
        'primary': '#003594',  # Cowboys blue
        'secondary': '#869397'  # Cowboys silver
    }

    chart = CommunityIndexChart(cowboys_colors)
    output_path = chart.create(mock_data, 'test_cowboys_community_chart.png')
    print(f"✓ Created: {output_path}")

    # Test 3: Custom colors
    print("\nGenerating chart with custom colors...")
    custom_colors = {
        'primary': '#1E88E5',  # Bright blue
        'secondary': '#FFC107'  # Amber
    }

    chart = CommunityIndexChart(custom_colors)
    output_path = chart.create(mock_data, 'test_custom_community_chart.png')
    print(f"✓ Created: {output_path}")

    # Test 4: With title
    print("\nGenerating chart with title...")
    chart = CommunityIndexChart(jazz_colors)
    output_path = chart.create(
        mock_data,
        'test_titled_community_chart.png',
        title='Top Fan Communities by Index Score'
    )
    print(f"✓ Created: {output_path}")

    # Test 5: Different data ranges (to test scaling)
    print("\nGenerating chart with different data ranges...")
    scaled_data = mock_data.copy()
    scaled_data['Composite_Index'] = scaled_data['Composite_Index'] / 2  # Smaller indices
    scaled_data['Audience_Pct'] = scaled_data['Audience_Pct'] / 2  # Smaller percentages

    chart = CommunityIndexChart(jazz_colors)
    output_path = chart.create(scaled_data, 'test_scaled_community_chart.png')
    print(f"✓ Created: {output_path}")

    print("\n✅ All test charts generated successfully!")
    print("\nYou can now open these files to compare formatting:")
    print("- test_jazz_community_chart.png")
    print("- test_cowboys_community_chart.png")
    print("- test_custom_community_chart.png")
    print("- test_titled_community_chart.png")
    print("- test_scaled_community_chart.png")


def test_font_variations():
    """Test different font size combinations"""

    # You would need to modify the CommunityIndexChart class to accept
    # font sizes as parameters for this to work. For now, this shows
    # the concept of how you'd test different sizes.

    mock_data = pd.DataFrame({
        'Community': [
            'Live Entertainment Seekers',
            'Sports Merchandise Shopper',
            'College Sports',
            'Youth Sports',
            'Trend Setters'
        ],
        'Audience_Pct': [71, 44, 36, 30, 28],
        'Composite_Index': [798, 444, 364, 303, 287]
    })

    print("\nTo test font variations, modify these values in community_index_chart.py:")
    print("- Line 143: ax.set_yticklabels(..., fontsize=15, fontweight='bold', ...)")
    print("- Line 148: ax.tick_params(axis='x', labelsize=14, ...)")
    print("- Line 131: ax.text(..., fontsize=12, ...) # Yellow box text")
    print("- Line 145: ax.set_xlabel(..., fontsize=14, ...)")
    print("- Line 165: ax.set_title(..., fontsize=16, ...)")
    print("- Line 177: ax.legend(..., fontsize=14, ...)")

    # Generate one chart with current settings
    chart = CommunityIndexChart({'primary': '#4472C4', 'secondary': '#FFC000'})
    output_path = chart.create(mock_data, 'test_font_check.png')
    print(f"\n✓ Created font test chart: {output_path}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Test Community Index Chart formatting')
    parser.add_argument('--fonts', action='store_true',
                        help='Test font variations')
    parser.add_argument('--quick', action='store_true',
                        help='Quick test with single chart')

    args = parser.parse_args()

    if args.fonts:
        test_font_variations()
    elif args.quick:
        # Quick single chart test
        mock_data = pd.DataFrame({
            'Community': ['Entertainment', 'Sports', 'Fitness', 'Gaming', 'Travel'],
            'Audience_Pct': [71, 44, 36, 30, 28],
            'Composite_Index': [798, 444, 364, 303, 287]
        })

        chart = CommunityIndexChart({'primary': '#4472C4', 'secondary': '#FFC000'})
        output_path = chart.create(mock_data, 'quick_test.png')
        print(f"Created quick test: {output_path}")
    else:
        test_chart_formatting()