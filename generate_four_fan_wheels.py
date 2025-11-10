#!/usr/bin/env python3
"""
Generate fan wheel visualizations for MLB, MLS, NWSL, and Super Bowl audiences
"""

import pandas as pd
from visualizations.fan_wheel_standalone import FanWheel
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_audience_config(audience: str) -> dict:
    """Get color configuration for each audience"""
    configs = {
        'MLB Fan': {
            'team_name': 'MLB Fans',
            'team_name_short': 'MLB',
            'colors': {
                'primary': '#041E42',     # Navy blue
                'secondary': '#BF0D3E',   # Red
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
        'Super Bowl Fan': {
            'team_name': 'Super Bowl Fans',
            'team_name_short': 'SB',
            'colors': {
                'primary': '#013369',     # NFL Blue
                'secondary': '#D50A0A',   # Red
                'accent': '#87CEEB'       # Light blue
            }
        }
    }
    return configs.get(audience, {})


def prepare_fan_wheel_data(csv_path: str, audience: str) -> pd.DataFrame:
    """
    Load and prepare fan wheel data for a specific audience from the comprehensive CSV
    
    Args:
        csv_path: Path to audience_category_merchant_mapping.csv
        audience: Name of the audience to generate for
        
    Returns:
        DataFrame formatted for fan wheel generation
    """
    # Read the comprehensive CSV
    df = pd.read_csv(csv_path)
    
    # Filter for the specific audience
    audience_df = df[df['audience'] == audience].copy()
    
    if len(audience_df) == 0:
        logger.error(f"No data found for audience: {audience}")
        return pd.DataFrame()
    
    # Prepare data in the format expected by fan wheel
    fan_wheel_data = []
    
    for _, row in audience_df.iterrows():
        # Always use merchant_perc_audience for bar sizing (shows merchant performance)
        if pd.notna(row['merchant_perc_audience']):
            audience_pct = row['merchant_perc_audience'] * 100
        else:
            audience_pct = 50.0  # Fallback default if merchant data is missing
        
        # Use clean_name for the label (shorter, cleaner text)
        label_text = row['clean_name'] if pd.notna(row['clean_name']) else row['display_name']
        
        fan_wheel_data.append({
            'behavior': label_text,  # Use clean name for category label
            'COMMUNITY': label_text,
            'MERCHANT': row['top_merchant'],
            'audience_pct': audience_pct,  # For variable bar sizing - shows merchant audience
            'COMMUNITY_INDEX': row['category_perc_index'] if pd.notna(row['category_perc_index']) else None,
            'MERCHANT_INDEX': row['merchant_perc_index'] if pd.notna(row['merchant_perc_index']) else None,
            'PERC_AUDIENCE': row['merchant_perc_audience']  # Store merchant percentage
        })
    
    result_df = pd.DataFrame(fan_wheel_data)
    
    logger.info(f"Prepared {len(result_df)} categories for {audience}")
    
    return result_df


def generate_fan_wheels(csv_path: str = "audience_category_merchant_mapping.csv", 
                        output_dir: str = "output/fan_wheels_test"):
    """
    Generate fan wheels for MLB, MLS, NWSL, and Super Bowl audiences
    
    Args:
        csv_path: Path to the audience_category_merchant_mapping.csv file
        output_dir: Directory to save the fan wheel images
    """
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Define the four audiences
    audiences = ['MLB Fan', 'MLS Fan', 'NWSL Fan', 'Super Bowl Fan']
    
    results = {}
    
    for audience in audiences:
        logger.info(f"\n{'='*80}")
        logger.info(f"Generating fan wheel for: {audience}")
        logger.info(f"{'='*80}")
        
        try:
            # Load data from comprehensive CSV
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
            output_file = output_path / f"{safe_name}_visualization.png"
            
            fan_wheel.create(
                wheel_data=fan_wheel_df,
                output_path=output_file
            )
            
            logger.info(f"✅ Saved {audience} fan wheel to {output_file}")
            results[audience] = output_file
            
            # Print preview
            print(f"\n{audience} - Top Categories:")
            print("-"*80)
            for idx, row in fan_wheel_df.head(5).iterrows():
                merchant = row.get('MERCHANT', 'N/A')
                print(f"  {idx+1}. {row['COMMUNITY']:30} → {merchant:30} ({row['audience_pct']:.1f}%)")
            
        except Exception as e:
            logger.error(f"❌ Failed to generate fan wheel for {audience}: {e}")
            import traceback
            traceback.print_exc()
    
    logger.info(f"\n{'='*80}")
    logger.info(f"Summary: Generated {len(results)}/{len(audiences)} fan wheels")
    logger.info(f"Output directory: {output_path.absolute()}")
    logger.info(f"{'='*80}")
    
    for audience, path in results.items():
        print(f"✅ {audience}: {path}")
    
    return results


if __name__ == "__main__":
    import sys
    
    # Get CSV path and output directory from command line or use defaults
    csv_path = sys.argv[1] if len(sys.argv) > 1 else "audience_category_merchant_mapping.csv"
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "output/fan_wheels_test"
    
    logger.info(f"Starting fan wheel generation")
    logger.info(f"Data source: {csv_path}")
    logger.info(f"Output directory: {output_dir}")
    
    results = generate_fan_wheels(csv_path, output_dir)
    
    print(f"\n🎉 Complete! Generated {len(results)} fan wheels in {output_dir}")

