#!/usr/bin/env python3
"""
Standalone script to add missing columns to the jobs table
Run this once to migrate your database
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import sys

# Replace this with your External Database URL from Render
DATABASE_URL = "postgresql://sil_powerpoint_db_user:NcqJKvXxBcRgsuFnPWNVgeUXrrxATLpR@dpg-d1u2jf3uibrs73821rqg-a.virginia-postgres.render.com/sil_powerpoint_db"


def migrate_database():
    """Add missing columns to jobs table"""
    conn = None
    try:
        print("Connecting to database...")
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        # First, check what columns currently exist
        print("\nChecking existing columns...")
        cur.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'jobs'
            ORDER BY ordinal_position
        """)

        existing_columns = cur.fetchall()
        print("\nCurrent columns:")
        for col in existing_columns:
            print(f"  - {col[0]} ({col[1]})")

        # Add missing columns
        print("\nAdding missing columns...")
        cur.execute('''
            ALTER TABLE jobs 
            ADD COLUMN IF NOT EXISTS team_name VARCHAR(200),
            ADD COLUMN IF NOT EXISTS message TEXT,
            ADD COLUMN IF NOT EXISTS output_file TEXT,
            ADD COLUMN IF NOT EXISTS output_dir TEXT,
            ADD COLUMN IF NOT EXISTS completed_at TIMESTAMP WITH TIME ZONE;
        ''')

        conn.commit()
        print("✅ Migration completed successfully!")

        # Verify the new columns were added
        print("\nVerifying new columns...")
        cur.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'jobs'
            ORDER BY ordinal_position
        """)

        new_columns = cur.fetchall()
        print("\nColumns after migration:")
        for col in new_columns:
            print(f"  - {col[0]} ({col[1]})")

        # Show which columns were added
        old_names = {col[0] for col in existing_columns}
        new_names = {col[0] for col in new_columns}
        added = new_names - old_names

        if added:
            print(f"\n✨ Added {len(added)} new columns: {', '.join(added)}")
        else:
            print("\n✓ All columns already existed")

    except psycopg2.Error as e:
        print(f"\n❌ Database error: {e}")
        if conn:
            conn.rollback()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
    finally:
        if conn:
            cur.close()
            conn.close()
            print("\nDatabase connection closed.")


if __name__ == "__main__":
    print("PostgreSQL Jobs Table Migration Script")
    print("=" * 40)

    # Safety check
    response = input("\nThis will modify your database. Continue? (yes/no): ")
    if response.lower() != 'yes':
        print("Migration cancelled.")
        sys.exit(0)

    migrate_database()
    print("\n✅ Migration complete! Your app should now work.")