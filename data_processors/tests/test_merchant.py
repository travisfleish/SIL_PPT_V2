# test_restaurants_insights.py
"""
Test script for restaurants category merchant insights
"""

import sys
from pathlib import Path
import pandas as pd

# Add parent directories to path
sys.path.append(str(Path(__file__).parent.parent))
sys.path.append(str(Path(__file__).parent.parent.parent))

from data_processors.category_analyzer import CategoryAnalyzer
from data_processors.snowflake_connector import query_to_dataframe, test_connection
from utils.team_config_manager import TeamConfigManager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_restaurants_category():
    """Test Restaurants category with proper whitespace handling"""
    print(f"\n{'=' * 80}")
    print(f"TESTING RESTAURANTS MERCHANT INSIGHTS")
    print(f"{'=' * 80}")

    # Test connection
    print("\n1. Testing Snowflake connection...")
    if not test_connection():
        print("❌ Failed to connect to Snowflake")
        return None
    print("✅ Connected to Snowflake")

    # Get team configuration
    config_manager = TeamConfigManager()
    team_config = config_manager.get_team_config('utah_jazz')
    view_prefix = team_config['view_prefix']

    # Initialize analyzer
    analyzer = CategoryAnalyzer(
        team_name=team_config['team_name'],
        team_short=team_config['team_name_short'],
        league=team_config['league']
    )

    # IMPORTANT: Use TRIM in the SQL query to handle whitespace
    print("\n2. Loading Restaurants merchant data with TRIM...")
    merchant_query = f"""
    SELECT 
        TRIM(AUDIENCE) as AUDIENCE,
        TRIM(COMPARISON_POPULATION) as COMPARISON_POPULATION,
        TRIM(MERCHANT) as MERCHANT,
        TRIM(PARENT_MERCHANT) as PARENT_MERCHANT,
        TRIM(CATEGORY) as CATEGORY,
        TRIM(SUBCATEGORY) as SUBCATEGORY,
        AUDIENCE_COUNT,
        TOTAL_AUDIENCE_COUNT,
        PERC_AUDIENCE,
        AUDIENCE_TRANSACTIONS,
        AUDIENCE_TOTAL_SPEND,
        SPC,
        SPP,
        PPC,
        COMPARISON_COUNT,
        COMPARISON_TOTAL_COUNT,
        PERC_COMPARISON,
        COMPARISON_TOTAL_SPEND,
        COMPARISON_SPC,
        COMPARISON_SPP,
        COMPARISON_PPC,
        PERC_INDEX,
        SPC_INDEX,
        SPP_INDEX,
        PPC_INDEX,
        COMPOSITE_INDEX
    FROM {view_prefix}_MERCHANT_INDEXING_ALL_TIME 
    WHERE TRIM(CATEGORY) = 'Restaurants'
    """

    try:
        merchant_df = query_to_dataframe(merchant_query)
        print(f"✅ Loaded {len(merchant_df)} merchant records")

        # Show sample data
        if not merchant_df.empty:
            print("\nSample of loaded data:")
            print(f"Unique audiences: {merchant_df['AUDIENCE'].unique()}")
            print(f"Unique comparison populations: {merchant_df['COMPARISON_POPULATION'].unique()}")

            # Check Utah Jazz data
            utah_data = merchant_df[merchant_df['AUDIENCE'] == 'Utah Jazz Fans']
            print(f"\nUtah Jazz Fans records: {len(utah_data)}")

            if not utah_data.empty:
                print("\nTop 5 merchants by audience %:")
                top_5 = utah_data.nlargest(5, 'PERC_AUDIENCE')[['MERCHANT', 'PERC_AUDIENCE', 'COMPOSITE_INDEX']]
                print(top_5)

    except Exception as e:
        print(f"❌ Failed to load merchant data: {str(e)}")
        return None

    # Create minimal dataframes for other data
    category_df = pd.DataFrame()
    subcategory_df = pd.DataFrame()

    # Run the analysis
    print("\n3. Running category analysis...")
    try:
        results = analyzer.analyze_category(
            category_key='restaurants',
            category_df=category_df,
            subcategory_df=subcategory_df,
            merchant_df=merchant_df,
            validate=False
        )
        print("✅ Analysis completed successfully")

        # Display results
        print(f"\n{'=' * 60}")
        print("MERCHANT INSIGHTS:")
        print(f"{'=' * 60}")

        for i, insight in enumerate(results.get('merchant_insights', []), 1):
            print(f"\nInsight {i}: {insight}")

        # Display recommendation
        print(f"\n{'=' * 60}")
        print("SPONSORSHIP RECOMMENDATION:")
        print(f"{'=' * 60}")

        rec = results.get('recommendation')
        if rec:
            print(f"\nTarget: {rec['merchant']}")
            print(f"Composite Index: {rec['composite_index']:.0f}")
            print(f"Explanation: {rec['explanation']}")

        # Show merchant stats table
        print(f"\n{'=' * 60}")
        print("TOP 5 MERCHANTS TABLE:")
        print(f"{'=' * 60}")
        merchant_table, top_merchants = results.get('merchant_stats', (pd.DataFrame(), []))
        if not merchant_table.empty:
            print(merchant_table.to_string(index=False))

            # Also show PPC and SPC values for verification
            print(f"\n{'=' * 60}")
            print("MERCHANT METRICS FOR VERIFICATION:")
            print(f"{'=' * 60}")
            print(f"{'Merchant':<25} {'PPC':>10} {'SPC':>12} {'Composite':>12}")
            print("-" * 60)

            # Get comparison data for top 5 merchants
            for merchant in top_merchants:
                merchant_data = merchant_df[
                    (merchant_df['MERCHANT'] == merchant) &
                    (merchant_df['AUDIENCE'] == 'Utah Jazz Fans') &
                    (merchant_df['COMPARISON_POPULATION'] == 'Local Gen Pop (Excl. Jazz)')
                    ]
                if not merchant_data.empty:
                    row = merchant_data.iloc[0]
                    ppc = float(row.get('PPC', 0))
                    spc = float(row.get('SPC', 0))
                    composite = float(row.get('COMPOSITE_INDEX', 0))
                    print(f"{merchant:<25} {ppc:>10.1f} ${spc:>11.2f} {composite:>12.1f}")

            # Also check NBA comparison for insight 4
            print(f"\n{'=' * 60}")
            print("NBA COMPARISON FOR VERIFICATION:")
            print(f"{'=' * 60}")
            print(f"{'Merchant':<25} {'NBA Index':>10} {'% More Likely':>15}")
            print("-" * 60)

            for merchant in top_merchants:
                nba_data = merchant_df[
                    (merchant_df['MERCHANT'] == merchant) &
                    (merchant_df['AUDIENCE'] == 'Utah Jazz Fans') &
                    (merchant_df['COMPARISON_POPULATION'] == 'NBA Fans')
                    ]
                if not nba_data.empty:
                    row = nba_data.iloc[0]
                    perc_index = float(row.get('PERC_INDEX', 100))
                    more_likely = perc_index - 100
                    print(f"{merchant:<25} {perc_index:>10.1f} {more_likely:>14.0f}%")

    except Exception as e:
        print(f"❌ Analysis failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

    return results


def verify_category_data():
    """Quick check to verify restaurants data exists"""
    print("\n" + "=" * 80)
    print("VERIFYING RESTAURANTS CATEGORY DATA")
    print("=" * 80)

    if not test_connection():
        return

    # Check restaurants data
    queries = [
        ("RESTAURANTS COUNT", """
        SELECT COUNT(*) as count
        FROM V_UTAH_JAZZ_SIL_MERCHANT_INDEXING_ALL_TIME
        WHERE TRIM(CATEGORY) = 'Restaurants'
        AND TRIM(AUDIENCE) = 'Utah Jazz Fans'
        """),

        ("TOP RESTAURANTS BY AUDIENCE", """
        SELECT 
            MERCHANT,
            PERC_AUDIENCE * 100 as PERCENT_OF_FANS,
            COMPOSITE_INDEX
        FROM V_UTAH_JAZZ_SIL_MERCHANT_INDEXING_ALL_TIME
        WHERE TRIM(CATEGORY) = 'Restaurants'
        AND TRIM(AUDIENCE) = 'Utah Jazz Fans'
        AND TRIM(COMPARISON_POPULATION) = 'Local Gen Pop (Excl. Jazz)'
        ORDER BY PERC_AUDIENCE DESC
        LIMIT 5
        """),

        ("CHECK CATEGORY VALUES", """
        SELECT DISTINCT 
            CATEGORY,
            COUNT(*) as count
        FROM V_UTAH_JAZZ_SIL_MERCHANT_INDEXING_ALL_TIME
        WHERE CATEGORY LIKE '%Restaurant%'
        GROUP BY CATEGORY
        """)
    ]

    for label, query in queries:
        print(f"\n{label}:")
        try:
            result = query_to_dataframe(query)
            print(result)
        except Exception as e:
            print(f"Error: {e}")


def main():
    """Main test function"""
    print("\n🧪 RESTAURANTS MERCHANT INSIGHTS TEST")
    print("=" * 80)

    # First verify the data exists
    verify_category_data()

    # Then run the test
    test_restaurants_category()


if __name__ == "__main__":
    main()