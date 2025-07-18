#!/usr/bin/env python3
"""
Check the exact implementation of get_top_communities and test it
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from data_processors.merchant_ranker import MerchantRanker
from data_processors.snowflake_connector import query_to_dataframe


def test_merchant_ranker_directly():
    """Test MerchantRanker directly for both teams"""

    print("\n🔍 Testing MerchantRanker.get_top_communities() Directly")
    print("=" * 80)

    teams = [
        ('Utah Jazz', 'V_UTAH_JAZZ_SIL_'),
        ('Carolina Panthers', 'V_CAROLINA_PANTHERS_SIL_')
    ]

    for team_name, view_prefix in teams:
        print(f"\n{'=' * 40}")
        print(f"📊 {team_name}")
        print(f"{'=' * 40}")

        try:
            # Initialize MerchantRanker
            ranker = MerchantRanker(team_view_prefix=view_prefix)
            print(f"✅ MerchantRanker initialized with prefix: {view_prefix}")

            # Call get_top_communities
            print("\nCalling get_top_communities()...")
            communities_df = ranker.get_top_communities(
                min_audience_pct=0.20,
                top_n=10
            )

            print(f"✅ Returned {len(communities_df)} communities")

            if len(communities_df) > 0:
                print("\nTop 5 communities:")
                for idx, row in communities_df.head().iterrows():
                    print(f"  - {row['COMMUNITY']}: {row['PERC_AUDIENCE']:.3f} ({row['PERC_AUDIENCE'] * 100:.1f}%)")

        except Exception as e:
            print(f"❌ Error: {str(e)}")
            import traceback
            traceback.print_exc()


def check_approved_communities_filter():
    """Check if approved communities is filtering out Panthers"""

    print("\n\n🔍 Checking Approved Communities Filter")
    print("=" * 80)

    # Check what happens without the filter
    query_template = """
    SELECT 
        COMMUNITY,
        MAX(PERC_AUDIENCE) as MAX_PERC_AUDIENCE
    FROM {view}
    WHERE PERC_AUDIENCE >= 0.20
    GROUP BY COMMUNITY
    ORDER BY MAX_PERC_AUDIENCE DESC
    """

    teams = [
        ('Utah Jazz', 'V_UTAH_JAZZ_SIL_COMMUNITY_INDEXING_ALL_TIME'),
        ('Carolina Panthers', 'V_CAROLINA_PANTHERS_SIL_COMMUNITY_INDEXING_ALL_TIME')
    ]

    for team_name, view in teams:
        print(f"\n{team_name} - Communities with PERC_AUDIENCE >= 0.20:")

        try:
            df = query_to_dataframe(query_template.format(view=view))
            print(f"  Total: {len(df)} communities")

            # Show top 10
            for _, row in df.head(10).iterrows():
                print(f"  - {row['COMMUNITY']}: {row['MAX_PERC_AUDIENCE']:.3f}")

        except Exception as e:
            print(f"  ❌ Error: {str(e)}")


def check_comparison_population_issue():
    """Check if comparison_population is the issue"""

    print("\n\n🔍 Checking Comparison Population Filter")
    print("=" * 80)

    # The get_top_communities method might be filtering by comparison_pop
    # Line shows: comparison_pop: str = "Local Gen Pop (Excl. Jazz)"

    teams = [
        ('Utah Jazz', 'V_UTAH_JAZZ_SIL_COMMUNITY_INDEXING_ALL_TIME', 'Local Gen Pop (Excl. Jazz)'),
        ('Carolina Panthers', 'V_CAROLINA_PANTHERS_SIL_COMMUNITY_INDEXING_ALL_TIME', 'Local Gen Pop (Excl. Panthers)')
    ]

    for team_name, view, comp_pop in teams:
        print(f"\n{team_name}:")

        # Check with exact comparison population
        query = f"""
        SELECT COUNT(*) as cnt
        FROM {view}
        WHERE PERC_AUDIENCE >= 0.20
        AND COMPARISON_POPULATION = '{comp_pop}'
        """

        try:
            df = query_to_dataframe(query)
            print(f"  With comparison_pop = '{comp_pop}': {df['cnt'][0]} rows")
        except Exception as e:
            print(f"  ❌ Error: {str(e)}")

        # Check what comparison populations exist
        query2 = f"""
        SELECT DISTINCT COMPARISON_POPULATION, COUNT(*) as cnt
        FROM {view}
        WHERE PERC_AUDIENCE >= 0.20
        GROUP BY COMPARISON_POPULATION
        """

        try:
            df = query_to_dataframe(query2)
            print("  Available comparison populations:")
            for _, row in df.iterrows():
                print(f"    - {row['COMPARISON_POPULATION']}: {row['cnt']} rows")
        except Exception as e:
            print(f"  ❌ Error: {str(e)}")


if __name__ == "__main__":
    test_merchant_ranker_directly()
    check_approved_communities_filter()
    check_comparison_population_issue()

    print("\n\n💡 Key Questions:")
    print("=" * 80)
    print("""
1. Does MerchantRanker return different results for Panthers?
2. Is the approved communities filter removing Panthers communities?
3. Is the comparison_population filter using the wrong value?
4. Is there an error being silently caught somewhere?
""")