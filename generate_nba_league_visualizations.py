#!/usr/bin/env python3
"""
Generate NBA League Fan Wheel and Community Index Chart
Using the specified communities and merchants
"""

import sys
from pathlib import Path
import pandas as pd
import logging
import yaml
import asyncio

sys.path.insert(0, str(Path(__file__).parent))

from visualizations.fan_wheel import FanWheel
from visualizations.community_index_chart import CommunityIndexChart
from utils.merchant_name_standardizer import MerchantNameStandardizer
import matplotlib.pyplot as plt

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_approved_communities() -> dict:
    """Load approved communities and their action verbs"""
    try:
        config_path = Path(__file__).parent / 'config' / 'approved_communities.yaml'
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        community_actions = {}
        for community in config['approved_communities']:
            community_actions[community['name']] = community['action']
        
        return community_actions
    except Exception as e:
        logger.warning(f"Could not load approved communities: {e}")
        return {}


def generate_behavior_text(community: str, merchant: str, community_actions: dict, original_merchant: str = None) -> str:
    """Generate behavior text from community and merchant"""
    # Custom behavior texts (check both original and standardized names)
    custom_behaviors = {
        'GoFan': 'Buys on GoFan',
        "Dave & Buster's": 'Enjoys Dave & Busters',
        "DAVE & BUSTER'S": 'Enjoys Dave & Busters'  # Also check original
    }
    
    # Check if merchant (standardized) or original has custom behavior
    if merchant in custom_behaviors:
        return custom_behaviors[merchant]
    if original_merchant and original_merchant in custom_behaviors:
        return custom_behaviors[original_merchant]
    
    # Otherwise use standard action
    action = community_actions.get(community, "Engage with")
    return f"{action} {merchant}"


def main():
    """Generate NBA League visualizations"""
    logger.info("="*100)
    logger.info("NBA LEAGUE VISUALIZATION GENERATOR")
    logger.info("="*100)
    
    # Load community data
    community_data_path = Path('nba_league_community_index_chart_data.csv')
    if not community_data_path.exists():
        raise FileNotFoundError(f"Community data file not found: {community_data_path}")
    
    communities_df = pd.read_csv(community_data_path)
    logger.info(f"✅ Loaded {len(communities_df)} communities from CSV")
    
    # Define the specific community-merchant pairs
    community_merchant_pairs = [
        ('Live Entertainment Seekers', "DAVE & BUSTER'S"),
        ('Sports Merchandise Shopper', 'Rally House'),
        ('Sportstainment', 'TOPGOLF'),
        ('Youth Sports', 'GoFan'),
        ('Travelers', 'MARRIOTT'),
        ('Trend Setters', 'Skims'),
        ('Fitness Enthusiasts', 'PLANET FITNESS'),
        ('Movie Buffs', 'AMC THEATRES'),
        ('Theme Parkers', 'DISNEYLAND RESORT'),
        ('Casual Outdoor Enthusiasts', 'REI')
    ]
    
    logger.info("\n📋 Community-Merchant Pairs:")
    for comm, merch in community_merchant_pairs:
        logger.info(f"   {comm} → {merch}")
    
    # Load approved communities for behavior text
    community_actions = load_approved_communities()
    
    # Standardize merchant names
    logger.info("\n🔄 Standardizing merchant names...")
    merchant_names = [merchant for _, merchant in community_merchant_pairs]
    
    standardizer = MerchantNameStandardizer(cache_enabled=True)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        name_mapping = loop.run_until_complete(standardizer.standardize_merchants(merchant_names))
        logger.info("✅ Merchant names standardized")
        
        # Log standardization results
        for original, standardized in name_mapping.items():
            if original != standardized:
                logger.info(f"   {original} → {standardized}")
    finally:
        loop.close()
    
    # Build fan wheel data with standardized names
    wheel_data_list = []
    for community, merchant in community_merchant_pairs:
        # Find community data
        comm_row = communities_df[communities_df['COMMUNITY'] == community]
        if comm_row.empty:
            logger.warning(f"⚠️  Community not found in data: {community}")
            continue
        
        comm_data = comm_row.iloc[0]
        
        # Use standardized merchant name
        standardized_merchant = name_mapping.get(merchant, merchant)
        # Pass both original and standardized to handle custom behaviors
        behavior = generate_behavior_text(community, standardized_merchant, community_actions, original_merchant=merchant)
        
        wheel_data_list.append({
            'COMMUNITY': community,
            'MERCHANT': standardized_merchant,
            'behavior': behavior,
            'PERC_INDEX': comm_data['PERC_INDEX']
        })
    
    wheel_data = pd.DataFrame(wheel_data_list)
    
    # Sort by PERC_INDEX descending for proper wheel ordering
    wheel_data = wheel_data.sort_values('PERC_INDEX', ascending=False).reset_index(drop=True)
    
    logger.info(f"\n✅ Prepared {len(wheel_data)} items for fan wheel")
    
    # Create NBA team config
    nba_config = {
        'team_name': 'NBA Fans',
        'team_name_short': 'NBA',
        'colors': {
            'primary': '#0A08D9',  # Bright Electric Blue
            'secondary': '#DBF66F',  # Neon Yellow-Green
            'accent': '#DBF66F'  # Neon Yellow-Green
        }
    }
    
    # Generate Fan Wheel with transparent background
    logger.info("\n" + "="*100)
    logger.info("GENERATING FAN WHEEL (TRANSPARENT BACKGROUND)")
    logger.info("="*100)
    
    fan_wheel = FanWheel(nba_config, enable_logos=True)
    fan_wheel_path = Path('nba_league_fan_wheel.png')
    
    # Override the create method to use transparent background
    # Create figure with transparent background
    dpi = 150 if fan_wheel.enable_logos else 100
    fig = plt.figure(figsize=(12, 12), facecolor='none', dpi=dpi)
    ax = fig.add_subplot(111, aspect='equal')
    
    # Set limits
    margin = 0.3
    limit = fan_wheel.outer_radius + margin
    ax.set_xlim(-limit, limit)
    ax.set_ylim(-limit, limit)
    ax.axis('off')
    
    # Make the axes background transparent
    ax.patch.set_alpha(0.0)
    fig.patch.set_alpha(0.0)
    
    num_items = len(wheel_data)
    angle_step = 360 / num_items
    
    # Draw all elements
    fan_wheel._draw_wedges(ax, num_items, angle_step)
    fan_wheel._add_dividing_lines(ax, num_items, angle_step)
    fan_wheel._add_arrows(ax, num_items, angle_step)
    fan_wheel._draw_center_circle(ax, team_logo=None)
    fan_wheel._add_segment_content(ax, wheel_data, angle_step)
    
    # Save with transparent background
    plt.tight_layout()
    plt.savefig(fan_wheel_path, dpi=300, bbox_inches='tight',
                facecolor='none', edgecolor='none',
                pad_inches=0.05, transparent=True)
    plt.close()
    
    logger.info(f"✅ Fan wheel saved to: {fan_wheel_path}")
    
    # Prepare community index chart data
    logger.info("\n" + "="*100)
    logger.info("GENERATING COMMUNITY INDEX CHART")
    logger.info("="*100)
    
    # Filter to only the selected communities
    selected_communities = [comm for comm, _ in community_merchant_pairs]
    chart_data = communities_df[communities_df['COMMUNITY'].isin(selected_communities)].copy()
    
    # Rename columns to match chart expectations
    chart_data = chart_data.rename(columns={
        'COMMUNITY': 'Community',
        'PERC_AUDIENCE_PCT': 'Audience_Pct',
        'COMPOSITE_INDEX': 'Composite_Index'
    })
    
    # Ensure Audience_Pct is in percentage format (0-100)
    if chart_data['Audience_Pct'].max() <= 1.0:
        chart_data['Audience_Pct'] = chart_data['Audience_Pct'] * 100
    
    logger.info(f"✅ Prepared {len(chart_data)} communities for chart")
    
    # Generate Community Index Chart
    chart = CommunityIndexChart(team_colors=nba_config['colors'])
    chart_path = Path('nba_league_community_index_chart.png')
    
    chart.create(chart_data, chart_path, title='NBA League Community Index')
    logger.info(f"✅ Community index chart saved to: {chart_path}")
    
    # Summary
    logger.info("\n" + "="*100)
    logger.info("✅ VISUALIZATION GENERATION COMPLETE")
    logger.info("="*100)
    logger.info("\n📁 Files Created:")
    logger.info(f"   1. {fan_wheel_path}")
    logger.info(f"   2. {chart_path}")
    logger.info("="*100)


if __name__ == "__main__":
    main()

