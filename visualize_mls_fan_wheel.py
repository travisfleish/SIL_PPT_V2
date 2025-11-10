#!/usr/bin/env python3
"""
Generate visual fan wheel for MLS Fan
"""

import pandas as pd
from visualizations.fan_wheel_standalone import FanWheel
from pathlib import Path

# MLS Fan colors (matching the CFB mockup style)
mls_config = {
    'team_name': 'MLS Fans',
    'team_name_short': 'MLS',
    'colors': {
        'primary': '#005DAA',    # Dark blue for the variable bars
        'secondary': '#E03A3E',  # MLS Red for center circle
        'accent': '#87CEEB'      # Light blue for the outer wedges
    }
}

# Read the fan wheel data
df = pd.read_csv('mls_fan_fan_wheel_v2.csv')

# Convert PERC_AUDIENCE to audience_pct (multiply by 100 to convert from decimal to percentage)
df['audience_pct'] = df['PERC_AUDIENCE'] * 100

# Rename COMMUNITY to behavior (what the fan_wheel expects)
df['behavior'] = df['COMMUNITY']

print("MLS Fan Wheel Data:")
print(df[['behavior', 'MERCHANT', 'audience_pct']])

# Create the fan wheel visualization
fan_wheel = FanWheel(mls_config, enable_logos=True)

# Generate the visualization
output_path = 'mls_fan_wheel_final.png'
fan_wheel.create(
    wheel_data=df,
    output_path=Path(output_path)
)

print(f"\n✅ Fan wheel saved to {output_path}")
