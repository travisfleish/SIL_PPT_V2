#!/usr/bin/env python3
"""
Centralized Snowflake connection manager for Sports Innovation Lab
Handles authentication and provides reusable connection/query functions
ENHANCED with connection pooling for better performance
"""

import os
import sys
import base64
import snowflake.connector
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
import logging
import threading
import queue
import time
from contextlib import contextmanager
from typing import Optional

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


class SnowflakeConnectionPool:
    """Thread-safe connection pool for Snowflake"""

    def __init__(self, min_connections=5, max_connections=20, connection_lifetime=3600):
        """
        Initialize connection pool

        Args:
            min_connections: Minimum number of connections to maintain
            max_connections: Maximum number of connections allowed
            connection_lifetime: How long a connection can live (seconds)
        """
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.connection_lifetime = connection_lifetime

        # Thread-safe queue to hold available connections
        self._pool = queue.Queue(maxsize=max_connections)
        self._all_connections = []
        self._lock = threading.Lock()
        self._created_connections = 0
        self._closed = False

        # Connection parameters (will be set on first use)
        self._conn_params = None

        logger.info(f"Initializing connection pool (min={min_connections}, max={max_connections})")

    def _create_connection_params(self):
        """Create connection parameters (only called once)"""
        # Get credentials from environment
        account = os.getenv('SNOWFLAKE_ACCOUNT')
        user = os.getenv('SNOWFLAKE_USER')
        password = os.getenv('SNOWFLAKE_PASSWORD')
        private_key_path = os.getenv('SNOWFLAKE_PRIVATE_KEY_PATH')
        private_key_base64 = os.getenv('SNOWFLAKE_PRIVATE_KEY_BASE64')

        if not account or not user:
            raise ValueError("Missing required Snowflake credentials in .env file")

        # Base connection parameters
        conn_params = {
            'account': account,
            'user': user,
            'warehouse': os.getenv('SNOWFLAKE_WAREHOUSE', 'COMPUTE_WH'),
            'database': os.getenv('SNOWFLAKE_DATABASE', 'SIL__TB_OTT_TEST'),
            'schema': os.getenv('SNOWFLAKE_SCHEMA', 'SC_TWINBRAINAI'),
            'role': os.getenv('SNOWFLAKE_ROLE', 'ACCOUNTADMIN')
        }

        # Import cryptography modules
        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives import serialization

        # Try different authentication methods in order
        private_key_loaded = False

        # 1. Try base64 encoded private key first (for production/Render)
        if private_key_base64:
            try:
                logger.info("Using key-pair authentication (base64)")
                private_key_pem = base64.b64decode(private_key_base64)

                p_key = serialization.load_pem_private_key(
                    private_key_pem,
                    password=None,
                    backend=default_backend()
                )

                pkb = p_key.private_bytes(
                    encoding=serialization.Encoding.DER,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                )

                conn_params['private_key'] = pkb
                private_key_loaded = True

            except Exception as e:
                logger.warning(f"Failed to load base64 private key: {str(e)}")

        # 2. Try private key from file path (for local development)
        if not private_key_loaded and private_key_path and os.path.exists(private_key_path):
            try:
                logger.info("Using key-pair authentication (file)")
                with open(private_key_path, "rb") as key_file:
                    private_key = key_file.read()

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
                private_key_loaded = True

            except Exception as e:
                logger.warning(f"Failed to load private key from file: {str(e)}")

        # 3. Fall back to password authentication
        if not private_key_loaded:
            if password:
                logger.info("Using password authentication")
                conn_params['password'] = password
            else:
                raise ValueError("No authentication method available (password or private key)")

        return conn_params

    def _create_connection(self):
        """Create a new Snowflake connection"""
        if self._conn_params is None:
            self._conn_params = self._create_connection_params()

        conn = snowflake.connector.connect(**self._conn_params)
        conn._created_time = time.time()  # Track creation time
        return conn

    def _is_connection_valid(self, conn):
        """Check if a connection is still valid"""
        try:
            # Check if connection is alive
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()

            # Check connection age
            if hasattr(conn, '_created_time'):
                age = time.time() - conn._created_time
                if age > self.connection_lifetime:
                    logger.debug(f"Connection exceeded lifetime ({age:.0f}s)")
                    return False

            return True
        except Exception:
            return False

    def _ensure_min_connections(self):
        """Ensure minimum number of connections exist"""
        with self._lock:
            while self._created_connections < self.min_connections and not self._closed:
                try:
                    conn = self._create_connection()
                    self._pool.put(conn)
                    self._all_connections.append(conn)
                    self._created_connections += 1
                    logger.debug(f"Created connection {self._created_connections}/{self.min_connections}")
                except Exception as e:
                    logger.error(f"Failed to create connection: {e}")
                    break

    def get_connection(self, timeout=30):
        """
        Get a connection from the pool

        Args:
            timeout: Maximum time to wait for a connection (seconds)

        Returns:
            Snowflake connection object
        """
        if self._closed:
            raise RuntimeError("Connection pool is closed")

        # Initialize pool on first use (lazy loading)
        if self._created_connections == 0:
            self._ensure_min_connections()

        # Try to get a connection from the pool
        try:
            # Try to get existing connection without blocking
            conn = self._pool.get_nowait()

            # Validate connection
            if self._is_connection_valid(conn):
                logger.debug("Reusing connection from pool")
                return conn
            else:
                # Connection is dead, remove it
                logger.debug("Removing invalid connection")
                with self._lock:
                    self._all_connections.remove(conn)
                    self._created_connections -= 1
                try:
                    conn.close()
                except:
                    pass
        except queue.Empty:
            pass

        # No valid connection available, create new one if under limit
        with self._lock:
            if self._created_connections < self.max_connections:
                try:
                    conn = self._create_connection()
                    self._all_connections.append(conn)
                    self._created_connections += 1
                    logger.debug(f"Created new connection ({self._created_connections}/{self.max_connections})")
                    return conn
                except Exception as e:
                    logger.error(f"Failed to create new connection: {e}")
                    raise

        # Max connections reached, wait for one to be returned
        logger.debug(f"Waiting for connection (timeout={timeout}s)")
        try:
            conn = self._pool.get(timeout=timeout)
            if self._is_connection_valid(conn):
                return conn
            else:
                # Recursive call to try again
                return self.get_connection(timeout=timeout)
        except queue.Empty:
            raise RuntimeError(f"No connection available within {timeout} seconds")

    def return_connection(self, conn):
        """Return a connection to the pool"""
        if self._closed:
            # Pool is closed, just close the connection
            try:
                conn.close()
            except:
                pass
            return

        if conn is None:
            return

        # Check if connection is still valid before returning to pool
        if self._is_connection_valid(conn):
            try:
                self._pool.put_nowait(conn)
                logger.debug("Returned connection to pool")
            except queue.Full:
                # Pool is full, close the connection
                logger.debug("Pool full, closing connection")
                with self._lock:
                    self._all_connections.remove(conn)
                    self._created_connections -= 1
                try:
                    conn.close()
                except:
                    pass
        else:
            # Connection is invalid, close it
            logger.debug("Invalid connection, closing")
            with self._lock:
                if conn in self._all_connections:
                    self._all_connections.remove(conn)
                    self._created_connections -= 1
            try:
                conn.close()
            except:
                pass

    def close_all(self):
        """Close all connections and shut down the pool"""
        logger.info("Closing connection pool")
        self._closed = True

        # Close all connections
        with self._lock:
            # Empty the queue
            while not self._pool.empty():
                try:
                    conn = self._pool.get_nowait()
                    conn.close()
                except:
                    pass

            # Close any remaining connections
            for conn in self._all_connections:
                try:
                    conn.close()
                except:
                    pass

            self._all_connections.clear()
            self._created_connections = 0


# Create a global connection pool instance
_connection_pool = None


def _get_pool():
    """Get or create the global connection pool"""
    global _connection_pool
    if _connection_pool is None:
        _connection_pool = SnowflakeConnectionPool(
            min_connections=5,
            max_connections=20,
            connection_lifetime=3600  # 1 hour
        )
    return _connection_pool


@contextmanager
def get_connection():
    """
    Get a Snowflake connection from the pool

    Usage:
        with get_connection() as conn:
            # use connection
            pass
    """
    pool = _get_pool()
    conn = None
    try:
        conn = pool.get_connection()
        yield conn
    finally:
        if conn:
            pool.return_connection(conn)


def query_to_dataframe(query, params=None):
    """
    Execute a query and return results as a pandas DataFrame
    Now uses connection pooling for better performance

    Args:
        query (str): SQL query to execute
        params (dict): Optional query parameters

    Returns:
        pd.DataFrame: Query results
    """
    conn = None
    pool = _get_pool()

    try:
        # Get connection from pool
        conn = pool.get_connection()
        cursor = conn.cursor()

        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)

        # Fetch results into DataFrame
        df = cursor.fetch_pandas_all()
        cursor.close()

        return df

    except Exception as e:
        logger.error(f"Query failed: {str(e)}")
        raise
    finally:
        if conn:
            # Return connection to pool instead of closing
            pool.return_connection(conn)


def test_connection():
    """Test Snowflake connection (now tests pool)"""
    try:
        with get_connection() as conn:
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
            cursor.close()

            print(f"✅ Connected successfully!")
            print(f"   User: {result[0]}")
            print(f"   Account: {result[1]}")
            print(f"   Warehouse: {result[2]}")
            print(f"   Database: {result[3]}")
            print(f"   Schema: {result[4]}")

            # Show pool status
            pool = _get_pool()
            print(f"\n📊 Connection Pool Status:")
            print(f"   Active connections: {pool._created_connections}")
            print(f"   Available in pool: {pool._pool.qsize()}")

        return True
    except Exception as e:
        print(f"❌ Connection failed: {str(e)}")
        return False


def close_pool():
    """Close the connection pool (call at application shutdown)"""
    global _connection_pool
    if _connection_pool:
        _connection_pool.close_all()
        _connection_pool = None


if __name__ == "__main__":
    # Test the connection when run directly
    test_connection()

    # Test multiple queries to see pooling in action
    print("\n🔄 Testing multiple queries...")
    import time

    start = time.time()
    for i in range(5):
        df = query_to_dataframe("SELECT CURRENT_TIMESTAMP() as time")
        print(f"   Query {i + 1}: {df.iloc[0]['TIME']}")

    elapsed = time.time() - start
    print(f"\n⏱️  5 queries completed in {elapsed:.2f} seconds")
    print(f"   Average: {elapsed / 5:.2f} seconds per query")

    # Clean up
    close_pool()