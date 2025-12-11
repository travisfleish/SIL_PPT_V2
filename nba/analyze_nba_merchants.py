#!/usr/bin/env python3
"""
Analyze all NBA aggregate merchants and their PERC_AUDIENCE distribution
"""

import sys
from pathlib import Path
import pandas as pd
import logging

sys.path.insert(0, str(Path(__file__).parent))

from data_processors.snowflake_connector import query_to_dataframe

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_all_aggregated_merchants() -> pd.DataFrame:
    """
    Get aggregated merchant data across all NBA teams (not filtered by community)
    
    Returns:
        DataFrame with all aggregated merchant metrics
    """
    logger.info("🔍 Aggregating ALL NBA merchant data across all teams...")
    
    query = """
    SELECT 
        MERCHANT,
        PARENT_MERCHANT,
        CATEGORY,
        SUBCATEGORY,
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
        -- Comparison metrics
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
        -- Composite index
        ((SUM(AUDIENCE_COUNT) / NULLIF(SUM(TOTAL_AUDIENCE_COUNT), 0)) / NULLIF(MAX(PERC_COMPARISON), 0) * 100 +
         (SUM(AUDIENCE_TOTAL_SPEND) / NULLIF(SUM(AUDIENCE_COUNT), 0)) / NULLIF(MAX(COMPARISON_SPC), 0) * 100 +
         (SUM(AUDIENCE_TOTAL_SPEND) / NULLIF(SUM(TOTAL_AUDIENCE_COUNT), 0)) / NULLIF(MAX(COMPARISON_SPP), 0) * 100 +
         (SUM(AUDIENCE_TRANSACTIONS) / NULLIF(SUM(AUDIENCE_COUNT), 0)) / NULLIF(MAX(COMPARISON_PPC), 0) * 100) / 4.0 as COMPOSITE_INDEX,
        -- Count of teams contributing to this merchant
        COUNT(DISTINCT AUDIENCE) as NUM_TEAMS
    FROM NBA_SIL_MERCHANT_INDEXING_SNAPSHOT
    WHERE COMPARISON_POPULATION = 'General Population'
    AND MERCHANT != 'LEVELUP'  -- Exclude LEVELUP
    GROUP BY MERCHANT, PARENT_MERCHANT, CATEGORY, SUBCATEGORY, COMPARISON_POPULATION
    HAVING SUM(AUDIENCE_COUNT) >= 10  -- Minimum audience count
    ORDER BY PERC_AUDIENCE DESC
    """
    
    df = query_to_dataframe(query)
    
    logger.info(f"✅ Found {len(df)} merchants (with min 10 audience count)")
    return df


def analyze_perc_audience_distribution(df: pd.DataFrame):
    """Analyze PERC_AUDIENCE distribution"""
    total_merchants = len(df)
    
    # Calculate percentages above thresholds
    above_5_pct = len(df[df['PERC_AUDIENCE'] >= 0.05])
    above_10_pct = len(df[df['PERC_AUDIENCE'] >= 0.10])
    above_20_pct = len(df[df['PERC_AUDIENCE'] >= 0.20])
    
    pct_above_5 = (above_5_pct / total_merchants * 100) if total_merchants > 0 else 0
    pct_above_10 = (above_10_pct / total_merchants * 100) if total_merchants > 0 else 0
    pct_above_20 = (above_20_pct / total_merchants * 100) if total_merchants > 0 else 0
    
    logger.info("\n" + "="*80)
    logger.info("PERC_AUDIENCE DISTRIBUTION ANALYSIS")
    logger.info("="*80)
    logger.info(f"\n📊 Total Merchants: {total_merchants:,}")
    logger.info(f"\n📈 Merchants by PERC_AUDIENCE Threshold:")
    logger.info(f"   ≥ 5%:  {above_5_pct:,} merchants ({pct_above_5:.2f}%)")
    logger.info(f"   ≥ 10%: {above_10_pct:,} merchants ({pct_above_10:.2f}%)")
    logger.info(f"   ≥ 20%: {above_20_pct:,} merchants ({pct_above_20:.2f}%)")
    
    # Show distribution buckets
    logger.info(f"\n📊 Distribution Buckets:")
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
        logger.info(f"   {label:<15} {count:>6,} merchants ({pct:>5.2f}%)")
    
    # Show top merchants
    logger.info(f"\n🏆 Top 20 Merchants by PERC_AUDIENCE:")
    logger.info("-"*80)
    top_merchants = df.head(20)
    for idx, row in top_merchants.iterrows():
        logger.info(f"   {idx+1:2d}. {row['MERCHANT']:<40} "
                   f"{row['PERC_AUDIENCE']*100:>6.2f}% | "
                   f"Index: {row['COMPOSITE_INDEX']:>6.1f} | "
                   f"Teams: {int(row['NUM_TEAMS'])}")
    
    logger.info("="*80)
    
    return {
        'total_merchants': total_merchants,
        'above_5_pct': above_5_pct,
        'above_10_pct': above_10_pct,
        'above_20_pct': above_20_pct,
        'pct_above_5': pct_above_5,
        'pct_above_10': pct_above_10,
        'pct_above_20': pct_above_20
    }


def export_to_csv(df: pd.DataFrame):
    """Export all merchant data to CSV"""
    # Format columns
    df_formatted = df.copy()
    
    # Add percentage column
    df_formatted['PERC_AUDIENCE_PCT'] = pd.to_numeric(df_formatted['PERC_AUDIENCE'], errors='coerce') * 100
    df_formatted['PERC_AUDIENCE_PCT'] = df_formatted['PERC_AUDIENCE_PCT'].round(2)
    
    # Round numeric columns
    numeric_cols = df_formatted.select_dtypes(include=[float, int]).columns
    for col in numeric_cols:
        if col not in ['PERC_AUDIENCE', 'PERC_AUDIENCE_PCT']:
            if 'INDEX' in col or 'MOE' in col:
                df_formatted[col] = df_formatted[col].round(2)
            elif 'SPEND' in col or 'TRANSACTIONS' in col:
                df_formatted[col] = df_formatted[col].round(0)
            else:
                df_formatted[col] = df_formatted[col].round(2)
    
    # Reorder columns
    column_order = [
        'MERCHANT',
        'PARENT_MERCHANT',
        'CATEGORY',
        'SUBCATEGORY',
        'COMPARISON_POPULATION',
        'NUM_TEAMS',
        'AUDIENCE_COUNT',
        'TOTAL_AUDIENCE_COUNT',
        'PERC_AUDIENCE',
        'PERC_AUDIENCE_PCT',
        'AUDIENCE_TRANSACTIONS',
        'AUDIENCE_TOTAL_SPEND',
        'SPC',
        'SPP',
        'PPC',
        'COMPARISON_COUNT',
        'COMPARISON_TOTAL_COUNT',
        'PERC_COMPARISON',
        'COMPARISON_TOTAL_SPEND',
        'COMPARISON_SPC',
        'COMPARISON_SPP',
        'COMPARISON_PPC',
        'PERC_INDEX',
        'SPC_INDEX',
        'SPP_INDEX',
        'PPC_INDEX',
        'COMPOSITE_INDEX'
    ]
    
    # Only include columns that exist
    column_order = [col for col in column_order if col in df_formatted.columns]
    remaining_cols = [col for col in df_formatted.columns if col not in column_order]
    final_column_order = column_order + remaining_cols
    
    df_formatted = df_formatted[final_column_order]
    
    # Export
    output_path = Path('nba_aggregate_all_merchants.csv')
    df_formatted.to_csv(output_path, index=False)
    
    logger.info(f"\n✅ Exported to: {output_path}")
    return output_path


def main():
    """Main analysis function"""
    logger.info("="*80)
    logger.info("NBA AGGREGATE MERCHANT ANALYSIS")
    logger.info("="*80)
    
    # Get all aggregated merchants
    df = get_all_aggregated_merchants()
    
    # Analyze distribution
    stats = analyze_perc_audience_distribution(df)
    
    # Export to CSV
    logger.info("\n💾 Exporting to CSV...")
    export_to_csv(df)
    
    logger.info("\n" + "="*80)
    logger.info("✨ Analysis Complete!")
    logger.info("="*80)


if __name__ == "__main__":
    main()

