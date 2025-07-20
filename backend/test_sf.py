#!/usr/bin/env python3
"""
Test script for Hot Brands Preview - FIXED VERSION with subcategory support
"""

import os
import sys
from pathlib import Path
import json
import logging
from datetime import datetime
import pandas as pd

# Setup paths
script_dir = Path(__file__).parent
project_dir = script_dir.parent
sys.path.insert(0, str(project_dir))

# Load environment
from dotenv import load_dotenv

env_path = project_dir / '.env'
load_dotenv(env_path, override=True)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_hot_brands_preview_fixed(team_key='utah_jazz'):
    """Test getting hot brand recommendations with subcategory support"""

    print(f"\n{'=' * 80}")
    print(f"Testing Hot Brands Preview (WITH SUBCATEGORIES) for {team_key}")
    print(f"{'=' * 80}\n")

    try:
        # Initialize components
        from utils.team_config_manager import TeamConfigManager
        from data_processors.category_analyzer import CategoryAnalyzer
        from data_processors.snowflake_connector import query_to_dataframe
        from utils.cache_manager import CacheManager
        from postgresql_job_store import PostgreSQLJobStore

        # Initialize cache manager
        cache_manager = None
        try:
            job_store = PostgreSQLJobStore(os.environ.get('DATABASE_URL'))
            cache_manager = CacheManager(job_store.pool)
            print("✅ Cache manager initialized")
        except Exception as e:
            print(f"⚠️  Cache manager not available: {e}")

        # Get team config
        config_manager = TeamConfigManager()
        if team_key not in config_manager.list_teams():
            print(f"❌ Team {team_key} not found!")
            return None

        team_config = config_manager.get_team_config(team_key)
        print(f"✅ Team: {team_config['team_name']}")
        print()

        # Initialize CategoryAnalyzer
        analyzer = CategoryAnalyzer(
            team_name=team_config['team_name'],
            team_short=team_config.get('team_short', team_config['team_name'].split()[-1]),
            league=team_config['league'],
            comparison_population=team_config.get('comparison_population'),
            cache_manager=cache_manager
        )
        print(f"✅ CategoryAnalyzer initialized")
        print()

        # Load data
        print("Loading data from Snowflake...")
        view_prefix = team_config['view_prefix']

        category_df = query_to_dataframe(f"SELECT * FROM {view_prefix}_CATEGORY_INDEXING_ALL_TIME")
        subcategory_df = query_to_dataframe(f"SELECT * FROM {view_prefix}_SUBCATEGORY_INDEXING_ALL_TIME")
        merchant_df = query_to_dataframe(f"SELECT * FROM {view_prefix}_MERCHANT_INDEXING_ALL_TIME")

        # STRIP WHITESPACE FROM ALL STRING COLUMNS
        print("Cleaning data (removing trailing whitespace)...")
        for df in [category_df, subcategory_df, merchant_df]:
            string_cols = df.select_dtypes(include=['object']).columns
            for col in string_cols:
                df[col] = df[col].str.strip()

        print(f"   ✅ Data cleaned")
        print(f"   Merchant data: {len(merchant_df)} rows, {merchant_df['MERCHANT'].nunique()} unique merchants")
        print()

        recommendations = []
        merchants_to_standardize = []

        # Process fixed categories
        print("Processing fixed categories with subcategory support...")
        print("-" * 60)
        fixed_categories = ['restaurants', 'athleisure', 'finance', 'gambling', 'travel', 'auto']

        for category_key in fixed_categories:
            try:
                if category_key not in analyzer.categories:
                    continue

                print(f"\n   Analyzing {category_key}...")

                # Get category configuration
                category_config = analyzer.categories[category_key]
                category_names = category_config.get('category_names_in_data', [])

                # Strip whitespace from expected category names
                category_names = [name.strip() for name in category_names]

                # IMPORTANT: Include subcategories to match full report logic
                # Get all categories that start with any of our category names
                all_category_values = merchant_df['CATEGORY'].unique()
                expanded_categories = []

                for cat_name in category_names:
                    # Include exact matches
                    expanded_categories.append(cat_name)
                    # Include subcategories (e.g., "Travel - Airlines" for "Travel")
                    subcats = [cat for cat in all_category_values if cat.startswith(f"{cat_name} - ")]
                    expanded_categories.extend(subcats)

                # Remove duplicates
                expanded_categories = list(set(expanded_categories))
                print(f"      Base categories: {category_names}")
                print(f"      Expanded to include: {sorted(expanded_categories)}")

                # Filter merchant data with expanded categories
                category_merchant_df = merchant_df[
                    merchant_df['CATEGORY'].isin(expanded_categories)
                ].copy()

                print(f"      Found {len(category_merchant_df)} merchants across all subcategories")

                if category_merchant_df.empty:
                    print(f"      No merchants found in any subcategory")
                    continue

                # Find top merchant by composite index
                team_merchants = category_merchant_df[
                    (category_merchant_df['AUDIENCE'] == analyzer.audience_name) &
                    (category_merchant_df['COMPARISON_POPULATION'] == analyzer.comparison_pop) &
                    (category_merchant_df['COMPOSITE_INDEX'] > 0) &
                    (category_merchant_df['PERC_AUDIENCE'] >= 0.01)
                    ]

                if team_merchants.empty:
                    print(f"      No merchants meet criteria")
                    continue

                # Show top 5 merchants for debugging
                print(f"      Top 5 merchants by composite index:")
                top_5 = team_merchants.nlargest(5, 'COMPOSITE_INDEX')
                for idx, row in top_5.iterrows():
                    print(f"         {row['MERCHANT']}: {row['COMPOSITE_INDEX']:.0f} (Category: {row['CATEGORY']})")

                # Get top merchant
                top_merchant_row = team_merchants.nlargest(1, 'COMPOSITE_INDEX').iloc[0]

                merchants_to_standardize.append({
                    'original_name': top_merchant_row['MERCHANT'],
                    'category': category_config['display_name'],
                    'composite_index': int(top_merchant_row['COMPOSITE_INDEX']),
                    'audience_pct': float(top_merchant_row['PERC_AUDIENCE']) * 100,
                    'perc_index': int(top_merchant_row.get('PERC_INDEX', 0)),
                    'actual_category': top_merchant_row['CATEGORY']  # Track which subcategory it came from
                })

                print(f"   ✅ {category_config['display_name']}: {top_merchant_row['MERCHANT']} "
                      f"(index: {top_merchant_row['COMPOSITE_INDEX']:.0f}, "
                      f"from: {top_merchant_row['CATEGORY']})")

            except Exception as e:
                print(f"   ❌ {category_key}: Error - {str(e)}")
                import traceback
                traceback.print_exc()
                continue

        # Get custom categories
        print(f"\n{'=' * 60}")
        print("Processing custom categories...")
        print("-" * 60)

        try:
            custom_categories = analyzer.get_custom_categories(
                category_df=category_df,
                merchant_df=merchant_df,
                is_womens_team=team_config.get('is_womens_team', False),
                existing_categories=fixed_categories
            )

            print(f"Found {len(custom_categories)} custom categories")

            for custom_cat in custom_categories[:4]:
                try:
                    print(f"\n   Analyzing {custom_cat['display_name']}...")

                    # Strip whitespace from category names
                    category_names_clean = [name.strip() for name in custom_cat['category_names_in_data']]

                    # For custom categories, also check for subcategories
                    all_category_values = merchant_df['CATEGORY'].unique()
                    expanded_categories = []

                    for cat_name in category_names_clean:
                        expanded_categories.append(cat_name)
                        subcats = [cat for cat in all_category_values if cat.startswith(f"{cat_name} - ")]
                        expanded_categories.extend(subcats)

                    expanded_categories = list(set(expanded_categories))

                    # Filter merchant data
                    custom_merchant_df = merchant_df[
                        merchant_df['CATEGORY'].isin(expanded_categories)
                    ].copy()

                    print(f"      Found {len(custom_merchant_df)} merchants")

                    if custom_merchant_df.empty:
                        continue

                    # Find top merchant
                    team_merchants = custom_merchant_df[
                        (custom_merchant_df['AUDIENCE'] == analyzer.audience_name) &
                        (custom_merchant_df['COMPARISON_POPULATION'] == analyzer.comparison_pop) &
                        (custom_merchant_df['COMPOSITE_INDEX'] > 0) &
                        (custom_merchant_df['PERC_AUDIENCE'] >= 0.01)
                        ]

                    if team_merchants.empty:
                        print(f"      No merchants meet criteria")
                        continue

                    # Get top merchant
                    top_merchant_row = team_merchants.nlargest(1, 'COMPOSITE_INDEX').iloc[0]

                    merchants_to_standardize.append({
                        'original_name': recommended_merchant,  # Already standardized
                        'category': custom_cat['display_name'],
                        'composite_index': int(composite_index),
                        'audience_pct': audience_percentage,
                        'perc_index': perc_index,
                        'is_emerging': custom_cat.get('is_emerging', False),
                        'actual_category': actual_category
                    })

                    print(f"   ✅ {custom_cat['display_name']}: {recommended_merchant} "
                          f"(index: {composite_index:.0f})")

                except Exception as e:
                    print(f"   ❌ {custom_cat['display_name']}: Error - {str(e)}")
                    continue

        except Exception as e:
            print(f"   ❌ Could not get custom categories: {str(e)}")

        # Skip standardization - analyze_category already standardized the names
        print(f"\n{'=' * 60}")
        print(f"Merchant names already standardized by analyze_category")
        print("-" * 60)

        # Convert to recommendations format
        for merchant_info in merchants_to_standardize:
            recommendations.append({
                'merchant': merchant_info['original_name'],  # Already standardized
                'category': merchant_info['category'],
                'composite_index': merchant_info['composite_index'],
                'affinity_index': merchant_info['perc_index'],
                'audience_percentage': merchant_info['audience_pct'],
                'is_emerging': merchant_info.get('is_emerging', False),
                'source_category': merchant_info.get('actual_category', merchant_info['category'])
            })

        # Summary
        print(f"\n{'=' * 80}")
        print(f"SUMMARY: Found {len(recommendations)} hot brand targets")
        print(f"{'=' * 80}\n")

        for i, rec in enumerate(recommendations[:10], 1):
            emerging = " ⭐" if rec.get('is_emerging') else ""
            source = f" (from: {rec.get('source_category', 'N/A')})" if rec.get('source_category') != rec[
                'category'] else ""
            print(f"{i:2d}. {rec['category']:<20} → {rec['merchant']:<25} "
                  f"(Index: {rec['composite_index']:>4}){emerging}{source}")

        # Save results
        output = {
            'team_name': team_config['team_name'],
            'recommendations': recommendations[:10],
            'generated_at': datetime.now().isoformat()
        }

        output_file = f"hot_brands_{team_key}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w') as f:
            json.dump(output, f, indent=2)

        print(f"\n✅ Results saved to: {output_file}")

        return output

    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    test_hot_brands_preview_fixed('utah_jazz')