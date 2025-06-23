# test_team_views.py
"""
Test script to verify team views exist in Snowflake using the config file
"""

from utils.team_config_manager import TeamConfigManager
from data_processors.snowflake_connector import query_to_dataframe
import pandas as pd


def test_team_views():
    print("🔍 Testing Team Views from Config File")
    print("=" * 60)

    # Initialize the config manager
    config = TeamConfigManager()

    # Get list of teams
    teams = config.list_teams()
    print(f"\n📋 Teams in config: {', '.join(teams)}")

    # Test each team
    for team_key in teams:
        print(f"\n\n🏀 Testing {config.get_team_config(team_key)['team_name']}")
        print("-" * 40)

        # Get all views for this team
        views = config.get_all_views_for_team(team_key)

        # Check which views exist
        existing_views = []
        missing_views = []

        for view_type, view_name in views.items():
            try:
                # Simple query to check if view exists and has data
                query = f"SELECT COUNT(*) as row_count FROM {view_name} LIMIT 1"
                df = query_to_dataframe(query)
                row_count = df['ROW_COUNT'].iloc[0]
                existing_views.append(f"✅ {view_type}: {row_count:,} rows")
            except Exception as e:
                if "does not exist" in str(e):
                    missing_views.append(f"❌ {view_type}: View doesn't exist")
                else:
                    missing_views.append(f"⚠️  {view_type}: Error - {str(e)[:50]}...")

        # Print results
        if existing_views:
            print("\nExisting views:")
            for view in existing_views:
                print(f"  {view}")

        if missing_views:
            print("\nMissing/Error views:")
            for view in missing_views:
                print(f"  {view}")

        # Summary
        print(f"\nSummary: {len(existing_views)}/{len(views)} views available")


def quick_test():
    """Even simpler test - just check if we can build view names correctly"""
    print("🚀 Quick Config Test")
    print("=" * 40)

    config = TeamConfigManager()

    # Test Utah Jazz
    print("\nUtah Jazz views:")
    jazz_community = config.get_view_name('utah_jazz', 'community_all_time')
    jazz_merchant = config.get_view_name('utah_jazz', 'merchant_all_time')
    print(f"  Community: {jazz_community}")
    print(f"  Merchant: {jazz_merchant}")

    # Test Dallas Cowboys
    print("\nDallas Cowboys views:")
    cowboys_community = config.get_view_name('dallas_cowboys', 'community_all_time')
    print(f"  Community: {cowboys_community}")

    print("\n✅ Config file working correctly!")


if __name__ == "__main__":
    # Run the quick test first
    quick_test()

    print("\n" + "=" * 60 + "\n")

    # Then run the full database test
    user_input = input("Run full database test? (y/n): ")
    if user_input.lower() == 'y':
        test_team_views()