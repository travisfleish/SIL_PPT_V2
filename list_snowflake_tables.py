#!/usr/bin/env python3
"""
Script to list all available tables in Snowflake
"""

from data_processors.snowflake_connector import get_connection, query_to_dataframe
import pandas as pd

def list_all_tables():
    """List all tables visible in the current database"""
    
    # Query to get all tables in the database
    query = """
    SELECT 
        TABLE_CATALOG as database,
        TABLE_SCHEMA as schema,
        TABLE_NAME as table_name,
        TABLE_TYPE as table_type,
        CREATED as created,
        LAST_ALTERED as last_altered,
        ROW_COUNT as row_count,
        BYTES as bytes,
        COMMENT as comment
    FROM INFORMATION_SCHEMA.TABLES
    WHERE TABLE_CATALOG = CURRENT_DATABASE()
    ORDER BY TABLE_SCHEMA, TABLE_NAME
    """
    
    try:
        print("Connecting to Snowflake...\n")
        df = query_to_dataframe(query)
        
        print("=" * 80)
        print(f"Found {len(df)} tables in database")
        print("=" * 80)
        
        if len(df) > 0:
            # Convert column names to lowercase for easier access
            df.columns = df.columns.str.lower()
            
            # Group by schema
            for schema in df['schema'].unique():
                print(f"\n{'='*80}")
                print(f"SCHEMA: {schema}")
                print(f"{'='*80}")
                
                schema_tables = df[df['schema'] == schema]
                for idx, row in schema_tables.iterrows():
                    print(f"\n📊 {row['table_name']}")
                    print(f"   Type: {row['table_type']}")
                    print(f"   Rows: {row['row_count']:,}" if pd.notna(row['row_count']) else "   Rows: N/A")
                    print(f"   Size: {row['bytes']:,} bytes" if pd.notna(row['bytes']) else "   Size: N/A")
                    print(f"   Created: {row['created']}" if pd.notna(row['created']) else "")
                    print(f"   Last Altered: {row['last_altered']}" if pd.notna(row['last_altered']) else "")
                    if pd.notna(row['comment']) and row['comment']:
                        print(f"   Comment: {row['comment']}")
        else:
            print("No tables found")
            
    except Exception as e:
        print(f"Error listing tables: {str(e)}")
        raise


def list_views():
    """List all views visible in the current database"""
    
    query = """
    SELECT 
        TABLE_CATALOG as database,
        TABLE_SCHEMA as schema,
        TABLE_NAME as view_name
    FROM INFORMATION_SCHEMA.VIEWS
    WHERE TABLE_CATALOG = CURRENT_DATABASE()
    ORDER BY TABLE_SCHEMA, TABLE_NAME
    """
    
    try:
        print("\n" + "="*80)
        print("VIEWS")
        print("="*80)
        
        df = query_to_dataframe(query)
        
        if len(df) > 0:
            # Convert column names to lowercase for easier access
            df.columns = df.columns.str.lower()
            
            for schema in df['schema'].unique():
                print(f"\nSCHEMA: {schema}")
                schema_views = df[df['schema'] == schema]
                for idx, row in schema_views.iterrows():
                    print(f"  - {row['view_name']}")
        else:
            print("No views found")
            
    except Exception as e:
        print(f"Error listing views: {str(e)}")
        raise


if __name__ == "__main__":
    try:
        list_all_tables()
        list_views()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

