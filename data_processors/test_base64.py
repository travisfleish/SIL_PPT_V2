#!/usr/bin/env python3
"""
Test script to verify base64 private key authentication with Snowflake
"""

import os
import base64
import snowflake.connector
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def test_base64_connection():
    """Test Snowflake connection using base64 encoded private key"""

    print("=== Testing Base64 Private Key Connection ===\n")

    # Get the base64 key from environment
    private_key_base64 = os.getenv('SNOWFLAKE_PRIVATE_KEY_BASE64')

    if not private_key_base64:
        print("❌ SNOWFLAKE_PRIVATE_KEY_BASE64 not found in environment")
        return False

    print(f"✅ Found base64 private key (length: {len(private_key_base64)} chars)")

    try:
        # Decode base64
        print("\n1. Decoding base64...")
        private_key_pem = base64.b64decode(private_key_base64)
        print(f"✅ Decoded to {len(private_key_pem)} bytes")

        # Check if it's a valid PEM format
        pem_str = private_key_pem.decode('utf-8')
        if "BEGIN PRIVATE KEY" in pem_str or "BEGIN RSA PRIVATE KEY" in pem_str:
            print("✅ Valid PEM format detected")
        else:
            print("⚠️  Warning: May not be valid PEM format")

        # Load the private key
        print("\n2. Loading private key...")
        p_key = serialization.load_pem_private_key(
            private_key_pem,
            password=None,
            backend=default_backend()
        )
        print("✅ Private key loaded successfully")

        # Convert to DER format
        print("\n3. Converting to DER format...")
        pkb = p_key.private_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        print(f"✅ Converted to DER format ({len(pkb)} bytes)")

        # Try to connect
        print("\n4. Connecting to Snowflake...")
        conn_params = {
            'account': os.getenv('SNOWFLAKE_ACCOUNT'),
            'user': os.getenv('SNOWFLAKE_USER'),
            'warehouse': os.getenv('SNOWFLAKE_WAREHOUSE', 'COMPUTE_WH'),
            'database': os.getenv('SNOWFLAKE_DATABASE', 'SIL__TB_OTT_TEST'),
            'schema': os.getenv('SNOWFLAKE_SCHEMA', 'SC_TWINBRAINAI'),
            'role': os.getenv('SNOWFLAKE_ROLE', 'ACCOUNTADMIN'),
            'private_key': pkb
        }

        print(f"   Account: {conn_params['account']}")
        print(f"   User: {conn_params['user']}")
        print(f"   Database: {conn_params['database']}")

        conn = snowflake.connector.connect(**conn_params)

        # Test the connection
        cursor = conn.cursor()
        cursor.execute("SELECT CURRENT_USER(), CURRENT_ACCOUNT()")
        result = cursor.fetchone()

        print(f"\n✅ CONNECTION SUCCESSFUL!")
        print(f"   Connected as: {result[0]}")
        print(f"   Account: {result[1]}")

        conn.close()
        return True

    except base64.binascii.Error as e:
        print(f"\n❌ Base64 decode error: {e}")
        print("   Make sure the SNOWFLAKE_PRIVATE_KEY_BASE64 is valid base64")

    except ValueError as e:
        print(f"\n❌ Private key format error: {e}")
        print("   The decoded content doesn't appear to be a valid private key")

    except Exception as e:
        print(f"\n❌ Connection failed: {type(e).__name__}: {e}")

    return False


def compare_keys():
    """Compare file-based and base64 keys to ensure they match"""
    print("\n=== Comparing File and Base64 Keys ===\n")

    private_key_path = os.getenv('SNOWFLAKE_PRIVATE_KEY_PATH')
    private_key_base64 = os.getenv('SNOWFLAKE_PRIVATE_KEY_BASE64')

    if not private_key_path or not os.path.exists(private_key_path):
        print("❌ SNOWFLAKE_PRIVATE_KEY_PATH not found or file doesn't exist")
        return

    if not private_key_base64:
        print("❌ SNOWFLAKE_PRIVATE_KEY_BASE64 not found")
        return

    try:
        # Read file
        with open(private_key_path, 'rb') as f:
            file_content = f.read()

        # Decode base64
        base64_content = base64.b64decode(private_key_base64)

        # Compare
        if file_content == base64_content:
            print("✅ File and base64 keys MATCH!")
        else:
            print("❌ File and base64 keys DO NOT MATCH!")
            print(f"   File length: {len(file_content)} bytes")
            print(f"   Base64 decoded length: {len(base64_content)} bytes")

            # Check if one is encrypted and other isn't
            file_str = file_content.decode('utf-8', errors='ignore')
            base64_str = base64_content.decode('utf-8', errors='ignore')

            if "ENCRYPTED" in file_str and "ENCRYPTED" not in base64_str:
                print("   ⚠️  File key is encrypted, base64 key is not")
            elif "ENCRYPTED" not in file_str and "ENCRYPTED" in base64_str:
                print("   ⚠️  Base64 key is encrypted, file key is not")

    except Exception as e:
        print(f"❌ Error comparing keys: {e}")


def create_base64_from_file():
    """Helper to create base64 from file if needed"""
    print("\n=== Creating Base64 from File ===\n")

    private_key_path = os.getenv('SNOWFLAKE_PRIVATE_KEY_PATH')

    if not private_key_path or not os.path.exists(private_key_path):
        print("❌ SNOWFLAKE_PRIVATE_KEY_PATH not found or file doesn't exist")
        return

    try:
        with open(private_key_path, 'rb') as f:
            file_content = f.read()

        # Encode to base64
        base64_encoded = base64.b64encode(file_content).decode('utf-8')

        print("✅ Base64 encoded successfully!")
        print(f"   Original size: {len(file_content)} bytes")
        print(f"   Base64 length: {len(base64_encoded)} chars")
        print("\n📋 Add this to your .env file:")
        print(f"SNOWFLAKE_PRIVATE_KEY_BASE64={base64_encoded[:50]}...{base64_encoded[-50:]}")
        print(f"\n(Full base64 string is {len(base64_encoded)} characters)")

        # Save to file if you want
        # with open('private_key_base64.txt', 'w') as f:
        #     f.write(f"SNOWFLAKE_PRIVATE_KEY_BASE64={base64_encoded}")
        # print("\n💾 Saved to private_key_base64.txt")

    except Exception as e:
        print(f"❌ Error creating base64: {e}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "create":
        create_base64_from_file()
    elif len(sys.argv) > 1 and sys.argv[1] == "compare":
        compare_keys()
    else:
        # Test the base64 connection
        success = test_base64_connection()

        if not success:
            print("\n💡 Tip: Run 'python test_base64_connection.py create' to generate base64 from your file")
            print("     Or: Run 'python test_base64_connection.py compare' to compare file and base64 keys")