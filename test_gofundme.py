"""
Diagnostic script to investigate duplicate GoFundMe in Carolina Panthers fan wheel
"""

import pandas as pd
import logging
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from data_processors.merchant_ranker import MerchantRanker
from data_processors.snowflake_connector import query_to_dataframe

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def diagnose_gofundme_duplicate(team_view_prefix: str, comparison_population: str):
    """
    Diagnose why GoFundMe appears twice in the fan wheel

    Args:
        team_view_prefix: The view prefix for Carolina Panthers
        comparison_population: The comparison population string
    """
    logger.info("=" * 80)
    logger.info("GOFUNDME DUPLICATE DIAGNOSTIC REPORT")
    logger.info("=" * 80)

    # Initialize merchant ranker without cache manager (or with None)
    # The CacheManager requires a connection_pool parameter that we don't have in this context
    ranker = MerchantRanker(
        team_view_prefix=team_view_prefix,
        comparison_population=comparison_population,
        cache_manager=None  # Skip cache for diagnostic
    )

    # Step 1: Get the fan wheel data
    logger.info("\n1. FETCHING FAN WHEEL DATA...")
    wheel_data = ranker.get_fan_wheel_data(
        min_audience_pct=0.20,
        top_n_communities=10,
        comparison_pop=comparison_population
    )

    # Check for GoFundMe in the results
    gofundme_rows = wheel_data[wheel_data['MERCHANT'].str.contains('GoFundMe', case=False, na=False)]

    logger.info(f"\nFound {len(gofundme_rows)} instances of GoFundMe in fan wheel data")

    if len(gofundme_rows) > 0:
        logger.info("\nGoFundMe appears in these communities:")
        for _, row in gofundme_rows.iterrows():
            logger.info(f"  - Community: {row['COMMUNITY']}")
            logger.info(f"    Merchant: {row['MERCHANT']}")
            logger.info(f"    Behavior: {row['behavior']}")
            logger.info(f"    Community Index: {row.get('COMMUNITY_COMPOSITE_INDEX', 'N/A')}")
            logger.info(f"    Audience %: {row.get('PERC_AUDIENCE', 'N/A')}")
            logger.info("")

    # Step 2: Deep dive into communities where GoFundMe is top merchant
    logger.info("\n2. ANALYZING COMMUNITIES WHERE GOFUNDME RANKS HIGH...")

    # Get all merchants for the top communities
    communities = wheel_data['COMMUNITY'].tolist()
    all_merchants = ranker.get_top_merchants_for_communities(
        communities=communities,
        comparison_pop=comparison_population,
        top_n_per_community=5,  # Get top 5 to see ranking
        exclude_live_entertainment_sports=True
    )

    # Filter for GoFundMe
    gofundme_all = all_merchants[all_merchants['MERCHANT'].str.contains('GoFundMe', case=False, na=False)]

    if len(gofundme_all) > 0:
        logger.info("\nGoFundMe rankings across communities:")
        for community in gofundme_all['COMMUNITY'].unique():
            community_data = all_merchants[all_merchants['COMMUNITY'] == community].head(5)
            logger.info(f"\n  Community: {community}")
            for rank, (_, row) in enumerate(community_data.iterrows(), 1):
                is_gofundme = 'GoFundMe' in str(row['MERCHANT'])
                marker = " <-- GoFundMe" if is_gofundme else ""
                logger.info(f"    #{rank}: {row['MERCHANT']} (Audience: {row['PERC_AUDIENCE']:.2%}){marker}")

    # Step 3: Check for standardization issues
    logger.info("\n3. CHECKING MERCHANT NAME STANDARDIZATION...")

    # Query raw data to see original vs standardized names
    query = f"""
    SELECT DISTINCT
        MERCHANT,
        COMMUNITY,
        PERC_AUDIENCE
    FROM {ranker.merchant_view}
    WHERE 
        COMPARISON_POPULATION = '{comparison_population}'
        AND UPPER(MERCHANT) LIKE '%GOFUNDME%'
        AND COMMUNITY IN ('{("', '".join(communities))}')
    ORDER BY PERC_AUDIENCE DESC
    """

    raw_gofundme = query_to_dataframe(query)

    if not raw_gofundme.empty:
        logger.info("\nRaw GoFundMe entries from Snowflake:")
        for _, row in raw_gofundme.iterrows():
            logger.info(f"  - '{row['MERCHANT']}' in {row['COMMUNITY']} (Audience: {row['PERC_AUDIENCE']:.2%})")

    # Step 4: Check if standardization is working
    if ranker.standardizer:
        logger.info("\n4. TESTING NAME STANDARDIZATION...")
        test_names = raw_gofundme['MERCHANT'].unique().tolist() if not raw_gofundme.empty else ['GoFundMe', 'gofundme', 'Go Fund Me']

        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            name_mapping = loop.run_until_complete(ranker.standardizer.standardize_merchants(test_names))
            logger.info("\nStandardization mapping:")
            for original, standardized in name_mapping.items():
                if original != standardized:
                    logger.info(f"  '{original}' -> '{standardized}'")
                else:
                    logger.info(f"  '{original}' (no change)")
        finally:
            loop.close()

    # Step 5: Summary and recommendations
    logger.info("\n" + "=" * 80)
    logger.info("SUMMARY AND RECOMMENDATIONS")
    logger.info("=" * 80)

    if len(gofundme_rows) > 1:
        logger.info("\n✓ CONFIRMED: GoFundMe appears multiple times in the fan wheel")
        logger.info("\nThis happens because:")
        logger.info("1. GoFundMe is the top merchant for multiple communities")
        logger.info("2. Each community gets its own segment in the wheel")
        logger.info("3. The fan wheel shows the TOP merchant for each community")

        logger.info("\nPOSSIBLE SOLUTIONS:")
        logger.info("1. Exclude GoFundMe from certain communities")
        logger.info("2. Show the 2nd highest merchant if 1st is already displayed")
        logger.info("3. Add logic to ensure merchant diversity in the wheel")
        logger.info("4. This might be correct behavior - GoFundMe could legitimately be #1 for multiple fan communities")
    else:
        logger.info("\n✗ No duplicate GoFundMe found in current data")
        logger.info("The issue may have been resolved or may occur under different conditions")

    return wheel_data, gofundme_rows


def main():
    """Run the diagnostic"""
    # Carolina Panthers configuration
    # First, let's try to get the actual configuration
    try:
        from utils.team_config_manager import TeamConfigManager
        config_manager = TeamConfigManager()
        team_config = config_manager.get_team_config('carolina_panthers')

        team_view_prefix = team_config.get('view_prefix', 'V_CAROLINA_PANTHERS')
        comparison_population = team_config.get('comparison_population', 'Local Gen Pop (Excl. Panthers)')

        logger.info(f"Using team config: view_prefix={team_view_prefix}")
        logger.info(f"Using comparison_population: {comparison_population}")
    except Exception as e:
        logger.warning(f"Could not load team config: {e}")
        # Fallback values
        team_view_prefix = "V_CAROLINA_PANTHERS"
        comparison_population = "Local Gen Pop (Excl. Panthers)"
        logger.info("Using fallback configuration values")

    try:
        wheel_data, gofundme_rows = diagnose_gofundme_duplicate(
            team_view_prefix=team_view_prefix,
            comparison_population=comparison_population
        )

        # Optionally save the diagnostic data
        output_dir = Path("diagnostics")
        output_dir.mkdir(exist_ok=True)

        wheel_data.to_csv(output_dir / "panthers_fan_wheel_data.csv", index=False)
        if len(gofundme_rows) > 0:
            gofundme_rows.to_csv(output_dir / "gofundme_instances.csv", index=False)

        logger.info(f"\nDiagnostic data saved to {output_dir}/")

    except Exception as e:
        logger.error(f"Diagnostic failed: {e}", exc_info=True)


if __name__ == "__main__":
    main()