# test_demographic_charts_fixed.py
"""
Test script to generate demographic charts from Snowflake data
Fixed to match the expected data format
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from data_processors.demographic_processor import DemographicsProcessor
from data_processors.snowflake_connector import query_to_dataframe
from visualizations.demographic_charts import DemographicCharts
from utils.team_config_manager import TeamConfigManager
import matplotlib.pyplot as plt


def test_demographic_charts(team_key='utah_jazz'):
    """Generate demographic charts for a team"""
    print("=" * 60)
    print("DEMOGRAPHIC CHARTS GENERATION TEST")
    print("=" * 60)

    try:
        # 1. Get team configuration
        config_manager = TeamConfigManager()
        team_config = config_manager.get_team_config(team_key)
        team_name = team_config['team_name']
        team_colors = team_config.get('colors', None)

        print(f"\n1. Processing {team_name} demographics...")

        # 2. Fetch data from Snowflake
        demographics_view = config_manager.get_view_name(team_key, 'demographics')
        query = f"SELECT * FROM {demographics_view}"

        print(f"   Fetching from: {demographics_view}")
        df = query_to_dataframe(query)
        print(f"   ✅ Loaded {len(df):,} rows")

        # 3. Process demographics
        processor = DemographicsProcessor(
            data_source=df,
            team_name=team_name,
            league=team_config['league']
        )

        demographic_data = processor.process_all_demographics()
        print("   ✅ Demographics processed")

        # 4. Create charts
        print("\n2. Generating charts...")
        charter = DemographicCharts(team_colors=team_colors)

        # Create output directory
        output_dir = Path(f"{team_key}_demographic_charts")
        output_dir.mkdir(exist_ok=True)

        # Generate all individual charts
        charts = charter.create_all_demographic_charts(
            demographic_data,
            output_dir=output_dir
        )

        print(f"   ✅ Generated {len(charts)} charts")

        print(f"\n✅ All charts saved to {output_dir}/")
        print("\nChart files generated:")
        for file in sorted(output_dir.glob('*.png')):
            print(f"   - {file.name}")

        return charts, demographic_data

    except Exception as e:
        print(f"\n❌ ERROR: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return None, None


def test_with_mock_data():
    """Test charts with mock data for quick validation"""
    print("\n\n" + "=" * 60)
    print("TESTING CHARTS WITH MOCK DATA")
    print("=" * 60)

    # Create mock demographic data IN THE CORRECT FORMAT
    mock_data = {
        'team_name': 'Utah Jazz',
        'league': 'NBA',
        'communities': ['Utah Jazz Fans', 'Local Gen Pop (Excl. Jazz)', 'NBA Fans'],
        'total_sample_size': 500000,
        'key_insights': 'Jazz fans are younger, and more likely to be parents who are working professionals versus the Utah gen pop.',
        'demographics': {
            'generation': {
                'chart_type': 'grouped_bar',
                'title': 'Generation',
                'categories': [
                    '1. Millennials and Gen Z (1982 and after)',
                    '2. Generation X (1961-1981)',
                    '3. Baby Boomers (1943-1960)',
                    '4. Post-WWII (1942 and before)'
                ],
                'data': {
                    'Utah Jazz Fans': {
                        '1. Millennials and Gen Z (1982 and after)': 51,
                        '2. Generation X (1961-1981)': 45,
                        '3. Baby Boomers (1943-1960)': 10,
                        '4. Post-WWII (1942 and before)': 2
                    },
                    'Local Gen Pop (Excl. Jazz)': {
                        '1. Millennials and Gen Z (1982 and after)': 37,
                        '2. Generation X (1961-1981)': 34,
                        '3. Baby Boomers (1943-1960)': 17,
                        '4. Post-WWII (1942 and before)': 4
                    },
                    'NBA Fans': {
                        '1. Millennials and Gen Z (1982 and after)': 45,
                        '2. Generation X (1961-1981)': 40,
                        '3. Baby Boomers (1943-1960)': 12,
                        '4. Post-WWII (1942 and before)': 3
                    }
                },
                'insights': ['Jazz fans skew younger']
            },
            'income': {
                'chart_type': 'grouped_bar',
                'title': 'Household Income',
                'categories': [
                    '$10,000 to $49,999',
                    '$50,000 to $74,999',
                    '$75,000 to $99,999',
                    '$100,000 to $149,999',
                    '$150,000 to $199,999',
                    '$200,000 or more'
                ],
                'data': {
                    'Utah Jazz Fans': {
                        '$10,000 to $49,999': 25,
                        '$50,000 to $74,999': 17,
                        '$75,000 to $99,999': 14,
                        '$100,000 to $149,999': 21,
                        '$150,000 to $199,999': 12,
                        '$200,000 or more': 6
                    },
                    'Local Gen Pop (Excl. Jazz)': {
                        '$10,000 to $49,999': 24,
                        '$50,000 to $74,999': 17,
                        '$75,000 to $99,999': 15,
                        '$100,000 to $149,999': 23,
                        '$150,000 to $199,999': 12,
                        '$200,000 or more': 6
                    },
                    'NBA Fans': {
                        '$10,000 to $49,999': 20,
                        '$50,000 to $74,999': 15,
                        '$75,000 to $99,999': 18,
                        '$100,000 to $149,999': 25,
                        '$150,000 to $199,999': 15,
                        '$200,000 or more': 7
                    }
                },
                'insights': []
            },
            'occupation': {
                'chart_type': 'grouped_bar',
                'title': 'Occupation Category',
                'categories': [
                    'Blue Collar', 'Homemaker', 'Lower Management',
                    'Professional', 'Upper Management', 'White Collar Worker',
                    'Retired', 'Other'
                ],
                'data': {
                    'Utah Jazz Fans': {
                        'Blue Collar': 12,
                        'Homemaker': 6,
                        'Lower Management': 11,
                        'Professional': 29,
                        'Upper Management': 15,
                        'White Collar Worker': 21,
                        'Retired': 2,
                        'Other': 4
                    },
                    'Local Gen Pop (Excl. Jazz)': {
                        'Blue Collar': 17,
                        'Homemaker': 11,
                        'Lower Management': 12,
                        'Professional': 19,
                        'Upper Management': 13,
                        'White Collar Worker': 18,
                        'Retired': 5,
                        'Other': 5
                    },
                    'NBA Fans': {
                        'Blue Collar': 15,
                        'Homemaker': 8,
                        'Lower Management': 12,
                        'Professional': 25,
                        'Upper Management': 14,
                        'White Collar Worker': 20,
                        'Retired': 3,
                        'Other': 3
                    }
                },
                'insights': ['29% of Jazz fans are Professionals']
            },
            'gender': {
                'chart_type': 'pie',
                'title': 'Gender',
                'categories': ['Male', 'Female'],
                'data': {
                    'Utah Jazz Fans': {'Male': 59, 'Female': 41},
                    'Local Gen Pop (Excl. Jazz)': {'Male': 49, 'Female': 51},
                    'NBA Fans': {'Male': 55, 'Female': 45}
                },
                'insights': []
            },
            'children': {
                'chart_type': 'grouped_bar',
                'title': 'Children in Household',
                'categories': ['No Children in HH', 'At least 1 Child in HH'],
                'data': {
                    'Utah Jazz Fans': {
                        'No Children in HH': 34,
                        'At least 1 Child in HH': 66
                    },
                    'Local Gen Pop (Excl. Jazz)': {
                        'No Children in HH': 46,
                        'At least 1 Child in HH': 54
                    },
                    'NBA Fans': {
                        'No Children in HH': 40,
                        'At least 1 Child in HH': 60
                    }
                },
                'insights': ['Jazz fans are more likely to be parents']
            }
        }
    }

    # Create charts with mock data
    print("\nGenerating charts with mock data...")

    # Use Utah Jazz colors
    team_colors = {
        'primary': '#002B5C',  # Jazz blue
        'secondary': '#F9A01B',  # Jazz yellow
        'accent': '#00471B'  # Jazz green
    }

    charter = DemographicCharts(team_colors=team_colors)

    output_dir = Path('mock_demographic_charts')
    output_dir.mkdir(exist_ok=True)

    charts = charter.create_all_demographic_charts(
        mock_data,
        output_dir=output_dir
    )

    print(f"✅ Generated {len(charts)} mock charts in {output_dir}/")

    # Note: create_summary_visualization is not in the corrected demographic_charts.py
    # If you need a summary, you would need to add that method

    return charts


if __name__ == "__main__":
    # First test with mock data
    print("Testing with mock data first...")
    mock_charts = test_with_mock_data()

    # Then test with real data
    user_input = input("\n\nTest with real Snowflake data? (y/n): ")
    if user_input.lower() == 'y':
        # Test with Utah Jazz
        charts, data = test_demographic_charts('utah_jazz')

        # Optionally test Dallas Cowboys
        user_input = input("\n\nAlso test Dallas Cowboys? (y/n): ")
        if user_input.lower() == 'y':
            test_demographic_charts('dallas_cowboys')