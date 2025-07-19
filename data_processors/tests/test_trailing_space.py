#!/usr/bin/env python3
"""
Check for trailing whitespace in category names
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from data_processors.snowflake_connector import query_to_dataframe
from data_processors.category_analyzer import CategoryAnalyzer
from utils.team_config_manager import TeamConfigManager


def check_whitespace():
    """Check for whitespace issues in category names"""

    print("=" * 80)
    print("CHECKING FOR WHITESPACE IN CATEGORY NAMES")
    print("=" * 80)

    # Get Panthers categories
    panthers_query = """
    SELECT DISTINCT 
        CATEGORY,
        LENGTH(CATEGORY) as CAT_LENGTH,
        LENGTH(TRIM(CATEGORY)) as TRIMMED_LENGTH
    FROM V_CAROLINA_PANTHERS_SIL_CATEGORY_INDEXING_ALL_TIME
    WHERE AUDIENCE = 'Carolina Panthers Fans'
    ORDER BY CATEGORY
    """

    # Get Jazz categories for comparison
    jazz_query = """
    SELECT DISTINCT 
        CATEGORY,
        LENGTH(CATEGORY) as CAT_LENGTH,
        LENGTH(TRIM(CATEGORY)) as TRIMMED_LENGTH
    FROM V_UTAH_JAZZ_SIL_CATEGORY_INDEXING_ALL_TIME
    WHERE AUDIENCE = 'Utah Jazz Fans'
    ORDER BY CATEGORY
    """

    try:
        panthers_df = query_to_dataframe(panthers_query)
        jazz_df = query_to_dataframe(jazz_query)

        # Check Panthers for whitespace
        print("\nPANTHERS CATEGORIES - WHITESPACE CHECK:")
        print("-" * 70)
        print(f"{'Category':<30} {'Length':<10} {'Trimmed':<10} {'Has Space?':<15}")
        print("-" * 70)

        panthers_with_space = []
        for _, row in panthers_df.iterrows():
            cat = row['CATEGORY']
            length = row['CAT_LENGTH']
            trimmed = row['TRIMMED_LENGTH']
            has_space = length != trimmed

            if has_space:
                panthers_with_space.append(cat)
                print(f"{repr(cat):<30} {length:<10} {trimmed:<10} {'YES ⚠️':<15}")
            else:
                print(f"{repr(cat):<30} {length:<10} {trimmed:<10} {'No':<15}")

        # Check Jazz for comparison
        print("\n\nJAZZ CATEGORIES - WHITESPACE CHECK (first 20):")
        print("-" * 70)
        print(f"{'Category':<30} {'Length':<10} {'Trimmed':<10} {'Has Space?':<15}")
        print("-" * 70)

        jazz_with_space = []
        for i, (_, row) in enumerate(jazz_df.iterrows()):
            if i >= 20:
                break
            cat = row['CATEGORY']
            length = row['CAT_LENGTH']
            trimmed = row['TRIMMED_LENGTH']
            has_space = length != trimmed

            if has_space:
                jazz_with_space.append(cat)
                print(f"{repr(cat):<30} {length:<10} {trimmed:<10} {'YES ⚠️':<15}")
            else:
                print(f"{repr(cat):<30} {length:<10} {trimmed:<10} {'No':<15}")

        # Summary
        print("\n" + "=" * 70)
        print("SUMMARY:")
        print(f"Panthers categories with whitespace: {len(panthers_with_space)}")
        print(f"Jazz categories with whitespace: {len(jazz_with_space)} (out of first 20)")

        if len(panthers_with_space) > 0:
            print("\n⚠️  PANTHERS HAS TRAILING WHITESPACE IN CATEGORIES!")
            print("This is likely causing the matching issue.")

    except Exception as e:
        print(f"Error: {e}")


def test_trimmed_matching():
    """Test if trimming would fix the matching"""

    print("\n" + "=" * 80)
    print("TESTING IF TRIMMING FIXES THE MATCH")
    print("=" * 80)

    # Initialize analyzer to get allowed list
    config_manager = TeamConfigManager()
    panthers_config = config_manager.get_team_config('carolina_panthers')

    analyzer = CategoryAnalyzer(
        team_name=panthers_config['team_name'],
        team_short=panthers_config['team_name_short'],
        league=panthers_config['league'],
        comparison_population=panthers_config['comparison_population']
    )

    # Get Panthers categories
    query = """
    SELECT DISTINCT 
        CATEGORY,
        TRIM(CATEGORY) as CATEGORY_TRIMMED
    FROM V_CAROLINA_PANTHERS_SIL_CATEGORY_INDEXING_ALL_TIME
    WHERE AUDIENCE = 'Carolina Panthers Fans'
    """

    try:
        df = query_to_dataframe(query)

        # Test matching
        print(f"\nAllowed list has {len(analyzer.allowed_custom)} entries")

        # Original matching
        original_matches = df[df['CATEGORY'].isin(analyzer.allowed_custom)]
        print(f"\nOriginal matching (no trim): {len(original_matches)} matches")

        # Trimmed matching
        trimmed_matches = df[df['CATEGORY_TRIMMED'].isin(analyzer.allowed_custom)]
        print(f"Trimmed matching: {len(trimmed_matches)} matches")

        if len(trimmed_matches) > len(original_matches):
            print("\n✅ TRIMMING FIXES THE ISSUE!")
            print(f"   {len(trimmed_matches) - len(original_matches)} additional matches after trimming")

            # Show what would match after trimming
            print("\nCategories that would match after trimming:")
            new_matches = df[
                (~df['CATEGORY'].isin(analyzer.allowed_custom)) &
                (df['CATEGORY_TRIMMED'].isin(analyzer.allowed_custom))
                ]

            for _, row in new_matches.head(10).iterrows():
                print(f"  - '{row['CATEGORY']}' -> '{row['CATEGORY_TRIMMED']}'")

    except Exception as e:
        print(f"Error: {e}")


def suggest_fix():
    """Suggest how to fix the whitespace issue"""

    print("\n" + "=" * 80)
    print("SUGGESTED FIX")
    print("=" * 80)

    print("""
If Panthers categories have trailing whitespace, you need to update the 
_clean_dataframe method in category_analyzer.py to be more aggressive:

```python
def _clean_dataframe(self, df: pd.DataFrame):
    \"\"\"Clean dataframe in place\"\"\"
    # Strip whitespace from string columns
    string_cols = df.select_dtypes(include=['object']).columns
    for col in string_cols:
        if col in df.columns:
            # MORE AGGRESSIVE TRIMMING
            df[col] = df[col].astype(str).str.strip()

    # Remove rows with null audiences
    if 'AUDIENCE' in df.columns:
        df.dropna(subset=['AUDIENCE'], inplace=True)
```

Or update the filter in get_custom_categories to trim before comparing:

```python
# In get_custom_categories method:
established_candidates = category_df[
    base_filter &
    (category_df['PERC_AUDIENCE'] >= established_cat_threshold) &
    (category_df['CATEGORY'].str.strip().isin(self.allowed_custom)) &  # TRIM HERE
    (~category_df['CATEGORY'].isin(self.excluded_custom)) &
    (~category_df['CATEGORY'].str.lower().isin(category_names_to_exclude_lower))
].copy()
```
""")


if __name__ == "__main__":
    check_whitespace()
    test_trimmed_matching()
    suggest_fix()