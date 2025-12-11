#!/usr/bin/env python3
"""
Generate bar chart from F1 streaming CSV data
Shows non-social media merchants and their streaming percentages
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
import logging
from utils.font_manager import font_manager
from utils.team_config_manager import TeamConfigManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def parse_streaming_csv(csv_path: Path) -> pd.DataFrame:
    """Parse the streaming CSV file and extract merchant data"""
    # Read CSV, skipping first 2 rows and using row 3 as header
    df = pd.read_csv(csv_path, skiprows=2, header=0)
    
    # Forward fill AUDIENCE column (since it's only in first row)
    df['AUDIENCE'] = df['AUDIENCE'].ffill()
    
    # Filter to only F1 Racing Fans rows (not totals)
    df = df[df['AUDIENCE'] == 'F1 Racing Fans'].copy()
    
    # Remove rows with empty MERCHANT (totals)
    df = df[df['MERCHANT'].notna()].copy()
    
    # Filter out social media merchants
    social_media = ['TIKTOK', 'LinkedIn', 'Discord']
    df = df[~df['MERCHANT'].isin(social_media)].copy()
    
    # Remove total rows (where MERCHANT might be empty or NaN)
    df = df[df['MERCHANT'] != 'F1 Racing Fans Total'].copy()
    df = df[df['MERCHANT'] != 'Grand Total'].copy()
    
    # Reset index
    df = df.reset_index(drop=True)
    
    return df


def extract_percentages(df: pd.DataFrame) -> pd.DataFrame:
    """Extract percentage values from the dataframe"""
    # Get all streaming category columns
    streaming_cols = [
        'Streaming - OTT',
        'Streaming - Platforms',
        'Streaming - Specialty OTT - Anime',
        'Streaming - Specialty OTT - Sports'
    ]
    
    # Create a new dataframe with merchant and their max percentage
    result_data = []
    
    for _, row in df.iterrows():
        merchant = row['MERCHANT']
        
        # Get all percentage values for this merchant
        percentages = []
        for col in streaming_cols:
            if col in row and pd.notna(row[col]):
                # Remove % sign and convert to float
                pct_str = str(row[col]).replace('%', '').strip()
                try:
                    pct_val = float(pct_str)
                    percentages.append(pct_val)
                except ValueError:
                    pass
        
        # Use the maximum percentage value for each merchant
        if percentages:
            max_pct = max(percentages)
            result_data.append({
                'MERCHANT': merchant,
                'PERCENTAGE': max_pct
            })
    
    result_df = pd.DataFrame(result_data)
    
    # Sort by percentage descending
    result_df = result_df.sort_values('PERCENTAGE', ascending=False).reset_index(drop=True)
    
    return result_df


def create_bar_chart(data: pd.DataFrame, output_path: Path, team_config: dict):
    """Create a bar chart from the streaming data"""
    # Get team colors
    colors = team_config.get('colors', {})
    primary_color = colors.get('primary', '#E10600')  # F1 Red
    secondary_color = colors.get('secondary', '#1E1E1E')  # F1 Black
    
    # Get font family
    font_family = font_manager.get_font_family('Red Hat Display')
    
    # Create figure
    fig, ax = plt.subplots(figsize=(12, 8))
    fig.patch.set_facecolor('none')  # Transparent background
    fig.patch.set_alpha(0.0)
    ax.set_facecolor('none')  # Transparent background
    ax.patch.set_alpha(0.0)
    
    # Prepare data
    merchants = data['MERCHANT'].values
    percentages = data['PERCENTAGE'].values
    
    # Create bars
    bars = ax.barh(merchants, percentages, color=primary_color, alpha=0.8)
    
    # Add value labels on bars
    for i, (bar, pct) in enumerate(zip(bars, percentages)):
        width = bar.get_width()
        ax.text(width + 0.5, bar.get_y() + bar.get_height()/2,
                f'{pct:.2f}%',
                ha='left', va='center',
                fontsize=12,
                fontweight='bold',
                fontfamily=font_family,
                color='white')
    
    # Customize axes
    ax.set_xlabel('Percentage (%)', fontsize=14, fontweight='bold', fontfamily=font_family, color='white')
    ax.set_ylabel('Merchant', fontsize=14, fontweight='bold', fontfamily=font_family, color='white')
    ax.set_title('F1 Racing Fans - Streaming Services', fontsize=16, fontweight='bold', fontfamily=font_family, color='white')
    
    # Set x-axis limits with some padding
    ax.set_xlim(0, max(percentages) * 1.15)
    
    # Style
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('white')
    ax.spines['bottom'].set_color('white')
    
    # Set font for tick labels and make them white
    ax.tick_params(axis='both', labelsize=11, colors='white')
    for label in ax.get_yticklabels():
        label.set_fontfamily(font_family)
        label.set_color('white')
    for label in ax.get_xticklabels():
        label.set_fontfamily(font_family)
        label.set_color('white')
    
    # Invert y-axis to show highest at top
    ax.invert_yaxis()
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='none', transparent=True)
    plt.close()
    
    logger.info(f"Bar chart saved to {output_path}")


def main():
    """Main function to generate the bar chart"""
    csv_path = Path('f1_streaming.csv')
    output_path = Path('output/f1_streaming_bar_chart.png')
    
    if not csv_path.exists():
        logger.error(f"CSV file not found: {csv_path}")
        return
    
    # Get F1 team config
    config_manager = TeamConfigManager()
    f1_config = config_manager.get_team_config('f1_racing_fans')
    
    # Parse CSV
    logger.info(f"Parsing CSV: {csv_path}")
    df = parse_streaming_csv(csv_path)
    
    # Extract percentages
    logger.info("Extracting percentage data")
    chart_data = extract_percentages(df)
    
    logger.info(f"Found {len(chart_data)} merchants")
    logger.info(f"\nChart data:\n{chart_data}")
    
    # Create bar chart
    logger.info("Creating bar chart")
    create_bar_chart(chart_data, output_path, f1_config)
    
    logger.info(f"✅ Bar chart saved to: {output_path}")


if __name__ == '__main__':
    main()

