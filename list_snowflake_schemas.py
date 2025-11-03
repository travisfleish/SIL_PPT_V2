#!/usr/bin/env python3
"""
Script to summarize schemas and table counts in Snowflake
"""

from data_processors.snowflake_connector import get_connection, query_to_dataframe
import pandas as pd

def summarize_schemas():
    """Summarize schemas with table counts"""
    
    # Query to get schema summaries
    query = """
    SELECT 
        TABLE_SCHEMA as schema,
        TABLE_TYPE as table_type,
        COUNT(*) as table_count
    FROM INFORMATION_SCHEMA.TABLES
    WHERE TABLE_CATALOG = CURRENT_DATABASE()
    GROUP BY TABLE_SCHEMA, TABLE_TYPE
    ORDER BY TABLE_SCHEMA, TABLE_TYPE
    """
    
    try:
        print("Connecting to Snowflake...\n")
        df = query_to_dataframe(query)
        
        # Convert column names to lowercase for easier access
        df.columns = df.columns.str.lower()
        
        print("=" * 80)
        print("SNOWFLAKE SCHEMA SUMMARY")
        print("=" * 80)
        
        # Group by schema
        current_schema = None
        for idx, row in df.iterrows():
            if row['schema'] != current_schema:
                current_schema = row['schema']
                print(f"\n📁 SCHEMA: {row['schema']}")
                print("-" * 80)
            
            print(f"  {row['table_type']}: {row['table_count']:,} tables")
            
    except Exception as e:
        print(f"Error summarizing schemas: {str(e)}")
        raise


def list_schemas_only():
    """List just the schema names"""
    
    query = """
    SELECT DISTINCT
        TABLE_SCHEMA as schema
    FROM INFORMATION_SCHEMA.TABLES
    WHERE TABLE_CATALOG = CURRENT_DATABASE()
    ORDER BY schema
    """
    
    try:
        print("\n" + "=" * 80)
        print("ALL SCHEMAS IN DATABASE")
        print("=" * 80)
        
        df = query_to_dataframe(query)
        df.columns = df.columns.str.lower()
        
        for idx, row in df.iterrows():
            print(f"  {row['schema']}")
            
        print(f"\nTotal schemas: {len(df)}")
            
    except Exception as e:
        print(f"Error listing schemas: {str(e)}")
        raise


if __name__ == "__main__":
    try:
        summarize_schemas()
        list_schemas_only()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()


