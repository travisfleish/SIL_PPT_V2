#!/usr/bin/env python3
"""
Analyze merchant PERC_AUDIENCE distribution in NBA_LEAGUE_INSIGHTS schema
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


def analyze_merchant_thresholds():
    """Analyze how many merchants meet different PERC_AUDIENCE thresholds"""
    logger.info("="*80)
    logger.info("NBA LEAGUE MERCHANT PERC_AUDIENCE THRESHOLD ANALYSIS")
    logger.info("="*80)
    
    # Temporarily set schema
    original_schema = os.getenv('SNOWFLAKE_SCHEMA')
    os.environ['SNOWFLAKE_SCHEMA'] = 'NBA_LEAGUE_INSIGHTS'
    
    try:
        # Get all merchants with their PERC_AUDIENCE
        query = """
        SELECT 
            COMMUNITY,
            MERCHANT,
            PARENT_MERCHANT,
            CATEGORY,
            PERC_AUDIENCE,
            PERC_INDEX,
            COMPOSITE_INDEX
        FROM V_NBA_LEAGUE_GENIUS_SPORTS_COMMUNITY_MERCHANT_INDEXING_SNAPSHOT
        WHERE MERCHANT != 'LEVELUP'
        AND NOT (COMMUNITY = 'Live Entertainment Seekers' AND CATEGORY = 'Professional Sports')
        ORDER BY PERC_AUDIENCE DESC
        """
        
        logger.info("🔍 Fetching merchant data...")
        df = query_to_dataframe(query)
        
        total_merchants = len(df)
        total_unique_merchants = df['MERCHANT'].nunique()
        
        logger.info(f"✅ Found {total_merchants:,} merchant-community combinations")
        logger.info(f"   Unique merchants: {total_unique_merchants:,}")
        
        # Analyze by threshold
        thresholds = [0.01, 0.05, 0.10]  # 1%, 5%, 10%
        
        print("\n" + "="*80)
        print("MERCHANT PERC_AUDIENCE THRESHOLD ANALYSIS")
        print("="*80)
        
        for threshold in thresholds:
            above_threshold = df[df['PERC_AUDIENCE'] >= threshold]
            count = len(above_threshold)
            pct = (count / total_merchants * 100) if total_merchants > 0 else 0
            
            unique_merchants = above_threshold['MERCHANT'].nunique()
            unique_pct = (unique_merchants / total_unique_merchants * 100) if total_unique_merchants > 0 else 0
            
            print(f"\n📊 ≥ {threshold*100:.0f}% PERC_AUDIENCE:")
            print(f"   Merchant-Community Combinations: {count:,} ({pct:.2f}%)")
            print(f"   Unique Merchants: {unique_merchants:,} ({unique_pct:.2f}%)")
        
        # Distribution buckets
        print(f"\n📊 Distribution Buckets:")
        print("-"*80)
        buckets = [
            (0.0, 0.01, "0% - 1%"),
            (0.01, 0.05, "1% - 5%"),
            (0.05, 0.10, "5% - 10%"),
            (0.10, 0.20, "10% - 20%"),
            (0.20, 0.50, "20% - 50%"),
            (0.50, 1.0, "50%+")
        ]
        
        for min_val, max_val, label in buckets:
            count = len(df[(df['PERC_AUDIENCE'] >= min_val) & (df['PERC_AUDIENCE'] < max_val)])
            pct = (count / total_merchants * 100) if total_merchants > 0 else 0
            print(f"   {label:<15} {count:>8,} combinations ({pct:>5.2f}%)")
        
        # Show top merchants by PERC_AUDIENCE
        print(f"\n🏆 Top 20 Merchant-Community Combinations by PERC_AUDIENCE:")
        print("-"*80)
        top_merchants = df.head(20)
        for idx, row in top_merchants.iterrows():
            print(f"   {idx+1:2d}. {row['COMMUNITY']:<35} {row['MERCHANT']:<40} "
                 f"{row['PERC_AUDIENCE']*100:>6.2f}% | Index: {row['COMPOSITE_INDEX']:>6.1f}")
        
        # Analyze by community
        print(f"\n📊 Merchants by Community (showing communities with most merchants ≥1%):")
        print("-"*80)
        community_stats = []
        for community in df['COMMUNITY'].unique():
            comm_df = df[df['COMMUNITY'] == community]
            above_1pct = len(comm_df[comm_df['PERC_AUDIENCE'] >= 0.01])
            above_5pct = len(comm_df[comm_df['PERC_AUDIENCE'] >= 0.05])
            above_10pct = len(comm_df[comm_df['PERC_AUDIENCE'] >= 0.10])
            
            if above_1pct > 0:
                community_stats.append({
                    'COMMUNITY': community,
                    'TOTAL': len(comm_df),
                    '≥1%': above_1pct,
                    '≥5%': above_5pct,
                    '≥10%': above_10pct
                })
        
        community_stats_df = pd.DataFrame(community_stats)
        community_stats_df = community_stats_df.sort_values('≥1%', ascending=False)
        
        for idx, row in community_stats_df.head(15).iterrows():
            print(f"   {row['COMMUNITY']:<40} Total: {row['TOTAL']:>3} | "
                 f"≥1%: {row['≥1%']:>3} | ≥5%: {row['≥5%']:>3} | ≥10%: {row['≥10%']:>3}")
        
        print("\n" + "="*80)
        
    finally:
        # Restore original schema
        if original_schema:
            os.environ['SNOWFLAKE_SCHEMA'] = original_schema


if __name__ == "__main__":
    analyze_merchant_thresholds()

