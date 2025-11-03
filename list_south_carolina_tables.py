#!/usr/bin/env python3
"""
Script to list tables in SOUTH_CAROLINA_TOURISM schema
"""

from data_processors.snowflake_connector import query_to_dataframe
import pandas as pd

def list_south_carolina_tables():
    """List all tables in SOUTH_CAROLINA_TOURISM schema"""
    
    query = """
    SELECT 
        TABLE_NAME as table_name,
        TABLE_TYPE as table_type,
        ROW_COUNT as row_count,
        BYTES as bytes,
        CREATED as created,
        LAST_ALTERED as last_altered,
        COMMENT as comment
    FROM INFORMATION_SCHEMA.TABLES
    WHERE TABLE_CATALOG = CURRENT_DATABASE()
      AND TABLE_SCHEMA = 'SOUTH_CAROLINA_TOURISM'
    ORDER BY TABLE_NAME
    """
    
    try:
        print("Connecting to Snowflake...\n")
        df = query_to_dataframe(query)
        df.columns = df.columns.str.lower()
        
        print("=" * 80)
        print("SOUTH_CAROLINA_TOURISM SCHEMA - TABLES")
        print("=" * 80)
        print(f"Found {len(df)} table(s)\n")
        
        for idx, row in df.iterrows():
            print(f"📊 {row['table_name']}")
            print(f"   Type: {row['table_type']}")
            if pd.notna(row['row_count']):
                print(f"   Rows: {row['row_count']:,}")
            if pd.notna(row['bytes']):
                print(f"   Size: {row['bytes']:,} bytes")
            if pd.notna(row['created']):
                print(f"   Created: {row['created']}")
            if pd.notna(row['last_altered']):
                print(f"   Last Altered: {row['last_altered']}")
            if pd.notna(row['comment']) and row['comment']:
                print(f"   Comment: {row['comment']}")
            print()
            
    except Exception as e:
        print(f"Error listing tables: {str(e)}")
        raise


if __name__ == "__main__":
    try:
        list_south_carolina_tables()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()


