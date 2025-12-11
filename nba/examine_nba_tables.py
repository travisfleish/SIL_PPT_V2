#!/usr/bin/env python3
"""
Examine the structure and sample data from each NBA table
"""

import sys
from pathlib import Path
import pandas as pd

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from data_processors.snowflake_connector import query_to_dataframe

def examine_table(table_name):
    """Examine a table's structure and sample data"""
    print(f"\n{'='*100}")
    print(f"📊 TABLE: {table_name}")
    print('='*100)
    
    try:
        # Get column information
        col_query = f"""
        SELECT 
            COLUMN_NAME,
            DATA_TYPE,
            CHARACTER_MAXIMUM_LENGTH,
            IS_NULLABLE,
            COLUMN_DEFAULT
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = CURRENT_SCHEMA()
        AND TABLE_NAME = '{table_name}'
        ORDER BY ORDINAL_POSITION
        """
        
        cols_df = query_to_dataframe(col_query)
        
        print(f"\n📋 Columns ({len(cols_df)} total):")
        print("-" * 100)
        for idx, row in cols_df.iterrows():
            col_type = row['DATA_TYPE']
            if row['CHARACTER_MAXIMUM_LENGTH']:
                col_type += f"({row['CHARACTER_MAXIMUM_LENGTH']})"
            nullable = "NULL" if row['IS_NULLABLE'] == 'YES' else "NOT NULL"
            print(f"  {idx+1:2d}. {row['COLUMN_NAME']:<40} {col_type:<20} {nullable}")
        
        # Get row count
        count_query = f"SELECT COUNT(*) as cnt FROM {table_name}"
        count_df = query_to_dataframe(count_query)
        row_count = count_df['CNT'].iloc[0]
        print(f"\n📈 Row Count: {row_count:,}")
        
        # Get sample data (first 5 rows)
        sample_query = f"SELECT * FROM {table_name} LIMIT 5"
        sample_df = query_to_dataframe(sample_query)
        
        print(f"\n🔍 Sample Data (first 5 rows):")
        print("-" * 100)
        if not sample_df.empty:
            # Display sample with better formatting
            pd.set_option('display.max_columns', None)
            pd.set_option('display.width', None)
            pd.set_option('display.max_colwidth', 50)
            print(sample_df.to_string(index=False))
        else:
            print("  (No data)")
        
        # Get distinct values for key columns (if they exist)
        key_columns = ['AUDIENCE', 'COMMUNITY', 'CATEGORY', 'SUBCATEGORY', 'MERCHANT']
        print(f"\n🔑 Distinct Values in Key Columns:")
        print("-" * 100)
        for col in key_columns:
            if col in sample_df.columns:
                distinct_query = f"SELECT COUNT(DISTINCT {col}) as cnt FROM {table_name}"
                distinct_df = query_to_dataframe(distinct_query)
                count = distinct_df['CNT'].iloc[0]
                print(f"  {col}: {count:,} distinct values")
                
                # Show sample values
                values_query = f"SELECT DISTINCT {col} FROM {table_name} LIMIT 10"
                values_df = query_to_dataframe(values_query)
                if not values_df.empty:
                    sample_values = values_df[col].tolist()
                    print(f"    Examples: {', '.join(str(v) for v in sample_values[:5])}")
        
    except Exception as e:
        print(f"❌ Error examining table: {str(e)}")
        import traceback
        traceback.print_exc()

def main():
    """Examine all five base tables"""
    tables = [
        'NBA_SIL_CATEGORY_INDEXING_SNAPSHOT',
        'NBA_SIL_COMMUNITY_INDEXING_SNAPSHOT',
        'NBA_SIL_COMMUNITY_MERCHANT_INDEXING_SNAPSHOT',
        'NBA_SIL_MERCHANT_INDEXING_SNAPSHOT',
        'NBA_SIL_SUBCATEGORY_INDEXING_SNAPSHOT'
    ]
    
    print("🔍 Examining NBA_THOUGHT_LEADERSHIP Tables")
    print("="*100)
    
    for table in tables:
        examine_table(table)
        print("\n")
    
    print("="*100)
    print("✨ Analysis Complete!")

if __name__ == "__main__":
    main()

