#!/usr/bin/env python3
"""
Extract sample data from Snowflake views for analysis and validation
Saves CSVs with sample data from each view
"""

import pandas as pd
from pathlib import Path
import sys
from datetime import datetime

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from data_processors.snowflake_connector import query_to_dataframe, test_connection
from utils.team_config_manager import TeamConfigManager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def extract_sample_data(team_key: str = 'utah_jazz', sample_size: int = 100):
    """
    Extract sample data from all category-related views

    Args:
        team_key: Team identifier
        sample_size: Number of rows to extract per view
    """
    print("\n" + "=" * 80)
    print("SNOWFLAKE DATA EXTRACTION FOR VALIDATION")
    print("=" * 80)

    # Test connection
    print("\n1. Testing Snowflake connection...")
    if not test_connection():
        print("❌ Failed to connect to Snowflake")
        return
    print("✅ Connected to Snowflake")

    # Get team configuration
    print("\n2. Getting team configuration...")
    config_manager = TeamConfigManager()
    team_config = config_manager.get_team_config(team_key)
    view_prefix = team_config['view_prefix']
    print(f"✅ Team: {team_config['team_name']}")
    print(f"✅ View prefix: {view_prefix}")

    # Create output directory
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_dir = Path(f'snowflake_samples_{team_key}_{timestamp}')
    output_dir.mkdir(exist_ok=True)
    print(f"\n3. Output directory: {output_dir}")

    # Define views to extract
    views_to_extract = [
        {
            'name': 'CATEGORY_INDEXING_ALL_TIME',
            'description': 'Category-level metrics',
            'filter': "WHERE TRIM(CATEGORY) = 'Restaurants'",  # Focus on Restaurants for validation
            'order_by': "ORDER BY AUDIENCE, COMPARISON_POPULATION"
        },
        {
            'name': 'SUBCATEGORY_INDEXING_ALL_TIME',
            'description': 'Subcategory-level metrics',
            'filter': "WHERE TRIM(CATEGORY) = 'Restaurants'",
            'order_by': "ORDER BY AUDIENCE, SUBCATEGORY, COMPARISON_POPULATION"
        },
        {
            'name': 'MERCHANT_INDEXING_ALL_TIME',
            'description': 'Merchant-level metrics',
            'filter': "WHERE TRIM(CATEGORY) = 'Restaurants' AND AUDIENCE = 'Utah Jazz Fans'",
            'order_by': "ORDER BY PERC_AUDIENCE DESC"
        },
        {
            'name': 'CATEGORY_INDEXING_YOY',
            'description': 'Year-over-year category metrics',
            'filter': "WHERE TRIM(CATEGORY) = 'Restaurants' AND TRANSACTION_YEAR >= '2023-01-01'",
            'order_by': "ORDER BY TRANSACTION_YEAR DESC, AUDIENCE"
        },
        {
            'name': 'MERCHANT_INDEXING_YOY',
            'description': 'Year-over-year merchant metrics',
            'filter': """WHERE TRIM(CATEGORY) = 'Restaurants' 
                        AND AUDIENCE = 'Utah Jazz Fans'
                        AND MERCHANT IN (
                            SELECT MERCHANT 
                            FROM {view_prefix}_MERCHANT_INDEXING_ALL_TIME
                            WHERE AUDIENCE = 'Utah Jazz Fans'
                            AND TRIM(CATEGORY) = 'Restaurants'
                            ORDER BY PERC_AUDIENCE DESC
                            LIMIT 10
                        )""",
            'order_by': "ORDER BY MERCHANT, TRANSACTION_YEAR DESC"
        }
    ]

    # Extract data from each view
    print("\n4. Extracting data from views...")
    extracted_files = []

    for view_info in views_to_extract:
        view_name = f"{view_prefix}_{view_info['name']}"
        print(f"\n   📊 Extracting from {view_info['name']}...")
        print(f"      Description: {view_info['description']}")

        try:
            # Build query
            query = f"""
            SELECT * 
            FROM {view_name}
            {view_info['filter']}
            {view_info['order_by']}
            LIMIT {sample_size}
            """

            # Special handling for YOY merchant query
            if '{view_prefix}' in query:
                query = query.format(view_prefix=view_prefix)

            # Execute query
            df = query_to_dataframe(query)

            if df.empty:
                print(f"      ⚠️  No data returned")
                continue

            # Save to CSV
            output_file = output_dir / f"{view_info['name']}.csv"
            df.to_csv(output_file, index=False)

            print(f"      ✅ Extracted {len(df)} rows")
            print(f"      ✅ Saved to: {output_file.name}")
            print(f"      📋 Columns: {', '.join(df.columns[:5])}..." if len(
                df.columns) > 5 else f"      📋 Columns: {', '.join(df.columns)}")

            extracted_files.append(output_file)

            # Show sample data
            print(f"      📝 Sample data:")
            pd.set_option('display.max_columns', 6)
            pd.set_option('display.width', 120)
            print(df.head(3).to_string(index=False))

        except Exception as e:
            print(f"      ❌ Error: {str(e)}")
            logger.error(f"Failed to extract {view_name}", exc_info=True)

    # Create a summary file
    print("\n5. Creating summary file...")
    summary_file = output_dir / 'extraction_summary.txt'

    with open(summary_file, 'w') as f:
        f.write(f"Snowflake Data Extraction Summary\n")
        f.write(f"{'=' * 50}\n")
        f.write(f"Team: {team_config['team_name']}\n")
        f.write(f"Timestamp: {timestamp}\n")
        f.write(f"View Prefix: {view_prefix}\n")
        f.write(f"\nExtracted Files:\n")
        for file in extracted_files:
            f.write(f"  - {file.name}\n")

    print(f"✅ Summary saved to: {summary_file.name}")

    # Additional validation queries
    print("\n6. Running validation queries...")
    validation_queries = [
        {
            'name': 'Check all comparison populations',
            'query': f"""
            SELECT DISTINCT COMPARISON_POPULATION, COUNT(*) as ROW_COUNT
            FROM {view_prefix}_CATEGORY_INDEXING_ALL_TIME
            WHERE AUDIENCE = 'Utah Jazz Fans'
            GROUP BY COMPARISON_POPULATION
            ORDER BY COMPARISON_POPULATION
            """
        },
        {
            'name': 'Check SPC values for Restaurants',
            'query': f"""
            SELECT 
                AUDIENCE,
                COMPARISON_POPULATION,
                SPC,
                AUDIENCE_TOTAL_SPEND,
                AUDIENCE_COUNT,
                AUDIENCE_TOTAL_SPEND / AUDIENCE_COUNT as CALCULATED_SPC
            FROM {view_prefix}_CATEGORY_INDEXING_ALL_TIME
            WHERE TRIM(CATEGORY) = 'Restaurants'
            AND AUDIENCE = 'Utah Jazz Fans'
            """
        },
        {
            'name': 'Check QSR subcategory SPC',
            'query': f"""
            SELECT 
                SUBCATEGORY,
                SPC,
                AUDIENCE_TOTAL_SPEND / AUDIENCE_COUNT as CALCULATED_SPC
            FROM {view_prefix}_SUBCATEGORY_INDEXING_ALL_TIME
            WHERE SUBCATEGORY LIKE '%QSR%'
            AND AUDIENCE = 'Utah Jazz Fans'
            """
        }
    ]

    validation_file = output_dir / 'validation_queries.csv'
    validation_results = []

    for val_query in validation_queries:
        print(f"\n   🔍 {val_query['name']}...")
        try:
            df = query_to_dataframe(val_query['query'])
            print(f"      ✅ Results:")
            print(df.to_string(index=False))

            # Add to validation results
            df['validation_query'] = val_query['name']
            validation_results.append(df)

        except Exception as e:
            print(f"      ❌ Error: {str(e)}")

    # Combine validation results
    if validation_results:
        combined_validation = pd.concat(validation_results, ignore_index=True)
        combined_validation.to_csv(validation_file, index=False)
        print(f"\n✅ Validation results saved to: {validation_file.name}")

    print(f"\n{'=' * 80}")
    print(f"✅ EXTRACTION COMPLETE!")
    print(f"📁 All files saved to: {output_dir.absolute()}")
    print(f"{'=' * 80}")

    return output_dir


def extract_all_categories(team_key: str = 'utah_jazz', rows_per_category: int = 50):
    """
    Extract sample data for all categories (not just Restaurants)
    """
    print("\n" + "=" * 80)
    print("EXTRACTING ALL CATEGORIES")
    print("=" * 80)

    # Get unique categories
    config_manager = TeamConfigManager()
    team_config = config_manager.get_team_config(team_key)
    view_prefix = team_config['view_prefix']

    # Get list of all categories
    query = f"""
    SELECT DISTINCT TRIM(CATEGORY) as CATEGORY, COUNT(*) as ROW_COUNT
    FROM {view_prefix}_CATEGORY_INDEXING_ALL_TIME
    WHERE AUDIENCE = '{team_config['team_name']} Fans'
    GROUP BY TRIM(CATEGORY)
    ORDER BY ROW_COUNT DESC
    LIMIT 20
    """

    categories_df = query_to_dataframe(query)

    if categories_df.empty:
        print("❌ No categories found")
        return

    print(f"\n📊 Found {len(categories_df)} categories:")
    print(categories_df.to_string(index=False))

    # Create output directory
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_dir = Path(f'all_categories_{team_key}_{timestamp}')
    output_dir.mkdir(exist_ok=True)

    # Extract data for each category
    for category in categories_df['CATEGORY'].tolist()[:10]:  # Top 10 categories
        print(f"\n📁 Extracting data for: {category}")

        category_file = output_dir / f"category_{category.replace(' ', '_').replace('/', '_')}.csv"

        query = f"""
        SELECT *
        FROM {view_prefix}_CATEGORY_INDEXING_ALL_TIME
        WHERE TRIM(CATEGORY) = '{category}'
        AND AUDIENCE IN ('{team_config['team_name']} Fans', 'General Population', 'NBA Fans')
        LIMIT {rows_per_category}
        """

        try:
            df = query_to_dataframe(query)
            df.to_csv(category_file, index=False)
            print(f"   ✅ Saved {len(df)} rows to {category_file.name}")
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")

    print(f"\n✅ All category files saved to: {output_dir.absolute()}")
    return output_dir


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Extract sample data from Snowflake')
    parser.add_argument('--team', type=str, default='utah_jazz',
                        help='Team key (utah_jazz or dallas_cowboys)')
    parser.add_argument('--rows', type=int, default=100,
                        help='Number of rows to extract per view')
    parser.add_argument('--all-categories', action='store_true',
                        help='Extract data for all categories, not just Restaurants')

    args = parser.parse_args()

    if args.all_categories:
        extract_all_categories(args.team, args.rows)
    else:
        extract_sample_data(args.team, args.rows)