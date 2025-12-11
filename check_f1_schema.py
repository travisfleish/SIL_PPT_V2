#!/usr/bin/env python3
"""
Check F1_RACING_INSIGHTS schema and list all tables/views
"""

import sys
from pathlib import Path
import pandas as pd
import logging
import os
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))

from data_processors.snowflake_connector import query_to_dataframe

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_schema_tables():
    """Check what tables/views exist in F1_RACING_INSIGHTS schema"""
    logger.info("🔍 Checking F1_RACING_INSIGHTS schema...")
    
    # Get schema from environment
    schema = os.getenv('SNOWFLAKE_SCHEMA', 'F1_RACING_INSIGHTS')
    logger.info(f"Using schema: {schema}")
    
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
        WHERE TABLE_SCHEMA = UPPER(%(schema)s)
        ORDER BY TABLE_NAME
        """
        
        df = query_to_dataframe(query, params={'schema': schema})
        
        logger.info(f"\n✅ Found {len(df)} tables/views in {schema} schema:\n")
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
            if row['LAST_ALTERED']:
                print(f"   Last Altered: {row['LAST_ALTERED']}")
        
        print("\n" + "="*100)
        return df
        
    except Exception as e:
        logger.error(f"Error checking schema: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()


def examine_table_structure(table_name: str):
    """Examine the structure of a specific table"""
    schema = os.getenv('SNOWFLAKE_SCHEMA', 'F1_RACING_INSIGHTS')
    logger.info(f"\n🔍 Examining table/view: {table_name}")
    
    try:
        # Get column information
        col_query = """
        SELECT 
            COLUMN_NAME,
            DATA_TYPE,
            CHARACTER_MAXIMUM_LENGTH,
            IS_NULLABLE,
            ORDINAL_POSITION
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = UPPER(%(schema)s)
        AND TABLE_NAME = UPPER(%(table_name)s)
        ORDER BY ORDINAL_POSITION
        """
        
        cols_df = query_to_dataframe(col_query, params={'schema': schema, 'table_name': table_name})
        
        print(f"\n📋 Columns in {table_name} ({len(cols_df)} total):")
        print("-"*100)
        for idx, row in cols_df.iterrows():
            col_type = row['DATA_TYPE']
            if row['CHARACTER_MAXIMUM_LENGTH']:
                col_type += f"({row['CHARACTER_MAXIMUM_LENGTH']})"
            nullable = "NULL" if row['IS_NULLABLE'] == 'YES' else "NOT NULL"
            print(f"  {idx+1:2d}. {row['COLUMN_NAME']:<40} {col_type:<20} {nullable}")
        
        # Get sample data
        sample_query = f"SELECT * FROM {schema}.{table_name} LIMIT 3"
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
        
    except Exception as e:
        logger.error(f"Error examining table: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()


def main():
    """Main analysis function"""
    logger.info("="*100)
    logger.info("F1_RACING_INSIGHTS SCHEMA EVALUATION")
    logger.info("="*100)
    
    # Check what tables exist
    tables_df = check_schema_tables()
    
    if len(tables_df) > 0:
        logger.info("\n" + "="*100)
        logger.info("TABLE SUMMARY")
        logger.info("="*100)
        
        # Group by type
        by_type = tables_df.groupby('TABLE_TYPE').size()
        print("\n📊 Tables by Type:")
        for table_type, count in by_type.items():
            print(f"   {table_type}: {count}")
        
        # List all table names
        print("\n📋 All Tables/Views:")
        for idx, row in tables_df.iterrows():
            print(f"   {idx+1:2d}. {row['TABLE_NAME']} ({row['TABLE_TYPE']})")
        
        # Ask if user wants to examine specific tables
        logger.info("\n" + "="*100)
        logger.info("To examine a specific table structure, run:")
        logger.info("   python check_f1_schema.py --examine TABLE_NAME")
        logger.info("="*100)
    else:
        logger.warning("No tables found in schema")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Check F1_RACING_INSIGHTS schema')
    parser.add_argument('--examine', type=str, help='Examine structure of a specific table')
    
    args = parser.parse_args()
    
    if args.examine:
        examine_table_structure(args.examine)
    else:
        main()

