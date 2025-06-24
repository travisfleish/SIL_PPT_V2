#!/usr/bin/env python3
"""
Test script for the updated CategoryAnalyzer
Tests all the corrected insight generation logic
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys
from datetime import datetime
import json

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from data_processors.category_analyzer import CategoryAnalyzer, CategoryMetrics
from data_processors.snowflake_connector import query_to_dataframe, test_connection
from utils.team_config_manager import TeamConfigManager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_single_category(analyzer: CategoryAnalyzer,
                         category_key: str,
                         view_prefix: str,
                         is_custom: bool = False) -> dict:
    """Test a single category analysis"""

    print(f"\n{'=' * 80}")
    print(f"TESTING: {category_key.upper()} {'[CUSTOM]' if is_custom else '[FIXED]'}")
    print(f"{'=' * 80}")

    # Get category configuration
    if is_custom:
        cat_config = analyzer.create_custom_category_config(category_key)
        cat_names = [category_key]
    else:
        cat_config = analyzer.categories.get(category_key, {})
        cat_names = cat_config.get('category_names_in_data', [])

    if not cat_names:
        print(f"⚠️  No category names configured for {category_key}")
        return None

    # Build WHERE clause for category names
    category_where = " OR ".join([f"TRIM(CATEGORY) = '{cat}'" for cat in cat_names])

    # Load category data
    print(f"\n1. Loading category data...")
    category_query = f"""
    SELECT * FROM {view_prefix}_CATEGORY_INDEXING_ALL_TIME 
    WHERE {category_where}
    """
    category_df = query_to_dataframe(category_query)
    print(f"   ✅ Loaded {len(category_df)} rows from CATEGORY view")

    # Load subcategory data
    print(f"\n2. Loading subcategory data...")
    subcategory_query = f"""
    SELECT * FROM {view_prefix}_SUBCATEGORY_INDEXING_ALL_TIME 
    WHERE {category_where}
    """
    subcategory_df = query_to_dataframe(subcategory_query)
    print(f"   ✅ Loaded {len(subcategory_df)} rows from SUBCATEGORY view")

    # Load merchant data
    print(f"\n3. Loading merchant data...")
    merchant_query = f"""
    SELECT * FROM {view_prefix}_MERCHANT_INDEXING_ALL_TIME 
    WHERE {category_where}
    LIMIT 5000
    """
    merchant_df = query_to_dataframe(merchant_query)
    print(f"   ✅ Loaded {len(merchant_df)} rows from MERCHANT view")

    # Run analysis
    print(f"\n4. Running {category_key} analysis...")
    try:
        # For custom categories, temporarily add the config
        if is_custom:
            analyzer.categories[category_key] = cat_config

        results = analyzer.analyze_category(
            category_key=category_key,
            category_df=category_df,
            subcategory_df=subcategory_df,
            merchant_df=merchant_df,
            validate=True
        )

        # Mark as custom category
        results['is_custom'] = is_custom

        # Clean up temporary config
        if is_custom:
            del analyzer.categories[category_key]

        print("✅ Analysis completed successfully")
        return results
    except Exception as e:
        print(f"❌ Analysis failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def display_results(results: dict):
    """Display analysis results with focus on insights"""
    if not results:
        return

    category_type = "[CUSTOM]" if results.get('is_custom', False) else "[FIXED]"
    print(f"\n📊 RESULTS: {results['display_name']} {category_type}")
    print("=" * 80)

    # Category metrics
    metrics = results['category_metrics']
    print(f"\n📈 Category Metrics:")
    print(f"   - Percent of fans who spend: {metrics.format_percent_fans()}")
    print(f"   - Likelihood vs gen pop: {metrics.format_likelihood()}")
    print(f"   - Purchases vs gen pop: {metrics.format_purchases()}")
    print(f"   - Composite Index: {metrics.composite_index:.1f}")

    # Insights - THE KEY PART TO TEST
    print(f"\n💡 CATEGORY INSIGHTS (Testing corrected logic):")
    for i, insight in enumerate(results['insights'], 1):
        print(f"\n   Insight {i}: {insight}")

        # Validate insights
        if i == 4 and "per fan per year on" in insight:
            print("      ✅ Insight 4: Correctly shows highest spending subcategory")
        elif i == 5 and "NBA average" in insight:
            print("      ✅ Insight 5: Correctly shows NBA comparison for subcategory")

    # Check for removed YOY insights
    has_yoy = any("2024 vs. 2023" in insight or "year over year" in insight.lower()
                  for insight in results['insights'])
    if has_yoy:
        print("\n   ❌ ERROR: Found YOY insight that should be removed!")
    else:
        print("\n   ✅ No YOY insights found (correct)")

    # Subcategory table
    print(f"\n📊 Top Subcategories:")
    if not results['subcategory_stats'].empty:
        print(results['subcategory_stats'].to_string(index=False))

    # Top merchants
    print(f"\n🏪 Top Merchants:")
    merchant_df, _ = results['merchant_stats']
    if not merchant_df.empty:
        print(merchant_df.head(3).to_string(index=False))

    # Validation report
    if results.get('validation_report'):
        report = results['validation_report']
        if report['valid']:
            print(f"\n✅ Validation: PASSED")
        else:
            print(f"\n❌ Validation: FAILED")
            for issue in report['issues']:
                print(f"   - {issue}")


def test_insight_generation_specifically():
    """Focused test on the insight generation logic"""
    print("\n" + "=" * 80)
    print("FOCUSED TEST: Insight Generation Logic")
    print("=" * 80)

    # Expected insight patterns
    expected_patterns = {
        1: "likely to spend on",
        2: "purchases per fan on",
        3: "likely to spend on.*vs\.",  # Subcategory likelihood
        4: "spend an average of.*per fan per year",  # NEW: Highest SPC subcategory
        5: "compared to the NBA average"  # NEW: NBA comparison
    }

    print("\nExpected Insight Patterns:")
    for i, pattern in expected_patterns.items():
        print(f"   Insight {i}: {pattern}")

    return expected_patterns


def main():
    """Main test function"""
    print("\n🧪 UPDATED CATEGORY ANALYZER TEST")
    print("Testing corrected insight generation")
    print("=" * 80)

    # Test connection
    print("\n1. Testing Snowflake connection...")
    if not test_connection():
        print("❌ Failed to connect to Snowflake")
        return
    print("✅ Connected to Snowflake")

    # Initialize analyzer
    print("\n2. Initializing CategoryAnalyzer...")
    analyzer = CategoryAnalyzer(
        team_name="Utah Jazz",
        team_short="Jazz",
        league="NBA"
    )
    print("✅ CategoryAnalyzer initialized")

    # Get team configuration
    print("\n3. Getting team configuration...")
    config_manager = TeamConfigManager()
    team_config = config_manager.get_team_config('utah_jazz')
    view_prefix = team_config['view_prefix']
    print(f"✅ View prefix: {view_prefix}")

    # Test specific categories
    test_categories = ['restaurants', 'auto']  # Testing both to see different insights

    all_results = {}

    for category_key in test_categories:
        results = test_single_category(analyzer, category_key, view_prefix, is_custom=False)
        if results:
            all_results[category_key] = results
            display_results(results)

    # Also test one custom category
    print("\n4. Testing custom category selection...")
    category_query = f"SELECT * FROM {view_prefix}_CATEGORY_INDEXING_ALL_TIME"
    all_category_df = query_to_dataframe(category_query)

    custom_categories = analyzer.get_custom_categories(
        category_df=all_category_df,
        is_womens_team=False
    )

    if custom_categories:
        # Test just the first custom category
        custom_cat = custom_categories[0]
        results = test_single_category(
            analyzer,
            custom_cat['display_name'],
            view_prefix,
            is_custom=True
        )
        if results:
            all_results[custom_cat['category_key']] = results
            display_results(results)

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    print(f"\n✅ Tested {len(all_results)} categories")

    # Validate insight patterns
    print("\n📋 Insight Validation:")
    expected_patterns = test_insight_generation_specifically()

    for cat_key, results in all_results.items():
        print(f"\n{cat_key.upper()}:")
        insights = results['insights']

        # Check insight 4 (highest spending subcategory)
        insight_4 = insights[3] if len(insights) > 3 else None
        if insight_4 and "per fan per year on" in insight_4 and "$" in insight_4:
            print("   ✅ Insight 4: Correctly shows highest spending subcategory with dollar amount")
        else:
            print("   ❌ Insight 4: Missing or incorrect highest spending subcategory insight")

        # Check insight 5 (NBA comparison)
        insight_5 = insights[4] if len(insights) > 4 else None
        if insight_5 and "NBA average" in insight_5:
            print("   ✅ Insight 5: Correctly shows NBA subcategory comparison")
        else:
            print("   ❌ Insight 5: Missing or incorrect NBA comparison")

        # Verify NO YOY insights
        has_yoy = any("2024 vs. 2023" in insight or "year over year" in insight.lower()
                      for insight in insights)
        if not has_yoy:
            print("   ✅ No YOY insights (correct)")
        else:
            print("   ❌ Found YOY insights that should be removed")

    print("\n✅ Test completed!")

    # Save results for inspection
    output_file = f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        # Convert non-serializable objects
        serializable_results = {}
        for key, value in all_results.items():
            serializable_results[key] = {
                'display_name': value['display_name'],
                'insights': value['insights'],
                'is_custom': value.get('is_custom', False),
                'validation': value.get('validation_report', {})
            }
        json.dump(serializable_results, f, indent=2)

    print(f"\n📝 Results saved to: {output_file}")


if __name__ == "__main__":
    main()