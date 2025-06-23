#!/usr/bin/env python3
"""
Centralized Snowflake connection manager for Sports Innovation Lab
Handles authentication and provides reusable connection/query functions
"""

import os
import sys
import snowflake.connector
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


def get_connection():
    """
    Get Snowflake connection using environment variables
    Supports both password and key-pair authentication
    """
    try:
        # Get credentials from environment
        account = os.getenv('SNOWFLAKE_ACCOUNT')
        user = os.getenv('SNOWFLAKE_USER')
        password = os.getenv('SNOWFLAKE_PASSWORD')
        private_key_path = os.getenv('SNOWFLAKE_PRIVATE_KEY_PATH')

        if not account or not user:
            raise ValueError("Missing required Snowflake credentials in .env file")

        # Base connection parameters - CORRECTED DATABASE NAME
        conn_params = {
            'account': account,
            'user': user,
            'warehouse': os.getenv('SNOWFLAKE_WAREHOUSE', 'COMPUTE_WH'),
            'database': os.getenv('SNOWFLAKE_DATABASE', 'SIL__TB_OTT_TEST'),  # Two underscores!
            'schema': os.getenv('SNOWFLAKE_SCHEMA', 'SC_TWINBRAINAI'),
            'role': os.getenv('SNOWFLAKE_ROLE', 'ACCOUNTADMIN')
        }

        # Use private key if available, otherwise use password
        if private_key_path and os.path.exists(private_key_path):
            logger.info("Using key-pair authentication")
            with open(private_key_path, "rb") as key_file:
                private_key = key_file.read()

            from cryptography.hazmat.backends import default_backend
            from cryptography.hazmat.primitives import serialization

            p_key = serialization.load_pem_private_key(
                private_key,
                password=None,
                backend=default_backend()
            )

            pkb = p_key.private_bytes(
                encoding=serialization.Encoding.DER,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )

            conn_params['private_key'] = pkb
        elif password:
            logger.info("Using password authentication")
            conn_params['password'] = password
        else:
            raise ValueError("No authentication method available (password or private key)")

        # Create connection
        conn = snowflake.connector.connect(**conn_params)
        logger.info("Successfully connected to Snowflake")
        return conn

    except Exception as e:
        logger.error(f"Failed to connect to Snowflake: {str(e)}")
        raise


def query_to_dataframe(query, params=None):
    """
    Execute a query and return results as a pandas DataFrame

    Args:
        query (str): SQL query to execute
        params (dict): Optional query parameters

    Returns:
        pd.DataFrame: Query results
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)

        # Fetch results into DataFrame
        df = cursor.fetch_pandas_all()

        return df

    except Exception as e:
        logger.error(f"Query failed: {str(e)}")
        raise
    finally:
        if conn:
            conn.close()


def test_connection():
    """Test Snowflake connection"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                CURRENT_USER() as user, 
                CURRENT_ACCOUNT() as account, 
                CURRENT_WAREHOUSE() as warehouse,
                CURRENT_DATABASE() as database,
                CURRENT_SCHEMA() as schema
        """)
        result = cursor.fetchone()
        print(f"✅ Connected successfully!")
        print(f"   User: {result[0]}")
        print(f"   Account: {result[1]}")
        print(f"   Warehouse: {result[2]}")
        print(f"   Database: {result[3]}")
        print(f"   Schema: {result[4]}")
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Connection failed: {str(e)}")
        return False


if __name__ == "__main__":
    # Test the connection when run directly
    test_connection()