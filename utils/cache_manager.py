"""
CacheManager - Centralized caching layer for SIL PowerPoint Generator
Integrates with existing PostgreSQL connection pool for optimal performance
"""

import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from contextlib import contextmanager
import time

from psycopg2.extras import RealDictCursor, Json, execute_values
import psycopg2

logger = logging.getLogger(__name__)


class CacheManager:
    """
    Unified cache manager for all caching needs in the PowerPoint generator.
    Uses PostgreSQL as the cache backend for persistence and sharing across instances.
    """

    def __init__(self, connection_pool):
        """
        Initialize with existing PostgreSQL connection pool.

        Args:
            connection_pool: SimpleConnectionPool instance from PostgreSQLJobStore
        """
        self.pool = connection_pool
        self._ensure_cache_stats()

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

    def _ensure_cache_stats(self):
        """Initialize cache statistics for today if not exists."""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cache_types = ['merchant_names', 'ai_insights', 'snowflake_results', 'logos']
                for cache_type in cache_types:
                    cur.execute("""
                        INSERT INTO cache_statistics (cache_type, date, hits, misses)
                        VALUES (%s, CURRENT_DATE, 0, 0)
                        ON CONFLICT (cache_type, date) DO NOTHING
                    """, (cache_type,))
                conn.commit()

    def _update_stats(self, cache_type: str, hit: bool):
        """Update cache statistics."""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                field = 'hits' if hit else 'misses'
                cur.execute(f"""
                    UPDATE cache_statistics
                    SET {field} = {field} + 1
                    WHERE cache_type = %s AND date = CURRENT_DATE
                """, (cache_type,))
                conn.commit()

    # ==================== MERCHANT NAME CACHE ====================

    def get_merchant_name(self, raw_name: str) -> Tuple[str, float, bool]:
        """
        Get standardized merchant name from cache.

        Args:
            raw_name: Raw merchant name to standardize

        Returns:
            Tuple of (standardized_name, confidence_score, cache_hit)
        """
        start_time = time.time()

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                # Check cache
                cur.execute("""
                    SELECT standardized_name, confidence_score
                    FROM cache_merchant_names
                    WHERE cache_key = %s AND expires_at > NOW()
                """, (raw_name,))

                result = cur.fetchone()

                if result:
                    # Update hit count and last accessed
                    cur.execute("""
                        UPDATE cache_merchant_names
                        SET hit_count = hit_count + 1, last_accessed = NOW()
                        WHERE cache_key = %s
                    """, (raw_name,))
                    conn.commit()

                    self._update_stats('merchant_names', True)
                    logger.debug(f"Merchant cache HIT: {raw_name} -> {result[0]} ({time.time() - start_time:.3f}s)")
                    return result[0], result[1], True
                else:
                    self._update_stats('merchant_names', False)
                    logger.debug(f"Merchant cache MISS: {raw_name} ({time.time() - start_time:.3f}s)")
                    return raw_name, 0.0, False

    def set_merchant_name(self, raw_name: str, standardized_name: str,
                          confidence_score: float = 0.95, source: str = 'api'):
        """
        Add or update merchant name in cache.

        Args:
            raw_name: Raw merchant name
            standardized_name: Standardized version
            confidence_score: Confidence in the mapping (0-1)
            source: Source of the mapping (api, manual, ml, etc.)
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO cache_merchant_names 
                        (cache_key, standardized_name, confidence_score, source, expires_at)
                    VALUES (%s, %s, %s, %s, NOW() + INTERVAL '30 days')
                    ON CONFLICT (cache_key) 
                    DO UPDATE SET
                        standardized_name = EXCLUDED.standardized_name,
                        confidence_score = EXCLUDED.confidence_score,
                        source = EXCLUDED.source,
                        expires_at = EXCLUDED.expires_at,
                        last_accessed = NOW()
                """, (raw_name, standardized_name, confidence_score, source))
                conn.commit()

        logger.info(f"Cached merchant name: {raw_name} -> {standardized_name}")

    def get_merchant_names_batch(self, raw_names: List[str]) -> Dict[str, Tuple[str, float, bool]]:
        """
        Get multiple merchant names in one query (efficient for batch processing).

        Args:
            raw_names: List of raw merchant names

        Returns:
            Dict mapping raw_name to (standardized_name, confidence_score, cache_hit)
        """
        if not raw_names:
            return {}

        start_time = time.time()
        results = {}

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                # Get all cached values in one query
                cur.execute("""
                    SELECT cache_key, standardized_name, confidence_score
                    FROM cache_merchant_names
                    WHERE cache_key = ANY(%s) AND expires_at > NOW()
                """, (raw_names,))

                cached = {row[0]: (row[1], row[2]) for row in cur.fetchall()}

                # Update hit counts for found entries
                if cached:
                    cur.execute("""
                        UPDATE cache_merchant_names
                        SET hit_count = hit_count + 1, last_accessed = NOW()
                        WHERE cache_key = ANY(%s)
                    """, (list(cached.keys()),))
                    conn.commit()

                # Build results
                hits = 0
                for raw_name in raw_names:
                    if raw_name in cached:
                        results[raw_name] = (cached[raw_name][0], cached[raw_name][1], True)
                        hits += 1
                    else:
                        results[raw_name] = (raw_name, 0.0, False)

                # Update stats
                self._update_stats('merchant_names', True)  # Count as hit if any found

                hit_rate = (hits / len(raw_names)) * 100 if raw_names else 0
                logger.info(
                    f"Merchant batch lookup: {hits}/{len(raw_names)} hits ({hit_rate:.1f}%) in {time.time() - start_time:.3f}s")

        return results

    # ==================== AI INSIGHTS CACHE ====================

    def _generate_ai_cache_key(self, prompt_template: str, **context) -> str:
        """Generate deterministic cache key for AI insights."""
        # Create a deterministic string from the context
        context_str = json.dumps(context, sort_keys=True)
        combined = f"{prompt_template}:{context_str}"
        return hashlib.sha256(combined.encode()).hexdigest()

    def get_ai_insight(self, prompt_template: str, insight_type: str,
                       team_key: Optional[str] = None, **context) -> Optional[Dict[str, Any]]:
        """
        Get cached AI insight.

        Args:
            prompt_template: Template identifier (e.g., 'demographic_overview')
            insight_type: Type of insight ('demographic', 'behavior', 'category')
            team_key: Team identifier
            **context: Additional context used to generate the insight

        Returns:
            Cached response data or None if not found
        """
        cache_key = self._generate_ai_cache_key(prompt_template, team_key=team_key, **context)

        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT response_data, model_used, tokens_used
                    FROM cache_ai_insights
                    WHERE cache_key = %s AND expires_at > NOW()
                """, (cache_key,))

                result = cur.fetchone()

                if result:
                    # Update hit count
                    cur.execute("""
                        UPDATE cache_ai_insights
                        SET hit_count = hit_count + 1, last_accessed = NOW()
                        WHERE cache_key = %s
                    """, (cache_key,))
                    conn.commit()

                    self._update_stats('ai_insights', True)
                    logger.info(f"AI cache HIT: {prompt_template} for {team_key}")
                    return dict(result)
                else:
                    self._update_stats('ai_insights', False)
                    logger.debug(f"AI cache MISS: {prompt_template} for {team_key}")
                    return None

    def set_ai_insight(self, prompt_template: str, insight_type: str,
                       response_data: Dict[str, Any], model_used: str = 'gpt-4',
                       tokens_used: Optional[int] = None, team_key: Optional[str] = None,
                       ttl_days: int = 7, **context):
        """
        Cache an AI insight response.

        Args:
            prompt_template: Template identifier
            insight_type: Type of insight
            response_data: The AI response to cache
            model_used: AI model used
            tokens_used: Number of tokens consumed
            team_key: Team identifier
            ttl_days: Time to live in days
            **context: Additional context used to generate the insight
        """
        cache_key = self._generate_ai_cache_key(prompt_template, team_key=team_key, **context)

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO cache_ai_insights 
                        (cache_key, prompt_template, team_key, category, insight_type,
                         response_data, model_used, tokens_used, expires_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW() + INTERVAL '%s days')
                    ON CONFLICT (cache_key) 
                    DO UPDATE SET
                        response_data = EXCLUDED.response_data,
                        model_used = EXCLUDED.model_used,
                        tokens_used = EXCLUDED.tokens_used,
                        expires_at = EXCLUDED.expires_at,
                        last_accessed = NOW()
                """, (cache_key, prompt_template, team_key, context.get('category'),
                      insight_type, Json(response_data), model_used, tokens_used, ttl_days))
                conn.commit()

        logger.info(f"Cached AI insight: {prompt_template} for {team_key} (TTL: {ttl_days} days)")

    # ==================== SNOWFLAKE RESULTS CACHE ====================

    def _generate_snowflake_cache_key(self, query_template: str, **params) -> str:
        """Generate deterministic cache key for Snowflake queries."""
        params_str = json.dumps(params, sort_keys=True)
        combined = f"{query_template}:{params_str}"
        return hashlib.sha256(combined.encode()).hexdigest()

    def get_snowflake_result(self, query_template: str, team_key: str,
                             view_name: str, **params) -> Optional[List[Dict]]:
        """
        Get cached Snowflake query result.

        Args:
            query_template: Query identifier
            team_key: Team identifier
            view_name: Snowflake view name
            **params: Query parameters

        Returns:
            Cached result data or None if not found
        """
        cache_key = self._generate_snowflake_cache_key(
            query_template, team_key=team_key, view_name=view_name, **params
        )

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT result_data, row_count
                    FROM cache_snowflake_results
                    WHERE cache_key = %s AND expires_at > NOW()
                """, (cache_key,))

                result = cur.fetchone()

                if result:
                    # Update hit count
                    cur.execute("""
                        UPDATE cache_snowflake_results
                        SET hit_count = hit_count + 1, last_accessed = NOW()
                        WHERE cache_key = %s
                    """, (cache_key,))
                    conn.commit()

                    self._update_stats('snowflake_results', True)
                    logger.info(f"Snowflake cache HIT: {view_name} for {team_key} ({result[1]} rows)")
                    return result[0]
                else:
                    self._update_stats('snowflake_results', False)
                    logger.debug(f"Snowflake cache MISS: {view_name} for {team_key}")
                    return None

    def set_snowflake_result(self, query_template: str, team_key: str,
                             view_name: str, result_data: List[Dict],
                             query_duration_ms: Optional[int] = None,
                             ttl_hours: int = 24, **params):
        """
        Cache a Snowflake query result.

        Args:
            query_template: Query identifier
            team_key: Team identifier
            view_name: Snowflake view name
            result_data: Query results to cache
            query_duration_ms: Original query execution time
            ttl_hours: Time to live in hours
            **params: Query parameters
        """
        cache_key = self._generate_snowflake_cache_key(
            query_template, team_key=team_key, view_name=view_name, **params
        )

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO cache_snowflake_results 
                        (cache_key, query_template, team_key, view_name, time_period,
                         result_data, row_count, query_duration_ms, expires_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW() + INTERVAL '%s hours')
                    ON CONFLICT (cache_key) 
                    DO UPDATE SET
                        result_data = EXCLUDED.result_data,
                        row_count = EXCLUDED.row_count,
                        query_duration_ms = EXCLUDED.query_duration_ms,
                        expires_at = EXCLUDED.expires_at,
                        last_accessed = NOW()
                """, (cache_key, query_template, team_key, view_name,
                      params.get('time_period'), Json(result_data), len(result_data),
                      query_duration_ms, ttl_hours))
                conn.commit()

        logger.info(f"Cached Snowflake result: {view_name} for {team_key} ({len(result_data)} rows, TTL: {ttl_hours}h)")

    # ==================== LOGO CACHE ====================

    def get_logo_url(self, merchant_name: str) -> Optional[str]:
        """
        Get cached logo URL for a merchant.

        Args:
            merchant_name: Merchant name to look up

        Returns:
            Logo URL or None if not found/not cached
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT logo_url, logo_found
                    FROM cache_logos
                    WHERE merchant_name = %s AND expires_at > NOW()
                """, (merchant_name,))

                result = cur.fetchone()

                if result:
                    # Update hit count
                    cur.execute("""
                        UPDATE cache_logos
                        SET hit_count = hit_count + 1
                        WHERE merchant_name = %s
                    """, (merchant_name,))
                    conn.commit()

                    self._update_stats('logos', True)
                    # Return None if we previously determined no logo exists
                    return result[0] if result[1] else None
                else:
                    self._update_stats('logos', False)
                    return None

    def set_logo_url(self, merchant_name: str, logo_url: Optional[str],
                     source: str = 'api', ttl_days: int = 60):
        """
        Cache a logo URL lookup result.

        Args:
            merchant_name: Merchant name
            logo_url: URL of the logo (or None if not found)
            source: Source of the logo (clearbit, brandfetch, manual)
            ttl_days: Time to live in days
        """
        logo_found = logo_url is not None

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO cache_logos 
                        (merchant_name, logo_url, logo_source, logo_found, expires_at)
                    VALUES (%s, %s, %s, %s, NOW() + INTERVAL '%s days')
                    ON CONFLICT (merchant_name) 
                    DO UPDATE SET
                        logo_url = EXCLUDED.logo_url,
                        logo_source = EXCLUDED.logo_source,
                        logo_found = EXCLUDED.logo_found,
                        last_attempt = NOW(),
                        expires_at = EXCLUDED.expires_at
                """, (merchant_name, logo_url, source, logo_found, ttl_days))
                conn.commit()

        status = "found" if logo_found else "not found"
        logger.info(f"Cached logo lookup: {merchant_name} - {status}")

    # ==================== CACHE MANAGEMENT ====================

    def get_cache_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get comprehensive cache statistics."""
        stats = {}

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                # Get today's hit/miss stats
                cur.execute("""
                    SELECT cache_type, hits, misses
                    FROM cache_statistics
                    WHERE date = CURRENT_DATE
                """)

                for row in cur.fetchall():
                    total = row[1] + row[2]
                    hit_rate = (row[1] / total * 100) if total > 0 else 0
                    stats[row[0]] = {
                        'hits': row[1],
                        'misses': row[2],
                        'total': total,
                        'hit_rate': hit_rate
                    }

                # Get cache sizes and space usage
                cur.execute("SELECT * FROM get_cache_stats()")
                for row in cur.fetchall():
                    cache_type = row[0]
                    if cache_type in stats:
                        stats[cache_type].update({
                            'entries': row[1],
                            'total_hits': row[2],
                            'avg_hits_per_entry': float(row[3]) if row[3] else 0,
                            'space_mb': float(row[4])
                        })

        return stats

    def clean_expired_entries(self) -> Dict[str, int]:
        """Clean expired entries from all caches."""
        cleaned = {}

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM clean_expired_cache()")
                for table_name, count in cur.fetchall():
                    cleaned[table_name] = count

        total = sum(cleaned.values())
        if total > 0:
            logger.info(f"Cleaned {total} expired cache entries: {cleaned}")

        return cleaned

    def warm_cache_for_team(self, team_key: str):
        """
        Pre-warm cache for a specific team by loading commonly used data.
        This can be called before report generation to improve performance.
        """
        logger.info(f"Pre-warming cache for team: {team_key}")
        # Implementation depends on your specific warming strategy
        # Could pre-fetch common merchant names, demographic data, etc.
        pass