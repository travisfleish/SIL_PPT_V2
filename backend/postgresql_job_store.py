import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from contextlib import contextmanager
from uuid import uuid4
import time

import psycopg2
from psycopg2.extras import RealDictCursor, Json
from psycopg2.pool import SimpleConnectionPool

logger = logging.getLogger(__name__)


class PostgreSQLJobStore:
    """PostgreSQL-backed job storage with connection pooling and automatic cleanup."""

    def __init__(self, database_url: Optional[str] = None, min_conn: int = 1, max_conn: int = 10):
        self.database_url = database_url or os.environ.get('DATABASE_URL')
        if not self.database_url:
            raise ValueError("DATABASE_URL must be provided")

        # Render.com provides the database URL, but we might need to handle SSL
        if 'render.com' in self.database_url and 'sslmode' not in self.database_url:
            self.database_url += '?sslmode=require'

        # Initialize connection pool with retry logic
        max_retries = 3
        retry_delay = 2

        for attempt in range(max_retries):
            try:
                self.pool = SimpleConnectionPool(min_conn, max_conn, self.database_url)
                logger.info("Successfully created PostgreSQL connection pool")
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                logger.warning(f"Failed to create connection pool (attempt {attempt + 1}/{max_retries}): {e}")
                time.sleep(retry_delay)

        self._ensure_tables()

    def _ensure_tables(self):
        """Create tables if they don't exist."""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                # Create jobs table
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS jobs (
                        job_id UUID PRIMARY KEY,
                        team_key VARCHAR(100) NOT NULL,
                        status VARCHAR(50) NOT NULL DEFAULT 'pending',
                        progress INTEGER DEFAULT 0,
                        error TEXT,
                        result JSONB,
                        options JSONB,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        expires_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() + INTERVAL '24 hours'
                    )
                ''')

                # Create indexes for better performance
                indexes = [
                    "CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)",
                    "CREATE INDEX IF NOT EXISTS idx_jobs_team_key ON jobs(team_key)",
                    "CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at DESC)",
                    "CREATE INDEX IF NOT EXISTS idx_jobs_expires_at ON jobs(expires_at)"
                ]

                for index in indexes:
                    cur.execute(index)

                # Create update trigger for updated_at
                cur.execute('''
                    CREATE OR REPLACE FUNCTION update_updated_at_column()
                    RETURNS TRIGGER AS $$
                    BEGIN
                        NEW.updated_at = NOW();
                        RETURN NEW;
                    END;
                    $$ language 'plpgsql';
                ''')

                cur.execute('''
                    DROP TRIGGER IF EXISTS update_jobs_updated_at ON jobs;
                    CREATE TRIGGER update_jobs_updated_at 
                    BEFORE UPDATE ON jobs 
                    FOR EACH ROW 
                    EXECUTE FUNCTION update_updated_at_column();
                ''')

                conn.commit()
                logger.info("Database tables and indexes created/verified")

    @contextmanager
    def _get_connection(self):
        """Get a connection from the pool."""
        conn = None
        try:
            conn = self.pool.getconn()
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                self.pool.putconn(conn)

    def create_job(self, team_key: str, options: Dict[str, Any]) -> str:
        """Create a new job and return its ID."""
        job_id = str(uuid4())

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    INSERT INTO jobs (job_id, team_key, status, options)
                    VALUES (%s, %s, %s, %s)
                    RETURNING job_id
                ''', (job_id, team_key, 'pending', Json(options)))
                conn.commit()

        logger.info(f"Created job {job_id} for team {team_key}")
        return job_id

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job by ID."""
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute('''
                        SELECT job_id, team_key, status, progress, error, result, options,
                               created_at, updated_at
                        FROM jobs
                        WHERE job_id = %s
                    ''', (job_id,))

                    row = cur.fetchone()
                    if row:
                        # Convert to regular dict and ensure job_id is string
                        job_data = dict(row)
                        job_data['job_id'] = str(job_data['job_id'])
                        # Convert datetime objects to ISO format strings
                        if job_data.get('created_at'):
                            job_data['created_at'] = job_data['created_at'].isoformat()
                        if job_data.get('updated_at'):
                            job_data['updated_at'] = job_data['updated_at'].isoformat()
                        return job_data
                    return None
        except Exception as e:
            logger.error(f"Error getting job {job_id}: {e}")
            return None

    def update_job(self, job_id: str, **kwargs) -> bool:
        """Update job fields."""
        # Build dynamic UPDATE query
        allowed_fields = {'status', 'progress', 'error', 'result'}
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}

        if not updates:
            return False

        # Convert result to JSON if present
        if 'result' in updates:
            updates['result'] = Json(updates['result'])

        set_clause = ', '.join(f"{k} = %s" for k in updates.keys())
        values = list(updates.values())
        values.append(job_id)

        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(f'''
                        UPDATE jobs
                        SET {set_clause}
                        WHERE job_id = %s
                    ''', values)
                    conn.commit()

                    updated = cur.rowcount > 0
                    if updated:
                        logger.info(f"Updated job {job_id}: {list(updates.keys())}")
                    return updated
        except Exception as e:
            logger.error(f"Error updating job {job_id}: {e}")
            return False

    def list_recent_jobs(self, limit: int = 100) -> List[Dict[str, Any]]:
        """List recent jobs."""
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute('''
                        SELECT job_id, team_key, status, progress, created_at
                        FROM jobs
                        WHERE expires_at > NOW()
                        ORDER BY created_at DESC
                        LIMIT %s
                    ''', (limit,))

                    jobs = []
                    for row in cur.fetchall():
                        job_data = dict(row)
                        job_data['job_id'] = str(job_data['job_id'])
                        if job_data.get('created_at'):
                            job_data['created_at'] = job_data['created_at'].isoformat()
                        jobs.append(job_data)

                    return jobs
        except Exception as e:
            logger.error(f"Error listing jobs: {e}")
            return []

    def cleanup_expired_jobs(self) -> int:
        """Remove expired jobs. Returns count of deleted jobs."""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute('''
                        DELETE FROM jobs
                        WHERE expires_at < NOW()
                        RETURNING job_id
                    ''')
                    deleted_count = cur.rowcount
                    conn.commit()

                    if deleted_count > 0:
                        logger.info(f"Cleaned up {deleted_count} expired jobs")

                    return deleted_count
        except Exception as e:
            logger.error(f"Error cleaning up jobs: {e}")
            return 0

    def get_job_stats(self) -> Dict[str, Any]:
        """Get job statistics."""
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute('''
                        SELECT 
                            COUNT(*) as total_jobs,
                            COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed,
                            COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed,
                            COUNT(CASE WHEN status = 'running' THEN 1 END) as running,
                            COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending
                        FROM jobs
                        WHERE expires_at > NOW()
                    ''')

                    return dict(cur.fetchone())
        except Exception as e:
            logger.error(f"Error getting job stats: {e}")
            return {
                'total_jobs': 0,
                'completed': 0,
                'failed': 0,
                'running': 0,
                'pending': 0
            }

    def close(self):
        """Close all connections in the pool."""
        if hasattr(self, 'pool'):
            self.pool.closeall()
            logger.info("Closed all PostgreSQL connections")


# Example usage for testing
if __name__ == '__main__':
    # Test the connection
    store = PostgreSQLJobStore()

    # Create a test job
    job_id = store.create_job('test_team', {'test': True})
    print(f"Created job: {job_id}")

    # Get the job
    job = store.get_job(job_id)
    print(f"Retrieved job: {job}")

    # Update the job
    store.update_job(job_id, status='running', progress=50)

    # Get updated job
    job = store.get_job(job_id)
    print(f"Updated job: {job}")

    # List jobs
    jobs = store.list_recent_jobs()
    print(f"Recent jobs: {jobs}")

    # Get stats
    stats = store.get_job_stats()
    print(f"Job stats: {stats}")

    # Close connections
    store.close()