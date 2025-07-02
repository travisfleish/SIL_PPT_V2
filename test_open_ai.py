#!/usr/bin/env python3
"""
One-off test script to validate OpenAI merchant name standardization
Tests with mock all-caps merchant names to verify proper formatting
"""

import json
import asyncio
from typing import List, Dict
from openai import AsyncOpenAI
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Mock merchant names in all caps (representing raw Snowflake data)
MOCK_MERCHANTS = [
    "MCDONALD'S",
    "PANDA EXPRESS",
    "CHICK-FIL-A",
    "TACO BELL",
    "LULULEMON",
    "UNDER ARMOUR",
    "NIKE",
    "ADIDAS",
    "STARBUCKS",
    "CHIPOTLE MEXICAN GRILL",
    "SUBWAY",
    "WENDY'S",
    "BURGER KING",
    "KFC",
    "PIZZA HUT",
    "DOMINO'S PIZZA",
    "PAPA JOHN'S",
    "7-ELEVEN",
    "CVS PHARMACY",
    "WALGREENS",
    "TARGET",
    "WALMART",
    "COSTCO WHOLESALE",
    "HOME DEPOT",
    "LOWE'S"
]


class MerchantNameStandardizer:
    """Test implementation of OpenAI-powered merchant name standardization"""

    def __init__(self, api_key: str):
        """Initialize with OpenAI API key"""
        self.client = AsyncOpenAI(api_key=api_key)
        self.batch_size = 10  # Process 10 at a time for testing

    async def standardize_merchants(self, merchant_names: List[str]) -> Dict[str, str]:
        """
        Standardize merchant names using OpenAI

        Args:
            merchant_names: List of merchant names to standardize

        Returns:
            Dictionary mapping original names to standardized names
        """
        print(f"🔄 Standardizing {len(merchant_names)} merchant names...")

        # Process in batches to avoid token limits
        all_results = {}

        for i in range(0, len(merchant_names), self.batch_size):
            batch = merchant_names[i:i + self.batch_size]
            print(f"   Processing batch {i // self.batch_size + 1}: {len(batch)} names")

            batch_results = await self._standardize_batch(batch)
            all_results.update(batch_results)

        return all_results

    async def _standardize_batch(self, names: List[str]) -> Dict[str, str]:
        """Standardize a batch of merchant names"""

        # Create the prompt with specific instructions
        prompt = self._create_standardization_prompt(names)

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a brand name standardization expert. Return only valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0,  # Deterministic output
                max_tokens=1000
            )

            # Parse the JSON response
            response_text = response.choices[0].message.content.strip()

            # Handle potential markdown code blocks
            if response_text.startswith("```json"):
                response_text = response_text.replace("```json", "").replace("```", "").strip()

            return json.loads(response_text)

        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing error: {e}")
            print(f"Response was: {response_text}")
            # Fallback to simple title case
            return {name: self._simple_fallback(name) for name in names}

        except Exception as e:
            print(f"❌ OpenAI API error: {e}")
            # Fallback to simple title case
            return {name: self._simple_fallback(name) for name in names}

    def _create_standardization_prompt(self, names: List[str]) -> str:
        """Create the standardization prompt for OpenAI"""

        names_list = "\n".join([f"- {name}" for name in names])

        return f"""
Please standardize these merchant/brand names to their official brand formatting:

{names_list}

Requirements:
- Use the official brand capitalization and formatting
- Preserve apostrophes, hyphens, and special characters as the brand uses them
- Examples of correct formatting:
  * McDonald's (not Mcdonald's or MCDONALD'S)
  * Chick-fil-A (not Chick-Fil-A or CHICK-FIL-A)
  * lululemon (all lowercase, official brand style)
  * Under Armour (not Under Armor)
  * CVS Pharmacy (not Cvs Pharmacy)

Return a JSON object mapping each original name to its standardized version:
{{
  "ORIGINAL_NAME": "Standardized Name",
  "ANOTHER_NAME": "Another Standardized Name"
}}
"""

    def _simple_fallback(self, name: str) -> str:
        """Simple fallback formatting if OpenAI fails"""
        # Handle common cases manually
        exceptions = {
            "MCDONALD'S": "McDonald's",
            "CHICK-FIL-A": "Chick-fil-A",
            "LULULEMON": "lululemon",
            "CVS PHARMACY": "CVS Pharmacy",
            "7-ELEVEN": "7-Eleven"
        }

        return exceptions.get(name, name.title())


async def main():
    """Main test function"""
    print("=" * 60)
    print("MERCHANT NAME STANDARDIZATION TEST")
    print("=" * 60)

    # Get OpenAI API key from .env file
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ Error: OPENAI_API_KEY not found in .env file")
        print("\nAdd to your .env file:")
        print("OPENAI_API_KEY=your-api-key-here")
        return

    # Initialize standardizer
    standardizer = MerchantNameStandardizer(api_key)

    # Test with mock merchants
    print(f"\n📝 Testing with {len(MOCK_MERCHANTS)} mock merchants:")
    for i, merchant in enumerate(MOCK_MERCHANTS, 1):
        print(f"   {i:2d}. {merchant}")

    # Run standardization
    try:
        results = await standardizer.standardize_merchants(MOCK_MERCHANTS)

        # Display results
        print(f"\n✅ Standardization complete! Results:")
        print("-" * 60)
        print(f"{'ORIGINAL':<25} | {'STANDARDIZED':<25}")
        print("-" * 60)

        for original, standardized in results.items():
            # Highlight changes
            changed = "🔄" if original != standardized else "  "
            print(f"{original:<25} | {standardized:<25} {changed}")

        # Summary stats
        total_changed = sum(1 for orig, std in results.items() if orig != std)
        print(f"\n📊 Summary:")
        print(f"   Total merchants: {len(results)}")
        print(f"   Names changed: {total_changed}")
        print(f"   Names unchanged: {len(results) - total_changed}")

        # Show some interesting changes
        print(f"\n🎯 Notable standardizations:")
        interesting_changes = [
            (orig, std) for orig, std in results.items()
            if orig != std and any(char in orig for char in ["'", "-", "LULULEMON", "CVS"])
        ]

        for orig, std in interesting_changes[:5]:  # Show first 5
            print(f"   {orig} → {std}")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        return

    print(f"\n✅ Test completed successfully!")


if __name__ == "__main__":
    # Instructions for running
    print("To run this test:")
    print("1. Add OPENAI_API_KEY=your-key to your .env file")
    print("2. Install dependencies: pip install openai python-dotenv")
    print("3. Run: python merchant_name_test.py")
    print()

    # Run the test
    asyncio.run(main())