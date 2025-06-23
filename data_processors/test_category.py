#!/usr/bin/env python3
"""
Test script for CategoryAnalyzer using real Snowflake data
Validates functionality with actual Utah Jazz data
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


def run_category_analysis(analyzer, category_key: str, view_prefix: str, is_custom: bool = False) -> dict:
    """Run full analysis for a single category"""

    print(f"\n{'=' * 70}")
    print(f"ANALYZING: {category_key.upper()} {'[CUSTOM]' if is_custom else '[FIXED]'}")
    print(f"{'=' * 70}")

    # Get category configuration
    if is_custom:
        # For custom categories, we need to create a temporary config
        # The category_key for custom categories is the actual category name
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

    # Load YOY data (optional)
    print(f"\n4. Loading YOY data...")
    yoy_category_query = f"""
    SELECT * FROM {view_prefix}_CATEGORY_INDEXING_YOY 
    WHERE ({category_where})
    AND TRANSACTION_YEAR IN ('2023-01-01', '2024-01-01')
    """
    yoy_category_df = query_to_dataframe(yoy_category_query)
    print(f"   ✅ Loaded {len(yoy_category_df)} rows from CATEGORY YOY view")

    yoy_merchant_query = f"""
    SELECT * FROM {view_prefix}_MERCHANT_INDEXING_YOY 
    WHERE ({category_where})
    AND AUDIENCE = '{analyzer.audience_name}'
    AND TRANSACTION_YEAR IN ('2023-01-01', '2024-01-01')
    LIMIT 1000
    """
    yoy_merchant_df = query_to_dataframe(yoy_merchant_query)
    print(f"   ✅ Loaded {len(yoy_merchant_df)} rows from MERCHANT YOY view")

    # Run analysis
    print(f"\n5. Running {category_key} analysis...")
    try:
        # For custom categories, temporarily add the config
        if is_custom:
            analyzer.categories[category_key] = cat_config

        results = analyzer.analyze_category(
            category_key=category_key,
            category_df=category_df,
            subcategory_df=subcategory_df,
            merchant_df=merchant_df,
            yoy_category_df=yoy_category_df,
            yoy_merchant_df=yoy_merchant_df
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
    """Display analysis results in a formatted way"""
    if not results:
        return

    category_type = "[CUSTOM]" if results.get('is_custom', False) else "[FIXED]"
    print(f"\n📊 Category: {results['display_name']} {category_type}")
    print(f"   Slide Title: {results['slide_title']}")

    metrics = results['category_metrics']
    print(f"\n   Category Metrics:")
    print(f"   - Percent of fans who spend: {metrics.format_percent_fans()}")
    print(f"   - Likelihood vs gen pop: {metrics.format_likelihood()}")
    print(f"   - Purchases vs gen pop: {metrics.format_purchases()}")
    print(f"   - Composite Index: {metrics.composite_index:.1f}")
    print(f"   - Total Spend: ${metrics.total_spend:,.2f}")
    print(f"   - Spend per Customer: ${metrics.spc:.2f}")

    # Subcategory stats
    print(f"\n📊 Top Subcategories:")
    if not results['subcategory_stats'].empty:
        print(results['subcategory_stats'].to_string(index=False))
    else:
        print("   No subcategory data available")

    # Insights
    print(f"\n💡 Category Insights:")
    for i, insight in enumerate(results['insights'], 1):
        print(f"   {i}. {insight}")

    # Merchant stats
    print(f"\n🏪 Top Merchants:")
    merchant_df, top_merchants = results['merchant_stats']
    if not merchant_df.empty:
        print(merchant_df.to_string(index=False))
    else:
        print("   No merchant data available")

    # Merchant insights
    print(f"\n💡 Merchant Insights:")
    for i, insight in enumerate(results['merchant_insights'], 1):
        print(f"   {i}. {insight}")

    # Sponsorship recommendation
    if results['recommendation']:
        rec = results['recommendation']
        print(f"\n🎯 Sponsorship Recommendation:")
        print(f"   Target: {rec['merchant']}")
        print(f"   Composite Index: {rec['composite_index']:.1f}")
        print(f"   Rationale: {rec['explanation']}")


def create_category_dataframes(results: dict) -> dict:
    """Convert category results into multiple DataFrames for Excel export"""

    dataframes = {}

    # 1. Category Summary
    metrics = results['category_metrics']
    summary_data = {
        'Metric': [
            'Display Name',
            'Slide Title',
            'Category Type',
            'Percent of Fans Who Spend',
            'Likelihood vs Gen Pop',
            'Purchases vs Gen Pop',
            'Composite Index',
            'Total Spend',
            'Spend per Customer',
            'Audience Count'
        ],
        'Value': [
            results['display_name'],
            results['slide_title'],
            'CUSTOM' if results.get('is_custom', False) else 'FIXED',
            metrics.format_percent_fans(),
            metrics.format_likelihood(),
            metrics.format_purchases(),
            f"{metrics.composite_index:.1f}",
            f"${metrics.total_spend:,.2f}",
            f"${metrics.spc:.2f}",
            f"{metrics.audience_count:,}"
        ]
    }
    dataframes['Summary'] = pd.DataFrame(summary_data)

    # 2. Subcategories
    if not results['subcategory_stats'].empty:
        dataframes['Subcategories'] = results['subcategory_stats']

    # 3. Top Merchants
    merchant_df, _ = results['merchant_stats']
    if not merchant_df.empty:
        dataframes['Top_Merchants'] = merchant_df

    # 4. Category Insights
    if results['insights']:
        insights_df = pd.DataFrame({
            'Insight_Number': range(1, len(results['insights']) + 1),
            'Insight': results['insights']
        })
        dataframes['Category_Insights'] = insights_df

    # 5. Merchant Insights
    if results['merchant_insights']:
        merchant_insights_df = pd.DataFrame({
            'Insight_Number': range(1, len(results['merchant_insights']) + 1),
            'Insight': results['merchant_insights']
        })
        dataframes['Merchant_Insights'] = merchant_insights_df

    # 6. Sponsorship Recommendation
    if results['recommendation']:
        rec = results['recommendation']
        rec_df = pd.DataFrame({
            'Field': ['Target Merchant', 'Composite Index', 'Rationale'],
            'Value': [rec['merchant'], f"{rec['composite_index']:.1f}", rec['explanation']]
        })
        dataframes['Recommendation'] = rec_df

    return dataframes


def test_all_categories():
    """Test CategoryAnalyzer with all categories including custom ones"""

    print("\n" + "=" * 80)
    print("CATEGORY ANALYZER TEST - FIXED + CUSTOM CATEGORIES")
    print("=" * 80)

    # 1. Test Snowflake connection
    print("\n1. Testing Snowflake connection...")
    if not test_connection():
        print("❌ Failed to connect to Snowflake")
        return
    print("✅ Connected to Snowflake")

    # 2. Initialize analyzer
    print("\n2. Initializing CategoryAnalyzer...")
    analyzer = CategoryAnalyzer(
        team_name="Utah Jazz",
        team_short="Jazz",
        league="NBA"
    )
    print("✅ CategoryAnalyzer initialized")

    # 3. Get team configuration for view names
    print("\n3. Getting team configuration...")
    config_manager = TeamConfigManager()
    team_config = config_manager.get_team_config('utah_jazz')
    view_prefix = team_config['view_prefix']
    print(f"✅ View prefix: {view_prefix}")

    # 4. Get custom categories first
    print("\n4. Selecting custom categories...")

    # Load all category data for custom selection
    category_query = f"""
    SELECT * FROM {view_prefix}_CATEGORY_INDEXING_ALL_TIME
    """
    all_category_df = query_to_dataframe(category_query)

    # Get custom categories
    custom_categories = analyzer.get_custom_categories(
        category_df=all_category_df,
        is_womens_team=False
    )

    print(f"✅ Selected {len(custom_categories)} custom categories:")
    for cat in custom_categories:
        print(f"   - {cat['display_name']} (composite index: {cat['composite_index']:.1f})")

    # 5. Define all categories to test
    fixed_categories = [
        'restaurants',
        'athleisure',
        'finance',
        'gambling',
        'travel',
        'auto'
    ]

    all_results = {}

    # 6. Run analysis for fixed categories
    print("\n5. Analyzing FIXED categories...")
    for category_key in fixed_categories:
        results = run_category_analysis(analyzer, category_key, view_prefix, is_custom=False)
        if results:
            all_results[category_key] = results
            display_results(results)

    # 7. Run analysis for custom categories
    print("\n6. Analyzing CUSTOM categories...")
    for custom_cat in custom_categories:
        # For custom categories, use the display name as the key
        category_key = custom_cat['display_name']
        results = run_category_analysis(analyzer, category_key, view_prefix, is_custom=True)
        if results:
            # Add custom category metadata
            results['custom_metadata'] = {
                'composite_index': custom_cat['composite_index'],
                'audience_pct': custom_cat['audience_pct'],
                'selection_rank': custom_categories.index(custom_cat) + 1
            }
            all_results[custom_cat['category_key']] = results
            display_results(results)

    # 8. Save all results to Excel file with multiple sheets
    print("\n\n" + "=" * 60)
    print("SAVING ALL RESULTS TO EXCEL")
    print("=" * 60)

    output_dir = Path('test_output')
    output_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = output_dir / f'category_analysis_results_with_custom_{timestamp}.xlsx'

    # Create Excel writer
    with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:

        # Create overview sheet
        overview_data = []
        for cat_key, results in all_results.items():
            metrics = results['category_metrics']
            is_custom = results.get('is_custom', False)

            row_data = {
                'Category': results['display_name'],
                'Type': 'CUSTOM' if is_custom else 'FIXED',
                'Percent Fans Spend': metrics.format_percent_fans(),
                'Likelihood vs Gen Pop': metrics.format_likelihood(),
                'Purchases vs Gen Pop': metrics.format_purchases(),
                'Composite Index': f"{metrics.composite_index:.1f}",
                'Total Spend': f"${metrics.total_spend:,.0f}",
                'SPC': f"${metrics.spc:.2f}",
                'Top Subcategories': len(results['subcategory_stats']),
                'Top Merchants': len(results['merchant_stats'][0]) if results['merchant_stats'][0] is not None else 0,
                'Has Recommendation': 'Yes' if results['recommendation'] else 'No'
            }

            # Add custom category metadata if available
            if is_custom and 'custom_metadata' in results:
                row_data['Selection Rank'] = results['custom_metadata']['selection_rank']
            else:
                row_data['Selection Rank'] = '-'

            overview_data.append(row_data)

        overview_df = pd.DataFrame(overview_data)

        # Sort by Type (FIXED first) then by composite index
        overview_df['Sort_Type'] = overview_df['Type'].map({'FIXED': 0, 'CUSTOM': 1})
        overview_df['Sort_Index'] = overview_df['Composite Index'].str.replace('$', '').str.replace(',', '').astype(
            float)
        overview_df = overview_df.sort_values(['Sort_Type', 'Sort_Index'], ascending=[True, False])
        overview_df = overview_df.drop(['Sort_Type', 'Sort_Index'], axis=1)

        overview_df.to_excel(writer, sheet_name='Overview', index=False)

        # Create custom categories summary sheet
        custom_summary_data = []
        for cat_key, results in all_results.items():
            if results.get('is_custom', False):
                metrics = results['category_metrics']
                custom_summary_data.append({
                    'Rank': results['custom_metadata']['selection_rank'],
                    'Category': results['display_name'],
                    'Composite Index': metrics.composite_index,
                    'Audience %': f"{results['custom_metadata']['audience_pct'] * 100:.1f}%",
                    'Total Spend': f"${metrics.total_spend:,.0f}",
                    'SPC': f"${metrics.spc:.2f}",
                    'Top Merchant': results['recommendation']['merchant'] if results['recommendation'] else 'N/A'
                })

        if custom_summary_data:
            custom_summary_df = pd.DataFrame(custom_summary_data)
            custom_summary_df = custom_summary_df.sort_values('Rank')
            custom_summary_df.to_excel(writer, sheet_name='Custom Categories', index=False)

        # Create sheet for each category
        for cat_key, results in all_results.items():
            # Create dataframes for this category
            cat_dataframes = create_category_dataframes(results)

            # Create a safe sheet name (no special characters, limited length)
            base_name = results['display_name']
            # Remove any characters that Excel doesn't like
            safe_name = base_name.replace('[', '').replace(']', '').replace(':', '').replace('*', '').replace('?',
                                                                                                              '').replace(
                '/', '').replace('\\', '')

            # Limit to 28 characters to leave room for suffix
            if len(safe_name) > 28:
                safe_name = safe_name[:28]

            # Add suffix to indicate Fixed or Custom
            if results.get('is_custom', False):
                sheet_name = f"{safe_name} - C"
            else:
                sheet_name = f"{safe_name} - F"

            # Write each dataframe to the same sheet with spacing
            current_row = 0
            for df_name, df in cat_dataframes.items():
                # Write section header
                header_df = pd.DataFrame([[f"=== {df_name.upper().replace('_', ' ')} ==="]])
                header_df.to_excel(writer, sheet_name=sheet_name,
                                   startrow=current_row, startcol=0,
                                   header=False, index=False)
                current_row += 2

                # Write the dataframe
                df.to_excel(writer, sheet_name=sheet_name,
                            startrow=current_row, startcol=0,
                            index=False)
                current_row += len(df) + 3  # Add spacing between sections

        # Format the workbook
        workbook = writer.book

        # Add formats
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#D9D9D9',
            'border': 1
        })

        currency_format = workbook.add_format({'num_format': '$#,##0.00'})
        percent_format = workbook.add_format({'num_format': '0.0%'})

        # Apply formatting to Overview sheet
        worksheet = writer.sheets['Overview']
        worksheet.set_column('A:A', 20)  # Category column
        worksheet.set_column('B:L', 18)  # Other columns

    print(f"✅ Results saved to: {output_file}")

    # Also save a simplified CSV for the overview
    csv_file = output_dir / f'category_overview_with_custom_{timestamp}.csv'
    overview_df.to_csv(csv_file, index=False)
    print(f"✅ Overview CSV saved to: {csv_file}")

    # 9. Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    fixed_count = sum(1 for r in all_results.values() if not r.get('is_custom', False))
    custom_count = sum(1 for r in all_results.values() if r.get('is_custom', False))

    print(f"✅ Successfully tested {len(all_results)} categories:")
    print(f"   - Fixed categories: {fixed_count}")
    print(f"   - Custom categories: {custom_count}")

    print("\nFixed Categories:")
    for cat, result in all_results.items():
        if not result.get('is_custom', False):
            metrics = result['category_metrics']
            print(f"   - {result['display_name']}: {metrics.format_percent_fans()} of fans spend")

    print("\nCustom Categories:")
    for cat, result in all_results.items():
        if result.get('is_custom', False):
            metrics = result['category_metrics']
            print(
                f"   - {result['display_name']}: {metrics.format_percent_fans()} of fans spend (Rank #{result['custom_metadata']['selection_rank']})")

    print("\n✅ All tests completed successfully!")
    return all_results


def validate_data_structure():
    """Validate the structure of Snowflake data matches expectations"""

    print("\n" + "=" * 60)
    print("DATA STRUCTURE VALIDATION")
    print("=" * 60)

    config_manager = TeamConfigManager()
    team_config = config_manager.get_team_config('utah_jazz')
    view_prefix = team_config['view_prefix']

    # Check each view
    views_to_check = [
        ('CATEGORY_INDEXING_ALL_TIME', ['AUDIENCE', 'COMPARISON_POPULATION', 'CATEGORY',
                                        'PERC_AUDIENCE', 'PERC_INDEX', 'PPC', 'COMPARISON_PPC',
                                        'SPC', 'COMPOSITE_INDEX']),
        ('SUBCATEGORY_INDEXING_ALL_TIME', ['AUDIENCE', 'COMPARISON_POPULATION', 'CATEGORY',
                                           'SUBCATEGORY', 'PERC_AUDIENCE', 'PERC_INDEX']),
        ('MERCHANT_INDEXING_ALL_TIME', ['AUDIENCE', 'COMPARISON_POPULATION', 'CATEGORY',
                                        'MERCHANT', 'PERC_AUDIENCE', 'PERC_INDEX', 'COMPOSITE_INDEX'])
    ]

    for view_suffix, expected_cols in views_to_check:
        print(f"\n📊 Checking {view_suffix}...")

        query = f"""
        SELECT * FROM {view_prefix}_{view_suffix}
        LIMIT 1
        """

        try:
            df = query_to_dataframe(query)
            actual_cols = df.columns.tolist()

            print(f"   Columns found: {len(actual_cols)}")

            # Check for expected columns
            missing = set(expected_cols) - set(actual_cols)
            if missing:
                print(f"   ⚠️  Missing columns: {missing}")
            else:
                print(f"   ✅ All expected columns present")

            # Show sample data types
            print("   Data types:")
            for col in expected_cols:
                if col in df.columns:
                    print(f"      {col}: {df[col].dtype}")

        except Exception as e:
            print(f"   ❌ Error: {str(e)}")


if __name__ == "__main__":
    # First validate data structure
    print("Step 1: Validating Snowflake data structure...")
    validate_data_structure()

    # Then run main test for all categories
    print("\n\nStep 2: Running CategoryAnalyzer tests for all categories (fixed + custom)...")
    user_input = input("\nContinue with full test for all categories? (y/n): ")

    if user_input.lower() == 'y':
        test_results = test_all_categories()
    else:
        print("Test cancelled.")