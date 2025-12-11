#!/usr/bin/env python3
"""
Export NBA League communities and merchants to CSV before fan wheel generation
Using General Population comparison and 20% PERC_AUDIENCE threshold
"""

import sys
from pathlib import Path
import pandas as pd
import logging
import os
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))

from data_processors.snowflake_connector import query_to_dataframe

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def export_communities_and_merchants():
    """Export top communities and their merchants to CSV"""
    logger.info("="*80)
    logger.info("NBA LEAGUE COMMUNITIES & MERCHANTS EXPORT")
    logger.info("Comparison Population: General Population")
    logger.info("Community Threshold: 20% PERC_AUDIENCE")
    logger.info("Merchant Threshold: 5% PERC_AUDIENCE (with fallback)")
    logger.info("="*80)
    
    # Temporarily set schema
    original_schema = os.getenv('SNOWFLAKE_SCHEMA')
    os.environ['SNOWFLAKE_SCHEMA'] = 'NBA_LEAGUE_INSIGHTS'
    
    try:
        # Get communities with 20% threshold, then filter to only those with merchants ≥5%
        logger.info("\n🔍 Getting communities (≥20% threshold, General Population)...")
        
        # First, get all communities meeting 20% threshold
        all_communities_query = """
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
        AND PERC_AUDIENCE >= 0.20
        QUALIFY ROW_NUMBER() OVER (PARTITION BY COMMUNITY ORDER BY COMPOSITE_INDEX DESC) = 1
        ORDER BY COMPOSITE_INDEX DESC
        """
        
        all_communities_df = query_to_dataframe(all_communities_query)
        logger.info(f"✅ Found {len(all_communities_df)} total communities meeting 20% threshold")
        
        # Now filter to only communities that have merchants ≥5%
        logger.info("\n🔍 Filtering to communities with merchants ≥5% (excluding NBA merchants)...")
        communities_with_merchants = []
        
        for idx, comm_row in all_communities_df.iterrows():
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
            AND PERC_AUDIENCE >= 0.05
            AND COMPOSITE_INDEX <= 1000
            """
            
            check_df = query_to_dataframe(check_query)
            merchant_count = check_df['CNT'].iloc[0]
            
            if merchant_count > 0:
                communities_with_merchants.append(comm_row)
                logger.info(f"   ✓ {community} ({merchant_count} merchants ≥5%)")
                
                if len(communities_with_merchants) >= 10:
                    break
            else:
                logger.info(f"   ✗ {community} (no merchants ≥5%, skipping)")
        
        communities_df = pd.DataFrame(communities_with_merchants)
        logger.info(f"\n✅ Selected {len(communities_df)} communities with merchants ≥5%")
        
        # Display communities
        logger.info("\n📊 Top 10 Communities:")
        for idx, row in communities_df.iterrows():
            logger.info(f"   {idx+1:2d}. {row['COMMUNITY']:<45} {row['PERC_AUDIENCE_PCT']:>6.2f}%  |  Index: {row['COMPOSITE_INDEX']:>6.1f}")
        
        # Get merchants for these communities
        community_names = communities_df['COMMUNITY'].tolist()
        escaped_communities = [c.replace("'", "''") for c in community_names]
        placeholders = ','.join([f"'{c}'" for c in escaped_communities])
        
        logger.info(f"\n🔍 Getting top 5 merchants per community (≥5% threshold, no fallback - communities already filtered)...")
        
        # First, get merchants above 5% threshold
        merchants_above_query = f"""
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
                ROW_NUMBER() OVER (PARTITION BY COMMUNITY ORDER BY COMPOSITE_INDEX DESC) as rn
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
        WHERE rn <= 5
        """
        
        merchants_df = query_to_dataframe(merchants_above_query)
        logger.info(f"✅ Found {len(merchants_df)} merchants across {merchants_df['COMMUNITY'].nunique()} communities")
        
        # Merge community and merchant data for export
        export_data = []
        
        for _, comm_row in communities_df.iterrows():
            community = comm_row['COMMUNITY']
            comm_merchants = merchants_df[merchants_df['COMMUNITY'] == community].sort_values('COMPOSITE_INDEX', ascending=False)
            
            if comm_merchants.empty:
                # Community with no merchants
                export_data.append({
                    'COMMUNITY': community,
                    'COMMUNITY_PERC_AUDIENCE_PCT': comm_row['PERC_AUDIENCE_PCT'],
                    'COMMUNITY_COMPOSITE_INDEX': comm_row['COMPOSITE_INDEX'],
                    'COMMUNITY_PERC_INDEX': comm_row['PERC_INDEX'],
                    'MERCHANT': None,
                    'PARENT_MERCHANT': None,
                    'CATEGORY': None,
                    'SUBCATEGORY': None,
                    'MERCHANT_PERC_AUDIENCE_PCT': None,
                    'MERCHANT_COMPOSITE_INDEX': None,
                    'MERCHANT_PERC_INDEX': None,
                    'MERCHANT_RANK': None
                })
            else:
                # Add top merchant for fan wheel (first one)
                top_merchant = comm_merchants.iloc[0]
                export_data.append({
                    'COMMUNITY': community,
                    'COMMUNITY_PERC_AUDIENCE_PCT': comm_row['PERC_AUDIENCE_PCT'],
                    'COMMUNITY_COMPOSITE_INDEX': comm_row['COMPOSITE_INDEX'],
                    'COMMUNITY_PERC_INDEX': comm_row['PERC_INDEX'],
                    'MERCHANT': top_merchant['MERCHANT'],
                    'PARENT_MERCHANT': top_merchant['PARENT_MERCHANT'],
                    'CATEGORY': top_merchant['CATEGORY'],
                    'SUBCATEGORY': top_merchant['SUBCATEGORY'],
                    'MERCHANT_PERC_AUDIENCE_PCT': top_merchant['PERC_AUDIENCE_PCT'],
                    'MERCHANT_COMPOSITE_INDEX': top_merchant['COMPOSITE_INDEX'],
                    'MERCHANT_PERC_INDEX': top_merchant['PERC_INDEX'],
                    'MERCHANT_RANK': 1
                })
        
        # Create export DataFrame
        export_df = pd.DataFrame(export_data)
        
        # Round numeric columns
        numeric_cols = ['COMMUNITY_PERC_AUDIENCE_PCT', 'COMMUNITY_COMPOSITE_INDEX', 'COMMUNITY_PERC_INDEX',
                       'MERCHANT_PERC_AUDIENCE_PCT', 'MERCHANT_COMPOSITE_INDEX', 'MERCHANT_PERC_INDEX']
        for col in numeric_cols:
            if col in export_df.columns:
                export_df[col] = pd.to_numeric(export_df[col], errors='coerce')
                export_df[col] = export_df[col].round(2)
        
        # Export to CSV
        output_path = Path('nba_league_communities_merchants_export.csv')
        export_df.to_csv(output_path, index=False)
        
        logger.info("\n" + "="*80)
        logger.info(f"✅ Exported to: {output_path}")
        logger.info(f"   Total rows: {len(export_df)}")
        logger.info(f"   Communities: {export_df['COMMUNITY'].nunique()}")
        logger.info(f"   Communities with merchants: {export_df['MERCHANT'].notna().sum()}")
        logger.info("="*80)
        
        # Display summary
        logger.info("\n📊 Summary:")
        for idx, row in export_df.iterrows():
            if pd.notna(row['MERCHANT']):
                logger.info(f"   {idx+1:2d}. {row['COMMUNITY']:<40} → {row['MERCHANT']:<40} "
                          f"(Comm: {row['COMMUNITY_PERC_AUDIENCE_PCT']:.1f}%, "
                          f"Merch: {row['MERCHANT_PERC_AUDIENCE_PCT']:.2f}%)")
            else:
                logger.info(f"   {idx+1:2d}. {row['COMMUNITY']:<40} → No merchant found")
        
    finally:
        # Restore original schema
        if original_schema:
            os.environ['SNOWFLAKE_SCHEMA'] = original_schema


if __name__ == "__main__":
    export_communities_and_merchants()

