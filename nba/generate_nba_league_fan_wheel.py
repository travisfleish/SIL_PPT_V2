#!/usr/bin/env python3
"""
Generate NBA League fan wheel using NBA_LEAGUE_INSIGHTS schema
No thresholds for communities or merchants
"""

import sys
from pathlib import Path
import pandas as pd
import logging
import os
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))

from data_processors.snowflake_connector import query_to_dataframe
from visualizations.fan_wheel import FanWheel
from visualizations.community_index_chart import CommunityIndexChart
import yaml

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_top_communities(top_n: int = 10, min_perc_audience: float = 0.20) -> pd.DataFrame:
    """
    Get top N communities by composite index with PERC_AUDIENCE threshold
    """
    logger.info(f"🔍 Getting top {top_n} communities (≥{min_perc_audience*100:.0f}% threshold)...")
    
    # Temporarily set schema
    original_schema = os.getenv('SNOWFLAKE_SCHEMA')
    os.environ['SNOWFLAKE_SCHEMA'] = 'NBA_LEAGUE_INSIGHTS'
    
    try:
        query = f"""
        SELECT 
            COMMUNITY,
            COMPARISON_POPULATION,
            PERC_AUDIENCE,
            PERC_INDEX,
            SPC_INDEX,
            SPP_INDEX,
            PPC_INDEX,
            COMPOSITE_INDEX
        FROM V_NBA_LEAGUE_COMMUNITY_INDEXING_ALL_TIME
        WHERE COMPARISON_POPULATION = 'General Population'
        AND PERC_AUDIENCE >= {min_perc_audience}
        QUALIFY ROW_NUMBER() OVER (PARTITION BY COMMUNITY ORDER BY COMPOSITE_INDEX DESC) = 1
        ORDER BY COMPOSITE_INDEX DESC
        LIMIT {top_n}
        """
        
        df = query_to_dataframe(query)
        
        logger.info(f"✅ Found {len(df)} communities")
        return df
        
    finally:
        # Restore original schema
        if original_schema:
            os.environ['SNOWFLAKE_SCHEMA'] = original_schema


def get_top_merchants_for_communities(communities: list, top_n_per_community: int = 5, min_perc_audience: float = 0.05) -> pd.DataFrame:
    """
    Get top N merchants for each community with threshold, with fallback to highest if none meet threshold
    Excludes Professional Sports category for Live Entertainment Seekers
    """
    logger.info(f"🔍 Getting top {top_n_per_community} merchants per community (≥{min_perc_audience*100:.0f}% threshold, with fallback)...")
    
    # Temporarily set schema
    original_schema = os.getenv('SNOWFLAKE_SCHEMA')
    os.environ['SNOWFLAKE_SCHEMA'] = 'NBA_LEAGUE_INSIGHTS'
    
    try:
        # Escape single quotes in community names
        escaped_communities = [c.replace("'", "''") for c in communities]
        placeholders = ','.join([f"'{c}'" for c in escaped_communities])
        
        # First, try to get merchants above threshold
        query_above_threshold = f"""
        WITH ranked_merchants AS (
            SELECT 
                COMMUNITY,
                MERCHANT,
                PARENT_MERCHANT,
                CATEGORY,
                SUBCATEGORY,
                COMPARISON_POPULATION,
                PERC_AUDIENCE,
                PERC_INDEX,
                SPC_INDEX,
                SPP_INDEX,
                PPC_INDEX,
                COMPOSITE_INDEX,
                ROW_NUMBER() OVER (PARTITION BY COMMUNITY ORDER BY COMPOSITE_INDEX DESC) as rn
            FROM V_NBA_LEAGUE_GENIUS_SPORTS_COMMUNITY_MERCHANT_INDEXING_ALL_TIME
            WHERE COMMUNITY IN ({placeholders})
            AND COMPARISON_POPULATION = 'General Population'
            AND MERCHANT != 'LEVELUP'
            AND NOT (COMMUNITY = 'Live Entertainment Seekers' AND CATEGORY = 'Professional Sports')
            AND UPPER(MERCHANT) NOT LIKE '%NBA%'
            AND UPPER(PARENT_MERCHANT) NOT LIKE '%NBA%'
            AND PERC_AUDIENCE >= {min_perc_audience}
            AND COMPOSITE_INDEX <= 1000
        )
        SELECT * FROM ranked_merchants
        WHERE rn <= {top_n_per_community}
        """
        
        df_above = query_to_dataframe(query_above_threshold)
        
        # Find communities that don't have any merchants above threshold
        communities_with_merchants = set(df_above['COMMUNITY'].unique())
        communities_without = [c for c in communities if c not in communities_with_merchants]
        
        # For communities without merchants above threshold, get the top merchant regardless
        df_fallback = pd.DataFrame()
        if communities_without:
            logger.info(f"   ⚠️  {len(communities_without)} communities have no merchants ≥{min_perc_audience*100:.0f}%, using fallback...")
            escaped_fallback = [c.replace("'", "''") for c in communities_without]
            placeholders_fallback = ','.join([f"'{c}'" for c in escaped_fallback])
            
            query_fallback = f"""
            WITH ranked_merchants AS (
                SELECT 
                    COMMUNITY,
                    MERCHANT,
                    PARENT_MERCHANT,
                    CATEGORY,
                    SUBCATEGORY,
                    COMPARISON_POPULATION,
                    PERC_AUDIENCE,
                    PERC_INDEX,
                    SPC_INDEX,
                    SPP_INDEX,
                    PPC_INDEX,
                    COMPOSITE_INDEX,
                    ROW_NUMBER() OVER (PARTITION BY COMMUNITY ORDER BY COMPOSITE_INDEX DESC) as rn
                FROM V_NBA_LEAGUE_GENIUS_SPORTS_COMMUNITY_MERCHANT_INDEXING_ALL_TIME
                WHERE COMMUNITY IN ({placeholders_fallback})
                AND COMPARISON_POPULATION = 'General Population'
                AND MERCHANT != 'LEVELUP'
                AND NOT (COMMUNITY = 'Live Entertainment Seekers' AND CATEGORY = 'Professional Sports')
                AND UPPER(MERCHANT) NOT LIKE '%NBA%'
                AND UPPER(PARENT_MERCHANT) NOT LIKE '%NBA%'
                AND COMPOSITE_INDEX <= 1000
            )
            SELECT * FROM ranked_merchants
            WHERE rn = 1
            """
            
            df_fallback = query_to_dataframe(query_fallback)
            
            for community in communities_without:
                comm_merchants = df_fallback[df_fallback['COMMUNITY'] == community]
                if not comm_merchants.empty:
                    top_merchant = comm_merchants.iloc[0]
                    logger.info(f"      {community}: {top_merchant['MERCHANT']} ({top_merchant['PERC_AUDIENCE']*100:.2f}%)")
        
        # Combine results
        df = pd.concat([df_above, df_fallback], ignore_index=True)
        df = df.sort_values(['COMMUNITY', 'COMPOSITE_INDEX'], ascending=[True, False])
        
        logger.info(f"✅ Found {len(df)} merchants across {df['COMMUNITY'].nunique()} communities")
        return df
        
    finally:
        # Restore original schema
        if original_schema:
            os.environ['SNOWFLAKE_SCHEMA'] = original_schema


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


def get_fan_wheel_data(top_n_communities: int = 10) -> pd.DataFrame:
    """
    Get fan wheel data for NBA League (no thresholds)
    
    Args:
        top_n_communities: Number of top communities to include
        
    Returns:
        DataFrame formatted for fan wheel
    """
    # Get all communities with 20% threshold, then filter to only those with merchants ≥5%
    logger.info("\n🔍 Getting communities (≥20% threshold, filtering to those with merchants ≥5%)...")
    
    # Get all communities meeting 20% threshold
    all_communities_df = get_top_communities(top_n=100, min_perc_audience=0.20)  # Get more to filter from
    
    if all_communities_df.empty:
        raise ValueError("No communities found")
    
    logger.info(f"✅ Found {len(all_communities_df)} total communities meeting 20% threshold")
    
    # Filter to only communities that have merchants ≥5% (excluding NBA)
    communities_with_merchants = []
    
    for idx, comm_row in all_communities_df.iterrows():
        community = comm_row['COMMUNITY']
        escaped_comm = community.replace("'", "''")
        
        # Temporarily set schema
        original_schema = os.getenv('SNOWFLAKE_SCHEMA')
        os.environ['SNOWFLAKE_SCHEMA'] = 'NBA_LEAGUE_INSIGHTS'
        
        try:
            # Check if this community has any merchants ≥5%
            check_query = f"""
            SELECT COUNT(*) as cnt
            FROM V_NBA_LEAGUE_GENIUS_SPORTS_COMMUNITY_MERCHANT_INDEXING_ALL_TIME
            WHERE COMMUNITY = '{escaped_comm}'
            AND COMPARISON_POPULATION = 'General Population'
            AND MERCHANT != 'LEVELUP'
            AND NOT (COMMUNITY = 'Live Entertainment Seekers' AND CATEGORY = 'Professional Sports')
            AND UPPER(MERCHANT) NOT LIKE '%NBA%'
            AND UPPER(PARENT_MERCHANT) NOT LIKE '%NBA%'
            AND PERC_AUDIENCE >= 0.05
            """
            
            check_df = query_to_dataframe(check_query)
            merchant_count = check_df['CNT'].iloc[0]
            
            if merchant_count > 0:
                communities_with_merchants.append(comm_row)
                logger.info(f"   ✓ {community} ({merchant_count} merchants ≥5%)")
                
                if len(communities_with_merchants) >= top_n_communities:
                    break
            else:
                logger.info(f"   ✗ {community} (no merchants ≥5%, skipping)")
        finally:
            if original_schema:
                os.environ['SNOWFLAKE_SCHEMA'] = original_schema
    
    communities_df = pd.DataFrame(communities_with_merchants)
    
    if communities_df.empty:
        raise ValueError("No communities found with merchants ≥5%")
    
    community_names = communities_df['COMMUNITY'].tolist()
    
    logger.info(f"\n📊 Selected {len(community_names)} communities with merchants ≥5%:")
    for idx, row in communities_df.iterrows():
        logger.info(f"   {idx+1}. {row['COMMUNITY']} (Index: {row['COMPOSITE_INDEX']:.1f})")
    
    # Get merchants for these communities (5% threshold, no fallback needed since we filtered)
    merchants_df = get_top_merchants_for_communities(community_names, top_n_per_community=5, min_perc_audience=0.05)
    
    # Merge community data with merchant data
    merged = merchants_df.merge(
        communities_df[['COMMUNITY', 'PERC_INDEX', 'COMPOSITE_INDEX']].rename(
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
    
    # Sort by community composite index, then merchant COMPOSITE_INDEX
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
    
    return result_df, communities_df


def main():
    """Generate NBA League fan wheel with no thresholds"""
    logger.info("="*80)
    logger.info("NBA LEAGUE FAN WHEEL GENERATOR")
    logger.info("Schema: NBA_LEAGUE_INSIGHTS (ALL_TIME views)")
    logger.info("Comparison Population: General Population")
    logger.info("20% threshold for communities")
    logger.info("5% threshold for merchants (with fallback to highest if none meet threshold)")
    logger.info("Excluding Professional Sports category for Live Entertainment Seekers")
    logger.info("="*80)
    
    # Get fan wheel data
    logger.info("\n1️⃣ Fetching NBA League fan wheel data (20% community, 5% merchant thresholds)...")
    wheel_data, communities_df = get_fan_wheel_data(top_n_communities=10)
    
    logger.info(f"\n✅ Generated fan wheel data with {len(wheel_data)} communities")
    logger.info("\n📊 Fan Wheel Data:")
    for idx, row in wheel_data.iterrows():
        logger.info(f"   {idx+1}. {row['COMMUNITY']}: {row['behavior']} (Index: {row['PERC_INDEX']:.1f})")
    
    # Create team config for NBA with custom colors
    nba_config = {
        'team_name': 'NBA Fans',
        'team_name_short': 'NBA',
        'colors': {
            'primary': '#0A08D9',  # Bright Electric Blue
            'secondary': '#DBF66F',  # Neon Yellow-Green
            'accent': '#DBF66F'  # Neon Yellow-Green
        }
    }
    
    # Generate fan wheel
    logger.info("\n2️⃣ Generating fan wheel visualization...")
    fan_wheel = FanWheel(nba_config, enable_logos=True)
    output_path = Path('nba_league_fan_wheel.png')
    
    fan_wheel.create(wheel_data, output_path, team_logo=None)
    
    logger.info(f"\n✅ Fan wheel saved to: {output_path}")
    
    # Generate community index chart
    logger.info("\n3️⃣ Generating community index chart...")
    
    # Prepare data for community index chart
    chart_data = communities_df.copy()
    chart_data = chart_data.rename(columns={
        'COMMUNITY': 'Community',
        'PERC_AUDIENCE': 'Audience_Pct',
        'COMPOSITE_INDEX': 'Composite_Index'
    })
    
    # Convert PERC_AUDIENCE to percentage if needed
    if chart_data['Audience_Pct'].max() <= 1.0:
        chart_data['Audience_Pct'] = chart_data['Audience_Pct'] * 100
    
    # Create chart with custom colors
    chart = CommunityIndexChart(team_colors=nba_config['colors'])
    chart_output_path = Path('nba_league_community_index_chart.png')
    chart.create(chart_data, chart_output_path, title='NBA League Community Index')
    
    logger.info(f"\n✅ Community index chart saved to: {chart_output_path}")
    logger.info("="*80)


if __name__ == "__main__":
    main()

