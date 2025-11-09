#!/usr/bin/env python3
"""
Test script to generate a mockup CFB fan wheel with variable inner rings
Demonstrates the bar graph concept where inner ring size varies by category audience %
"""

import pandas as pd
from pathlib import Path
import sys
from visualizations.fan_wheel import FanWheel

def create_mockup_cfb_wheel():
    """Create a mockup CFB fan wheel with grouped categories and color coding"""
    
    # Define category group colors - PRIMARY COLORS
    FOOD_COLOR = '#FF0000'      # Red for food-related
    SHOPPING_COLOR = '#00FF00'  # Green for shopping/retail
    ENTERTAINMENT_COLOR = '#FFFF00'  # Yellow for entertainment
    LIFESTYLE_COLOR = '#0000FF'  # Blue for lifestyle/wellness
    TRAVEL_COLOR = '#FF0000'    # Red for travel (using red again as primary color)
    
    # Mock CFB fan wheel data - GROUPED by category type
    # Food-related categories grouped together
    mock_data = {
        'COMMUNITY': [
            # Food Group (4 categories)
            'Quick Service Restaurant',
            'Restaurants', 
            'Grocery',
            'Food Delivery',
            # Shopping Group (3 categories)
            'Sports Merchandise',
            'Athleisure',
            'Beauty Products',
            # Entertainment Group (2 categories)
            'Streaming Services',
            'Sports Betting',
            # Lifestyle Group (2 categories)
            'Fitness',
            'Outdoor Gear',
            # Travel Group (1 category)
            'Hotels',
        ],
        'MERCHANT': [
            # Food Group
            "McDonald's",
            "Chili's Grill & Bar",
            'Whole Foods Market',
            'DoorDash',
            # Shopping Group
            'Fanatics',
            'Lululemon',
            'Sephora',
            # Entertainment Group
            'Prime Video',
            'DraftKings',
            # Lifestyle Group
            'Peloton',
            'Academy Sports + Outdoors',
            # Travel Group
            'Marriott',
        ],
        'behavior': [
            # Food Group
            'QSR',
            'Restaurants',
            'Grocery',
            'Delivery',
            # Shopping Group
            'Sports',
            'Athleisure',
            'Beauty',
            # Entertainment Group
            'Streaming',
            'Betting',
            # Lifestyle Group
            'Fitness',
            'Outdoor',
            # Travel Group
            'Hotels',
        ],
        'PERC_INDEX': [100] * 12,
        # Mock audience percentages - MORE VARIANCE for better visual contrast
        'audience_pct': [
            # Food Group - very high engagement
            95,  # QSR - highest
            88,  # Restaurants - very high
            78,  # Grocery - high
            72,  # Delivery - medium-high
            # Shopping Group - medium engagement
            65,  # Sports merchandise - medium
            58,  # Athleisure - medium-low
            48,  # Beauty - low-medium
            # Entertainment Group - mixed engagement
            82,  # Streaming - very high
            25,  # Betting - lowest
            # Lifestyle Group - low-medium engagement
            52,  # Fitness - medium-low
            42,  # Outdoor - low
            # Travel Group - low engagement
            35,  # Hotels - low
        ],
        # Category grouping information
        'category_group': [
            # Food Group
            'Food', 'Food', 'Food', 'Food',
            # Shopping Group
            'Shopping', 'Shopping', 'Shopping',
            # Entertainment Group
            'Entertainment', 'Entertainment',
            # Lifestyle Group
            'Lifestyle', 'Lifestyle',
            # Travel Group
            'Travel',
        ],
        'group_color': [
            # Food Group
            FOOD_COLOR, FOOD_COLOR, FOOD_COLOR, FOOD_COLOR,
            # Shopping Group
            SHOPPING_COLOR, SHOPPING_COLOR, SHOPPING_COLOR,
            # Entertainment Group
            ENTERTAINMENT_COLOR, ENTERTAINMENT_COLOR,
            # Lifestyle Group
            LIFESTYLE_COLOR, LIFESTYLE_COLOR,
            # Travel Group
            TRAVEL_COLOR,
        ]
    }
    
    wheel_data = pd.DataFrame(mock_data)
    
    # CFB team config (using college football colors)
    cfb_config = {
        'team_name': 'College Football',
        'team_name_short': 'CFB',
        'colors': {
            'primary': '#002244',  # Dark navy blue (for inner ring)
            'secondary': '#FFB612',  # Gold/yellow
            'accent': '#87CEEB'     # Light blue (for outer ring)
        }
    }
    
    # Create the fan wheel
    print("Creating CFB fan wheel mockup with variable ring bar graph...")
    fan_wheel = FanWheel(cfb_config, enable_logos=True)
    
    # Generate the wheel with white background and flush rings
    output_path = Path('cfb_fan_wheel_variable_rings_mockup.png')
    result_path = fan_wheel.create(
        wheel_data=wheel_data,
        output_path=output_path,
        team_logo=None,
        transparent=False  # White background with flush red/blue rings
    )
    
    print(f"\n✅ Mockup fan wheel created: {result_path}")
    print("\nKey features demonstrated:")
    print("  ✓ Color swap: Light blue inner bars (variable), dark blue outer rings")
    print("  ✓ Text outline: White stroke for readability on all backgrounds")
    print("  ✓ Category grouping: Thin colored outer ring groups related categories")
    print("\nCategory Groups:")
    print("  • Food (RED): QSR, Restaurants, Grocery, Delivery - adjacent on wheel")
    print("  • Shopping (GREEN): Sports, Athleisure, Beauty")
    print("  • Entertainment (YELLOW): Streaming, Betting")
    print("  • Lifestyle (BLUE): Fitness, Outdoor")
    print("  • Travel (RED): Hotels")
    print("\nBar Graph Data (Enhanced Variance):")
    print("  • QSR: 95% - longest light blue bar")
    print("  • Restaurants: 88% - very long bar")
    print("  • Streaming: 82% - long bar")
    print("  • Betting: 25% - shortest light blue bar")
    print("  • Hotels: 35% - very short bar")
    print("  • Range: 25% to 95% for dramatic visual contrast")
    
    return result_path


if __name__ == '__main__':
    try:
        create_mockup_cfb_wheel()
    except Exception as e:
        print(f"❌ Error creating mockup: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

