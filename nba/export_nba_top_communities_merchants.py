#!/usr/bin/env python3
"""
Export top 10 communities (5% threshold) with top 5 merchants each (1% threshold)
"""

import sys
from pathlib import Path
import pandas as pd
import logging

sys.path.insert(0, str(Path(__file__).parent))

from data_processors.snowflake_connector import query_to_dataframe

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_top_communities(min_audience_pct: float = 0.05, top_n: int = 10) -> pd.DataFrame:
    """Get top N communities meeting the threshold"""
    logger.info(f"🔍 Getting top {top_n} communities (≥{min_audience_pct*100}% threshold)...")
    
    query = """
    SELECT 
        COMMUNITY,
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
         (SUM(AUDIENCE_TRANSACTIONS) / NULLIF(SUM(AUDIENCE_COUNT), 0)) / NULLIF(MAX(COMPARISON_PPC), 0) * 100) / 4.0 as COMPOSITE_INDEX,
        COUNT(DISTINCT AUDIENCE) as NUM_TEAMS
    FROM NBA_SIL_COMMUNITY_INDEXING_SNAPSHOT
    WHERE COMPARISON_POPULATION = 'General Population'
    GROUP BY COMMUNITY, COMPARISON_POPULATION
    HAVING SUM(AUDIENCE_COUNT) / NULLIF(SUM(TOTAL_AUDIENCE_COUNT), 0) >= {min_pct}
    ORDER BY COMPOSITE_INDEX DESC
    LIMIT {top_n}
    """
    
    query = query.format(min_pct=min_audience_pct, top_n=top_n)
    df = query_to_dataframe(query)
    
    logger.info(f"✅ Found {len(df)} communities")
    return df


def get_top_merchants_for_communities(communities: list, min_merchant_perc: float = 0.01, top_n_per_community: int = 5) -> pd.DataFrame:
    """Get top N merchants for each community meeting the threshold"""
    logger.info(f"🔍 Getting top {top_n_per_community} merchants per community (≥{min_merchant_perc*100}% threshold)...")
    
    placeholders = ','.join([f"'{c}'" for c in communities])
    
    query = f"""
    WITH aggregated_merchants AS (
        SELECT 
            COMMUNITY,
            MERCHANT,
            PARENT_MERCHANT,
            CATEGORY,
            SUBCATEGORY,
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
             (SUM(AUDIENCE_TRANSACTIONS) / NULLIF(SUM(AUDIENCE_COUNT), 0)) / NULLIF(MAX(COMPARISON_PPC), 0) * 100) / 4.0 as COMPOSITE_INDEX,
            COUNT(DISTINCT AUDIENCE) as NUM_TEAMS
        FROM NBA_SIL_COMMUNITY_MERCHANT_INDEXING_SNAPSHOT
        WHERE COMPARISON_POPULATION = 'General Population'
        AND COMMUNITY IN ({placeholders})
        AND MERCHANT != 'LEVELUP'
        GROUP BY COMMUNITY, MERCHANT, PARENT_MERCHANT, CATEGORY, SUBCATEGORY, COMPARISON_POPULATION
        HAVING SUM(AUDIENCE_COUNT) >= 10
        AND SUM(AUDIENCE_COUNT) / NULLIF(SUM(TOTAL_AUDIENCE_COUNT), 0) >= {min_merchant_perc}
    ),
    ranked_merchants AS (
        SELECT 
            *,
            ROW_NUMBER() OVER (PARTITION BY COMMUNITY ORDER BY COMPOSITE_INDEX DESC) as MERCHANT_RANK
        FROM aggregated_merchants
    )
    SELECT * FROM ranked_merchants
    WHERE MERCHANT_RANK <= {top_n_per_community}
    ORDER BY COMMUNITY, MERCHANT_RANK
    """
    df = query_to_dataframe(query)
    
    logger.info(f"✅ Found {len(df)} merchants across {df['COMMUNITY'].nunique()} communities")
    return df


def main():
    """Export top communities and merchants to CSV"""
    logger.info("="*80)
    logger.info("NBA TOP COMMUNITIES & MERCHANTS EXPORT")
    logger.info("="*80)
    
    # Get top 10 communities (5% threshold)
    communities_df = get_top_communities(min_audience_pct=0.05, top_n=10)
    community_names = communities_df['COMMUNITY'].tolist()
    
    logger.info(f"\n📊 Top 10 Communities:")
    for idx, row in communities_df.iterrows():
        logger.info(f"   {idx+1:2d}. {row['COMMUNITY']:<40} Index: {row['COMPOSITE_INDEX']:>6.1f} | Audience: {row['PERC_AUDIENCE']*100:>5.2f}%")
    
    # Get top 5 merchants for each community (1% threshold)
    merchants_df = get_top_merchants_for_communities(
        communities=community_names,
        min_merchant_perc=0.01,
        top_n_per_community=5
    )
    
    # Merge community data with merchant data
    result_df = merchants_df.merge(
        communities_df[['COMMUNITY', 'COMPOSITE_INDEX', 'PERC_AUDIENCE']].rename(
            columns={
                'COMPOSITE_INDEX': 'COMMUNITY_COMPOSITE_INDEX',
                'PERC_AUDIENCE': 'COMMUNITY_PERC_AUDIENCE'
            }
        ),
        on='COMMUNITY',
        how='left'
    )
    
    # Format and prepare for export
    export_df = result_df[[
        'COMMUNITY',
        'COMMUNITY_COMPOSITE_INDEX',
        'COMMUNITY_PERC_AUDIENCE',
        'MERCHANT_RANK',
        'MERCHANT',
        'PARENT_MERCHANT',
        'CATEGORY',
        'SUBCATEGORY',
        'PERC_AUDIENCE',
        'AUDIENCE_COUNT',
        'TOTAL_AUDIENCE_COUNT',
        'AUDIENCE_TRANSACTIONS',
        'AUDIENCE_TOTAL_SPEND',
        'SPC',
        'SPP',
        'PPC',
        'PERC_INDEX',
        'SPC_INDEX',
        'SPP_INDEX',
        'PPC_INDEX',
        'COMPOSITE_INDEX',
        'NUM_TEAMS'
    ]].copy()
    
    # Add percentage columns
    export_df['COMMUNITY_PERC_AUDIENCE_PCT'] = pd.to_numeric(export_df['COMMUNITY_PERC_AUDIENCE'], errors='coerce') * 100
    export_df['COMMUNITY_PERC_AUDIENCE_PCT'] = export_df['COMMUNITY_PERC_AUDIENCE_PCT'].round(2)
    export_df['PERC_AUDIENCE_PCT'] = pd.to_numeric(export_df['PERC_AUDIENCE'], errors='coerce') * 100
    export_df['PERC_AUDIENCE_PCT'] = export_df['PERC_AUDIENCE_PCT'].round(2)
    
    # Round numeric columns
    numeric_cols = ['COMMUNITY_COMPOSITE_INDEX', 'PERC_INDEX', 'SPC_INDEX', 'SPP_INDEX', 'PPC_INDEX', 'COMPOSITE_INDEX', 'SPC', 'SPP', 'PPC']
    for col in numeric_cols:
        if col in export_df.columns:
            export_df[col] = pd.to_numeric(export_df[col], errors='coerce')
            export_df[col] = export_df[col].round(2)
    
    # Round spend and transaction columns
    for col in ['AUDIENCE_TRANSACTIONS', 'AUDIENCE_TOTAL_SPEND']:
        if col in export_df.columns:
            export_df[col] = pd.to_numeric(export_df[col], errors='coerce')
            export_df[col] = export_df[col].round(0)
    
    # Reorder columns
    column_order = [
        'COMMUNITY',
        'COMMUNITY_COMPOSITE_INDEX',
        'COMMUNITY_PERC_AUDIENCE_PCT',
        'MERCHANT_RANK',
        'MERCHANT',
        'PARENT_MERCHANT',
        'CATEGORY',
        'SUBCATEGORY',
        'PERC_AUDIENCE_PCT',
        'AUDIENCE_COUNT',
        'TOTAL_AUDIENCE_COUNT',
        'AUDIENCE_TRANSACTIONS',
        'AUDIENCE_TOTAL_SPEND',
        'SPC',
        'SPP',
        'PPC',
        'PERC_INDEX',
        'SPC_INDEX',
        'SPP_INDEX',
        'PPC_INDEX',
        'COMPOSITE_INDEX',
        'NUM_TEAMS'
    ]
    
    export_df = export_df[column_order]
    
    # Export to CSV
    output_path = Path('nba_top_10_communities_top_5_merchants.csv')
    export_df.to_csv(output_path, index=False)
    
    logger.info(f"\n✅ Exported to: {output_path}")
    logger.info(f"   Total rows: {len(export_df)}")
    logger.info(f"   Communities: {export_df['COMMUNITY'].nunique()}")
    logger.info(f"   Merchants: {export_df['MERCHANT'].nunique()}")
    
    # Show summary
    logger.info(f"\n📊 Summary by Community:")
    for community in community_names:
        comm_data = export_df[export_df['COMMUNITY'] == community]
        if len(comm_data) > 0:
            logger.info(f"   {community}: {len(comm_data)} merchants")
            for _, row in comm_data.iterrows():
                logger.info(f"      {int(row['MERCHANT_RANK'])}. {row['MERCHANT']:<40} "
                           f"Index: {row['COMPOSITE_INDEX']:>6.1f} | "
                           f"Audience: {row['PERC_AUDIENCE_PCT']:>5.2f}%")
    
    logger.info("\n" + "="*80)


if __name__ == "__main__":
    main()

