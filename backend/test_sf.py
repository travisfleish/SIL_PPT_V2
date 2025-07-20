#!/usr/bin/env python3
import os
import sys
from pathlib import Path

# Setup paths
backend_dir = Path(__file__).parent
project_dir = backend_dir.parent
os.chdir(backend_dir)
sys.path.insert(0, str(project_dir))

# Load env vars
from dotenv import load_dotenv

env_path = project_dir / '.env'
load_dotenv(env_path, override=True)

print("Environment Check:")
print(f"Working dir: {os.getcwd()}")
print(f"Env path: {env_path} (exists: {env_path.exists()})")
print(f"SNOWFLAKE_ACCOUNT: {os.getenv('SNOWFLAKE_ACCOUNT', 'NOT SET')}")

# Now try importing in Flask context
try:
    from flask import Flask

    app = Flask(__name__)

    # Import after Flask is created
    from data_processors.snowflake_connector import test_connection

    with app.app_context():
        print("\nTesting connection in Flask context:")
        result = test_connection()
        print(f"Result: {result}")

except Exception as e:
    print(f"Error: {e}")
    import traceback

    traceback.print_exc()