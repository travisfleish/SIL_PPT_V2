#!/usr/bin/env python3
"""
Export NBA aggregate community data to CSV with all metrics
"""

import sys
from pathlib import Path
import pandas as pd
import logging

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from data_processors.snowflake_connector import query_to_dataframe

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_aggregated_communities() -> pd.DataFrame:
    """
    Get aggregated community data across all NBA teams with all metrics
    
    Returns:
        DataFrame with all aggregated community metrics
    """
    logger.info("🔍 Aggregating NBA community data across all teams...")
    
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
        -- Median spend per customer (weighted average approximation)
        AVG(MEDIAN_SPEND_PER_CUSTOMER) as MEDIAN_SPEND_PER_CUSTOMER,
        -- Comparison metrics (should be same across all teams for General Population)
        MAX(COMPARISON_COUNT) as COMPARISON_COUNT,
        MAX(COMPARISON_TOTAL_COUNT) as COMPARISON_TOTAL_COUNT,
        MAX(PERC_COMPARISON) as PERC_COMPARISON,
        MAX(COMPARISON_TOTAL_SPEND) as COMPARISON_TOTAL_SPEND,
        MAX(COMPARISON_MEDIAN_SPEND_PER_CUSTOMER) as COMPARISON_MEDIAN_SPEND_PER_CUSTOMER,
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
         (SUM(AUDIENCE_TRANSACTIONS) / NULLIF(SUM(AUDIENCE_COUNT), 0)) / NULLIF(MAX(COMPARISON_PPC), 0) * 100) / 4.0 as COMPOSITE_INDEX,
        -- Margin of error (average across teams)
        AVG(AUDIENCE_MOE) as AUDIENCE_MOE,
        AVG(COMPARISON_MOE) as COMPARISON_MOE,
        -- Count of teams contributing to this community
        COUNT(DISTINCT AUDIENCE) as NUM_TEAMS
    FROM NBA_SIL_COMMUNITY_INDEXING_SNAPSHOT
    WHERE COMPARISON_POPULATION = 'General Population'
    GROUP BY COMMUNITY, COMPARISON_POPULATION
    ORDER BY COMPOSITE_INDEX DESC
    """
    
    df = query_to_dataframe(query)
    
    logger.info(f"✅ Found {len(df)} communities")
    return df


def main():
    """Export aggregated NBA community data to CSV"""
    logger.info("="*80)
    logger.info("NBA AGGREGATE COMMUNITY DATA EXPORT")
    logger.info("="*80)
    
    # Get aggregated data
    df = get_aggregated_communities()
    
    # Format columns for better readability
    df_formatted = df.copy()
    
    # Round numeric columns
    numeric_cols = df.select_dtypes(include=[float, int]).columns
    for col in numeric_cols:
        if 'INDEX' in col or 'MOE' in col:
            df_formatted[col] = df_formatted[col].round(2)
        elif 'PERC' in col and col != 'PERC_AUDIENCE' and col != 'PERC_COMPARISON':
            df_formatted[col] = df_formatted[col].round(2)
        elif col in ['SPC', 'SPP', 'PPC', 'COMPARISON_SPC', 'COMPARISON_SPP', 'COMPARISON_PPC']:
            df_formatted[col] = df_formatted[col].round(2)
        elif 'SPEND' in col or 'TRANSACTIONS' in col:
            df_formatted[col] = df_formatted[col].round(0)
        else:
            df_formatted[col] = df_formatted[col].round(2)
    
    # Format percentage columns as percentages
    if 'PERC_AUDIENCE' in df_formatted.columns:
        df_formatted['PERC_AUDIENCE_PCT'] = pd.to_numeric(df_formatted['PERC_AUDIENCE'], errors='coerce') * 100
        df_formatted['PERC_AUDIENCE_PCT'] = df_formatted['PERC_AUDIENCE_PCT'].round(2)
    if 'PERC_COMPARISON' in df_formatted.columns:
        df_formatted['PERC_COMPARISON_PCT'] = pd.to_numeric(df_formatted['PERC_COMPARISON'], errors='coerce') * 100
        df_formatted['PERC_COMPARISON_PCT'] = df_formatted['PERC_COMPARISON_PCT'].round(2)
    
    # Reorder columns for better readability
    column_order = [
        'COMMUNITY',
        'COMPARISON_POPULATION',
        'NUM_TEAMS',
        'AUDIENCE_COUNT',
        'TOTAL_AUDIENCE_COUNT',
        'PERC_AUDIENCE',
        'PERC_AUDIENCE_PCT',
        'AUDIENCE_TRANSACTIONS',
        'AUDIENCE_TOTAL_SPEND',
        'MEDIAN_SPEND_PER_CUSTOMER',
        'SPC',
        'SPP',
        'PPC',
        'COMPARISON_COUNT',
        'COMPARISON_TOTAL_COUNT',
        'PERC_COMPARISON',
        'PERC_COMPARISON_PCT',
        'COMPARISON_TOTAL_SPEND',
        'COMPARISON_MEDIAN_SPEND_PER_CUSTOMER',
        'COMPARISON_SPC',
        'COMPARISON_SPP',
        'COMPARISON_PPC',
        'PERC_INDEX',
        'SPC_INDEX',
        'SPP_INDEX',
        'PPC_INDEX',
        'COMPOSITE_INDEX',
        'AUDIENCE_MOE',
        'COMPARISON_MOE'
    ]
    
    # Only include columns that exist
    column_order = [col for col in column_order if col in df_formatted.columns]
    
    # Add any remaining columns
    remaining_cols = [col for col in df_formatted.columns if col not in column_order]
    final_column_order = column_order + remaining_cols
    
    df_formatted = df_formatted[final_column_order]
    
    # Export to CSV
    output_path = Path('nba_aggregate_communities.csv')
    df_formatted.to_csv(output_path, index=False)
    
    logger.info(f"\n✅ Exported {len(df_formatted)} communities to: {output_path}")
    logger.info(f"\n📊 Top 10 Communities by Composite Index:")
    logger.info("-"*80)
    for idx, row in df_formatted.head(10).iterrows():
        logger.info(f"  {idx+1:2d}. {row['COMMUNITY']:<35} "
                   f"Index: {row['COMPOSITE_INDEX']:>6.1f} | "
                   f"Audience: {row['PERC_AUDIENCE_PCT']:>5.2f}% | "
                   f"Teams: {int(row['NUM_TEAMS'])}")
    
    logger.info("\n" + "="*80)
    logger.info(f"📋 CSV contains {len(df_formatted.columns)} columns")
    logger.info("="*80)


if __name__ == "__main__":
    main()

