#!/usr/bin/env python3
"""
Import existing merchant names from JSON file to PostgreSQL cache
"""

import json
import psycopg2
from psycopg2.extras import execute_values
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Database connection
DATABASE_URL = "postgresql://sil_powerpoint_db_user:NcqJKvXxBcRgsuFnPWNVgeUXrrxATLpR@dpg-d1u2jf3uibrs73821rqg-a.virginia-postgres.render.com/sil_powerpoint_db?sslmode=require"


def load_merchant_names(json_path: str) -> dict:
    """Load merchant names from JSON file."""
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def import_to_postgresql(merchant_names: dict, conn):
    """Import merchant names to PostgreSQL cache table."""

    # Prepare data for bulk insert
    values = []
    for raw_name, standardized_name in merchant_names.items():
        # Determine confidence score based on similarity
        confidence = 1.0 if raw_name.upper() == standardized_name.upper() else 0.95

        # Source is 'imported' for bulk imports
        values.append((
            raw_name,
            standardized_name,
            confidence,
            'imported',
            json.dumps({'original_source': 'merchant_names.json'}),
            datetime.now() + timedelta(days=90)  # 90 days expiry for imported data
        ))

    with conn.cursor() as cur:
        # Use UPSERT to handle any duplicates gracefully
        logger.info(f"Importing {len(values)} merchant name mappings...")

        execute_values(
            cur,
            """
            INSERT INTO cache_merchant_names 
                (cache_key, standardized_name, confidence_score, source, metadata, expires_at)
            VALUES %s
            ON CONFLICT (cache_key) 
            DO UPDATE SET
                standardized_name = EXCLUDED.standardized_name,
                confidence_score = EXCLUDED.confidence_score,
                source = EXCLUDED.source,
                metadata = EXCLUDED.metadata,
                expires_at = EXCLUDED.expires_at,
                last_accessed = NOW()
            """,
            values,
            template="(%s, %s, %s, %s, %s, %s)"
        )

        # Get count of actual inserts vs updates
        cur.execute("""
            SELECT 
                COUNT(*) FILTER (WHERE source = 'imported') as imported_count,
                COUNT(*) FILTER (WHERE source = 'manual') as manual_count,
                COUNT(*) as total_count
            FROM cache_merchant_names
        """)

        stats = cur.fetchone()
        logger.info(f"Import complete! Database now contains:")
        logger.info(f"  - Imported entries: {stats[0]}")
        logger.info(f"  - Manual entries: {stats[1]}")
        logger.info(f"  - Total entries: {stats[2]}")

        conn.commit()


def analyze_cache_quality(conn):
    """Analyze the quality and coverage of the cache."""
    with conn.cursor() as cur:
        # Get statistics
        cur.execute("""
            SELECT 
                COUNT(*) as total_entries,
                COUNT(DISTINCT standardized_name) as unique_brands,
                AVG(confidence_score) as avg_confidence,
                COUNT(*) FILTER (WHERE confidence_score = 1.0) as perfect_matches,
                COUNT(*) FILTER (WHERE confidence_score < 1.0) as fuzzy_matches
            FROM cache_merchant_names
        """)

        stats = cur.fetchone()

        logger.info("\nCache Quality Analysis:")
        logger.info(f"  - Total mappings: {stats[0]}")
        logger.info(f"  - Unique brands: {stats[1]}")
        logger.info(f"  - Average confidence: {stats[2]:.3f}")
        logger.info(f"  - Perfect matches: {stats[3]} ({stats[3] / stats[0] * 100:.1f}%)")
        logger.info(f"  - Fuzzy matches: {stats[4]} ({stats[4] / stats[0] * 100:.1f}%)")

        # Get top standardized names by frequency
        cur.execute("""
            SELECT 
                standardized_name, 
                COUNT(*) as variation_count
            FROM cache_merchant_names
            GROUP BY standardized_name
            HAVING COUNT(*) > 1
            ORDER BY variation_count DESC
            LIMIT 10
        """)

        variations = cur.fetchall()
        if variations:
            logger.info("\nTop brands with multiple variations:")
            for brand, count in variations:
                logger.info(f"  - {brand}: {count} variations")


def create_lookup_function(conn):
    """Create an optimized function for merchant name lookups."""
    with conn.cursor() as cur:
        cur.execute("""
            CREATE OR REPLACE FUNCTION lookup_merchant_name(
                raw_name TEXT,
                increment_hit BOOLEAN DEFAULT TRUE
            ) RETURNS TABLE(
                standardized_name VARCHAR(500),
                confidence_score DECIMAL,
                cache_hit BOOLEAN
            ) AS $
            DECLARE
                result RECORD;
            BEGIN
                -- Try exact match first
                SELECT 
                    cm.standardized_name,
                    cm.confidence_score,
                    TRUE as cache_hit
                INTO result
                FROM cache_merchant_names cm
                WHERE cm.cache_key = raw_name
                    AND cm.expires_at > NOW();

                IF FOUND THEN
                    -- Update hit count if requested
                    IF increment_hit THEN
                        UPDATE cache_merchant_names
                        SET hit_count = hit_count + 1,
                            last_accessed = NOW()
                        WHERE cache_key = raw_name;
                    END IF;

                    RETURN QUERY SELECT 
                        result.standardized_name::VARCHAR(500),
                        result.confidence_score,
                        result.cache_hit;
                ELSE
                    -- Return cache miss
                    RETURN QUERY SELECT 
                        raw_name::VARCHAR(500),
                        0.0::DECIMAL,
                        FALSE;
                END IF;
            END;
            $ LANGUAGE plpgsql;
        """)

        # Create batch lookup function
        cur.execute("""
            CREATE OR REPLACE FUNCTION lookup_merchant_names_batch(
                raw_names TEXT[]
            ) RETURNS TABLE(
                raw_name VARCHAR(500),
                standardized_name VARCHAR(500),
                confidence_score DECIMAL,
                cache_hit BOOLEAN
            ) AS $
            BEGIN
                RETURN QUERY
                WITH input_names AS (
                    SELECT unnest(raw_names) as raw_name
                )
                SELECT 
                    i.raw_name::VARCHAR(500),
                    COALESCE(cm.standardized_name, i.raw_name)::VARCHAR(500) as standardized_name,
                    COALESCE(cm.confidence_score, 0.0) as confidence_score,
                    (cm.cache_key IS NOT NULL) as cache_hit
                FROM input_names i
                LEFT JOIN cache_merchant_names cm 
                    ON i.raw_name = cm.cache_key 
                    AND cm.expires_at > NOW();

                -- Update hit counts for found entries
                UPDATE cache_merchant_names
                SET hit_count = hit_count + 1,
                    last_accessed = NOW()
                WHERE cache_key = ANY(raw_names)
                    AND expires_at > NOW();
            END;
            $ LANGUAGE plpgsql;
        """)

        conn.commit()
        logger.info("\nCreated optimized lookup functions")


def main():
    """Main execution function."""
    # Path to your merchant names JSON file
    json_path = "root-cache-merchant_names.json"

    # Try multiple possible locations
    possible_paths = [
        json_path,  # Current directory
        Path("cache") / "merchant_names.json",  # cache subdirectory
        Path("..") / json_path,  # Parent directory
        Path.home() / "PycharmProjects" / "PPT_Generator_SIL" / json_path,  # Your project path
    ]

    # Find the file
    actual_path = None
    for path in possible_paths:
        if Path(path).exists():
            actual_path = path
            break

    if not actual_path:
        logger.error(f"File not found in any of these locations:")
        for path in possible_paths:
            logger.error(f"  - {path}")
        logger.info("\nPlease specify the correct path to root-cache-merchant_names.json")
        return

    json_path = str(actual_path)

    try:
        # Load merchant names
        logger.info(f"Loading merchant names from {json_path}...")
        merchant_names = load_merchant_names(json_path)
        logger.info(f"Loaded {len(merchant_names)} merchant name mappings")

        # Connect to database
        logger.info("Connecting to PostgreSQL...")
        conn = psycopg2.connect(DATABASE_URL)

        # Import to PostgreSQL
        import_to_postgresql(merchant_names, conn)

        # Analyze cache quality
        analyze_cache_quality(conn)

        # Create lookup functions
        create_lookup_function(conn)

        # Test the lookup function
        logger.info("\nTesting lookup function...")
        with conn.cursor() as cur:
            # Test single lookup
            cur.execute("SELECT * FROM lookup_merchant_name('MCDONALD''S')")
            result = cur.fetchone()
            logger.info(f"  Single lookup test: {result}")

            # Test batch lookup
            cur.execute("""
                SELECT * FROM lookup_merchant_names_batch(
                    ARRAY['NIKE', 'UNKNOWN_MERCHANT', 'WALMART']
                )
            """)
            results = cur.fetchall()
            logger.info("  Batch lookup test:")
            for r in results:
                logger.info(f"    {r[0]} -> {r[1]} (confidence: {r[2]}, hit: {r[3]})")

        conn.close()
        logger.info("\nImport completed successfully!")

    except Exception as e:
        logger.error(f"Error during import: {e}")
        raise


if __name__ == "__main__":
    main()