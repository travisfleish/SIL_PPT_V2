#!/usr/bin/env python3
"""
Quick test to see which Snowflake authentication method is being used
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Check which authentication method would be used
if os.getenv('SNOWFLAKE_PRIVATE_KEY_BASE64'):
    print("✅ Using SNOWFLAKE_PRIVATE_KEY_BASE64 from environment")
    print(f"   Base64 key starts with: {os.getenv('SNOWFLAKE_PRIVATE_KEY_BASE64')[:50]}...")
elif os.getenv('SNOWFLAKE_PRIVATE_KEY_PATH'):
    print("📁 Using SNOWFLAKE_PRIVATE_KEY_PATH from environment")
    print(f"   Path: {os.getenv('SNOWFLAKE_PRIVATE_KEY_PATH')}")
else:
    print("❌ No Snowflake private key configuration found!")
    print("   Please set either SNOWFLAKE_PRIVATE_KEY_BASE64 or SNOWFLAKE_PRIVATE_KEY_PATH")

# Test actual connection
print("\n🔄 Testing Snowflake connection...")
try:
    import sys

    sys.path.append('..')
    from data_processors.snowflake_connector import test_connection

    if test_connection():
        print("✅ Successfully connected to Snowflake!")
    else:
        print("❌ Failed to connect to Snowflake")
except Exception as e:
    print(f"❌ Error testing connection: {e}")