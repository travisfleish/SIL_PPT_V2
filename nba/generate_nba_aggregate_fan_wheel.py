#!/usr/bin/env python3
"""
Generate NBA aggregate fan wheel by aggregating all 30 NBA teams
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import logging

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from data_processors.snowflake_connector import query_to_dataframe
from visualizations.fan_wheel import FanWheel
import yaml

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def aggregate_nba_communities() -> pd.DataFrame:
    """
    Aggregate community data across all NBA teams (no threshold)
    
    Returns:
        DataFrame with aggregated community data
    """
    logger.info("🔍 Aggregating NBA community data across all teams (no threshold)...")
    
    query = """
    SELECT 
        COMMUNITY,
        COMPARISON_POPULATION,
        -- Aggregate counts (weighted by team size)
        SUM(AUDIENCE_COUNT) as AUDIENCE_COUNT,
        SUM(TOTAL_AUDIENCE_COUNT) as TOTAL_AUDIENCE_COUNT,
        -- Recalculate percentages from aggregated data
        SUM(AUDIENCE_COUNT) / NULLIF(SUM(TOTAL_AUDIENCE_COUNT), 0) as PERC_AUDIENCE,
        -- Aggregate transactions and spend
        SUM(AUDIENCE_TRANSACTIONS) as AUDIENCE_TRANSACTIONS,
        SUM(AUDIENCE_TOTAL_SPEND) as AUDIENCE_TOTAL_SPEND,
        -- Recalculate metrics
        SUM(AUDIENCE_TOTAL_SPEND) / NULLIF(SUM(AUDIENCE_COUNT), 0) as SPC,
        SUM(AUDIENCE_TOTAL_SPEND) / NULLIF(SUM(TOTAL_AUDIENCE_COUNT), 0) as SPP,
        SUM(AUDIENCE_TRANSACTIONS) / NULLIF(SUM(AUDIENCE_COUNT), 0) as PPC,
        -- Comparison metrics (should be same across all teams for General Population)
        MAX(COMPARISON_COUNT) as COMPARISON_COUNT,
        MAX(COMPARISON_TOTAL_COUNT) as COMPARISON_TOTAL_COUNT,
        MAX(PERC_COMPARISON) as PERC_COMPARISON,
        MAX(COMPARISON_TOTAL_SPEND) as COMPARISON_TOTAL_SPEND,
        MAX(COMPARISON_SPC) as COMPARISON_SPC,
        MAX(COMPARISON_SPP) as COMPARISON_SPP,
        MAX(COMPARISON_PPC) as COMPARISON_PPC,
        -- Recalculate indexes from aggregated data
        (SUM(AUDIENCE_COUNT) / NULLIF(SUM(TOTAL_AUDIENCE_COUNT), 0)) / 
        NULLIF(MAX(PERC_COMPARISON), 0) * 100 as PERC_INDEX,
        (SUM(AUDIENCE_TOTAL_SPEND) / NULLIF(SUM(AUDIENCE_COUNT), 0)) / 
        NULLIF(MAX(COMPARISON_SPC), 0) * 100 as SPC_INDEX,
        (SUM(AUDIENCE_TOTAL_SPEND) / NULLIF(SUM(TOTAL_AUDIENCE_COUNT), 0)) / 
        NULLIF(MAX(COMPARISON_SPP), 0) * 100 as SPP_INDEX,
        (SUM(AUDIENCE_TRANSACTIONS) / NULLIF(SUM(AUDIENCE_COUNT), 0)) / 
        NULLIF(MAX(COMPARISON_PPC), 0) * 100 as PPC_INDEX,
        -- Composite index (average of the four indexes)
        ((SUM(AUDIENCE_COUNT) / NULLIF(SUM(TOTAL_AUDIENCE_COUNT), 0)) / NULLIF(MAX(PERC_COMPARISON), 0) * 100 +
         (SUM(AUDIENCE_TOTAL_SPEND) / NULLIF(SUM(AUDIENCE_COUNT), 0)) / NULLIF(MAX(COMPARISON_SPC), 0) * 100 +
         (SUM(AUDIENCE_TOTAL_SPEND) / NULLIF(SUM(TOTAL_AUDIENCE_COUNT), 0)) / NULLIF(MAX(COMPARISON_SPP), 0) * 100 +
         (SUM(AUDIENCE_TRANSACTIONS) / NULLIF(SUM(AUDIENCE_COUNT), 0)) / NULLIF(MAX(COMPARISON_PPC), 0) * 100) / 4.0 as COMPOSITE_INDEX
    FROM NBA_SIL_COMMUNITY_INDEXING_SNAPSHOT
    WHERE COMPARISON_POPULATION = 'General Population'
    GROUP BY COMMUNITY, COMPARISON_POPULATION
    ORDER BY COMPOSITE_INDEX DESC
    """
    df = query_to_dataframe(query)
    
    logger.info(f"✅ Found {len(df)} communities (no threshold)")
    return df


def aggregate_nba_community_merchants(communities: list, top_n_per_community: int = 5, min_merchant_perc_audience: float = 0.0) -> pd.DataFrame:
    """
    Aggregate merchant data for specific communities across all NBA teams
    
    Args:
        communities: List of community names
        top_n_per_community: Number of top merchants to get per community
        
    Returns:
        DataFrame with aggregated merchant data
    """
    logger.info(f"🔍 Aggregating merchant data for {len(communities)} communities...")
    
    # Create placeholders for IN clause
    placeholders = ','.join([f"'{c}'" for c in communities])
    
    query = f"""
    WITH aggregated_merchants AS (
        SELECT 
            COMMUNITY,
            MERCHANT,
            PARENT_MERCHANT,
            CATEGORY,
            COMPARISON_POPULATION,
            -- Aggregate counts
            SUM(AUDIENCE_COUNT) as AUDIENCE_COUNT,
            SUM(TOTAL_AUDIENCE_COUNT) as TOTAL_AUDIENCE_COUNT,
            SUM(AUDIENCE_COUNT) / NULLIF(SUM(TOTAL_AUDIENCE_COUNT), 0) as PERC_AUDIENCE,
            -- Aggregate transactions and spend
            SUM(AUDIENCE_TRANSACTIONS) as AUDIENCE_TRANSACTIONS,
            SUM(AUDIENCE_TOTAL_SPEND) as AUDIENCE_TOTAL_SPEND,
            -- Recalculate metrics
            SUM(AUDIENCE_TOTAL_SPEND) / NULLIF(SUM(AUDIENCE_COUNT), 0) as SPC,
            SUM(AUDIENCE_TOTAL_SPEND) / NULLIF(SUM(TOTAL_AUDIENCE_COUNT), 0) as SPP,
            SUM(AUDIENCE_TRANSACTIONS) / NULLIF(SUM(AUDIENCE_COUNT), 0) as PPC,
            -- Comparison metrics
            MAX(COMPARISON_COUNT) as COMPARISON_COUNT,
            MAX(COMPARISON_TOTAL_COUNT) as COMPARISON_TOTAL_COUNT,
            MAX(PERC_COMPARISON) as PERC_COMPARISON,
            MAX(COMPARISON_TOTAL_SPEND) as COMPARISON_TOTAL_SPEND,
            MAX(COMPARISON_SPC) as COMPARISON_SPC,
            MAX(COMPARISON_SPP) as COMPARISON_SPP,
            MAX(COMPARISON_PPC) as COMPARISON_PPC,
            -- Recalculate indexes
            (SUM(AUDIENCE_COUNT) / NULLIF(SUM(TOTAL_AUDIENCE_COUNT), 0)) / 
            NULLIF(MAX(PERC_COMPARISON), 0) * 100 as PERC_INDEX,
            (SUM(AUDIENCE_TOTAL_SPEND) / NULLIF(SUM(AUDIENCE_COUNT), 0)) / 
            NULLIF(MAX(COMPARISON_SPC), 0) * 100 as SPC_INDEX,
            (SUM(AUDIENCE_TOTAL_SPEND) / NULLIF(SUM(TOTAL_AUDIENCE_COUNT), 0)) / 
            NULLIF(MAX(COMPARISON_SPP), 0) * 100 as SPP_INDEX,
            (SUM(AUDIENCE_TRANSACTIONS) / NULLIF(SUM(AUDIENCE_COUNT), 0)) / 
            NULLIF(MAX(COMPARISON_PPC), 0) * 100 as PPC_INDEX,
            -- Composite index
            ((SUM(AUDIENCE_COUNT) / NULLIF(SUM(TOTAL_AUDIENCE_COUNT), 0)) / NULLIF(MAX(PERC_COMPARISON), 0) * 100 +
             (SUM(AUDIENCE_TOTAL_SPEND) / NULLIF(SUM(AUDIENCE_COUNT), 0)) / NULLIF(MAX(COMPARISON_SPC), 0) * 100 +
             (SUM(AUDIENCE_TOTAL_SPEND) / NULLIF(SUM(TOTAL_AUDIENCE_COUNT), 0)) / NULLIF(MAX(COMPARISON_SPP), 0) * 100 +
             (SUM(AUDIENCE_TRANSACTIONS) / NULLIF(SUM(AUDIENCE_COUNT), 0)) / NULLIF(MAX(COMPARISON_PPC), 0) * 100) / 4.0 as COMPOSITE_INDEX
        FROM NBA_SIL_COMMUNITY_MERCHANT_INDEXING_SNAPSHOT
        WHERE COMPARISON_POPULATION = 'General Population'
        AND COMMUNITY IN ({placeholders})
        AND MERCHANT != 'LEVELUP'  -- Exclude LEVELUP
        AND NOT (COMMUNITY = 'Live Entertainment Seekers' AND CATEGORY = 'Professional Sports')
        GROUP BY COMMUNITY, MERCHANT, PARENT_MERCHANT, CATEGORY, COMPARISON_POPULATION
        HAVING SUM(AUDIENCE_COUNT) >= 10  -- Minimum audience count
        AND SUM(AUDIENCE_COUNT) / NULLIF(SUM(TOTAL_AUDIENCE_COUNT), 0) >= {min_merchant_perc_audience}
    ),
    ranked_merchants AS (
        SELECT 
            *,
            ROW_NUMBER() OVER (PARTITION BY COMMUNITY ORDER BY COMPOSITE_INDEX DESC) as rn
        FROM aggregated_merchants
    )
    SELECT * FROM ranked_merchants
    WHERE rn <= {top_n_per_community}
    ORDER BY COMMUNITY, COMPOSITE_INDEX DESC
    """
    df = query_to_dataframe(query)
    
    logger.info(f"✅ Found {len(df)} merchants across {df['COMMUNITY'].nunique()} communities")
    return df


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


def generate_behavior_text(community: str, merchant: str, community_actions: dict) -> str:
    """Generate behavior text from community and merchant"""
    action = community_actions.get(community, "Engage with")
    return f"{action} {merchant}"


def get_fan_wheel_data(top_n_communities: int = 10, min_merchant_perc_audience: float = 0.0) -> pd.DataFrame:
    """
    Get fan wheel data for NBA aggregate
    
    Args:
        min_audience_pct: Minimum audience percentage threshold
        top_n_communities: Number of top communities to include
        
    Returns:
        DataFrame formatted for fan wheel
    """
    # Get top communities (no threshold)
    communities_df = aggregate_nba_communities()
    
    if communities_df.empty:
        raise ValueError("No communities found matching criteria")
    
    # Take top N communities
    top_communities = communities_df.head(top_n_communities)
    community_names = top_communities['COMMUNITY'].tolist()
    
    logger.info(f"📊 Top {len(community_names)} communities:")
    for idx, row in top_communities.iterrows():
        logger.info(f"   {idx+1}. {row['COMMUNITY']} (Index: {row['COMPOSITE_INDEX']:.1f})")
    
    # Get merchants for these communities
    merchants_df = aggregate_nba_community_merchants(community_names, top_n_per_community=5, min_merchant_perc_audience=min_merchant_perc_audience)
    
    # Merge community data with merchant data
    merged = merchants_df.merge(
        top_communities[['COMMUNITY', 'PERC_INDEX', 'COMPOSITE_INDEX']].rename(
            columns={
                'PERC_INDEX': 'COMMUNITY_PERC_INDEX',
                'COMPOSITE_INDEX': 'COMMUNITY_COMPOSITE_INDEX'
            }
        ),
        on='COMMUNITY',
        how='left'
    )
    
    # Select one merchant per community (greedy selection to avoid duplicates)
    selected_merchants = {}
    used_merchants = set()
    
    # Sort by community composite index, then merchant composite index
    merged = merged.sort_values(['COMMUNITY_COMPOSITE_INDEX', 'COMPOSITE_INDEX'], ascending=[False, False])
    
    for _, row in merged.iterrows():
        community = row['COMMUNITY']
        merchant = row['MERCHANT']
        
        if community not in selected_merchants and merchant not in used_merchants:
            selected_merchants[community] = row
            used_merchants.add(merchant)
        
        if len(selected_merchants) >= len(community_names):
            break
    
    # If we still have communities without merchants, allow duplicates
    for _, row in merged.iterrows():
        community = row['COMMUNITY']
        if community not in selected_merchants:
            selected_merchants[community] = row
    
    # Build result DataFrame
    result_data = []
    community_actions = load_approved_communities()
    
    for community, row in selected_merchants.items():
        result_data.append({
            'COMMUNITY': community,
            'MERCHANT': row['MERCHANT'],
            'PERC_INDEX': row['COMMUNITY_PERC_INDEX'],
            'PERC_AUDIENCE': row['PERC_AUDIENCE'],
            'behavior': generate_behavior_text(community, row['MERCHANT'], community_actions)
        })
    
    result_df = pd.DataFrame(result_data)
    result_df = result_df.sort_values('PERC_INDEX', ascending=False).reset_index(drop=True)
    
    return result_df


def main():
    """Generate NBA aggregate fan wheel with different merchant thresholds"""
    
    # Create team config for NBA
    nba_config = {
        'team_name': 'NBA Fans',
        'team_name_short': 'NBA',
        'colors': {
            'primary': '#C8102E',  # NBA Red
            'secondary': '#1D428A',  # NBA Blue
            'accent': '#FDB927'  # NBA Gold
        }
    }
    
    # Generate fan wheel with 2% merchant threshold
    logger.info("="*80)
    logger.info("NBA AGGREGATE FAN WHEEL GENERATOR - 2% MERCHANT THRESHOLD")
    logger.info("Excluding Professional Sports category for Live Entertainment Seekers")
    logger.info("="*80)
    
    logger.info("\n1️⃣ Fetching aggregated NBA fan wheel data (2% merchant threshold, no community threshold)...")
    wheel_data = get_fan_wheel_data(top_n_communities=10, min_merchant_perc_audience=0.02)
    
    logger.info(f"\n✅ Generated fan wheel data with {len(wheel_data)} communities")
    logger.info("\n📊 Fan Wheel Data (2% merchant threshold):")
    for idx, row in wheel_data.iterrows():
        logger.info(f"   {idx+1}. {row['COMMUNITY']}: {row['behavior']} (Index: {row['PERC_INDEX']:.1f})")
    
    logger.info("\n2️⃣ Generating fan wheel visualization (2% merchant threshold)...")
    fan_wheel = FanWheel(nba_config, enable_logos=True)
    output_path = Path('nba_aggregate_fan_wheel_2pct_merchant.png')
    fan_wheel.create(wheel_data, output_path, team_logo=None)
    logger.info(f"\n✅ Fan wheel saved to: {output_path}")
    logger.info("="*80)


if __name__ == "__main__":
    main()

