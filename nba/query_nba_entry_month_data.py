#!/usr/bin/env python3
"""
Query NBA entry month subscriber type sports fans data with filters
"""

import pandas as pd
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from data_processors.snowflake_connector import get_connection

# SQL query with filters
query = """
SELECT *
FROM SILAB_DATA_SHARING.NBA_THOUGHT_LEADERSHIP.ENTRY_MONTH_SUBSCRIBER_TYPE_SPORTS_FANS
WHERE COMMUNITY = 'NBA'
  AND ENTRY_YEAR = 2024
  AND MERCHANT_FORMAT_NAME NOT IN ('Univision Now', 'FloSports')
"""

# Execute query using connection
with get_connection() as conn:
    cursor = conn.cursor()
    cursor.execute(query)
    
    # Load results into pandas DataFrame
    df = cursor.fetch_pandas_all()
    cursor.close()

# Print confirmation information
print("=" * 80)
print("QUERY RESULTS CONFIRMATION")
print("=" * 80)
print(f"\nDataFrame shape (rows, columns): {df.shape}")
print(f"\nDistinct COMMUNITY values:")
print(df['COMMUNITY'].unique())
print(f"\nDistinct ENTRY_YEAR values:")
print(df['ENTRY_YEAR'].unique())
print(f"\nDistinct MERCHANT_FORMAT_NAME values:")
print(df['MERCHANT_FORMAT_NAME'].unique())
print(f"\nFirst 5 rows:")
print(df.head())
print("=" * 80)

