"""
Diagnostic script to investigate why Pickleball & Racket Sports shows 0%
Run this to trace the data flow and identify where the issue occurs
"""

import pandas as pd
import logging
from pathlib import Path
import yaml

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def diagnose_pickleball_issue(
        subcategory_df: pd.DataFrame,
        team_name: str = "Utah Jazz",
        category_name: str = "Sportstainment"
):
    """
    Diagnose why Pickleball & Racket Sports shows 0% for Utah Jazz fans

    Args:
        subcategory_df: DataFrame from SUBCATEGORY_INDEXING_ALL_TIME view
        team_name: Team name to analyze
        category_name: Category to filter for
    """
    print("=" * 80)
    print("DIAGNOSTIC REPORT: Pickleball & Racket Sports 0% Issue")
    print("=" * 80)

    # 1. Check raw data structure
    print("\n1. RAW DATA STRUCTURE:")
    print(f"   Total rows: {len(subcategory_df)}")
    print(f"   Columns: {list(subcategory_df.columns)}")

    # 2. Check for Pickleball data
    print("\n2. SEARCHING FOR PICKLEBALL & RACKET SPORTS:")

    # Try different search patterns
    search_patterns = [
        "Pickleball & Racket Sports",
        "Pickleball",
        "Racket Sports",
        "PICKLEBALL",
        "pickleball",
        "Sportstainment - Pickleball & Racket Sports"
    ]

    for pattern in search_patterns:
        matches = subcategory_df[subcategory_df['SUBCATEGORY'].str.contains(pattern, case=False, na=False)]
        if not matches.empty:
            print(f"\n   Found {len(matches)} rows matching '{pattern}':")
            break
    else:
        print("   ❌ NO MATCHES FOUND for any Pickleball pattern!")
        print("\n   All unique subcategories in Sportstainment:")
        sport_subs = subcategory_df[subcategory_df['CATEGORY'] == category_name]['SUBCATEGORY'].unique()
        for sub in sorted(sport_subs):
            print(f"      - {sub}")
        return

    # 3. Analyze the matched data
    print("\n3. ANALYZING PICKLEBALL DATA:")

    # Filter for team fans
    team_audience = f"{team_name} Fans"
    team_data = matches[matches['AUDIENCE'] == team_audience]

    print(f"\n   Rows for {team_audience}: {len(team_data)}")

    if team_data.empty:
        print(f"   ❌ No data found for {team_audience}!")
        print(f"\n   Available audiences for Pickleball:")
        for aud in matches['AUDIENCE'].unique():
            print(f"      - {aud}")
        return

    # 4. Check PERC_AUDIENCE values
    print("\n4. PERC_AUDIENCE VALUES:")

    for _, row in team_data.iterrows():
        perc_audience = row['PERC_AUDIENCE']
        comparison_pop = row['COMPARISON_POPULATION']
        print(f"\n   Audience: {row['AUDIENCE']}")
        print(f"   Comparison: {comparison_pop}")
        print(f"   PERC_AUDIENCE (raw): {perc_audience}")
        print(f"   PERC_AUDIENCE (type): {type(perc_audience)}")

        # Check if it's actually 0 or just very small
        if isinstance(perc_audience, (int, float)):
            print(f"   PERC_AUDIENCE (exact): {perc_audience:.10f}")
            print(f"   As percentage: {perc_audience * 100:.10f}%")

            # Check if it rounds to 0
            if round(perc_audience * 100) == 0:
                print("   ⚠️  This rounds to 0% when displayed!")

        # Show other metrics
        print(f"   PERC_INDEX: {row.get('PERC_INDEX', 'N/A')}")
        print(f"   COMPOSITE_INDEX: {row.get('COMPOSITE_INDEX', 'N/A')}")
        print(f"   AUDIENCE_TOTAL_SPEND: ${row.get('AUDIENCE_TOTAL_SPEND', 0):,.2f}")
        print(f"   AUDIENCE_COUNT: {row.get('AUDIENCE_COUNT', 0):,}")

    # 5. Compare with other subcategories
    print("\n5. COMPARISON WITH OTHER SUBCATEGORIES:")

    # Get all subcategories for this team and category
    all_subs = subcategory_df[
        (subcategory_df['AUDIENCE'] == team_audience) &
        (subcategory_df['CATEGORY'] == category_name) &
        (subcategory_df['COMPARISON_POPULATION'].str.contains('Local Gen Pop', case=False, na=False))
        ].copy()

    if not all_subs.empty:
        all_subs['PERC_AUDIENCE_PCT'] = all_subs['PERC_AUDIENCE'] * 100
        all_subs = all_subs.sort_values('PERC_AUDIENCE_PCT')

        print(f"\n   Lowest 5 subcategories by PERC_AUDIENCE:")
        for _, row in all_subs.head(5).iterrows():
            sub_name = row['SUBCATEGORY'].replace(f"{category_name} - ", "")
            print(f"      {sub_name}: {row['PERC_AUDIENCE_PCT']:.2f}%")

    # 6. Check data processing logic
    print("\n6. DATA PROCESSING CHECK:")

    # Simulate the formatting logic
    test_values = [0, 0.0001, 0.001, 0.004, 0.005, 0.01, 0.1]
    print("\n   How different values get formatted:")
    for val in test_values:
        pct = val * 100
        rounded = round(pct)
        formatted = f"{rounded}%" if rounded > 0 else "EQUAL"
        print(f"      {val:.4f} -> {pct:.2f}% -> rounds to {rounded} -> displays as '{formatted}'")

    # 7. SQL Query suggestion
    print("\n7. SUGGESTED SQL QUERY TO VERIFY:")
    print("""
    SELECT 
        AUDIENCE,
        SUBCATEGORY,
        PERC_AUDIENCE,
        PERC_AUDIENCE * 100 as PERC_AUDIENCE_PCT,
        AUDIENCE_COUNT,
        AUDIENCE_TOTAL_SPEND,
        COMPOSITE_INDEX
    FROM SUBCATEGORY_INDEXING_ALL_TIME
    WHERE AUDIENCE = 'Utah Jazz Fans'
        AND SUBCATEGORY LIKE '%Pickleball%'
        AND COMPARISON_POPULATION LIKE '%Local Gen Pop%'
    ORDER BY PERC_AUDIENCE DESC;
    """)


def quick_check(subcategory_df: pd.DataFrame):
    """Quick check for the most common issues"""
    print("\nQUICK CHECK RESULTS:")
    print("-" * 40)

    # Check 1: Is there any Pickleball data?
    pickleball_rows = subcategory_df[
        subcategory_df['SUBCATEGORY'].str.contains('Pickleball', case=False, na=False)
    ]
    print(f"Total Pickleball rows in data: {len(pickleball_rows)}")

    if not pickleball_rows.empty:
        # Check 2: What's the PERC_AUDIENCE for Utah Jazz?
        jazz_pickleball = pickleball_rows[
            (pickleball_rows['AUDIENCE'] == 'Utah Jazz Fans') &
            (pickleball_rows['COMPARISON_POPULATION'].str.contains('Local Gen Pop', case=False, na=False))
            ]

        if not jazz_pickleball.empty:
            perc = jazz_pickleball.iloc[0]['PERC_AUDIENCE']
            print(f"Utah Jazz Fans PERC_AUDIENCE: {perc} ({perc * 100:.4f}%)")
            print(f"This rounds to: {round(perc * 100)}%")
        else:
            print("❌ No Utah Jazz Fans data for Pickleball vs Local Gen Pop")
    else:
        print("❌ No Pickleball data found at all!")


# Example usage:
if __name__ == "__main__":
    # You would load your actual data here
    # subcategory_df = load_subcategory_data()

    # For testing, create a sample DataFrame
    sample_data = pd.DataFrame({
        'AUDIENCE': ['Utah Jazz Fans', 'Utah Jazz Fans'],
        'CATEGORY': ['Sportstainment', 'Sportstainment'],
        'SUBCATEGORY': ['Sportstainment - Pickleball & Racket Sports', 'Sportstainment - Golf Resorts'],
        'COMPARISON_POPULATION': ['Local Gen Pop (Excl. Jazz)', 'Local Gen Pop (Excl. Jazz)'],
        'PERC_AUDIENCE': [0.0045, 0.10],  # 0.45% and 10%
        'PERC_INDEX': [614, 423],
        'COMPOSITE_INDEX': [300, 400],
        'AUDIENCE_COUNT': [1000, 20000],
        'AUDIENCE_TOTAL_SPEND': [50000, 1000000]
    })

    print("Running diagnostic with sample data...")
    print("(Replace with your actual subcategory_df)\n")

    # Run quick check first
    quick_check(sample_data)

    # Run full diagnostic
    diagnose_pickleball_issue(sample_data)