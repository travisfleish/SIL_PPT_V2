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
    """Create a mockup CFB fan wheel with the categories from the image"""
    
    # Mock CFB fan wheel data - ONLY using merchants with actual logos in assets/logos/merchants/
    # 12 categories going clockwise from top
    mock_data = {
        'COMMUNITY': [
            'Quick Service Restaurant',  # QSR
            'Sports Merchandise',
            'Sports Betting',
            'Streaming Services',
            'Food Delivery',
            'Fitness',
            'Beauty Products',
            'Restaurants',
            'Hotels',
            'Grocery',
            'Outdoor Gear',
            'Athleisure'
        ],
        'MERCHANT': [
            "McDonald's",  # mcdonalds.png exists
            'Fanatics',  # fanatics.png exists
            'DraftKings',  # draftkings.png exists
            'Prime Video',  # prime_video.png exists
            'DoorDash',  # doordash.png exists
            'Peloton',  # peloton.png exists
            'Sephora',  # sephora.png exists
            "Chili's Grill & Bar",  # chilis_grill_&_bar.png exists
            'Marriott',  # marriott.png exists
            'Whole Foods Market',  # whole_foods_market.png exists
            'Academy Sports + Outdoors',  # academy_sports_+_outdoors.png exists
            'Lululemon'  # lululemon.png exists
        ],
        'behavior': [
            'QSR',
            'Sports',
            'Betting',
            'Streaming',
            'Delivery',
            'Fitness',
            'Beauty',
            'Restaurants',
            'Hotels',
            'Grocery',
            'Outdoor',
            'Athleisure'
        ],
        'PERC_INDEX': [100] * 12,  # Placeholder index values
        # Mock audience percentages - high for QSR/restaurants, low for betting
        'audience_pct': [
            85,  # QSR - very high
            70,  # Sports merchandise - high
            30,  # Betting - low (as requested)
            75,  # Streaming - high
            65,  # Delivery - medium-high
            60,  # Fitness - medium
            55,  # Beauty - medium
            80,  # Restaurants - very high
            50,  # Hotels - medium
            70,  # Grocery - high
            55,  # Outdoor - medium
            65,  # Athleisure - medium-high
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
    print("Creating CFB fan wheel mockup with red heatmap...")
    fan_wheel = FanWheel(cfb_config, enable_logos=True)
    
    # Generate the wheel
    output_path = Path('cfb_fan_wheel_heatmap_mockup.png')
    result_path = fan_wheel.create(
        wheel_data=wheel_data,
        output_path=output_path,
        team_logo=None,
        transparent=False
    )
    
    print(f"\n✅ Mockup fan wheel created: {result_path}")
    print("\nKey features demonstrated:")
    print("  • QSR/McDonald's: Dark red (~85% audience) - high engagement")
    print("  • Restaurants/Chili's: Dark red (~80% audience) - high engagement")
    print("  • Betting/DraftKings: Light pink (~30% audience) - low engagement")
    print("  • Other categories: Red shades based on mock audience percentages")
    print("\nThe inner ring now uses a RED HEATMAP - darker = higher audience %!")
    
    return result_path


if __name__ == '__main__':
    try:
        create_mockup_cfb_wheel()
    except Exception as e:
        print(f"❌ Error creating mockup: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

