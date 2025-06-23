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


def run_category_analysis(analyzer, category_key: str, view_prefix: str) -> dict:
    """Run full analysis for a single category"""

    print(f"\n{'=' * 70}")
    print(f"ANALYZING: {category_key.upper()}")
    print(f"{'=' * 70}")

    # Get category configuration
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
    AND AUDIENCE = 'Utah Jazz Fans'
    AND TRANSACTION_YEAR IN ('2023-01-01', '2024-01-01')
    LIMIT 1000
    """
    yoy_merchant_df = query_to_dataframe(yoy_merchant_query)
    print(f"   ✅ Loaded {len(yoy_merchant_df)} rows from MERCHANT YOY view")

    # Run analysis
    print(f"\n5. Running {category_key} analysis...")
    try:
        results = analyzer.analyze_category(
            category_key=category_key,
            category_df=category_df,
            subcategory_df=subcategory_df,
            merchant_df=merchant_df,
            yoy_category_df=yoy_category_df,
            yoy_merchant_df=yoy_merchant_df
        )
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

    print(f"\n📊 Category: {results['display_name']}")
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
    """Test CategoryAnalyzer with all categories"""

    print("\n" + "=" * 80)
    print("CATEGORY ANALYZER TEST - ALL CATEGORIES")
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

    # 4. Define categories to test
    categories_to_test = [
        'restaurants',
        'athleisure',
        'finance',
        'gambling',
        'travel',
        'auto'
    ]

    # Add women's categories if testing women's team
    # categories_to_test.extend(['beauty', 'health'])

    all_results = {}

    # 5. Run analysis for each category
    for category_key in categories_to_test:
        results = run_category_analysis(analyzer, category_key, view_prefix)
        if results:
            all_results[category_key] = results
            display_results(results)

    # 6. Save all results to Excel file with multiple sheets
    print("\n\n" + "=" * 60)
    print("SAVING ALL RESULTS TO EXCEL")
    print("=" * 60)

    output_dir = Path('test_output')
    output_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = output_dir / f'category_analysis_results_{timestamp}.xlsx'

    # Create Excel writer
    with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:

        # Create overview sheet
        overview_data = []
        for cat_key, results in all_results.items():
            metrics = results['category_metrics']
            overview_data.append({
                'Category': results['display_name'],
                'Percent Fans Spend': metrics.format_percent_fans(),
                'Likelihood vs Gen Pop': metrics.format_likelihood(),
                'Purchases vs Gen Pop': metrics.format_purchases(),
                'Composite Index': f"{metrics.composite_index:.1f}",
                'Total Spend': f"${metrics.total_spend:,.0f}",
                'SPC': f"${metrics.spc:.2f}",
                'Top Subcategories': len(results['subcategory_stats']),
                'Top Merchants': len(results['merchant_stats'][0]) if results['merchant_stats'][0] is not None else 0,
                'Has Recommendation': 'Yes' if results['recommendation'] else 'No'
            })

        overview_df = pd.DataFrame(overview_data)
        overview_df.to_excel(writer, sheet_name='Overview', index=False)

        # Create sheet for each category
        for cat_key, results in all_results.items():
            # Create dataframes for this category
            cat_dataframes = create_category_dataframes(results)

            # Create a combined sheet for this category
            sheet_name = cat_key.replace('_', ' ').title()[:31]  # Excel sheet name limit

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
        worksheet.set_column('B:I', 18)  # Other columns

    print(f"✅ Results saved to: {output_file}")

    # Also save a simplified CSV for the overview
    csv_file = output_dir / f'category_overview_{timestamp}.csv'
    overview_df.to_csv(csv_file, index=False)
    print(f"✅ Overview CSV saved to: {csv_file}")

    # 7. Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"✅ Successfully tested {len(all_results)} categories:")
    for cat, result in all_results.items():
        metrics = result['category_metrics']
        print(f"   - {result['display_name']}: {metrics.format_percent_fans()} of fans spend")

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
    print("\n\nStep 2: Running CategoryAnalyzer tests for all categories...")
    user_input = input("\nContinue with full test for all categories? (y/n): ")

    if user_input.lower() == 'y':
        test_results = test_all_categories()
    else:
        print("Test cancelled.")