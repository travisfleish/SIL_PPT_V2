#!/usr/bin/env python3
"""
Check NBA_LEAGUE_INSIGHTS schema and evaluate views for fan wheel generation
"""

import sys
from pathlib import Path
import pandas as pd
import logging

sys.path.insert(0, str(Path(__file__).parent))

from data_processors.snowflake_connector import query_to_dataframe
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_schema_views():
    """Check what views exist in NBA_LEAGUE_INSIGHTS schema"""
    logger.info("🔍 Checking NBA_LEAGUE_INSIGHTS schema...")
    
    # Temporarily set schema
    original_schema = os.getenv('SNOWFLAKE_SCHEMA')
    os.environ['SNOWFLAKE_SCHEMA'] = 'NBA_LEAGUE_INSIGHTS'
    
    try:
        query = """
        SELECT 
            TABLE_NAME,
            TABLE_TYPE,
            ROW_COUNT,
            BYTES,
            CREATED,
            LAST_ALTERED
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = 'NBA_LEAGUE_INSIGHTS'
        ORDER BY TABLE_NAME
        """
        
        df = query_to_dataframe(query)
        
        logger.info(f"\n✅ Found {len(df)} tables/views in NBA_LEAGUE_INSIGHTS schema:\n")
        print("="*100)
        for idx, row in df.iterrows():
            print(f"\n📊 {row['TABLE_NAME']}")
            print(f"   Type: {row['TABLE_TYPE']}")
            if row['ROW_COUNT'] is not None:
                print(f"   Rows: {row['ROW_COUNT']:,}")
            if row['BYTES'] is not None:
                size_mb = row['BYTES'] / (1024 * 1024)
                print(f"   Size: {size_mb:.2f} MB")
            if row['CREATED']:
                print(f"   Created: {row['CREATED']}")
        
        print("\n" + "="*100)
        return df
        
    finally:
        # Restore original schema
        if original_schema:
            os.environ['SNOWFLAKE_SCHEMA'] = original_schema


def examine_view_structure(view_name: str):
    """Examine the structure of a specific view"""
    logger.info(f"\n🔍 Examining view: {view_name}")
    
    # Temporarily set schema
    original_schema = os.getenv('SNOWFLAKE_SCHEMA')
    os.environ['SNOWFLAKE_SCHEMA'] = 'NBA_LEAGUE_INSIGHTS'
    
    try:
        # Get column information
        col_query = f"""
        SELECT 
            COLUMN_NAME,
            DATA_TYPE,
            CHARACTER_MAXIMUM_LENGTH,
            IS_NULLABLE,
            ORDINAL_POSITION
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = 'NBA_LEAGUE_INSIGHTS'
        AND TABLE_NAME = '{view_name}'
        ORDER BY ORDINAL_POSITION
        """
        
        cols_df = query_to_dataframe(col_query)
        
        print(f"\n📋 Columns in {view_name} ({len(cols_df)} total):")
        print("-"*100)
        for idx, row in cols_df.iterrows():
            col_type = row['DATA_TYPE']
            if row['CHARACTER_MAXIMUM_LENGTH']:
                col_type += f"({row['CHARACTER_MAXIMUM_LENGTH']})"
            nullable = "NULL" if row['IS_NULLABLE'] == 'YES' else "NOT NULL"
            print(f"  {idx+1:2d}. {row['COLUMN_NAME']:<40} {col_type:<20} {nullable}")
        
        # Get sample data
        sample_query = f"SELECT * FROM {view_name} LIMIT 3"
        try:
            sample_df = query_to_dataframe(sample_query)
            if not sample_df.empty:
                print(f"\n🔍 Sample Data (first 3 rows):")
                print("-"*100)
                pd.set_option('display.max_columns', None)
                pd.set_option('display.width', None)
                pd.set_option('display.max_colwidth', 50)
                print(sample_df.to_string(index=False))
        except Exception as e:
            print(f"\n⚠️  Could not fetch sample data: {e}")
        
        return cols_df
        
    finally:
        # Restore original schema
        if original_schema:
            os.environ['SNOWFLAKE_SCHEMA'] = original_schema


def check_fan_wheel_requirements():
    """Check if the schema has what's needed for fan wheel generation"""
    logger.info("\n" + "="*100)
    logger.info("CHECKING FAN WHEEL REQUIREMENTS")
    logger.info("="*100)
    
    required_fields = {
        'community': ['COMMUNITY', 'PERC_INDEX', 'COMPOSITE_INDEX', 'PERC_AUDIENCE'],
        'merchant': ['MERCHANT', 'COMMUNITY', 'PERC_INDEX', 'COMPOSITE_INDEX', 'PERC_AUDIENCE', 'CATEGORY']
    }
    
    # Temporarily set schema
    original_schema = os.getenv('SNOWFLAKE_SCHEMA')
    os.environ['SNOWFLAKE_SCHEMA'] = 'NBA_LEAGUE_INSIGHTS'
    
    try:
        # Get all views
        views_query = """
        SELECT TABLE_NAME
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = 'NBA_LEAGUE_INSIGHTS'
        AND TABLE_TYPE = 'VIEW'
        ORDER BY TABLE_NAME
        """
        
        views_df = query_to_dataframe(views_query)
        view_names = views_df['TABLE_NAME'].tolist()
        
        print(f"\n📊 Evaluating {len(view_names)} views for fan wheel compatibility:\n")
        
        for view_name in view_names:
            print(f"\n{'='*100}")
            print(f"VIEW: {view_name}")
            print('='*100)
            
            # Get columns
            cols_query = f"""
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = 'NBA_LEAGUE_INSIGHTS'
            AND TABLE_NAME = '{view_name}'
            """
            
            cols_df = query_to_dataframe(cols_query)
            columns = [col.upper() for col in cols_df['COLUMN_NAME'].tolist()]
            
            # Check for community-related fields
            has_community = 'COMMUNITY' in columns
            has_merchant = 'MERCHANT' in columns
            has_perc_index = 'PERC_INDEX' in columns
            has_composite_index = 'COMPOSITE_INDEX' in columns
            has_perc_audience = 'PERC_AUDIENCE' in columns
            has_category = 'CATEGORY' in columns
            
            print(f"  Columns: {len(columns)}")
            print(f"  Has COMMUNITY: {has_community}")
            print(f"  Has MERCHANT: {has_merchant}")
            print(f"  Has PERC_INDEX: {has_perc_index}")
            print(f"  Has COMPOSITE_INDEX: {has_composite_index}")
            print(f"  Has PERC_AUDIENCE: {has_perc_audience}")
            print(f"  Has CATEGORY: {has_category}")
            
            # Determine view type
            if has_community and has_merchant:
                view_type = "Community-Merchant (✅ Good for fan wheel)"
            elif has_community and not has_merchant:
                view_type = "Community-only (⚠️  Need merchant data)"
            elif has_merchant and not has_community:
                view_type = "Merchant-only (⚠️  Need community data)"
            else:
                view_type = "Other"
            
            print(f"\n  View Type: {view_type}")
            
            # Check if suitable for fan wheel
            if has_community and has_merchant and has_perc_index and has_composite_index:
                print(f"  ✅ SUITABLE for fan wheel generation")
            elif has_community and has_perc_index:
                print(f"  ⚠️  Partial - has community data but may need merchant view")
            else:
                print(f"  ❌ Not suitable for fan wheel (missing key fields)")
        
        print("\n" + "="*100)
        
    finally:
        # Restore original schema
        if original_schema:
            os.environ['SNOWFLAKE_SCHEMA'] = original_schema


def main():
    """Main analysis function"""
    logger.info("="*100)
    logger.info("NBA_LEAGUE_INSIGHTS SCHEMA EVALUATION")
    logger.info("="*100)
    
    # Check what views exist
    views_df = check_schema_views()
    
    # Check fan wheel requirements
    check_fan_wheel_requirements()
    
    # Examine key views in detail
    if len(views_df) > 0:
        logger.info("\n" + "="*100)
        logger.info("DETAILED VIEW EXAMINATION")
        logger.info("="*100)
        
        # Look for community or merchant related views
        view_names = views_df['TABLE_NAME'].tolist()
        
        for view_name in view_names[:5]:  # Examine first 5 views
            examine_view_structure(view_name)
    
    logger.info("\n" + "="*100)
    logger.info("✨ Evaluation Complete!")
    logger.info("="*100)


if __name__ == "__main__":
    main()

