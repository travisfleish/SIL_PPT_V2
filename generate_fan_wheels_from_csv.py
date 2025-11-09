#!/usr/bin/env python3
"""
Generate fan wheels for all audiences using the CSV data (no Snowflake needed)
"""

import pandas as pd
from visualizations.fan_wheel import FanWheel
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def prepare_fan_wheel_data(csv_path: str, audience: str) -> pd.DataFrame:
    """
    Prepare fan wheel data for a specific audience from the CSV
    
    Args:
        csv_path: Path to the audience_category_merchant_mapping.csv
        audience: Name of the audience to generate for
        
    Returns:
        DataFrame formatted for fan wheel generation
    """
    # Read the CSV
    df = pd.read_csv(csv_path)
    
    # Filter for the specific audience
    audience_df = df[df['audience'] == audience].copy()
    
    if len(audience_df) == 0:
        logger.error(f"No data found for audience: {audience}")
        return pd.DataFrame()
    
    # Prepare data in the format expected by fan wheel
    fan_wheel_data = []
    
    for _, row in audience_df.iterrows():
        # Convert PERC_AUDIENCE to percentage (0-100) for audience_pct
        audience_pct = row['category_perc_audience'] * 100 if pd.notna(row['category_perc_audience']) else 50.0
        
        # Use clean_name for the label (shorter, cleaner text)
        label_text = row['clean_name'] if pd.notna(row['clean_name']) else row['display_name']
        
        fan_wheel_data.append({
            'behavior': label_text,  # Use clean name for category label
            'COMMUNITY': label_text,
            'MERCHANT': row['top_merchant'],
            'audience_pct': audience_pct,  # For variable bar sizing
            'COMMUNITY_INDEX': audience_pct,
            'MERCHANT_INDEX': row['merchant_perc_index'] if pd.notna(row['merchant_perc_index']) else None,
            'PERC_AUDIENCE': row['category_perc_audience'] if pd.notna(row['category_perc_audience']) else None
        })
    
    result_df = pd.DataFrame(fan_wheel_data)
    
    # Randomize the order for visual variety
    result_df = result_df.sample(frac=1, random_state=42).reset_index(drop=True)
    
    logger.info(f"Prepared {len(result_df)} categories for {audience}")
    
    return result_df


def get_audience_config(audience: str) -> dict:
    """
    Get color configuration for each audience
    
    Args:
        audience: Name of the audience
        
    Returns:
        Configuration dictionary with team name and colors
    """
    configs = {
        'College Basketball Fan': {
            'team_name': 'College Basketball Fans',
            'team_name_short': 'CBB',
            'colors': {
                'primary': '#003087',     # Dark blue
                'secondary': '#FFC72C',   # Gold/Yellow
                'accent': '#87CEEB'       # Light blue
            }
        },
        'MLB Fan': {
            'team_name': 'MLB Fans',
            'team_name_short': 'MLB',
            'colors': {
                'primary': '#041E42',     # Navy blue
                'secondary': '#BF0D3E',   # Red
                'accent': '#87CEEB'       # Light blue
            }
        },
        'Super Bowl Fan': {
            'team_name': 'Super Bowl Fans',
            'team_name_short': 'SB',
            'colors': {
                'primary': '#013369',     # NFL Blue
                'secondary': '#D50A0A',   # Red
                'accent': '#87CEEB'       # Light blue
            }
        },
        'NWSL Fan': {
            'team_name': 'NWSL Fans',
            'team_name_short': 'NWSL',
            'colors': {
                'primary': '#000000',     # Black
                'secondary': '#E4002B',   # Red
                'accent': '#87CEEB'       # Light blue
            }
        },
        'MLS Fan': {
            'team_name': 'MLS Fans',
            'team_name_short': 'MLS',
            'colors': {
                'primary': '#005DAA',     # MLS Blue
                'secondary': '#E03A3E',   # Red
                'accent': '#87CEEB'       # Light blue
            }
        }
    }
    
    return configs.get(audience, {
        'team_name': audience,
        'team_name_short': audience.split()[0],
        'colors': {
            'primary': '#003366',
            'secondary': '#CC0000',
            'accent': '#87CEEB'
        }
    })


def generate_all_fan_wheels(csv_path: str = "audience_category_merchant_mapping.csv", 
                            output_dir: str = "."):
    """
    Generate fan wheels for all audiences in the CSV
    
    Args:
        csv_path: Path to the CSV file
        output_dir: Directory to save the fan wheel images
    """
    # Read CSV to get list of audiences
    df = pd.read_csv(csv_path)
    audiences = df['audience'].unique()
    
    logger.info(f"Generating fan wheels for {len(audiences)} audiences")
    
    results = {}
    
    for audience in audiences:
        logger.info(f"\n{'='*80}")
        logger.info(f"Generating fan wheel for: {audience}")
        logger.info(f"{'='*80}")
        
        # Prepare data
        fan_wheel_df = prepare_fan_wheel_data(csv_path, audience)
        
        if len(fan_wheel_df) == 0:
            logger.warning(f"Skipping {audience} - no data")
            continue
        
        # Get configuration
        config = get_audience_config(audience)
        
        # Create fan wheel
        fan_wheel = FanWheel(config, enable_logos=True)
        
        # Generate visualization
        safe_name = audience.lower().replace(' ', '_')
        output_path = Path(output_dir) / f"{safe_name}_fan_wheel.png"
        
        try:
            fan_wheel.create(
                wheel_data=fan_wheel_df,
                output_path=output_path
            )
            
            logger.info(f"✅ Saved {audience} fan wheel to {output_path}")
            results[audience] = output_path
            
            # Print preview
            print(f"\n{audience} - Categories:")
            print("-"*80)
            for idx, row in fan_wheel_df.head(10).iterrows():
                print(f"  {idx+1}. {row['behavior']:30} → {row['MERCHANT']:30} ({row['audience_pct']:.1f}%)")
            
        except Exception as e:
            logger.error(f"Failed to generate fan wheel for {audience}: {e}")
            import traceback
            traceback.print_exc()
    
    logger.info(f"\n{'='*80}")
    logger.info(f"Generated {len(results)} fan wheels")
    logger.info(f"{'='*80}")
    
    for audience, path in results.items():
        print(f"✅ {audience}: {path}")
    
    return results


if __name__ == "__main__":
    import sys
    
    # Get CSV path from command line or use default
    csv_path = sys.argv[1] if len(sys.argv) > 1 else "audience_category_merchant_mapping.csv"
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "."
    
    logger.info(f"Reading data from: {csv_path}")
    logger.info(f"Saving fan wheels to: {output_dir}")
    
    results = generate_all_fan_wheels(csv_path, output_dir)
    
    print(f"\n🎉 Complete! Generated {len(results)} fan wheels.")

