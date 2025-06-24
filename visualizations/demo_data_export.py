#!/usr/bin/env python3
"""
Export demographic chart data to Excel for validation
Extracts the exact data shown in the PowerPoint demographic charts
"""

import pandas as pd
from pathlib import Path
import sys
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from data_processors.demographic_processor import DemographicsProcessor
from data_processors.snowflake_connector import query_to_dataframe
from utils.team_config_manager import TeamConfigManager


def export_demographic_chart_data(team_key='utah_jazz'):
    """Export demographic chart data to Excel"""

    print("\n" + "=" * 60)
    print("DEMOGRAPHIC CHART DATA EXPORT")
    print("=" * 60)

    try:
        # 1. Get team configuration
        config_manager = TeamConfigManager()
        team_config = config_manager.get_team_config(team_key)
        team_name = team_config['team_name']

        print(f"\nTeam: {team_name}")

        # 2. Fetch data from Snowflake
        demographics_view = config_manager.get_view_name(team_key, 'demographics')
        query = f"SELECT * FROM {demographics_view}"

        print(f"Fetching from: {demographics_view}")
        df = query_to_dataframe(query)
        print(f"✅ Loaded {len(df):,} rows")

        # 3. Process demographics
        processor = DemographicsProcessor(
            data_source=df,
            team_name=team_name,
            league=team_config['league']
        )

        demographic_data = processor.process_all_demographics()
        print("✅ Demographics processed")

        # 4. Export to Excel
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"{team_key}_demographic_charts_data_{timestamp}.xlsx"

        with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
            # Overview sheet
            overview = pd.DataFrame({
                'Field': ['Team Name', 'Total Sample Size', 'Communities', 'Key Insight'],
                'Value': [
                    demographic_data['team_name'],
                    f"{demographic_data['total_sample_size']:,}",
                    ', '.join(demographic_data['communities']),
                    demographic_data['key_insights']
                ]
            })
            overview.to_excel(writer, sheet_name='Overview', index=False)

            # For each demographic type, create a sheet with the chart data
            demographics = demographic_data['demographics']

            # 1. Generation Chart Data
            if 'generation' in demographics:
                gen_data = demographics['generation']['data']
                gen_df = pd.DataFrame(gen_data)
                gen_df.to_excel(writer, sheet_name='Generation_Chart', index=True)

                # Also create a transposed version for easier reading
                gen_transposed = gen_df.T
                gen_transposed.to_excel(writer, sheet_name='Generation_by_Community', index=True)

            # 2. Income Chart Data
            if 'income' in demographics:
                income_data = demographics['income']['data']
                income_df = pd.DataFrame(income_data)
                income_df.to_excel(writer, sheet_name='Income_Chart', index=True)

                income_transposed = income_df.T
                income_transposed.to_excel(writer, sheet_name='Income_by_Community', index=True)

            # 3. Occupation Chart Data
            if 'occupation' in demographics:
                occ_data = demographics['occupation']['data']
                occ_df = pd.DataFrame(occ_data)
                occ_df.to_excel(writer, sheet_name='Occupation_Chart', index=True)

                occ_transposed = occ_df.T
                occ_transposed.to_excel(writer, sheet_name='Occupation_by_Community', index=True)

            # 4. Gender Pie Chart Data
            if 'gender' in demographics:
                gender_data = demographics['gender']['data']
                # Create separate sheets for each community's pie chart
                for community, values in gender_data.items():
                    gender_df = pd.DataFrame(list(values.items()), columns=['Gender', 'Percentage'])
                    sheet_name = f'Gender_{community[:20]}'  # Limit sheet name length
                    gender_df.to_excel(writer, sheet_name=sheet_name, index=False)

            # 5. Children Chart Data
            if 'children' in demographics:
                children_data = demographics['children']['data']
                children_df = pd.DataFrame(children_data)
                children_df.to_excel(writer, sheet_name='Children_Chart', index=True)

                children_transposed = children_df.T
                children_transposed.to_excel(writer, sheet_name='Children_by_Community', index=True)

            # 6. All Insights
            all_insights = []
            for demo_type, demo_info in demographics.items():
                if isinstance(demo_info, dict) and 'insights' in demo_info:
                    for insight in demo_info['insights']:
                        all_insights.append({
                            'Demographic Type': demo_type.title(),
                            'Insight': insight
                        })

            if all_insights:
                insights_df = pd.DataFrame(all_insights)
                insights_df.to_excel(writer, sheet_name='All_Insights', index=False)

            # Apply formatting
            workbook = writer.book

            # Header format
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#D9D9D9',
                'border': 1
            })

            # Percentage format
            percent_format = workbook.add_format({'num_format': '0.0%'})

        print(f"\n✅ SUCCESS! Demographic chart data exported to: {output_file}")
        print("\nSheets included:")
        print("  - Overview: Team info and key insight")
        print("  - Generation_Chart: Data for generation bar chart")
        print("  - Income_Chart: Data for income bar chart")
        print("  - Occupation_Chart: Data for occupation bar chart")
        print("  - Gender_[Community]: Data for each gender pie chart")
        print("  - Children_Chart: Data for children bar chart")
        print("  - All_Insights: All demographic insights")

        return output_file

    except Exception as e:
        print(f"\n❌ ERROR: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def export_both_teams():
    """Export demographic data for both teams"""
    print("\nExporting demographic chart data for all teams...")

    teams = ['utah_jazz', 'dallas_cowboys']
    exported_files = []

    for team in teams:
        print(f"\n{'=' * 40}")
        print(f"Processing {team.replace('_', ' ').title()}")
        print('=' * 40)

        result = export_demographic_chart_data(team)
        if result:
            exported_files.append(result)

    print(f"\n✅ Exported {len(exported_files)} files:")
    for file in exported_files:
        print(f"  - {file}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Export demographic chart data to Excel')
    parser.add_argument('--team', type=str, default='utah_jazz',
                        choices=['utah_jazz', 'dallas_cowboys'],
                        help='Team to export data for')
    parser.add_argument('--all', action='store_true',
                        help='Export data for all teams')

    args = parser.parse_args()

    if args.all:
        export_both_teams()
    else:
        export_demographic_chart_data(args.team)