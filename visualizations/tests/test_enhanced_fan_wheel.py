#!/usr/bin/env python3
"""
Test script for Fan Wheel visualization with molly.png logo
Tests various scenarios including logo loading, data generation, and error handling
"""

import pandas as pd
from pathlib import Path
import logging
import sys
from PIL import Image
import numpy as np

# Add project root to path if needed
project_root = Path(__file__).parent
if project_root not in sys.path:
    sys.path.insert(0, str(project_root))

from visualizations.fan_wheel import FanWheel, LogoManager

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def generate_test_data():
    """Generate sample fan wheel data for testing"""
    test_data = pd.DataFrame([
        {
            'COMMUNITY': 'Live Entertainment Seekers',
            'MERCHANT': 'Southwest',
            'behavior': 'Flys with\nSouthwest',
            'PERC_INDEX': 571
        },
        {
            'COMMUNITY': 'Cost Conscious',
            'MERCHANT': 'AutoZone',
            'behavior': 'Shops at\nAutoZone',
            'PERC_INDEX': 470
        },
        {
            'COMMUNITY': 'Travelers',
            'MERCHANT': 'Ulta',
            'behavior': 'Beauty at\nUlta',
            'PERC_INDEX': 462
        },
        {
            'COMMUNITY': 'Gen Z Brand Shoppers',
            'MERCHANT': "Binny's",
            'behavior': "Drinks\nfrom\nBinny's",
            'PERC_INDEX': 460
        },
        {
            'COMMUNITY': 'Beauty Enthusiasts',
            'MERCHANT': 'Klarna',
            'behavior': 'Pays\nwith\nKlarna',
            'PERC_INDEX': 445
        },
        {
            'COMMUNITY': 'Movie Buffs',
            'MERCHANT': 'Wayfair',
            'behavior': 'Decorates\nwith\nWayfair',
            'PERC_INDEX': 445
        },
        {
            'COMMUNITY': 'Fans of Men\'s Sports',
            'MERCHANT': 'GrubHub',
            'behavior': 'Delivery\nwith\nGrubHub',
            'PERC_INDEX': 445
        },
        {
            'COMMUNITY': 'Sports Streamer',
            'MERCHANT': 'Jewel-Osco',
            'behavior': 'Groceries at\nJewel-Osco',
            'PERC_INDEX': 439
        },
        {
            'COMMUNITY': 'Gamers',
            'MERCHANT': 'Krispy Kreme',
            'behavior': 'Indulges\nat Krispy\nKreme',
            'PERC_INDEX': 435
        },
        {
            'COMMUNITY': 'Pet Owners',
            'MERCHANT': 'Kwik Trip',
            'behavior': 'Fills up at\nKwik Trip',
            'PERC_INDEX': 432
        }
    ])
    return test_data


def test_basic_fan_wheel():
    """Test basic fan wheel generation"""
    print("\n=== Test 1: Basic Fan Wheel Generation ===")

    # Team configuration
    team_config = {
        'team_name': 'Utah Jazz',
        'team_name_short': 'Jazz',
        'colors': {
            'primary': '#002244',
            'secondary': '#FFB612',
            'accent': '#4169E1'
        }
    }

    # Generate test data
    wheel_data = generate_test_data()

    # Create fan wheel
    fan_wheel = FanWheel(team_config, enable_logos=True)

    try:
        output_path = Path('test_outputs/test_fan_wheel_basic.png')
        output_path.parent.mkdir(exist_ok=True)

        result = fan_wheel.create(wheel_data, output_path)
        print(f"✓ Fan wheel created successfully: {result}")
        return True
    except Exception as e:
        print(f"✗ Fan wheel creation failed: {e}")
        logger.exception("Fan wheel creation error")
        return False


def test_logo_loading():
    """Test logo loading functionality"""
    print("\n=== Test 2: Logo Loading ===")

    # Test logo manager
    logo_manager = LogoManager()

    # Test finding molly.png
    test_paths = [
        Path('assets/logos/molly.png'),
        Path('assets/molly.png'),
        Path('molly.png')
    ]

    found = False
    for path in test_paths:
        if path.exists():
            print(f"✓ Found molly.png at: {path}")
            found = True

            # Try loading it
            try:
                img = Image.open(path)
                print(f"  - Image mode: {img.mode}")
                print(f"  - Image size: {img.size}")
                found = True
            except Exception as e:
                print(f"  ✗ Failed to load image: {e}")

    if not found:
        print("✗ molly.png not found in expected locations")
        print("  Please ensure molly.png is in one of these locations:")
        for path in test_paths:
            print(f"    - {path}")

    # Test merchant logos
    print("\n  Testing merchant logo availability:")
    available = logo_manager.list_available_logos()
    print(f"  Found {len(available)} merchant logos")

    return found


def test_custom_logo():
    """Test fan wheel with custom center logo"""
    print("\n=== Test 3: Custom Center Logo ===")

    team_config = {
        'team_name': 'Utah Jazz',
        'team_name_short': 'SKY',  # Changed to match the fan wheel
        'colors': {
            'primary': '#002244',
            'secondary': '#FFB612',
            'accent': '#4169E1'
        }
    }

    wheel_data = generate_test_data()
    fan_wheel = FanWheel(team_config, enable_logos=True)

    # Try to load molly.png manually
    custom_logo = None
    for path in [Path('assets/logos/molly.png'), Path('assets/molly.png'), Path('molly.png')]:
        if path.exists():
            try:
                custom_logo = Image.open(path)
                print(f"✓ Loaded custom logo from {path}")
                break
            except Exception as e:
                print(f"✗ Failed to load {path}: {e}")

    try:
        output_path = Path('test_outputs/test_fan_wheel_custom_logo.png')
        output_path.parent.mkdir(exist_ok=True)

        result = fan_wheel.create(wheel_data, output_path, team_logo=custom_logo)
        print(f"✓ Fan wheel with custom logo created: {result}")
        return True
    except Exception as e:
        print(f"✗ Custom logo fan wheel failed: {e}")
        return False


def test_logo_report():
    """Test logo availability reporting"""
    print("\n=== Test 4: Logo Availability Report ===")

    team_config = {
        'team_name': 'Test Team',
        'team_name_short': 'Test',
        'colors': {
            'primary': '#000000',
            'secondary': '#FFFFFF',
            'accent': '#888888'
        }
    }

    wheel_data = generate_test_data()
    fan_wheel = FanWheel(team_config, enable_logos=True)

    report = fan_wheel.generate_logo_report(wheel_data)

    print(f"  Total merchants: {report['total_merchants']}")
    print(f"  With logos: {report['with_logos']}")
    print(f"  Missing logos: {report['missing_logos']}")
    print(f"  Coverage: {report['coverage_percentage']:.1f}%")

    if report.get('missing_list'):
        print("\n  Missing logos for:")
        for merchant in report['missing_list']:
            print(f"    - {merchant}")

    return True


def test_edge_cases():
    """Test edge cases and error handling"""
    print("\n=== Test 5: Edge Cases ===")

    team_config = {
        'team_name': 'Edge Case Team',
        'team_name_short': 'Edge',
        'colors': {}  # Missing colors
    }

    # Test with empty data
    print("  Testing with empty data...")
    fan_wheel = FanWheel(team_config, enable_logos=False)

    try:
        empty_data = pd.DataFrame(columns=['COMMUNITY', 'MERCHANT', 'behavior', 'PERC_INDEX'])
        output_path = Path('test_outputs/test_empty.png')
        fan_wheel.create(empty_data, output_path)
        print("  ✗ Should have failed with empty data")
        return False
    except ValueError as e:
        print(f"  ✓ Correctly caught empty data: {e}")

    # Test with minimal data (1 segment)
    print("\n  Testing with single segment...")
    single_data = pd.DataFrame([{
        'COMMUNITY': 'Test',
        'MERCHANT': 'Test Merchant',
        'behavior': 'Tests',
        'PERC_INDEX': 100
    }])

    try:
        output_path = Path('test_outputs/test_single_segment.png')
        output_path.parent.mkdir(exist_ok=True)
        fan_wheel.create(single_data, output_path)
        print("  ✓ Single segment fan wheel created")
    except Exception as e:
        print(f"  ✗ Single segment failed: {e}")
        return False

    return True


def test_different_teams():
    """Test fan wheels for different teams"""
    print("\n=== Test 6: Multiple Teams ===")

    teams = [
        {
            'config': {
                'team_name': 'Dallas Cowboys',
                'team_name_short': 'Cowboys',
                'colors': {
                    'primary': '#003594',
                    'secondary': '#869397',
                    'accent': '#002244'
                }
            },
            'output': 'test_outputs/test_cowboys_fan_wheel.png'
        },
        {
            'config': {
                'team_name': 'Los Angeles Lakers',
                'team_name_short': 'Lakers',
                'colors': {
                    'primary': '#552583',
                    'secondary': '#FDB927',
                    'accent': '#000000'
                }
            },
            'output': 'test_outputs/test_lakers_fan_wheel.png'
        }
    ]

    wheel_data = generate_test_data()
    success_count = 0

    for team_info in teams:
        team_name = team_info['config']['team_name']
        print(f"\n  Creating fan wheel for {team_name}...")

        fan_wheel = FanWheel(team_info['config'], enable_logos=True)

        try:
            output_path = Path(team_info['output'])
            output_path.parent.mkdir(exist_ok=True)

            fan_wheel.create(wheel_data, output_path)
            print(f"  ✓ {team_name} fan wheel created")
            success_count += 1
        except Exception as e:
            print(f"  ✗ {team_name} failed: {e}")

    print(f"\n  Successfully created {success_count}/{len(teams)} team fan wheels")
    return success_count == len(teams)


def run_all_tests():
    """Run all test cases"""
    print("=" * 60)
    print("FAN WHEEL TEST SUITE")
    print("=" * 60)

    # Create test output directory
    Path('test_outputs').mkdir(exist_ok=True)

    # Run tests
    tests = [
        ("Basic Fan Wheel", test_basic_fan_wheel),
        ("Logo Loading", test_logo_loading),
        ("Custom Logo", test_custom_logo),
        ("Logo Report", test_logo_report),
        ("Edge Cases", test_edge_cases),
        ("Multiple Teams", test_different_teams)
    ]

    results = []
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            logger.exception(f"Test {test_name} crashed")
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for test_name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status} - {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")
    print("=" * 60)

    # Check if test outputs were created
    print("\nGenerated files:")
    output_dir = Path('test_outputs')
    if output_dir.exists():
        for file in sorted(output_dir.glob('*.png')):
            print(f"  - {file}")

    return passed == total


if __name__ == "__main__":
    # Run all tests
    success = run_all_tests()

    # Exit with appropriate code
    sys.exit(0 if success else 1)