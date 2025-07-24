# test_athletic_fix.py
"""Test that Athletic subcategory formatting works for both custom and non-custom cases"""

import pandas as pd
from pathlib import Path
import sys
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from data_processors.category_analyzer import CategoryAnalyzer


def test_athletic_formatting():
    """Test Athletic subcategory formatting in all scenarios"""

    print("=" * 80)
    print("TESTING ATHLETIC SUBCATEGORY FORMATTING AFTER FIX")
    print("=" * 80)

    # Initialize analyzer
    analyzer = CategoryAnalyzer(
        team_name="Utah Jazz",
        team_short="Jazz",
        league="NBA"
    )

    # Create test data
    subcategory_df = pd.DataFrame([
        {
            'AUDIENCE': 'Utah Jazz Fans',
            'COMPARISON_POPULATION': 'Local Gen Pop (Excl. Jazz)',
            'SUBCATEGORY': 'Athletic - Gear',
            'PERC_AUDIENCE': 0.16,
            'PERC_INDEX': 432,
            'PPC': 1.5,
            'COMPARISON_PPC': 1.0,
            'COMPOSITE_INDEX': 400,
            'SPC': 308
        },
        {
            'AUDIENCE': 'Utah Jazz Fans',
            'COMPARISON_POPULATION': 'Local Gen Pop (Excl. Jazz)',
            'SUBCATEGORY': 'Athletic - Goods',
            'PERC_AUDIENCE': 0.63,
            'PERC_INDEX': 243,
            'PPC': 2.0,
            'COMPARISON_PPC': 1.3,
            'COMPOSITE_INDEX': 250,
            'SPC': 250
        }
    ])

    # Test 1: Non-custom Athletic (as it would be in fixed categories)
    print("\n1. TESTING NON-CUSTOM ATHLETIC")
    print("-" * 40)

    non_custom_config = analyzer.categories['athletic'].copy()
    non_custom_config['is_custom'] = False

    print(f"Config: is_custom = {non_custom_config.get('is_custom')}")
    print(f"        display_name = '{non_custom_config.get('display_name')}'")
    print(f"        category_names_in_data = {non_custom_config.get('category_names_in_data')}")

    # Test direct formatting
    print("\nDirect _format_subcategory_name calls:")
    for subcat in ['Athletic - Gear', 'Athletic - Goods']:
        result = analyzer._format_subcategory_name(subcat, non_custom_config)
        print(f"  '{subcat}' → '{result}' {'✅' if result in ['Gear', 'Goods'] else '❌'}")

    # Test via _get_subcategory_stats
    print("\nVia _get_subcategory_stats:")
    stats = analyzer._get_subcategory_stats(subcategory_df, non_custom_config)
    for idx, row in stats.iterrows():
        subcat = row['Subcategory']
        is_correct = subcat in ['Gear', 'Goods']
        print(f"  Row {idx}: '{subcat}' {'✅' if is_correct else '❌'}")

    # Test 2: Custom Athletic (as it appears in your PowerPoint)
    print("\n\n2. TESTING CUSTOM ATHLETIC")
    print("-" * 40)

    custom_config = analyzer.create_custom_category_config("Athletic")

    print(f"Config: is_custom = {custom_config.get('is_custom')}")
    print(f"        display_name = '{custom_config.get('display_name')}'")
    print(f"        category_names_in_data = {custom_config.get('category_names_in_data')}")

    # Test direct formatting
    print("\nDirect _format_subcategory_name calls:")
    for subcat in ['Athletic - Gear', 'Athletic - Goods']:
        result = analyzer._format_subcategory_name(subcat, custom_config)
        print(f"  '{subcat}' → '{result}' {'✅' if result in ['Gear', 'Goods'] else '❌'}")

    # Test via _get_subcategory_stats
    print("\nVia _get_subcategory_stats:")
    stats = analyzer._get_subcategory_stats(subcategory_df, custom_config)
    for idx, row in stats.iterrows():
        subcat = row['Subcategory']
        is_correct = subcat in ['Gear', 'Goods']
        print(f"  Row {idx}: '{subcat}' {'✅' if is_correct else '❌'}")

    # Test 3: Edge cases
    print("\n\n3. TESTING EDGE CASES")
    print("-" * 40)

    # Test with a category that has different display name
    test_config = {
        'display_name': 'Some Other Name',
        'category_names_in_data': ['Athletic'],
        'is_custom': True
    }

    print("Config with mismatched display_name:")
    print(f"  display_name = '{test_config['display_name']}'")
    print(f"  category_names_in_data = {test_config['category_names_in_data']}")

    for subcat in ['Athletic - Gear', 'Athletic - Goods']:
        result = analyzer._format_subcategory_name(subcat, test_config)
        print(f"  '{subcat}' → '{result}' {'✅' if result in ['Gear', 'Goods'] else '❌'}")

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    # Re-run all tests and count successes
    all_tests = []

    # Non-custom tests
    for subcat in ['Athletic - Gear', 'Athletic - Goods']:
        result = analyzer._format_subcategory_name(subcat, non_custom_config)
        all_tests.append(('Non-custom', subcat, result, result in ['Gear', 'Goods']))

    # Custom tests
    for subcat in ['Athletic - Gear', 'Athletic - Goods']:
        result = analyzer._format_subcategory_name(subcat, custom_config)
        all_tests.append(('Custom', subcat, result, result in ['Gear', 'Goods']))

    # Edge case tests
    for subcat in ['Athletic - Gear', 'Athletic - Goods']:
        result = analyzer._format_subcategory_name(subcat, test_config)
        all_tests.append(('Edge case', subcat, result, result in ['Gear', 'Goods']))

    passed = sum(1 for _, _, _, success in all_tests if success)
    total = len(all_tests)

    if passed == total:
        print(f"✅ ALL TESTS PASSED ({passed}/{total})")
        print("\nThe Athletic subcategory formatting is now working correctly!")
        print("You can regenerate your PowerPoint and the subcategories should display as 'Gear' and 'Goods'")
    else:
        print(f"❌ SOME TESTS FAILED ({passed}/{total} passed)")
        print("\nFailed tests:")
        for test_type, input_val, output_val, success in all_tests:
            if not success:
                print(f"  {test_type}: '{input_val}' → '{output_val}' (expected 'Gear' or 'Goods')")


if __name__ == "__main__":
    test_athletic_formatting()