#!/usr/bin/env python3
"""
Extract ONLY the merchants that would be used in the actual report
Shows original names from Snowflake and standardized names
"""

import pandas as pd
from pathlib import Path
import sys
import asyncio
from datetime import datetime

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from data_processors.category_analyzer import CategoryAnalyzer
from data_processors.merchant_ranker import MerchantRanker
from data_processors.snowflake_connector import query_to_dataframe, test_connection
from utils.team_config_manager import TeamConfigManager
from utils.merchant_name_standardizer import MerchantNameStandardizer


def get_report_merchants_with_standardization(team_key: str = 'utah_jazz'):
    """
    Pull ONLY the merchants that would appear in the actual PowerPoint report

    Args:
        team_key: Team identifier (default: utah_jazz)

    Returns:
        DataFrame with original and standardized merchant names
    """

    print(f"\n{'=' * 80}")
    print(f"REPORT MERCHANT VALIDATION - {team_key.upper()}")
    print(f"{'=' * 80}")

    # Test connection
    print("\n1. Testing Snowflake connection...")
    if not test_connection():
        print("❌ Failed to connect to Snowflake")
        return None
    print("✅ Connected successfully")

    # Load team config
    print("\n2. Loading team configuration...")
    config_manager = TeamConfigManager()
    team_config = config_manager.get_team_config(team_key)
    view_prefix = team_config['view_prefix']
    print(f"✅ Team: {team_config['team_name']}")

    # Initialize components
    print("\n3. Initializing components...")
    analyzer = CategoryAnalyzer(
        team_name=team_config['team_name'],
        team_short=team_config['team_name_short'],
        league=team_config['league']
    )
    ranker = MerchantRanker(team_view_prefix=view_prefix)
    standardizer = MerchantNameStandardizer(cache_enabled=True)

    # Store all merchant data
    all_merchant_data = []

    # PART 1: CATEGORY MERCHANTS (TOP 5 PER CATEGORY)
    print("\n" + "=" * 60)
    print("PART 1: CATEGORY MERCHANTS (TOP 5 PER CATEGORY)")
    print("=" * 60)

    # Define all categories
    fixed_categories = ['restaurants', 'athleisure', 'finance', 'gambling', 'travel', 'auto']

    # Get custom categories
    print("\nIdentifying custom categories...")
    custom_categories = get_custom_categories(analyzer, view_prefix)

    all_categories = fixed_categories + custom_categories
    print(f"\nProcessing {len(all_categories)} categories...")

    # Process each category
    for i, category_key in enumerate(all_categories, 1):
        print(f"\n[{i}/{len(all_categories)}] Processing {category_key}...")

        try:
            # Get TOP 5 merchants for this category
            merchants_df = get_top5_category_merchants(analyzer, category_key, view_prefix)

            if not merchants_df.empty:
                print(f"   ✅ Found top {len(merchants_df)} merchants")

                # Add metadata
                merchants_df['source'] = 'category'
                merchants_df['category'] = category_key
                merchants_df['merchant_original'] = merchants_df['MERCHANT']
                merchants_df['rank'] = range(1, len(merchants_df) + 1)

                all_merchant_data.append(merchants_df)
            else:
                print(f"   ⚠️  No merchants found")

        except Exception as e:
            print(f"   ❌ Error: {str(e)}")

    # PART 2: FAN WHEEL MERCHANTS (TOP 1 PER COMMUNITY)
    print("\n" + "=" * 60)
    print("PART 2: FAN WHEEL MERCHANTS (TOP 1 PER COMMUNITY - 10 COMMUNITIES)")
    print("=" * 60)

    try:
        # Get fan wheel data WITHOUT using the MerchantRanker method (which pre-standardizes)
        # Instead, run the raw query to get original names

        # First get top communities
        communities_query = f"""
        SELECT 
            COMMUNITY,
            PERC_INDEX
        FROM {view_prefix}_COMMUNITY_INDEXING_ALL_TIME
        WHERE AUDIENCE = '{analyzer.audience_name}'
        AND COMPARISON_POPULATION = '{analyzer.comparison_pop}'
        AND PERC_AUDIENCE >= 0.20
        AND COMMUNITY IN ({','.join([f"'{c}'" for c in ranker.approved_communities])})
        ORDER BY COMPOSITE_INDEX DESC
        LIMIT 10
        """

        communities_df = query_to_dataframe(communities_query)
        communities = communities_df['COMMUNITY'].tolist()

        if communities:
            # Get top merchant per community (matching MerchantRanker logic)
            merchants_query = f"""
            WITH ranked_merchants AS (
                SELECT 
                    COMMUNITY,
                    MERCHANT,
                    CATEGORY,
                    SUBCATEGORY,
                    PERC_INDEX,
                    PERC_AUDIENCE,
                    AUDIENCE_TOTAL_SPEND,
                    AUDIENCE_COUNT,
                    ROW_NUMBER() OVER (PARTITION BY COMMUNITY ORDER BY PERC_AUDIENCE DESC) as rank
                FROM {view_prefix}_COMMUNITY_MERCHANT_INDEXING_ALL_TIME
                WHERE COMMUNITY IN ({','.join([f"'{c}'" for c in communities])})
                AND COMPARISON_POPULATION = '{analyzer.comparison_pop}'
                AND AUDIENCE_COUNT >= 10
                AND NOT (COMMUNITY = 'Live Entertainment Seekers' 
                        AND LOWER(SUBCATEGORY) LIKE '%professional sports%')
            )
            SELECT 
                COMMUNITY,
                MERCHANT,
                CATEGORY,
                SUBCATEGORY,
                PERC_INDEX,
                PERC_AUDIENCE,
                AUDIENCE_TOTAL_SPEND,
                AUDIENCE_COUNT
            FROM ranked_merchants 
            WHERE rank = 1
            ORDER BY PERC_AUDIENCE DESC
            """

            fan_wheel_df = query_to_dataframe(merchants_query)

            if not fan_wheel_df.empty:
                print(f"✅ Found {len(fan_wheel_df)} fan wheel merchants (raw from Snowflake)")

                # Add metadata
                fan_wheel_df['source'] = 'fan_wheel'
                fan_wheel_df['category'] = fan_wheel_df['COMMUNITY']
                fan_wheel_df['merchant_original'] = fan_wheel_df['MERCHANT']  # This is the TRUE original
                fan_wheel_df['rank'] = 1

                # Add a COMPOSITE_INDEX placeholder since we need it for output
                fan_wheel_df['COMPOSITE_INDEX'] = 0  # Not available in merchant view

                all_merchant_data.append(fan_wheel_df)
            else:
                print("⚠️  No fan wheel merchants found")
        else:
            print("⚠️  No qualifying communities found")

    except Exception as e:
        print(f"❌ Error getting fan wheel data: {e}")

    # Combine all data
    if not all_merchant_data:
        print("\n❌ No merchant data collected")
        return None

    print("\n" + "=" * 60)
    print("PART 3: STANDARDIZING MERCHANT NAMES")
    print("=" * 60)

    # Combine all dataframes
    full_df = pd.concat(all_merchant_data, ignore_index=True)

    # Get unique merchant names
    unique_merchants = full_df['merchant_original'].unique()
    print(f"\nStandardizing {len(unique_merchants)} unique merchant names...")

    # Standardize names
    try:
        # Run async standardization
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        standardized_mapping = loop.run_until_complete(
            standardizer.standardize_merchants(list(unique_merchants))
        )

        loop.close()

        # Apply standardization
        full_df['merchant_standardized'] = full_df['merchant_original'].map(standardized_mapping)

        # Flag which names changed
        full_df['name_changed'] = full_df['merchant_original'] != full_df['merchant_standardized']

        print(f"✅ Standardization complete")

        # Count changes
        changes = full_df[full_df['name_changed']]['merchant_original'].nunique()
        print(f"   - {changes} unique names were standardized")

    except Exception as e:
        print(f"❌ Error during standardization: {e}")
        full_df['merchant_standardized'] = full_df['merchant_original']
        full_df['name_changed'] = False

    # PART 4: CREATE SUMMARY REPORT
    print("\n" + "=" * 60)
    print("PART 4: CREATING SUMMARY REPORT")
    print("=" * 60)

    # Create summary statistics
    summary = {
        'Total Report Merchants': len(full_df),
        'Unique Merchants (Original)': full_df['merchant_original'].nunique(),
        'Unique Merchants (Standardized)': full_df['merchant_standardized'].nunique(),
        'Names Changed': full_df[full_df['name_changed']]['merchant_original'].nunique(),
        'Category Merchants (Top 5 each)': len(full_df[full_df['source'] == 'category']),
        'Fan Wheel Merchants': len(full_df[full_df['source'] == 'fan_wheel']),
        'Categories Processed': full_df[full_df['source'] == 'category']['category'].nunique(),
        'Communities in Fan Wheel': full_df[full_df['source'] == 'fan_wheel']['category'].nunique()
    }

    print("\nSummary Statistics:")
    for key, value in summary.items():
        print(f"  {key}: {value}")

    # Show breakdown by category
    print("\n" + "=" * 60)
    print("MERCHANTS BY CATEGORY")
    print("=" * 60)

    category_summary = full_df.groupby(['source', 'category']).size().reset_index(name='merchant_count')

    print("\nCategory Merchants (Top 5 per category):")
    for _, row in category_summary[category_summary['source'] == 'category'].iterrows():
        print(f"  {row['category']}: {row['merchant_count']} merchants")

    print("\nFan Wheel Merchants (Top 1 per community):")
    for _, row in category_summary[category_summary['source'] == 'fan_wheel'].iterrows():
        print(f"  {row['category']}: {row['merchant_count']} merchant")

    # Show examples of standardized names
    print("\n" + "=" * 60)
    print("EXAMPLES OF NAME STANDARDIZATION")
    print("=" * 60)

    changed_df = full_df[full_df['name_changed']].drop_duplicates('merchant_original')
    if not changed_df.empty:
        print(f"\nShowing all {len(changed_df)} name changes:")
        print(f"{'Original':<35} {'Standardized':<35}")
        print("-" * 70)
        for _, row in changed_df.iterrows():
            print(f"{row['merchant_original']:<35} {row['merchant_standardized']:<35}")
    else:
        print("\nNo names were changed during standardization")

    # Find merchants that appear in multiple contexts
    print("\n" + "=" * 60)
    print("MERCHANTS IN MULTIPLE CATEGORIES/COMMUNITIES")
    print("=" * 60)

    merchant_contexts = full_df.groupby('merchant_standardized')['category'].apply(list).reset_index()
    multi_context = merchant_contexts[merchant_contexts['category'].apply(len) > 1]

    if not multi_context.empty:
        print(f"\nFound {len(multi_context)} merchants in multiple contexts:")
        for _, row in multi_context.iterrows():
            contexts = sorted(set(row['category']))
            print(f"  {row['merchant_standardized']}: {', '.join(contexts)}")
    else:
        print("\nNo merchants appear in multiple categories/communities")

    # PART 5: SAVE RESULTS
    print("\n" + "=" * 60)
    print("PART 5: SAVING RESULTS")
    print("=" * 60)

    # Prepare final dataframe with key columns
    output_columns = [
        'source',
        'category',
        'rank',
        'merchant_original',
        'merchant_standardized',
        'name_changed',
        'PERC_AUDIENCE',
        'COMPOSITE_INDEX'
    ]

    # Add optional columns if they exist
    for col in ['COMMUNITY', 'PERC_INDEX']:
        if col in full_df.columns:
            output_columns.append(col)

    # Filter to existing columns
    output_columns = [col for col in output_columns if col in full_df.columns]

    final_df = full_df[output_columns].copy()

    # Sort by source, category, and rank
    final_df = final_df.sort_values(
        ['source', 'category', 'rank'],
        ascending=[True, True, True]
    )

    # Save main results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"{team_key}_report_merchants_{timestamp}.csv"
    final_df.to_csv(output_file, index=False)
    print(f"\n✅ Report merchants saved to: {output_file}")

    # Save summary report
    summary_file = f"{team_key}_merchant_summary_{timestamp}.txt"
    with open(summary_file, 'w') as f:
        f.write(f"Report Merchant Summary\n")
        f.write(f"Team: {team_config['team_name']}\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 60 + "\n\n")

        for key, value in summary.items():
            f.write(f"{key}: {value}\n")

        f.write("\n" + "=" * 60 + "\n")
        f.write("Name Standardizations:\n\n")

        if not changed_df.empty:
            for _, row in changed_df.iterrows():
                f.write(f"{row['merchant_original']} → {row['merchant_standardized']}\n")
        else:
            f.write("No names were standardized\n")

    print(f"✅ Summary report saved to: {summary_file}")

    return final_df


def get_custom_categories(analyzer, view_prefix):
    """Get the top 4 custom categories from Snowflake"""

    query = f"""
    SELECT TRIM(CATEGORY) as CATEGORY, COMPOSITE_INDEX
    FROM {view_prefix}_CATEGORY_INDEXING_ALL_TIME
    WHERE AUDIENCE = '{analyzer.audience_name}'
    AND COMPARISON_POPULATION = '{analyzer.comparison_pop}'
    ORDER BY COMPOSITE_INDEX DESC
    """

    category_df = query_to_dataframe(query)

    if category_df.empty:
        return []

    # Filter out excluded categories
    valid_categories = []
    for _, row in category_df.iterrows():
        category = row['CATEGORY']
        if category not in analyzer.excluded_custom:
            valid_categories.append(category)

        if len(valid_categories) >= 4:
            break

    return valid_categories


def get_top5_category_merchants(analyzer, category_key, view_prefix):
    """Get TOP 5 merchants for a specific category (exactly what goes in the report)"""

    # Determine if custom or fixed category
    is_custom = category_key not in analyzer.categories

    if is_custom:
        # For custom categories, use the category name directly
        category_names = [category_key]
    else:
        # For fixed categories, get configured names
        cat_config = analyzer.categories.get(category_key, {})
        category_names = cat_config.get('category_names_in_data', [])

    if not category_names:
        return pd.DataFrame()

    # Build WHERE clause with TRIM to handle trailing spaces
    category_conditions = ' OR '.join([f"TRIM(CATEGORY) = '{cat}'" for cat in category_names])

    # Query for TOP 5 merchants ONLY
    query = f"""
    SELECT DISTINCT
        MERCHANT,
        CATEGORY,
        PERC_AUDIENCE,
        COMPOSITE_INDEX,
        PERC_INDEX
    FROM {view_prefix}_MERCHANT_INDEXING_ALL_TIME
    WHERE ({category_conditions})
    AND AUDIENCE = '{analyzer.audience_name}'
    AND COMPARISON_POPULATION = '{analyzer.comparison_pop}'
    ORDER BY PERC_AUDIENCE DESC
    LIMIT 5
    """

    return query_to_dataframe(query)


if __name__ == "__main__":
    # Run the validation
    print("\n🚀 Starting report merchant validation...")

    # You can change the team here
    team_key = 'utah_jazz'  # or 'dallas_cowboys'

    results = get_report_merchants_with_standardization(team_key)

    if results is not None:
        print(f"\n✨ Validation complete! Check the output files for results.")
    else:
        print("\n❌ Validation failed")