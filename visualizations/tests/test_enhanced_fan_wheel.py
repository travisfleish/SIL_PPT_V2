# test_enhanced_fan_wheel.py
"""
Comprehensive test script for the enhanced fan wheel with logo support
Tests both real Snowflake data and sample data scenarios
"""

import sys
from pathlib import Path
import pandas as pd
import logging

# Add parent directories to path
sys.path.append(str(Path(__file__).parent))

from visualizations.fan_wheel import FanWheel, create_fan_wheel_from_data
from data_processors.merchant_ranker import MerchantRanker
from utils.team_config_manager import TeamConfigManager

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)


def test_logo_manager_standalone():
    """Test the LogoManager functionality independently"""
    print(f"\n{'=' * 70}")
    print("TEST 1: LOGO MANAGER STANDALONE")
    print(f"{'=' * 70}")

    from visualizations.fan_wheel import LogoManager

    # Initialize logo manager
    logo_mgr = LogoManager()

    print(f"Logo directory: {logo_mgr.logo_dir}")
    print(f"Directory exists: {logo_mgr.logo_dir.exists()}")

    # List available logos by scanning directory
    available_logos = []
    if logo_mgr.logo_dir.exists():
        for ext in logo_mgr.supported_formats:
            for logo_file in logo_mgr.logo_dir.glob(f"*{ext}"):
                available_logos.append(logo_file.stem)

    available_logos = sorted(set(available_logos))  # Remove duplicates

    print(f"\nAvailable logos ({len(available_logos)}):")
    for logo in available_logos:
        print(f"  ✅ {logo}")

    if not available_logos:
        print("  ❌ No logos found in directory!")
        print(f"  📁 Expected directory: {logo_mgr.logo_dir}")
        # Show what files ARE in the directory
        if logo_mgr.logo_dir.exists():
            all_files = list(logo_mgr.logo_dir.glob('*'))
            if all_files:
                print(f"  📄 Files found: {[f.name for f in all_files[:5]]}")
            else:
                print(f"  📄 Directory is empty")
        return False

    # Test logo loading with different variations
    test_merchants = [
        'lululemon',  # Should work if file exists
        'Lululemon',  # Test case variations
        'LULULEMON',
        'kwik trip',  # Test with spaces
        'AutoZone',  # Test different merchant
        'NonExistent Brand'  # Should fail gracefully
    ]

    print(f"\nTesting logo loading:")
    results = {}
    for merchant in test_merchants:
        logo = logo_mgr.get_logo(merchant)
        status = "✅ Found" if logo is not None else "❌ Missing"
        print(f"  {merchant:20}: {status}")
        results[merchant] = logo is not None

        # Show attempted filename variations for missing logos
        if logo is None and merchant != 'NonExistent Brand':
            variations = logo_mgr._generate_search_names(merchant)
            print(f"    🔍 Tried: {', '.join(variations[:3])}...")

    success_rate = sum(results.values()) / len(results) * 100
    print(f"\nLogo loading success rate: {success_rate:.1f}%")

    return len(available_logos) > 0


def test_fan_wheel_sample_data():
    """Test fan wheel with sample data"""
    print(f"\n{'=' * 70}")
    print("TEST 2: FAN WHEEL WITH SAMPLE DATA")
    print(f"{'=' * 70}")

    # Create sample data that includes lululemon if available
    sample_data = pd.DataFrame({
        'COMMUNITY': [
            'Athleisure Enthusiasts',
            'Cost Conscious',
            'Travelers',
            'Beauty Enthusiasts',
            'Gaming Enthusiasts'
        ],
        'MERCHANT': [
            'lululemon',  # Should have logo
            'Kwik Trip',  # Might have logo
            'Southwest',  # Probably no logo
            'Ulta',  # Might have logo
            'GameStop'  # Probably no logo
        ],
        'behavior': [
            'Shops at\nlululemon',
            'Fills up at\nKwik Trip',
            'Flies with\nSouthwest',
            'Beauty at\nUlta',
            'Games at\nGameStop'
        ],
        'PERC_INDEX': [150, 140, 130, 120, 110]
    })

    print("Sample data:")
    print(sample_data[['MERCHANT', 'behavior']].to_string(index=False))

    # Test with Utah Jazz team config
    try:
        config_manager = TeamConfigManager()
        team_config = config_manager.get_team_config('utah_jazz')
        print(f"\nUsing team: {team_config['team_name']}")
    except Exception as e:
        print(f"⚠️  Using fallback team config: {e}")
        team_config = {
            'team_name': 'Test Team',
            'team_name_short': 'Test',
            'colors': {
                'primary': '#002B5C',
                'secondary': '#F9A01B',
                'accent': '#4169E1'
            }
        }

    try:
        # Test with logos enabled
        print(f"\n🎨 Creating fan wheel with logos enabled...")
        fan_wheel = FanWheel(team_config, enable_logos=True)

        # Generate logo report
        logo_report = fan_wheel.generate_logo_report(sample_data)
        print(f"\nLogo Report:")
        print(f"  📊 Total merchants: {logo_report['total_merchants']}")
        print(f"  ✅ With logos: {logo_report['with_logos']}")
        print(f"  ❌ Missing logos: {logo_report['missing_logos']}")
        print(f"  📈 Coverage: {logo_report['coverage_percentage']:.1f}%")

        if logo_report['missing_list']:
            print(f"  🔍 Missing: {', '.join(logo_report['missing_list'])}")

        # Create visualization
        output_path = Path('test_sample_fan_wheel.png')
        result_path = fan_wheel.create(sample_data, output_path)

        print(f"\n✅ Fan wheel created: {result_path}")
        print(f"   File exists: {result_path.exists()}")

        if result_path.exists():
            file_size = result_path.stat().st_size / 1024  # KB
            print(f"   File size: {file_size:.1f} KB")

        # Test with logos disabled for comparison
        print(f"\n🎨 Creating fan wheel with logos disabled...")
        fan_wheel_no_logos = FanWheel(team_config, enable_logos=False)
        output_path_no_logos = Path('test_sample_fan_wheel_no_logos.png')
        result_path_no_logos = fan_wheel_no_logos.create(sample_data, output_path_no_logos)

        print(f"✅ Fan wheel (no logos) created: {result_path_no_logos}")

        return True

    except Exception as e:
        print(f"❌ Error creating fan wheel: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_fan_wheel_real_data(team_key: str = 'utah_jazz'):
    """Test fan wheel with real Snowflake data"""
    print(f"\n{'=' * 70}")
    print(f"TEST 3: FAN WHEEL WITH REAL DATA - {team_key.upper()}")
    print(f"{'=' * 70}")

    try:
        # Get team configuration
        config_manager = TeamConfigManager()
        team_config = config_manager.get_team_config(team_key)

        print(f"Team: {team_config['team_name']}")
        print(f"View prefix: {team_config['view_prefix']}")

        # Initialize merchant ranker
        print(f"\n🔌 Connecting to Snowflake...")
        ranker = MerchantRanker(team_view_prefix=team_config['view_prefix'])

        # Test data availability
        print(f"📊 Checking data availability...")
        wheel_data = ranker.get_fan_wheel_data(
            min_audience_pct=0.20,
            top_n_communities=8  # Smaller number for testing
        )

        if wheel_data.empty:
            print("❌ No fan wheel data found!")
            return False

        print(f"✅ Found {len(wheel_data)} merchant-community pairs")
        print(f"\nTop merchants in data:")
        for i, (_, row) in enumerate(wheel_data.head(5).iterrows(), 1):
            print(f"  {i}. {row['MERCHANT']} ({row['COMMUNITY']})")

        # Create enhanced fan wheel using convenience function
        print(f"\n🎨 Creating enhanced fan wheel...")
        output_path = Path(f'{team_key}_real_data_fan_wheel.png')

        wheel_path = create_fan_wheel_from_data(
            ranker, team_config,
            output_path=output_path,
            enable_logos=True
        )

        print(f"✅ Real data fan wheel created: {wheel_path}")
        print(f"   File exists: {wheel_path.exists()}")

        if wheel_path.exists():
            file_size = wheel_path.stat().st_size / 1024  # KB
            print(f"   File size: {file_size:.1f} KB")

        # Generate detailed logo report
        fan_wheel = FanWheel(team_config, enable_logos=True)
        logo_report = fan_wheel.generate_logo_report(wheel_data)

        print(f"\n📈 Final Logo Report:")
        print(f"   Total merchants: {logo_report['total_merchants']}")
        print(f"   With logos: {logo_report['with_logos']}")
        print(f"   Coverage: {logo_report['coverage_percentage']:.1f}%")

        if logo_report['missing_list']:
            print(f"\n📝 Consider adding these logo files:")
            for merchant in logo_report['missing_list'][:10]:  # Show first 10
                suggested_filename = merchant.lower().replace(' ', '_').replace("'", "")
                print(f"   • {merchant} → {suggested_filename}.png")

            if len(logo_report['missing_list']) > 10:
                print(f"   ... and {len(logo_report['missing_list']) - 10} more")

        return True

    except Exception as e:
        print(f"❌ Error with real data: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_performance_comparison():
    """Test performance with and without logos"""
    print(f"\n{'=' * 70}")
    print("TEST 4: PERFORMANCE COMPARISON")
    print(f"{'=' * 70}")

    # Create larger sample data for performance testing
    import time

    sample_data = pd.DataFrame({
        'COMMUNITY': [f'Community {i}' for i in range(10)],
        'MERCHANT': [f'Merchant {i}' for i in range(10)],
        'behavior': [f'Behavior {i}' for i in range(10)],
        'PERC_INDEX': list(range(150, 140, -1))
    })

    team_config = {
        'team_name': 'Performance Test',
        'team_name_short': 'Test',
        'colors': {'primary': '#002B5C', 'secondary': '#F9A01B', 'accent': '#4169E1'}
    }

    # Test with logos
    print("⏱️  Testing with logos enabled...")
    start_time = time.time()
    fan_wheel_logos = FanWheel(team_config, enable_logos=True)
    path_logos = fan_wheel_logos.create(sample_data, Path('perf_test_logos.png'))
    time_with_logos = time.time() - start_time

    # Test without logos
    print("⏱️  Testing with logos disabled...")
    start_time = time.time()
    fan_wheel_no_logos = FanWheel(team_config, enable_logos=False)
    path_no_logos = fan_wheel_no_logos.create(sample_data, Path('perf_test_no_logos.png'))
    time_without_logos = time.time() - start_time

    print(f"\n📊 Performance Results:")
    print(f"   With logos:    {time_with_logos:.3f} seconds")
    print(f"   Without logos: {time_without_logos:.3f} seconds")
    print(f"   Overhead:      {time_with_logos - time_without_logos:.3f} seconds")
    print(f"   Ratio:         {time_with_logos / time_without_logos:.2f}x")

    # Clean up performance test files
    Path('perf_test_logos.png').unlink(missing_ok=True)
    Path('perf_test_no_logos.png').unlink(missing_ok=True)

    return True


def main():
    """Run all tests"""
    print("🧪 ENHANCED FAN WHEEL COMPREHENSIVE TEST SUITE")
    print("=" * 80)

    test_results = {}

    # Test 1: Logo Manager
    test_results['logo_manager'] = test_logo_manager_standalone()

    # Test 2: Sample Data
    test_results['sample_data'] = test_fan_wheel_sample_data()

    # Test 3: Real Data (only if sample data works)
    if test_results['sample_data']:
        try:
            test_results['real_data'] = test_fan_wheel_real_data('utah_jazz')
        except Exception as e:
            print(f"⚠️  Skipping real data test: {e}")
            test_results['real_data'] = False
    else:
        test_results['real_data'] = False

    # Test 4: Performance
    test_results['performance'] = test_performance_comparison()

    # Summary
    print(f"\n{'=' * 80}")
    print("🏁 TEST SUMMARY")
    print(f"{'=' * 80}")

    passed = sum(test_results.values())
    total = len(test_results)

    for test_name, result in test_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {test_name.replace('_', ' ').title():20}: {status}")

    print(f"\nOverall: {passed}/{total} tests passed ({passed / total * 100:.1f}%)")

    if passed == total:
        print("\n🎉 All tests passed! Your enhanced fan wheel is working perfectly!")
        print("\n📁 Generated test files:")
        print("   • test_sample_fan_wheel.png")
        print("   • test_sample_fan_wheel_no_logos.png")
        if test_results['real_data']:
            print("   • utah_jazz_real_data_fan_wheel.png")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Check the error messages above.")

    return passed == total


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)