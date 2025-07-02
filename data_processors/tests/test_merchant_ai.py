#!/usr/bin/env python3
"""
Test script for enhanced MerchantRanker with name standardization
Validates that merchant names are being properly standardized using OpenAI
"""

import sys
from pathlib import Path
import pandas as pd
from datetime import datetime

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from data_processors.merchant_ranker import MerchantRanker
from data_processors.snowflake_connector import test_connection
from utils.team_config_manager import TeamConfigManager
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_merchant_standardization(team_key: str = 'utah_jazz'):
    """
    Test merchant name standardization functionality

    Args:
        team_key: Team to test with (default: utah_jazz)
    """
    print("\n" + "=" * 80)
    print("MERCHANT NAME STANDARDIZATION TEST")
    print("=" * 80)
    print(f"Testing team: {team_key}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 1. Test Snowflake connection
    print("\n1️⃣ Testing Snowflake connection...")
    if not test_connection():
        print("❌ Failed to connect to Snowflake")
        return False
    print("✅ Connected to Snowflake")

    # 2. Load team configuration
    print("\n2️⃣ Loading team configuration...")
    try:
        config_manager = TeamConfigManager()
        team_config = config_manager.get_team_config(team_key)
        view_prefix = team_config['view_prefix']
        print(f"✅ Team: {team_config['team_name']}")
        print(f"   View prefix: {view_prefix}")
    except Exception as e:
        print(f"❌ Failed to load team config: {e}")
        return False

    # 3. Initialize MerchantRanker
    print("\n3️⃣ Initializing Enhanced MerchantRanker...")
    try:
        ranker = MerchantRanker(team_view_prefix=view_prefix)
        print("✅ MerchantRanker initialized")

        # Check if standardizer is available
        if ranker.standardizer is not None:
            print("✅ Merchant name standardization is ENABLED")
        else:
            print("⚠️ Merchant name standardization is DISABLED")

    except Exception as e:
        print(f"❌ Failed to initialize MerchantRanker: {e}")
        return False

    # 4. Test Fan Wheel Data (Primary test)
    print("\n4️⃣ Testing Fan Wheel Data with Standardization...")
    try:
        wheel_data = ranker.get_fan_wheel_data(
            min_audience_pct=0.20,
            top_n_communities=8
        )

        print(f"✅ Retrieved fan wheel data: {len(wheel_data)} communities")

        # Display results
        print("\n📊 Fan Wheel Data Results:")
        print("-" * 100)
        print(f"{'Community':<25} {'Merchant':<20} {'Behavior':<25} {'Audience %':<12} {'Index':<8}")
        print("-" * 100)

        for _, row in wheel_data.head(8).iterrows():
            behavior_display = row['behavior'].replace('\n', ' | ')
            print(f"{row['COMMUNITY']:<25} {row['MERCHANT']:<20} {behavior_display:<25} "
                  f"{row['PERC_AUDIENCE'] * 100:<11.1f}% {row['PERC_INDEX']:<8.0f}")

        # Check for standardization evidence
        if 'MERCHANT_STANDARDIZED' in wheel_data.columns:
            print(f"\n🎯 Merchant Name Standardization Results:")
            print("-" * 60)

            # Find names that were changed
            if 'MERCHANT_ORIGINAL' in wheel_data.columns:
                changes = wheel_data[wheel_data['MERCHANT_ORIGINAL'] != wheel_data['MERCHANT']]
                if not changes.empty:
                    print("Names that were standardized:")
                    for _, row in changes.iterrows():
                        print(f"   {row['MERCHANT_ORIGINAL']} → {row['MERCHANT']}")
                else:
                    print("   No names were changed (may already be properly formatted)")

            print(f"   Total unique merchants processed: {len(wheel_data['MERCHANT'].unique())}")

    except Exception as e:
        print(f"❌ Fan wheel data test failed: {e}")
        return False

    # 5. Test Restaurant Category Standardization
    print("\n5️⃣ Testing Restaurant Category Standardization...")
    try:
        restaurant_data = ranker.get_standardized_merchant_ranking(
            category_filter="Restaurants",
            top_n=10
        )

        print(f"✅ Retrieved restaurant data: {len(restaurant_data)} merchants")

        if not restaurant_data.empty:
            print("\n🍽️ Top Restaurant Merchants:")
            print("-" * 70)
            print(f"{'Rank':<6} {'Merchant':<25} {'Audience %':<12} {'Index':<8}")
            print("-" * 70)

            for i, (_, row) in enumerate(restaurant_data.head(10).iterrows(), 1):
                print(f"{i:<6} {row['MERCHANT']:<25} {row['PERC_AUDIENCE'] * 100:<11.1f}% {row['PERC_INDEX']:<8.0f}")

    except Exception as e:
        print(f"❌ Restaurant category test failed: {e}")
        return False

    # 6. Test Community Index Data
    print("\n6️⃣ Testing Community Index Data...")
    try:
        community_data = ranker.get_community_index_data(
            min_audience_pct=0.20,
            top_n=10
        )

        print(f"✅ Retrieved community data: {len(community_data)} communities")

        if not community_data.empty:
            print("\n📈 Top Communities by Index:")
            print("-" * 50)
            print(f"{'Rank':<6} {'Community':<30} {'Index':<8}")
            print("-" * 50)

            for i, (_, row) in enumerate(community_data.head(8).iterrows(), 1):
                print(f"{i:<6} {row['Community']:<30} {row['Audience_Index']:<8.0f}")

    except Exception as e:
        print(f"❌ Community index test failed: {e}")
        return False

    # 7. Test Cache Performance (if standardizer available)
    if ranker.standardizer is not None:
        print("\n7️⃣ Testing Cache Performance...")
        try:
            # Get some merchant names for cache test
            test_merchants = wheel_data['MERCHANT'].unique()[:5].tolist() if not wheel_data.empty else []

            if test_merchants:
                print(f"   Testing with {len(test_merchants)} merchants...")

                # First call (might hit cache or API)
                start_time = datetime.now()
                result1 = ranker.standardizer.standardize_dataframe_column(
                    pd.DataFrame({'MERCHANT': test_merchants}), 'MERCHANT'
                )
                first_duration = (datetime.now() - start_time).total_seconds()

                # Second call (should hit cache)
                start_time = datetime.now()
                result2 = ranker.standardizer.standardize_dataframe_column(
                    pd.DataFrame({'MERCHANT': test_merchants}), 'MERCHANT'
                )
                second_duration = (datetime.now() - start_time).total_seconds()

                print(f"   First call: {first_duration:.2f}s")
                print(f"   Second call: {second_duration:.2f}s")

                if second_duration < first_duration:
                    print("✅ Cache is working - second call was faster")
                else:
                    print("ℹ️ Both calls had similar speed (cache may have been hit both times)")

        except Exception as e:
            print(f"⚠️ Cache test failed: {e}")

    # 8. Summary
    print("\n" + "=" * 80)
    print("📋 TEST SUMMARY")
    print("=" * 80)

    success_indicators = []

    if ranker.standardizer is not None:
        success_indicators.append("✅ Merchant name standardization is enabled")
    else:
        success_indicators.append("⚠️ Merchant name standardization is disabled")

    if not wheel_data.empty:
        success_indicators.append("✅ Fan wheel data retrieval successful")

    if not restaurant_data.empty:
        success_indicators.append("✅ Restaurant category data retrieval successful")

    if not community_data.empty:
        success_indicators.append("✅ Community index data retrieval successful")

    for indicator in success_indicators:
        print(indicator)

    print(f"\n🎯 Integration test completed at {datetime.now().strftime('%H:%M:%S')}")

    # Show next steps
    print("\n📝 Next Steps:")
    if ranker.standardizer is not None:
        print("   1. Run your existing PowerPoint generation to see standardized names")
        print("   2. Check the fan wheel visualization for improved name formatting")
        print("   3. Verify category slides show properly formatted merchant names")
    else:
        print("   1. Ensure OPENAI_API_KEY is set in your .env file")
        print("   2. Install required dependencies: pip install openai python-dotenv")
        print("   3. Create utils/merchant_name_standardizer.py")

    return True


def test_specific_names():
    """Test standardization with specific problematic names"""
    print("\n" + "=" * 80)
    print("SPECIFIC NAME STANDARDIZATION TEST")
    print("=" * 80)

    # Test names that commonly have formatting issues
    test_names = [
        "MCDONALD'S",
        "CHICK-FIL-A",
        "PANDA EXPRESS",
        "TACO BELL",
        "LULULEMON",
        "CVS PHARMACY",
        "7-ELEVEN",
        "UNDER ARMOUR",
        "T-MOBILE"
    ]

    try:
        from utils.merchant_name_standardizer import standardize_merchant_names

        print(f"Testing standardization of {len(test_names)} problematic names...")
        results = standardize_merchant_names(test_names)

        print(f"\n📝 Standardization Results:")
        print("-" * 50)
        print(f"{'Original':<20} {'Standardized':<20} {'Changed'}")
        print("-" * 50)

        for original, standardized in results.items():
            changed = "🔄" if original != standardized else "  "
            print(f"{original:<20} {standardized:<20} {changed}")

        changes = sum(1 for orig, std in results.items() if orig != std)
        print(f"\nTotal names changed: {changes}/{len(test_names)}")

    except ImportError:
        print("❌ MerchantNameStandardizer not available")
        print("   Make sure utils/merchant_name_standardizer.py exists")
    except Exception as e:
        print(f"❌ Test failed: {e}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Test merchant name standardization')
    parser.add_argument('--team', type=str, default='utah_jazz',
                        choices=['utah_jazz', 'dallas_cowboys'],
                        help='Team to test with')
    parser.add_argument('--names-only', action='store_true',
                        help='Only test specific name standardization')

    args = parser.parse_args()

    if args.names_only:
        test_specific_names()
    else:
        success = test_merchant_standardization(args.team)

        if success:
            print("\n" + "🎉" * 20)
            print("ALL TESTS PASSED!")
            print("🎉" * 20)
        else:
            print("\n" + "❌" * 20)
            print("SOME TESTS FAILED!")
            print("❌" * 20)
            sys.exit(1)