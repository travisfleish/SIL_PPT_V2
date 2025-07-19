#!/usr/bin/env python3
"""Test script for local development"""

import os
import sys
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Test imports
print("Testing imports...")
try:
    from backend.app import app
    print("✅ Flask app imported successfully")
except Exception as e:
    print(f"❌ Failed to import Flask app: {e}")

# Test Snowflake connection
print("\nTesting Snowflake connection...")
try:
    from data_processors.snowflake_connector import test_connection
    if test_connection():
        print("✅ Snowflake connection successful")
    else:
        print("❌ Snowflake connection failed")
except Exception as e:
    print(f"❌ Error testing Snowflake: {e}")

# Test team config
print("\nTesting team configuration...")
try:
    from utils.team_config_manager import TeamConfigManager
    config_manager = TeamConfigManager()
    teams = config_manager.list_teams()
    print(f"✅ Found {len(teams)} teams: {teams[:3]}...")  # Show first 3
except Exception as e:
    print(f"❌ Error loading teams: {e}")

print("\nTo run the app locally:")
print("cd backend && python app.py")