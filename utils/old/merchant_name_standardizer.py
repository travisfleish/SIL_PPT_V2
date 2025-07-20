# utils/merchant_name_standardizer.py
"""
Production-ready merchant name standardizer using OpenAI API
FIXED VERSION - properly overwrites original columns
"""

import json
import asyncio
import logging
from typing import Dict, List, Optional
from pathlib import Path
import pandas as pd
from openai import AsyncOpenAI
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class MerchantNameStandardizer:
    """
    Production merchant name standardizer with caching and error handling
    FIXED VERSION - properly overwrites original columns instead of creating new ones
    """

    def __init__(self, cache_enabled: bool = True):
        """
        Initialize standardizer with OpenAI client and optional caching

        Args:
            cache_enabled: Whether to use persistent caching
        """
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")

        self.client = AsyncOpenAI(api_key=api_key)
        self.batch_size = 15  # Optimal batch size for API efficiency

        # Initialize cache
        self.cache_enabled = cache_enabled
        self.cache_file = Path(__file__).parent.parent / 'cache' / 'merchant_names.json'
        self.cache = self._load_cache() if cache_enabled else {}

        # Create cache directory if needed
        if cache_enabled:
            self.cache_file.parent.mkdir(exist_ok=True)

    def _load_cache(self) -> Dict[str, str]:
        """Load existing cache from file"""
        try:
            if self.cache_file.exists():
                with open(self.cache_file, 'r') as f:
                    cache = json.load(f)
                logger.info(f"Loaded {len(cache)} cached merchant names")
                return cache
        except Exception as e:
            logger.warning(f"Failed to load cache: {e}")

        return {}

    def _save_cache(self):
        """Persist cache to file"""
        if not self.cache_enabled:
            return

        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.cache, f, indent=2)
            logger.debug(f"Saved cache with {len(self.cache)} entries")
        except Exception as e:
            logger.warning(f"Failed to save cache: {e}")

    def get_cached_name(self, original_name: str) -> Optional[str]:
        """Get standardized name from cache"""
        if not self.cache_enabled:
            return None
        return self.cache.get(original_name.upper())

    def cache_name_mapping(self, original: str, standardized: str):
        """Cache a name mapping"""
        if self.cache_enabled:
            self.cache[original.upper()] = standardized

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

        # Check cache first
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
            for original, standardized in new_results.items():
                self.cache_name_mapping(original, standardized)

            # Save cache
            self._save_cache()
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
        FIXED VERSION: Standardize a DataFrame column and OVERWRITE the original

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

        # OVERWRITE THE ORIGINAL COLUMN (this is the key fix)
        df[column_name] = df[column_name].map(name_mapping).fillna(df[column_name])

        logger.info(f"Standardized {len(unique_names)} unique merchant names in column '{column_name}'")
        return df


# Convenience function for easy integration
def standardize_merchant_names(names: List[str], cache_enabled: bool = True) -> Dict[str, str]:
    """
    Convenience function for one-off merchant name standardization

    Args:
        names: List of merchant names to standardize
        cache_enabled: Whether to use caching

    Returns:
        Dictionary mapping original names to standardized names
    """
    standardizer = MerchantNameStandardizer(cache_enabled=cache_enabled)

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

    def __init__(self, team_view_prefix: str):
        self.team_view_prefix = team_view_prefix
        self.standardizer = MerchantNameStandardizer(cache_enabled=True)

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
    test_names = ["MCDONALD'S", "PANDA EXPRESS", "CHICK-FIL-A", "LULULEMON"]
    results = standardize_merchant_names(test_names)

    print("Standardization Results:")
    for orig, std in results.items():
        print(f"  {orig} → {std}")