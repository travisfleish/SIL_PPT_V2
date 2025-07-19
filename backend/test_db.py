#!/usr/bin/env python3
"""Test PostgreSQL database connection from Render."""

import os
from postgresql_job_store import PostgreSQLJobStore

# Use the External Database URL for local testing
EXTERNAL_DB_URL = "postgresql://sil_powerpoint_db_user:NcqJKvXxBcRgsuFnPWNVgeUXrrxATLpR@dpg-d1u2jf3uibrs73821rqg-a.virginia-postgres.render.com/sil_powerpoint_db"


def test_connection():
    print("Testing PostgreSQL connection...")

    try:
        # Create job store instance
        store = PostgreSQLJobStore(EXTERNAL_DB_URL)
        print("✅ Successfully connected to PostgreSQL!")

        # Test creating a job
        job_id = store.create_job('test_team', {'test': True})
        print(f"✅ Created test job: {job_id}")

        # Test retrieving the job
        job = store.get_job(job_id)
        print(f"✅ Retrieved job: {job}")

        # Test updating the job
        success = store.update_job(job_id, status='completed', progress=100)
        print(f"✅ Updated job: {success}")

        # Test listing jobs
        jobs = store.list_recent_jobs(limit=5)
        print(f"✅ Found {len(jobs)} recent jobs")

        # Get statistics
        stats = store.get_job_stats()
        print(f"✅ Job statistics: {stats}")

        # Cleanup
        store.close()
        print("✅ All tests passed!")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_connection()