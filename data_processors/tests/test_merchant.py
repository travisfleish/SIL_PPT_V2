#!/usr/bin/env python3
"""
Simple test script to validate MerchantRanker data
Tests key functionality including Live Entertainment Seekers filtering
"""

import pandas as pd
from datetime import datetime
from data_processors.merchant_ranker import MerchantRanker
from utils.team_config_manager import TeamConfigManager


def test_merchant_ranker(team_key: str = 'utah_jazz'):
    """Test merchant ranker for a specific team"""

    print(f"\n{'=' * 80}")
    print(f"Testing MerchantRanker for {team_key.replace('_', ' ').title()}")
    print(f"{'=' * 80}")

    # Get team configuration
    config = TeamConfigManager()
    team_config = config.get_team_config(team_key)
    view_prefix = team_config['view_prefix']
    comparison_pop = team_config['comparison_population']

    print(f"\nTeam: {team_config['team_name']}")
    print(f"View Prefix: {view_prefix}")
    print(f"Comparison Population: {comparison_pop}")

    # Initialize ranker
    ranker = MerchantRanker(team_view_prefix=view_prefix)

    # Test 1: Get top communities
    print(f"\n{'─' * 60}")
    print("TEST 1: Top Communities (min 20% audience)")
    print(f"{'─' * 60}")

    try:
        communities_df = ranker.get_top_communities(
            min_audience_pct=0.20,
            comparison_pop=comparison_pop
        )

        if communities_df.empty:
            print("❌ No communities found!")
        else:
            print(f"✅ Found {len(communities_df)} communities\n")
            print(f"{'Rank':<5} {'Community':<35} {'Audience %':<12} {'Index':<10}")
            print(f"{'-' * 5} {'-' * 35} {'-' * 12} {'-' * 10}")

            for i, row in communities_df.iterrows():
                print(
                    f"{i + 1:<5} {row['COMMUNITY']:<35} {row['PERC_AUDIENCE']:>10.2%} {row['COMPOSITE_INDEX']:>10.0f}")

    except Exception as e:
        print(f"❌ Error getting communities: {e}")
        return

    # Test 2: Get fan wheel data (all top 10 communities with merchants)
    print(f"\n{'─' * 60}")
    print("TEST 2: Fan Wheel Data - Top 10 Communities & Their Top Merchants")
    print(f"{'─' * 60}")

    try:
        wheel_data = ranker.get_fan_wheel_data(min_audience_pct=0.20, top_n_communities=10)

        if wheel_data.empty:
            print("❌ No fan wheel data found!")
        else:
            print(f"✅ Found {len(wheel_data)} community-merchant pairs\n")

            # Check if Live Entertainment Seekers is present
            has_les = 'Live Entertainment Seekers' in wheel_data['COMMUNITY'].values
            if has_les:
                print("🎭 Live Entertainment Seekers Check:")
                les_data = wheel_data[wheel_data['COMMUNITY'] == 'Live Entertainment Seekers'].iloc[0]
                print(f"   Merchant: {les_data['MERCHANT']}")
                print(f"   Subcategory: {les_data['SUBCATEGORY']}")

                # Check if it's NOT professional sports
                if 'professional sports' not in les_data['SUBCATEGORY'].lower():
                    print("   ✅ CORRECT: Not a professional sports venue")
                else:
                    print("   ❌ ERROR: Professional sports venue still showing!")

            print(f"\n{'#':<3} {'Community':<35} {'Merchant':<30} {'Audience %':<12} {'Behavior':<25}")
            print(f"{'-' * 3} {'-' * 35} {'-' * 30} {'-' * 12} {'-' * 25}")

            # Sort by community index (should already be sorted, but making sure)
            wheel_data_sorted = wheel_data.sort_values('COMMUNITY_COMPOSITE_INDEX', ascending=False)

            for i, row in enumerate(wheel_data_sorted.iterrows(), 1):
                _, data = row
                behavior_text = data['behavior'].replace('\n', ' ')
                print(
                    f"{i:<3} {data['COMMUNITY']:<35} {data['MERCHANT']:<30} {data['PERC_AUDIENCE']:>10.2%} {behavior_text:<25}")

    except Exception as e:
        print(f"❌ Error getting fan wheel data: {e}")

    # Test 3: Get community index data
    print(f"\n{'─' * 60}")
    print("TEST 3: Community Index Data (for bar chart)")
    print(f"{'─' * 60}")

    try:
        index_data = ranker.get_community_index_data(min_audience_pct=0.20)

        if index_data.empty:
            print("❌ No index data found!")
        else:
            print(f"✅ Found {len(index_data)} communities for index chart\n")

            # Show top 5
            print(f"{'Community':<35} {'Audience Index':<15}")
            print(f"{'-' * 35} {'-' * 15}")

            for _, row in index_data.head(5).iterrows():
                print(f"{row['Community']:<35} {row['Audience_Index']:>10.0f}")

    except Exception as e:
        print(f"❌ Error getting index data: {e}")

    # Summary
    print(f"\n{'─' * 60}")
    print("SUMMARY")
    print(f"{'─' * 60}")

    print(f"✓ Approved communities loaded: {len(ranker.approved_communities)}")
    print(f"✓ Community actions loaded: {len(ranker.community_actions)}")
    print(f"✓ Community view: {ranker.community_view}")
    print(f"✓ Merchant view: {ranker.merchant_view}")


def validate_all_teams():
    """Run validation for all configured teams"""

    print("\n🏆 MERCHANT RANKER VALIDATION")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    teams = ['utah_jazz', 'dallas_cowboys']

    for team in teams:
        try:
            test_merchant_ranker(team)
        except Exception as e:
            print(f"\n❌ Critical error testing {team}: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n✅ Validation complete at {datetime.now().strftime('%H:%M:%S')}")


def quick_check():
    """Quick check showing all top 10 communities and their merchants"""

    print("\n⚡ QUICK CHECK - TOP 10 COMMUNITIES & MERCHANTS")
    print("=" * 100)

    for team_key in ['utah_jazz', 'dallas_cowboys']:
        try:
            config = TeamConfigManager()
            team_config = config.get_team_config(team_key)
            ranker = MerchantRanker(team_view_prefix=team_config['view_prefix'])

            # Get data
            wheel_data = ranker.get_fan_wheel_data(min_audience_pct=0.20, top_n_communities=10)

            print(f"\n{team_config['team_name'].upper()}")
            print("-" * 100)

            if wheel_data.empty:
                print("  ❌ No data found!")
            else:
                # Sort by composite index
                wheel_data_sorted = wheel_data.sort_values('COMMUNITY_COMPOSITE_INDEX', ascending=False)

                print(f"{'#':<3} {'Community':<35} {'Top Merchant':<30} {'Index':<8}")
                print(f"{'-' * 3} {'-' * 35} {'-' * 30} {'-' * 8}")

                for i, row in enumerate(wheel_data_sorted.iterrows(), 1):
                    _, data = row
                    # Mark Live Entertainment if it's not sports
                    marker = ""
                    if data['COMMUNITY'] == 'Live Entertainment Seekers':
                        if 'professional sports' not in data['SUBCATEGORY'].lower():
                            marker = " ✓"
                        else:
                            marker = " ✗"

                    print(
                        f"{i:<3} {data['COMMUNITY']:<35} {data['MERCHANT']:<30} {data['COMMUNITY_COMPOSITE_INDEX']:>6.0f}{marker}")

        except Exception as e:
            print(f"\n{team_key}: ERROR - {e}")


if __name__ == "__main__":
    # Quick check first
    quick_check()

    # Then full validation
    print("\n" + "=" * 80)
    user_input = input("\nRun full validation? (y/n): ")

    if user_input.lower() == 'y':
        validate_all_teams()
    else:
        print("Skipping full validation.")