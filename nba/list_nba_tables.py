#!/usr/bin/env python3
"""
List all tables in the NBA_THOUGHT_LEADERSHIP schema
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from data_processors.snowflake_connector import get_connection, query_to_dataframe

def list_tables_in_schema():
    """List all tables in the NBA_THOUGHT_LEADERSHIP schema"""
    try:
        # Query to get all tables in the schema
        query = """
        SELECT 
            TABLE_NAME,
            TABLE_TYPE,
            ROW_COUNT,
            BYTES,
            CREATED,
            LAST_ALTERED
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = CURRENT_SCHEMA()
        ORDER BY TABLE_NAME
        """
        
        print("🔍 Connecting to Snowflake...")
        print(f"   Schema: NBA_THOUGHT_LEADERSHIP\n")
        
        # Execute query
        df = query_to_dataframe(query)
        
        if df.empty:
            print("❌ No tables found in schema NBA_THOUGHT_LEADERSHIP")
            return
        
        print(f"✅ Found {len(df)} tables:\n")
        print("=" * 100)
        
        # Display results
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
        
        print("\n" + "=" * 100)
        print(f"\n✨ Total: {len(df)} tables")
        
        # Also list just the table names for easy reference
        print("\n📋 Table Names (alphabetical):")
        for table_name in df['TABLE_NAME'].values:
            print(f"   - {table_name}")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    list_tables_in_schema()

