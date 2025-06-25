#!/usr/bin/env python3
"""
validate_ai_integration.py
Simple test script to validate AI demographic insights are working with your data
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from data_processors.demographic_processor import DemographicsProcessor
from data_processors.snowflake_connector import query_to_dataframe
from utils.team_config_manager import TeamConfigManager


def validate_ai_integration(team_key='utah_jazz'):
    """Validate AI integration with real Snowflake data"""

    print("\n" + "=" * 70)
    print("🔍 VALIDATING AI DEMOGRAPHIC INSIGHTS INTEGRATION")
    print("=" * 70)

    # 1. Check environment
    print("\n1️⃣  Environment Check:")
    api_key_exists = bool(os.getenv('OPENAI_API_KEY'))
    print(f"   ✓ OpenAI API Key: {'Found' if api_key_exists else 'Not Found'}")
    print(f"   ✓ Python Path: {sys.executable}")

    if not api_key_exists:
        print("\n   ⚠️  No API key found - will use template insights")

    try:
        # 2. Load team configuration
        print("\n2️⃣  Loading Team Configuration:")
        config_manager = TeamConfigManager()
        team_config = config_manager.get_team_config(team_key)
        team_name = team_config['team_name']
        print(f"   ✓ Team: {team_name}")
        print(f"   ✓ League: {team_config['league']}")

        # 3. Fetch data from Snowflake
        print("\n3️⃣  Fetching Snowflake Data:")
        demographics_view = config_manager.get_view_name(team_key, 'demographics')
        query = f"SELECT * FROM {demographics_view}"
        print(f"   ✓ View: {demographics_view}")

        df = query_to_dataframe(query)
        print(f"   ✓ Records: {len(df):,}")
        print(f"   ✓ Customers: {df['CUSTOMER_COUNT'].sum():,}")

        # 4. Test WITHOUT AI (template insights)
        print("\n4️⃣  Testing Template Insights (AI disabled):")
        processor_template = DemographicsProcessor(
            data_source=df,
            team_name=team_name,
            league=team_config['league'],
            use_ai_insights=False  # Force template mode
        )

        results_template = processor_template.process_all_demographics()
        template_insight = results_template['key_insights']
        print(f"   📝 Template: \"{template_insight}\"")

        # 5. Test WITH AI (if available)
        print("\n5️⃣  Testing AI Insights:")
        processor_ai = DemographicsProcessor(
            data_source=df,
            team_name=team_name,
            league=team_config['league'],
            use_ai_insights=True  # Try to use AI
        )

        results_ai = processor_ai.process_all_demographics()
        ai_insight = results_ai['key_insights']

        if processor_ai.use_ai_insights:
            print(f"   🤖 AI: \"{ai_insight}\"")
            print(f"   ✓ AI insights are working!")
        else:
            print(f"   📝 Fallback: \"{ai_insight}\"")
            print(f"   ℹ️  AI not available, using template")

        # 6. Show demographic breakdown
        print("\n6️⃣  Sample Demographic Data:")
        demographics = results_ai['demographics']

        # Show a few key metrics
        if 'generation' in demographics:
            gen_data = demographics['generation']['data']
            fan_community = f"{team_name} Fans"
            if fan_community in gen_data:
                millennials = gen_data[fan_community].get('1. Millennials and Gen Z (1982 and after)', 0)
                print(f"   • Millennials/Gen Z: {millennials:.0f}%")

        if 'occupation' in demographics:
            occ_data = demographics['occupation']['data']
            fan_community = f"{team_name} Fans"
            if fan_community in occ_data:
                prof = occ_data[fan_community].get('Professional', 0)
                print(f"   • Professionals: {prof:.0f}%")

        if 'children' in demographics:
            child_data = demographics['children']['data']
            fan_community = f"{team_name} Fans"
            if fan_community in child_data:
                parents = child_data[fan_community].get('At least 1 Child in HH', 0)
                print(f"   • Parents: {parents:.0f}%")

        # 7. Compare insights
        print("\n7️⃣  Insight Comparison:")
        print("   Template vs AI:")
        print(f"   • Length: {len(template_insight)} vs {len(ai_insight)} characters")
        print(f"   • Contains percentages: {'Yes' if '%' in ai_insight else 'No'}")
        print(f"   • More specific: {'Yes' if len(ai_insight) > len(template_insight) else 'No'}")

        # 8. Save test results
        print("\n8️⃣  Saving Results:")
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"ai_validation_{team_key}_{timestamp}.txt"

        with open(output_file, 'w') as f:
            f.write(f"AI Integration Validation - {team_name}\n")
            f.write(f"{'=' * 50}\n")
            f.write(f"Timestamp: {datetime.now()}\n")
            f.write(f"API Key Available: {api_key_exists}\n")
            f.write(f"AI Insights Used: {processor_ai.use_ai_insights}\n")
            f.write(f"\nTemplate Insight:\n{template_insight}\n")
            f.write(f"\nAI/Final Insight:\n{ai_insight}\n")
            f.write(f"\nSample Size: {results_ai['total_sample_size']:,} customers\n")

        print(f"   ✓ Results saved to: {output_file}")

        # 9. Final status
        print("\n" + "=" * 70)
        if processor_ai.use_ai_insights and ai_insight != template_insight:
            print("✅ SUCCESS: AI insights are working correctly!")
            print("   Your demographic slides will now have enhanced insights.")
        else:
            print("⚠️  AI insights not active. Check your OpenAI API key.")
            print("   The system is working with template insights as fallback.")
        print("=" * 70 + "\n")

        return True

    except Exception as e:
        print(f"\n❌ ERROR: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # Run validation
    success = validate_ai_integration()

    # Optional: test multiple teams
    if success:
        print("\nWould you like to test Dallas Cowboys too? (y/n): ", end='')
        if input().lower() == 'y':
            validate_ai_integration('dallas_cowboys')