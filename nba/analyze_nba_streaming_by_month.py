#!/usr/bin/env python3
"""
Analyze NBA streaming platform fan volume by month for 2024
Creates stacked bar chart and percentage share analysis
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from data_processors.snowflake_connector import get_connection
from utils.font_manager import font_manager

# ============================================================================
# Step 1: Query Snowflake data with filters
# ============================================================================

query = """
SELECT *
FROM SILAB_DATA_SHARING.NBA_THOUGHT_LEADERSHIP.ENTRY_MONTH_SUBSCRIBER_TYPE_SPORTS_FANS
WHERE COMMUNITY = 'NBA'
  AND ENTRY_YEAR = 2024
  AND MERCHANT_FORMAT_NAME NOT IN ('Univision Now', 'FloSports')
"""

print("Querying Snowflake...")
with get_connection() as conn:
    cursor = conn.cursor()
    cursor.execute(query)
    df = cursor.fetch_pandas_all()
    cursor.close()

print(f"Loaded {len(df)} rows")

# ============================================================================
# Step 2: Create ENTRY_MONTH_NAME column with month names
# ============================================================================

# Map numeric month to full month name
month_map = {
    1: 'January', 2: 'February', 3: 'March', 4: 'April', 5: 'May', 6: 'June',
    7: 'July', 8: 'August', 9: 'September', 10: 'October', 11: 'November', 12: 'December'
}

df['ENTRY_MONTH_NAME'] = df['ENTRY_MONTH'].map(month_map)

# Ensure months are ordered correctly (January to December)
month_order = ['January', 'February', 'March', 'April', 'May', 'June', 
               'July', 'August', 'September', 'October', 'November', 'December']
df['ENTRY_MONTH_NAME'] = pd.Categorical(df['ENTRY_MONTH_NAME'], 
                                         categories=month_order, 
                                         ordered=True)

# ============================================================================
# Step 3: Aggregate data by ENTRY_MONTH_NAME and MERCHANT_FORMAT_NAME
# ============================================================================

# Group by month and merchant, summing AVG_FAN_COUNT
aggregated = df.groupby(['ENTRY_MONTH_NAME', 'MERCHANT_FORMAT_NAME'], observed=True)['AVG_FAN_COUNT'].sum().reset_index()

# Create pivot table: rows = months, columns = merchants, values = total AVG_FAN_COUNT
pivot_df = aggregated.pivot_table(
    index='ENTRY_MONTH_NAME',
    columns='MERCHANT_FORMAT_NAME',
    values='AVG_FAN_COUNT',
    fill_value=0
)

# Ensure months are in correct order
pivot_df = pivot_df.reindex(month_order)

print("\n" + "=" * 80)
print("Aggregated Data (Total AVG_FAN_COUNT by Month and Platform)")
print("=" * 80)
print(pivot_df)
print()

# ============================================================================
# Step 4: Create stacked bar chart
# ============================================================================

# Load custom fonts using direct file paths
klarheit_regular_path = '/Users/travisfleisher/Cursor Project/SIL_PPT_V2/backend/assets/fonts/KlarheitKurrent-Regular_2456150069.ttf'
klarheit_bold_path = '/Users/travisfleisher/Cursor Project/SIL_PPT_V2/backend/assets/fonts/KlarheitKurrent-Bold_4110053601.ttf'
redhat_display_path = '/Users/travisfleisher/Cursor Project/SIL_PPT_V2/backend/assets/fonts/RedHatDisplay-Regular.ttf'

# Create FontProperties objects using file paths directly
title_font_prop = fm.FontProperties(fname=klarheit_bold_path, size=16)
label_font_prop = fm.FontProperties(fname=klarheit_bold_path, size=12)
tick_font_prop = fm.FontProperties(fname=redhat_display_path, size=10)
legend_font_prop = fm.FontProperties(fname=redhat_display_path, size=10)
legend_title_font_prop = fm.FontProperties(fname=redhat_display_path, size=11)

# Set up the plot with transparent background
fig, ax = plt.subplots(figsize=(16, 8))
fig.patch.set_facecolor('none')  # Transparent figure background
ax.set_facecolor('none')  # Transparent axes background

# Create color palette with gradients for each platform
# Define base colors for each platform
platform_colors = {
    'PEACOCK TV': '#00A4E4',
    'DISNEY PLUS': '#113CCF',
    'ROKU': '#6F1AB6',
    'YOUTUBE TV': '#FF0000',
    'ESPN+': '#000000',
    'FUBO TV': '#00D4AA',
    'SLING TV': '#00C4FF',
    'HULU': '#1CE783',
    'DIRECTV': '#0066CC'
}

# Create gradient effect by varying color intensity across months
# Each platform gets a gradient from lighter (earlier months) to darker (later months)
from matplotlib.colors import rgb2hex, hex2color, to_rgb

def apply_gradient_to_color(base_color, month_idx, total_months):
    """Apply gradient effect: lighter in early months, darker in later months"""
    rgb = np.array(to_rgb(base_color))
    
    # Create subtle gradient: 85% to 100% intensity
    intensity = 0.85 + (month_idx / (total_months - 1)) * 0.15
    gradient_rgb = rgb * intensity
    gradient_rgb = np.clip(gradient_rgb, 0, 1)
    return rgb2hex(gradient_rgb)

# Calculate percentages for labels (each month sums to 100%)
pivot_pct = pivot_df.div(pivot_df.sum(axis=1), axis=0) * 100

# Create stacked bar chart with gradient colors
num_months = len(pivot_df)
month_positions = range(num_months)
bottom = np.zeros(num_months)

# Store bottom positions for each platform to use for labels
bottom_positions = {}

# Plot each platform with gradient colors that vary by month
for platform in pivot_df.columns:
    values = pivot_df[platform].values
    base_color = platform_colors.get(platform, '#808080')
    
    # Store bottom positions for this platform
    bottom_positions[platform] = bottom.copy()
    
    # Create gradient colors for each month
    gradient_colors = [apply_gradient_to_color(base_color, i, num_months) 
                       for i in range(num_months)]
    
    # Plot bars with individual colors for gradient effect
    bars = ax.bar(month_positions, values, bottom=bottom, label=platform, 
                  color=gradient_colors, width=0.8, 
                  edgecolor='white', linewidth=0.5, alpha=0.95)
    bottom += values

# Add percentage labels inside segments (only where large enough)
for month_idx, month_name in enumerate(pivot_df.index):
    month_total = pivot_df.loc[month_name].sum()
    
    for platform in pivot_df.columns:
        segment_value = pivot_df.loc[month_name, platform]
        segment_bottom = bottom_positions[platform][month_idx]
        segment_top = segment_bottom + segment_value
        segment_height = segment_value
        
        # Only add label if segment is large enough (at least 3% of total bar height)
        min_height_threshold = month_total * 0.03
        if segment_height >= min_height_threshold:
            # Calculate center y-position of segment
            segment_center_y = segment_bottom + (segment_height / 2)
            
            # Get percentage for this segment
            pct_value = pivot_pct.loc[month_name, platform]
            
            # Format percentage (1 decimal place if >= 10%, otherwise 1 decimal)
            if pct_value >= 10:
                label_text = f'{pct_value:.1f}%'
            else:
                label_text = f'{pct_value:.1f}%'
            
            # Add text label
            ax.text(month_idx, segment_center_y, label_text,
                   ha='center', va='center',
                   fontproperties=tick_font_prop,
                   fontsize=8,
                   color='white',
                   weight='bold',
                   zorder=15)

# Customize the chart with KlarheitKurrent for title and labels
ax.set_title('NBA Fan Streaming Volume by Platform – 2024', 
             fontproperties=title_font_prop, pad=20)
ax.set_xlabel('Month', fontproperties=label_font_prop)
ax.set_ylabel('Fan Volume', fontproperties=label_font_prop)

# Set axis tick labels with RedHatDisplay
ax.tick_params(axis='both', labelsize=10)
for label in ax.get_yticklabels():
    label.set_fontproperties(tick_font_prop)

# Set x-axis tick labels to month names
ax.set_xticks(range(len(pivot_df)))
ax.set_xticklabels(pivot_df.index, rotation=45, ha='right', fontproperties=tick_font_prop)

# Add legend with RedHatDisplay - transparent background, centered vertically and horizontally on border
# bbox_to_anchor=(1.1, 0.5) places anchor 10% to the right of axes edge, vertically centered
# loc='center' centers the legend horizontally on that anchor point
legend = ax.legend(title='Platform', bbox_to_anchor=(1.1, 0.5), loc='center', 
                   prop=legend_font_prop, title_fontproperties=legend_title_font_prop,
                   framealpha=0)  # Transparent background

# ============================================================================
# Add callout annotation for Peacock TV
# ============================================================================

# Get the bar positions and heights for proper annotation
jan_index = 0  # January is the first bar (index 0)
peacock_col = 'PEACOCK TV'

# Calculate cumulative heights to find Peacock TV's position in the stacked bar
# We need to sum all values that come before Peacock TV in the stacking order
peacock_bottom = 0
for col in pivot_df.columns:
    if col == peacock_col:
        break
    peacock_bottom += pivot_df.loc['January', col]

# Height of Peacock TV segment in January
peacock_height = pivot_df.loc['January', peacock_col]
# Middle y-coordinate of Peacock TV segment
peacock_mid_y = peacock_bottom + peacock_height / 2

# Position callout box - shifted down and to the right
# Position it above Feb/Mar/Apr (indices 1, 2, 3), shifted right
callout_x_data = 2.2  # Shifted right from center of Feb/Mar/Apr
y_max = ax.get_ylim()[1]
callout_y_data = y_max * 0.88  # Shifted down from top

# Create callout text
callout_text = "Peacock TV #1 average\nat 24.2%"

# Draw arrow from callout to Peacock TV segment in Jan
# Arrow points from callout to the middle of Peacock TV segment
arrow = FancyArrowPatch(
    (callout_x_data, callout_y_data),  # Start from callout position
    (jan_index, peacock_mid_y),  # Point to middle of Peacock TV segment
    arrowstyle='->',
    mutation_scale=25,
    linewidth=2,
    color='#333333',
    zorder=10,
    connectionstyle="arc3,rad=0.15"  # Slight curve
)
ax.add_patch(arrow)

# Add text without box - just the text with a subtle background for readability
ax.text(callout_x_data, callout_y_data, callout_text,
        ha='center', va='center',
        fontproperties=tick_font_prop,
        fontsize=9,
        zorder=12,
        bbox=dict(boxstyle='round,pad=0.5', facecolor='white', edgecolor='none', alpha=0.9))

# Use tight_layout to prevent label cutoff
plt.tight_layout()

# Save the plot with transparent background
output_file = 'nba_streaming_by_month_2024.png'
plt.savefig(output_file, dpi=300, bbox_inches='tight', transparent=True)
print(f"\nPlot saved to: {output_file}")

# Display the plot
plt.show()

# ============================================================================
# Step 5: Calculate percentage share by month (for console output)
# Note: pivot_pct was already calculated earlier for chart labels
# ============================================================================

# Round to 2 decimal places for readability
pivot_pct = pivot_pct.round(2)

print("\n" + "=" * 80)
print("Percentage Share by Month (each month sums to 100%)")
print("=" * 80)
print(pivot_pct)
print()

# Also show a summary - average percentage across all months
print("\n" + "=" * 80)
print("Average Percentage Share Across All Months")
print("=" * 80)
avg_pct = pivot_pct.mean().sort_values(ascending=False)
for platform, pct in avg_pct.items():
    print(f"{platform:20s}: {pct:6.2f}%")
print("=" * 80)

