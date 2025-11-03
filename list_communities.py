#!/usr/bin/env python3
"""
Script to list distinct communities in SIL_DEMOGRAPHICS_DIST table
"""

from data_processors.snowflake_connector import query_to_dataframe
import pandas as pd

def list_distinct_communities():
    """List distinct communities in SOUTH_CAROLINA_TOURISM.SIL_DEMOGRAPHICS_DIST"""
    
    # First, let's see what columns are available
    query_columns = """
    SELECT COLUMN_NAME, DATA_TYPE
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_CATALOG = CURRENT_DATABASE()
      AND TABLE_SCHEMA = 'SOUTH_CAROLINA_TOURISM'
      AND TABLE_NAME = 'SIL_DEMOGRAPHICS_DIST'
    ORDER BY ORDINAL_POSITION
    """
    
    try:
        print("Getting column information...\n")
        df_cols = query_to_dataframe(query_columns)
        df_cols.columns = df_cols.columns.str.lower()
        
        print("=" * 80)
        print("TABLE COLUMNS")
        print("=" * 80)
        for idx, row in df_cols.iterrows():
            print(f"{row['column_name']} ({row['data_type']})")
        
        # Now get distinct communities
        # Try common column name variations
        query_community = """
        SELECT DISTINCT COMMUNITY
        FROM SOUTH_CAROLINA_TOURISM.SIL_DEMOGRAPHICS_DIST
        ORDER BY COMMUNITY
        """
        
        print("\n" + "=" * 80)
        print("DISTINCT COMMUNITIES")
        print("=" * 80)
        
        df = query_to_dataframe(query_community)
        
        if len(df) > 0:
            print(f"\nFound {len(df)} distinct community(ies):\n")
            for idx, row in df.iterrows():
                print(f"  • {row['COMMUNITY']}")
        else:
            print("No communities found or column name might be different")
            
    except Exception as e:
        print(f"Error: {str(e)}")
        print("\nTrying to identify the community column...")
        
        # Try to get a sample row to see the structure
        sample_query = """
        SELECT *
        FROM SOUTH_CAROLINA_TOURISM.SIL_DEMOGRAPHICS_DIST
        LIMIT 1
        """
        
        try:
            df_sample = query_to_dataframe(sample_query)
            df_sample.columns = df_sample.columns.str.lower()
            print("\nSample row structure:")
            for col in df_sample.columns:
                print(f"  {col}: {df_sample.iloc[0][col]}")
        except:
            pass
        
        raise


if __name__ == "__main__":
    try:
        list_distinct_communities()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()


