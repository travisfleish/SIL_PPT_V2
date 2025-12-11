#!/usr/bin/env python3
"""
Export NBA League visualization data to CSV
Shows the data used for Community Index Chart and Fan Wheel visualizations
If a community doesn't have merchants ≥5%, replace it with next highest community that does
"""

import sys
from pathlib import Path
import pandas as pd
import logging
import os
from dotenv import load_dotenv
import yaml

sys.path.insert(0, str(Path(__file__).parent))

from data_processors.snowflake_connector import query_to_dataframe

load_dotenv()

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


def generate_behavior_text(community: str, merchant: str, community_actions: dict) -> str:
    """Generate behavior text from community and merchant"""
    action = community_actions.get(community, "Engage with")
    return f"{action} {merchant}"


def get_communities_with_merchants(top_n: int = 10, min_perc_audience: float = 0.20, min_merchant_perc: float = 0.05):
    """
    Get top N communities that have merchants meeting the threshold
    If a community doesn't have merchants ≥5%, replace it with next highest that does
    """
    logger.info("="*100)
    logger.info("STEP 1: GETTING COMMUNITIES WITH MERCHANTS ≥5%")
    logger.info("="*100)
    
    original_schema = os.getenv('SNOWFLAKE_SCHEMA')
    os.environ['SNOWFLAKE_SCHEMA'] = 'NBA_LEAGUE_INSIGHTS'
    
    try:
        # First, get all communities meeting 20% threshold, ordered by composite index
        logger.info(f"\n📊 Getting all communities (≥{min_perc_audience*100:.0f}% threshold, ordered by composite index)...")
        
        query = f"""
        SELECT 
            COMMUNITY,
            COMPARISON_POPULATION,
            PERC_AUDIENCE,
            PERC_AUDIENCE * 100 as PERC_AUDIENCE_PCT,
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
        """
        
        all_communities_df = query_to_dataframe(query)
        logger.info(f"✅ Found {len(all_communities_df)} total communities meeting {min_perc_audience*100:.0f}% threshold")
        
        # Now filter to only communities that have merchants ≥5%
        logger.info(f"\n🔍 Filtering to communities with merchants ≥{min_merchant_perc*100:.0f}%...")
        selected_communities = []
        skipped_communities = []
        
        for idx, comm_row in all_communities_df.iterrows():
            if len(selected_communities) >= top_n:
                break
                
            community = comm_row['COMMUNITY']
            escaped_comm = community.replace("'", "''")
            
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
            AND PERC_AUDIENCE >= {min_merchant_perc}
            AND COMPOSITE_INDEX <= 1000
            """
            
            check_df = query_to_dataframe(check_query)
            merchant_count = check_df['CNT'].iloc[0]
            
            if merchant_count > 0:
                selected_communities.append(comm_row)
                logger.info(f"   ✓ {community} ({merchant_count} merchants ≥{min_merchant_perc*100:.0f}%)")
            else:
                skipped_communities.append(community)
                logger.info(f"   ✗ {community} (no merchants ≥{min_merchant_perc*100:.0f}%, skipping)")
        
        communities_df = pd.DataFrame(selected_communities)
        
        if len(communities_df) < top_n:
            logger.warning(f"⚠️  Only found {len(communities_df)} communities with merchants ≥{min_merchant_perc*100:.0f}% (requested {top_n})")
        
        logger.info(f"\n✅ Selected {len(communities_df)} communities with merchants ≥{min_merchant_perc*100:.0f}%")
        if skipped_communities:
            logger.info(f"   Skipped {len(skipped_communities)} communities: {', '.join(skipped_communities)}")
        
        return communities_df
        
    finally:
        if original_schema:
            os.environ['SNOWFLAKE_SCHEMA'] = original_schema


def export_community_index_chart_data(communities_df: pd.DataFrame):
    """
    Export Community Index Chart Data for selected communities
    """
    logger.info("\n" + "="*100)
    logger.info("STEP 2: EXPORTING COMMUNITY INDEX CHART DATA")
    logger.info("="*100)
    
    logger.info("\n📋 Community Data Preview:")
    for idx, row in communities_df.iterrows():
        logger.info(f"   {idx+1:2d}. {row['COMMUNITY']:<45} "
                   f"Audience: {row['PERC_AUDIENCE_PCT']:>6.2f}%  "
                   f"Composite Index: {row['COMPOSITE_INDEX']:>7.1f}")
    
    # Export to CSV
    output_path = Path('nba_league_community_index_chart_data.csv')
    communities_df.to_csv(output_path, index=False)
    logger.info(f"\n💾 Exported to: {output_path}")
    
    return communities_df


def export_fan_wheel_data(communities_df: pd.DataFrame):
    """
    STEP 3: Export Fan Wheel Data
    This data is used to create the circular fan wheel visualization
    """
    logger.info("\n" + "="*100)
    logger.info("STEP 3: EXPORTING FAN WHEEL DATA")
    logger.info("="*100)
    
    original_schema = os.getenv('SNOWFLAKE_SCHEMA')
    os.environ['SNOWFLAKE_SCHEMA'] = 'NBA_LEAGUE_INSIGHTS'
    
    try:
        # Get community names
        community_names = communities_df['COMMUNITY'].tolist()
        escaped_communities = [c.replace("'", "''") for c in community_names]
        placeholders = ','.join([f"'{c}'" for c in escaped_communities])
        
        logger.info(f"\n📊 Querying V_NBA_LEAGUE_GENIUS_SPORTS_COMMUNITY_MERCHANT_INDEXING_ALL_TIME...")
        logger.info(f"   For {len(community_names)} communities:")
        for comm in community_names:
            logger.info(f"      - {comm}")
        logger.info("\n   Filters:")
        logger.info("   - COMPARISON_POPULATION = 'General Population'")
        logger.info("   - MERCHANT != 'LEVELUP' (exclude LEVELUP)")
        logger.info("   - NOT (COMMUNITY = 'Live Entertainment Seekers' AND CATEGORY = 'Professional Sports')")
        logger.info("   - UPPER(MERCHANT) NOT LIKE '%NBA%' (exclude NBA merchants)")
        logger.info("   - UPPER(PARENT_MERCHANT) NOT LIKE '%NBA%' (exclude NBA parent merchants)")
        logger.info("   - PERC_AUDIENCE >= 0.05 (5% threshold)")
        logger.info("   - COMPOSITE_INDEX <= 1000 (reasonable index limit)")
        logger.info("   - ROW_NUMBER() to get top 5 merchants per community")
        
        query = f"""
        WITH ranked_merchants AS (
            SELECT 
                COMMUNITY,
                MERCHANT,
                PARENT_MERCHANT,
                CATEGORY,
                SUBCATEGORY,
                COMPARISON_POPULATION,
                PERC_AUDIENCE,
                PERC_AUDIENCE * 100 as PERC_AUDIENCE_PCT,
                PERC_INDEX,
                SPC_INDEX,
                SPP_INDEX,
                PPC_INDEX,
                COMPOSITE_INDEX,
                ROW_NUMBER() OVER (PARTITION BY COMMUNITY ORDER BY COMPOSITE_INDEX DESC) as MERCHANT_RANK
            FROM V_NBA_LEAGUE_GENIUS_SPORTS_COMMUNITY_MERCHANT_INDEXING_ALL_TIME
            WHERE COMMUNITY IN ({placeholders})
            AND COMPARISON_POPULATION = 'General Population'
            AND MERCHANT != 'LEVELUP'
            AND NOT (COMMUNITY = 'Live Entertainment Seekers' AND CATEGORY = 'Professional Sports')
            AND UPPER(MERCHANT) NOT LIKE '%NBA%'
            AND UPPER(PARENT_MERCHANT) NOT LIKE '%NBA%'
            AND PERC_AUDIENCE >= 0.05
            AND COMPOSITE_INDEX <= 1000
        )
        SELECT * FROM ranked_merchants
        WHERE MERCHANT_RANK <= 5
        ORDER BY COMMUNITY, MERCHANT_RANK
        """
        
        merchants_df = query_to_dataframe(query)
        
        # Log column names for debugging
        logger.debug(f"Merchant DataFrame columns: {merchants_df.columns.tolist()}")
        
        # Normalize column names to uppercase
        merchants_df.columns = [col.upper() for col in merchants_df.columns]
        
        logger.info(f"\n✅ Found {len(merchants_df)} merchants across {merchants_df['COMMUNITY'].nunique()} communities")
        
        # Merge with community data
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
        
        # Rename columns for clarity before building behavior text
        merged_export = merged.copy()
        merged_export = merged_export.rename(columns={
            'PERC_AUDIENCE': 'MERCHANT_PERC_AUDIENCE',
            'PERC_AUDIENCE_PCT': 'MERCHANT_PERC_AUDIENCE_PCT',
            'PERC_INDEX': 'MERCHANT_PERC_INDEX',
            'COMPOSITE_INDEX': 'MERCHANT_COMPOSITE_INDEX'
        })
        
        # Build result DataFrame with behavior text (all top 5 per community)
        community_actions = load_approved_communities()
        merged_export['BEHAVIOR_TEXT'] = merged_export.apply(
            lambda row: generate_behavior_text(row['COMMUNITY'], row['MERCHANT'], community_actions),
            axis=1
        )
        
        # Sort by community composite index, then merchant rank
        merged_export = merged_export.sort_values(['COMMUNITY_COMPOSITE_INDEX', 'MERCHANT_RANK'], ascending=[False, True])
        
        logger.info("\n📋 Top 5 Merchants Per Community Preview:")
        for community in sorted(merged_export['COMMUNITY'].unique(), 
                               key=lambda x: merged_export[merged_export['COMMUNITY']==x]['COMMUNITY_COMPOSITE_INDEX'].iloc[0], 
                               reverse=True):
            comm_merchants = merged_export[merged_export['COMMUNITY'] == community].head(5)
            logger.info(f"\n   {community}:")
            for idx, row in comm_merchants.iterrows():
                logger.info(f"      {row['MERCHANT_RANK']}. {row['MERCHANT']:<30} "
                           f"({row['MERCHANT_PERC_AUDIENCE_PCT']:.2f}%)")
        
        # Export all top 5 merchants per community
        output_path = Path('nba_league_fan_wheel_data.csv')
        
        # Select final columns
        final_columns = [
            'COMMUNITY',
            'COMMUNITY_PERC_INDEX',
            'COMMUNITY_COMPOSITE_INDEX',
            'MERCHANT_RANK',
            'MERCHANT',
            'PARENT_MERCHANT',
            'CATEGORY',
            'SUBCATEGORY',
            'MERCHANT_PERC_AUDIENCE',
            'MERCHANT_PERC_AUDIENCE_PCT',
            'MERCHANT_PERC_INDEX',
            'MERCHANT_COMPOSITE_INDEX',
            'BEHAVIOR_TEXT'
        ]
        
        final_df = merged_export[final_columns].copy()
        final_df = final_df.sort_values(['COMMUNITY_COMPOSITE_INDEX', 'MERCHANT_RANK'], ascending=[False, True])
        final_df.to_csv(output_path, index=False)
        logger.info(f"\n💾 Exported top 5 merchants per community to: {output_path}")
        
        return final_df, merged_export
        
    finally:
        if original_schema:
            os.environ['SNOWFLAKE_SCHEMA'] = original_schema


def main():
    """Main execution function"""
    logger.info("="*100)
    logger.info("NBA LEAGUE VISUALIZATION DATA EXPORT")
    logger.info("="*100)
    logger.info("\nThis script exports the data used to create:")
    logger.info("  1. Community Index Chart (horizontal bar chart)")
    logger.info("  2. Fan Wheel (circular visualization)")
    logger.info("\nSchema: NBA_LEAGUE_INSIGHTS")
    logger.info("Comparison Population: General Population")
    logger.info("Strategy: Replace communities without merchants ≥5% with next highest that does")
    logger.info("="*100)
    
    # Step 1: Get communities with merchants ≥5%
    communities_df = get_communities_with_merchants(top_n=10, min_perc_audience=0.20, min_merchant_perc=0.05)
    
    # Step 2: Export community index chart data
    export_community_index_chart_data(communities_df)
    
    # Step 3: Export fan wheel data
    fan_wheel_df, full_merchants_df = export_fan_wheel_data(communities_df)
    
    # Summary
    logger.info("\n" + "="*100)
    logger.info("✅ EXPORT COMPLETE")
    logger.info("="*100)
    logger.info("\n📊 Summary:")
    logger.info(f"   Communities: {len(communities_df)}")
    logger.info(f"   Total Merchants: {len(fan_wheel_df)} (top 5 per community)")
    logger.info(f"   All communities have merchants ≥5% threshold")
    logger.info("\n📁 Files Created:")
    logger.info("   1. nba_league_community_index_chart_data.csv - Selected communities")
    logger.info("   2. nba_league_fan_wheel_data.csv - Top 5 merchants per community")
    logger.info("="*100)


if __name__ == "__main__":
    main()

