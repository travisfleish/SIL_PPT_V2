#!/usr/bin/env python3
"""
Test script to verify fan wheel visualization with font manager integration
Run this from the project root or backend directory
"""

import os
import sys
from pathlib import Path
import pandas as pd
import matplotlib
import logging

# Configure matplotlib backend
matplotlib.use('Agg')

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add project paths
backend_path = Path(__file__).parent
if backend_path.name != 'backend':
    backend_path = backend_path / 'backend'
sys.path.insert(0, str(backend_path))
sys.path.insert(0, str(backend_path.parent))


def test_font_manager():
    """Test font manager initialization"""
    print("\n" + "=" * 60)
    print("TESTING FONT MANAGER")
    print("=" * 60)

    try:
        from utils.font_manager import font_manager

        # Check if fonts are loaded
        print(f"✓ Font manager imported successfully")
        print(f"  - Fonts loaded: {font_manager.fonts_loaded}")

        # Test getting font family
        font_family = font_manager.get_font_family('Red Hat Display')
        print(f"  - Selected font family: {font_family}")

        # Check matplotlib configuration
        import matplotlib.pyplot as plt
        current_font = plt.rcParams['font.family']
        print(f"  - Matplotlib font family: {current_font}")

        # List available fonts containing 'Red Hat'
        from matplotlib import font_manager as fm
        red_hat_fonts = [f.name for f in fm.fontManager.ttflist if 'red hat' in f.name.lower()]
        if red_hat_fonts:
            print(f"  - Red Hat fonts found: {len(red_hat_fonts)}")
            for font in red_hat_fonts[:5]:  # Show first 5
                print(f"    • {font}")
        else:
            print("  ⚠ No Red Hat fonts found in system")

        return True

    except Exception as e:
        print(f"✗ Font manager test failed: {e}")
        logger.error(f"Font manager error: {e}", exc_info=True)
        return False


def create_test_data():
    """Create sample data for fan wheel"""
    print("\n" + "=" * 60)
    print("CREATING TEST DATA")
    print("=" * 60)

    test_data = pd.DataFrame({
        'COMMUNITY': [
            'Coffee Drinkers', 'Tech Enthusiasts', 'Outdoor Adventurers',
            'Foodies', 'Music Lovers', 'Fitness Fans',
            'Book Readers', 'Movie Buffs', 'Gamers', 'Pet Owners'
        ],
        'MERCHANT': [
            'Starbucks', 'Apple', 'REI',
            'Whole Foods', 'Spotify', 'Nike',
            'Barnes & Noble', 'AMC', 'GameStop', 'Petco'
        ],
        'behavior': [
            'Grabs coffee daily', 'Buys latest gadgets', 'Shops outdoor gear',
            'Tries new restaurants', 'Streams constantly', 'Works out regularly',
            'Reads voraciously', 'Watches weekly', 'Games often', 'Spoils pets'
        ],
        'PERC_INDEX': [150, 140, 130, 125, 120, 115, 110, 105, 102, 100]
    })

    print(f"✓ Created test data with {len(test_data)} entries")
    return test_data


def test_fan_wheel_creation():
    """Test fan wheel visualization creation"""
    print("\n" + "=" * 60)
    print("TESTING FAN WHEEL CREATION")
    print("=" * 60)

    try:
        from visualizations.fan_wheel import FanWheel

        # Create test team config
        team_config = {
            'team_name': 'Test Team',
            'team_name_short': 'Test',
            'colors': {
                'primary': '#002244',
                'secondary': '#FFB612',
                'accent': '#4169E1'
            }
        }

        # Create fan wheel instance
        fan_wheel = FanWheel(team_config, enable_logos=False)  # Disable logos for font test
        print(f"✓ Fan wheel instance created")
        print(f"  - Using font family: {fan_wheel.font_family}")

        # Get test data
        test_data = create_test_data()

        # Create visualization
        output_path = Path('test_fan_wheel_fonts.png')
        result_path = fan_wheel.create(test_data, output_path)

        if result_path.exists():
            file_size = result_path.stat().st_size / 1024  # KB
            print(f"✓ Fan wheel created successfully")
            print(f"  - Output file: {result_path}")
            print(f"  - File size: {file_size:.1f} KB")

            # Verify font was applied by checking if custom font warnings occurred
            print(f"  - Font application: Check image to verify font rendering")

            return True
        else:
            print(f"✗ Fan wheel creation failed - no output file")
            return False

    except Exception as e:
        print(f"✗ Fan wheel test failed: {e}")
        logger.error(f"Fan wheel error: {e}", exc_info=True)
        return False


def test_text_rendering():
    """Test matplotlib text rendering with custom fonts"""
    print("\n" + "=" * 60)
    print("TESTING TEXT RENDERING")
    print("=" * 60)

    try:
        import matplotlib.pyplot as plt
        from utils.font_manager import font_manager

        # Create a simple test plot
        fig, ax = plt.subplots(figsize=(10, 6))

        # Get font family
        font_family = font_manager.get_font_family('Red Hat Display')

        # Add text with different styles
        test_texts = [
            ("Default Font", 0.5, 0.8, {}),
            (f"Custom Font: {font_family}", 0.5, 0.6, {'fontfamily': font_family}),
            ("Bold Custom Font", 0.5, 0.4, {'fontfamily': font_family, 'fontweight': 'bold'}),
            ("Large Custom Font", 0.5, 0.2, {'fontfamily': font_family, 'fontsize': 20}),
        ]

        for text, x, y, props in test_texts:
            ax.text(x, y, text, ha='center', va='center', **props)

        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')

        # Save test plot
        output_path = Path('test_font_rendering.png')
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()

        if output_path.exists():
            print(f"✓ Font rendering test completed")
            print(f"  - Test image: {output_path}")
            print(f"  - Check image to verify font differences")
            return True
        else:
            print(f"✗ Font rendering test failed")
            return False

    except Exception as e:
        print(f"✗ Font rendering test failed: {e}")
        logger.error(f"Font rendering error: {e}", exc_info=True)
        return False


def cleanup_test_files():
    """Clean up test files"""
    print("\n" + "=" * 60)
    print("CLEANUP")
    print("=" * 60)

    test_files = ['test_fan_wheel_fonts.png', 'test_font_rendering.png']
    for file in test_files:
        path = Path(file)
        if path.exists():
            path.unlink()
            print(f"✓ Removed {file}")


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("FAN WHEEL FONT INTEGRATION TEST")
    print("=" * 60)

    # Keep track of test results
    results = []

    # Test 1: Font Manager
    results.append(("Font Manager", test_font_manager()))

    # Test 2: Text Rendering
    results.append(("Text Rendering", test_text_rendering()))

    # Test 3: Fan Wheel Creation
    results.append(("Fan Wheel Creation", test_fan_wheel_creation()))

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{test_name:.<30} {status}")

    print(f"\nTotal: {passed}/{total} tests passed")

    # Cleanup option
    if passed == total:
        response = input("\nClean up test files? (y/n): ").lower()
        if response == 'y':
            cleanup_test_files()
    else:
        print("\nTest files kept for debugging")
        print("- test_fan_wheel_fonts.png")
        print("- test_font_rendering.png")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)