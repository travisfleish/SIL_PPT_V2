# utils/merchant_name_standardizer.py
"""
Enhanced merchant name standardizer using PostgreSQL cache via CacheManager
Maintains the same interface as the original but uses centralized caching
"""

import json
import asyncio
import logging
from typing import Dict, List, Optional, TYPE_CHECKING
from pathlib import Path
import pandas as pd
from openai import AsyncOpenAI
import os
from dotenv import load_dotenv

# Import CacheManager (it should be in the same utils directory)
if TYPE_CHECKING:
    from .cache_manager import CacheManager

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class MerchantNameStandardizer:
    """
    Production merchant name standardizer with PostgreSQL caching
    Maintains backward compatibility while using centralized cache
    """

    def __init__(self, cache_enabled: bool = True, cache_manager: Optional['CacheManager'] = None):
        """
        Initialize standardizer with OpenAI client and caching

        Args:
            cache_enabled: Whether to use caching
            cache_manager: Optional CacheManager instance. If not provided, falls back to file cache
        """
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")

        self.client = AsyncOpenAI(api_key=api_key)
        self.batch_size = 15  # Optimal batch size for API efficiency
        self.cache_enabled = cache_enabled

        # Use provided CacheManager or fall back to file-based cache
        self.cache_manager = cache_manager
        self.use_postgres_cache = cache_manager is not None

        # Stats tracking
        self._api_calls = 0
        self._cache_hits = 0
        self._cache_misses = 0

        # Initialize file cache as fallback
        if not self.use_postgres_cache and cache_enabled:
            self.cache_file = Path(__file__).parent.parent / 'cache' / 'merchant_names.json'
            self.cache_file.parent.mkdir(exist_ok=True)
            self.file_cache = self._load_file_cache()
        else:
            self.file_cache = {}

        logger.info(f"Initialized MerchantNameStandardizer (PostgreSQL cache: {self.use_postgres_cache})")

    def _load_file_cache(self) -> Dict[str, str]:
        """Load existing cache from file (fallback method)"""
        try:
            if self.cache_file.exists():
                with open(self.cache_file, 'r') as f:
                    cache = json.load(f)
                logger.info(f"Loaded {len(cache)} cached merchant names from file")
                return cache
        except Exception as e:
            logger.warning(f"Failed to load file cache: {e}")
        return {}

    def _save_file_cache(self):
        """Persist cache to file (fallback method)"""
        if not self.cache_enabled or self.use_postgres_cache:
            return

        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.file_cache, f, indent=2)
            logger.debug(f"Saved file cache with {len(self.file_cache)} entries")
        except Exception as e:
            logger.warning(f"Failed to save file cache: {e}")

    def get_cached_name(self, original_name: str) -> Optional[str]:
        """Get standardized name from cache (PostgreSQL or file)"""
        if not self.cache_enabled:
            return None

        if self.use_postgres_cache:
            # Use PostgreSQL cache
            standardized, confidence, cache_hit = self.cache_manager.get_merchant_name(original_name)
            if cache_hit:
                self._cache_hits += 1
                return standardized
            else:
                self._cache_misses += 1
                return None
        else:
            # Fall back to file cache
            cached = self.file_cache.get(original_name.upper())
            if cached:
                self._cache_hits += 1
            else:
                self._cache_misses += 1
            return cached

    def cache_name_mapping(self, original: str, standardized: str):
        """Cache a name mapping (PostgreSQL or file)"""
        if not self.cache_enabled:
            return

        if self.use_postgres_cache:
            # Use PostgreSQL cache
            self.cache_manager.set_merchant_name(
                original,
                standardized,
                confidence_score=0.95,
                source='openai'
            )
        else:
            # Fall back to file cache
            self.file_cache[original.upper()] = standardized

    async def standardize_merchants(self, merchant_names: List[str]) -> Dict[str, str]:
        """
        Standardize merchant names with caching and batch processing

        Args:
            merchant_names: List of merchant names to standardize

        Returns:
            Dictionary mapping original names to standardized names
        """
        if not merchant_names:
            return {}

        logger.info(f"Standardizing {len(merchant_names)} merchant names...")

        # For PostgreSQL cache, we can use batch lookup for efficiency
        if self.use_postgres_cache and self.cache_enabled:
            # Batch lookup from PostgreSQL
            cache_results = self.cache_manager.get_merchant_names_batch(merchant_names)

            results = {}
            uncached_names = []

            for name in merchant_names:
                standardized, confidence, cache_hit = cache_results[name]
                if cache_hit:
                    results[name] = standardized
                else:
                    uncached_names.append(name)

        else:
            # Original single-lookup logic
            results = {}
            uncached_names = []

            for name in merchant_names:
                cached = self.get_cached_name(name)
                if cached is not None:
                    results[name] = cached
                else:
                    uncached_names.append(name)

        if uncached_names:
            logger.info(f"Found {len(results)} cached, processing {len(uncached_names)} new names")

            # Process uncached names in batches
            new_results = await self._process_uncached_names(uncached_names)
            results.update(new_results)

            # Update cache
            if self.use_postgres_cache and self.cache_enabled:
                # Batch insert for PostgreSQL (more efficient)
                for original, standardized in new_results.items():
                    self.cache_manager.set_merchant_name(
                        original,
                        standardized,
                        confidence_score=0.95,
                        source='openai'
                    )
            else:
                # Original caching logic
                for original, standardized in new_results.items():
                    self.cache_name_mapping(original, standardized)
                self._save_file_cache()
        else:
            logger.info(f"All {len(merchant_names)} names found in cache")

        return results

    async def _process_uncached_names(self, names: List[str]) -> Dict[str, str]:
        """Process names that aren't in cache"""
        all_results = {}

        # Process in batches
        for i in range(0, len(names), self.batch_size):
            batch = names[i:i + self.batch_size]
            logger.debug(f"Processing batch {i // self.batch_size + 1}: {len(batch)} names")

            batch_results = await self._standardize_batch_with_retry(batch)
            all_results.update(batch_results)

            # Small delay to be respectful to API
            if i + self.batch_size < len(names):
                await asyncio.sleep(0.1)

        return all_results

    async def _standardize_batch_with_retry(self, names: List[str]) -> Dict[str, str]:
        """Standardize a batch with retry logic"""
        max_retries = 3

        for attempt in range(max_retries):
            try:
                return await self._standardize_batch(names)
            except Exception as e:
                logger.warning(f"Batch standardization attempt {attempt + 1} failed: {e}")

                if attempt == max_retries - 1:
                    # Final fallback
                    logger.error("All attempts failed, using fallback formatting")
                    return {name: self._fallback_format(name) for name in names}

                # Exponential backoff
                await asyncio.sleep(2 ** attempt)

        return {}

    async def _standardize_batch(self, names: List[str]) -> Dict[str, str]:
        """Standardize a single batch using OpenAI"""
        self._api_calls += 1
        prompt = self._create_prompt(names)

        response = await self.client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": "You are a brand name standardization expert. Return only valid JSON with proper brand formatting."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0,
            max_tokens=1500
        )

        response_text = response.choices[0].message.content.strip()

        # Clean potential markdown formatting
        if response_text.startswith("```json"):
            response_text = response_text.replace("```json", "").replace("```", "").strip()

        try:
            return json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed: {e}, Response: {response_text}")
            raise

    def _create_prompt(self, names: List[str]) -> str:
        """Create standardization prompt"""
        names_list = "\n".join([f"- {name}" for name in names])

        return f"""Standardize these merchant/brand names to their official formatting:

{names_list}

Rules:
- Use official brand capitalization (McDonald's, Chick-fil-A, lululemon)
- Preserve special characters as brands use them
- Maintain proper spacing and punctuation
- Examples: "MCDONALD'S" → "McDonald's", "LULULEMON" → "lululemon"

Return JSON mapping each name:
{{
  "ORIGINAL_NAME": "Standardized Name"
}}"""

    def _fallback_format(self, name: str) -> str:
        """Fallback formatting when API fails"""
        # Manual overrides for common cases
        overrides = {
            "MCDONALD'S": "McDonald's",
            "CHICK-FIL-A": "Chick-fil-A",
            "LULULEMON": "lululemon",
            "CVS PHARMACY": "CVS Pharmacy",
            "7-ELEVEN": "7-Eleven",
            "T-MOBILE": "T-Mobile",
            "E-TRADE": "E*TRADE"
        }

        return overrides.get(name.upper(), name.title())

    def standardize_dataframe_column(self, df: pd.DataFrame, column_name: str,
                                     preserve_original: bool = True) -> pd.DataFrame:
        """
        Standardize a DataFrame column and OVERWRITE the original

        Args:
            df: DataFrame containing merchant names
            column_name: Name of column to standardize
            preserve_original: Whether to keep original values in COLUMN_NAME_ORIGINAL

        Returns:
            DataFrame with standardized column (original column is OVERWRITTEN)
        """
        if column_name not in df.columns:
            return df

        # Get unique names to minimize API calls
        unique_names = df[column_name].dropna().unique().tolist()

        if not unique_names:
            return df

        # PRESERVE ORIGINAL VALUES FIRST (if requested)
        if preserve_original:
            df[f"{column_name}_ORIGINAL"] = df[column_name].copy()

        # Run async standardization
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            name_mapping = loop.run_until_complete(self.standardize_merchants(unique_names))
        finally:
            loop.close()

        # OVERWRITE THE ORIGINAL COLUMN
        df[column_name] = df[column_name].map(name_mapping).fillna(df[column_name])

        logger.info(f"Standardized {len(unique_names)} unique merchant names in column '{column_name}'")
        return df

    def get_stats(self) -> Dict[str, any]:
        """Get standardization statistics"""
        total_lookups = self._cache_hits + self._cache_misses
        hit_rate = (self._cache_hits / total_lookups * 100) if total_lookups > 0 else 0

        return {
            'cache_type': 'PostgreSQL' if self.use_postgres_cache else 'File',
            'cache_hits': self._cache_hits,
            'cache_misses': self._cache_misses,
            'hit_rate': hit_rate,
            'api_calls': self._api_calls,
            'api_calls_saved': self._cache_hits
        }

    def log_performance(self):
        """Log performance statistics"""
        stats = self.get_stats()
        logger.info(f"MerchantNameStandardizer Performance:")
        logger.info(f"  Cache Type: {stats['cache_type']}")
        logger.info(f"  Hit Rate: {stats['hit_rate']:.1f}%")
        logger.info(f"  API Calls: {stats['api_calls']}")
        logger.info(f"  API Calls Saved: {stats['api_calls_saved']}")


# Convenience function for easy integration
def standardize_merchant_names(names: List[str], cache_enabled: bool = True,
                               cache_manager: Optional['CacheManager'] = None) -> Dict[str, str]:
    """
    Convenience function for one-off merchant name standardization

    Args:
        names: List of merchant names to standardize
        cache_enabled: Whether to use caching
        cache_manager: Optional CacheManager instance for PostgreSQL caching

    Returns:
        Dictionary mapping original names to standardized names
    """
    standardizer = MerchantNameStandardizer(cache_enabled=cache_enabled, cache_manager=cache_manager)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        return loop.run_until_complete(standardizer.standardize_merchants(names))
    finally:
        loop.close()


# Integration example for your existing pipeline
class StandardizedMerchantRanker:
    """
    Enhanced MerchantRanker that automatically standardizes merchant names
    Example of how to integrate with your existing classes
    """

    def __init__(self, team_view_prefix: str, cache_manager: Optional['CacheManager'] = None):
        self.team_view_prefix = team_view_prefix
        self.standardizer = MerchantNameStandardizer(cache_enabled=True, cache_manager=cache_manager)

    async def get_standardized_merchant_data(self, query_result: pd.DataFrame) -> pd.DataFrame:
        """
        Take merchant data and return it with standardized names

        Args:
            query_result: DataFrame from Snowflake query

        Returns:
            DataFrame with standardized merchant names
        """
        if 'MERCHANT' not in query_result.columns:
            return query_result

        # Get unique merchant names
        unique_merchants = query_result['MERCHANT'].dropna().unique().tolist()

        if not unique_merchants:
            return query_result

        # Standardize names
        name_mapping = await self.standardizer.standardize_merchants(unique_merchants)

        # Apply to dataframe - OVERWRITE original column
        result_df = query_result.copy()
        result_df['MERCHANT_ORIGINAL'] = result_df['MERCHANT']
        result_df['MERCHANT'] = result_df['MERCHANT'].map(name_mapping).fillna(result_df['MERCHANT'])

        return result_df


if __name__ == "__main__":
    # Test the integration

    # Example 1: Using file cache (default)
    print("Testing with file cache:")
    test_names = ["MCDONALD'S", "PANDA EXPRESS", "CHICK-FIL-A", "LULULEMON"]
    results = standardize_merchant_names(test_names)

    print("Standardization Results:")
    for orig, std in results.items():
        print(f"  {orig} → {std}")

    # Example 2: Using PostgreSQL cache
    print("\nTesting with PostgreSQL cache:")
    try:
        from postgresql_job_store import PostgreSQLJobStore
        from cache_manager import CacheManager

        # Initialize with PostgreSQL cache
        job_store = PostgreSQLJobStore()
        cache_manager = CacheManager(job_store.pool)

        # Create standardizer with cache manager
        standardizer = MerchantNameStandardizer(cache_enabled=True, cache_manager=cache_manager)

        # Test standardization
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            results = loop.run_until_complete(standardizer.standardize_merchants(test_names))
            print("PostgreSQL Cache Results:")
            for orig, std in results.items():
                print(f"  {orig} → {std}")

            # Show stats
            standardizer.log_performance()
        finally:
            loop.close()

    except ImportError:
        print("PostgreSQL cache not available, skipping test")