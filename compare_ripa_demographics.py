#!/usr/bin/env python3
"""
Compare demographics across all RIPA audiences
Generates a CSV showing side-by-side demographic breakdowns
"""

import sys
from pathlib import Path
import pandas as pd
from datetime import datetime

sys.path.append(str(Path(__file__).parent))

from data_processors.snowflake_connector import set_schema, query_to_dataframe
from utils.team_config_manager import TeamConfigManager


def get_ripa_audiences():
    """Get all RIPA audience configurations"""
    config_manager = TeamConfigManager()
    all_teams = config_manager.list_teams()
    
    ripa_audiences = {}
    for team_key in all_teams:
        config = config_manager.get_team_config(team_key)
        if config.get('snowflake_schema') == 'RIPA_GS':
            # Map audience_name to the COMMUNITY name in demographics table
            ripa_audiences[team_key] = {
                'name': config['team_name'],
                'audience_name': config['audience_name'],
                'community_name': config['audience_name']  # Same as audience_name for RIPA
            }
    
    return ripa_audiences


def get_demographic_breakdown(community_name, dimension):
    """
    Get demographic breakdown for a specific community and dimension
    Returns DataFrame with dimension values and percentages
    """
    safe_community = community_name.replace("'", "''")
    
    query = f"""
    SELECT 
        {dimension} as segment,
        SUM(CUSTOMER_COUNT) as count
    FROM GS_DEMOGRAPHICS_DIST
    WHERE COMMUNITY = '{safe_community}'
        AND {dimension} IS NOT NULL
    GROUP BY {dimension}
    ORDER BY count DESC
    """
    
    df = query_to_dataframe(query)
    
    if not df.empty:
        total = df['COUNT'].sum()
        df['PERCENTAGE'] = (df['COUNT'] / total * 100).round(1)
    
    return df


def create_demographics_comparison():
    """Create CSV comparing demographics across all RIPA audiences"""
    print("=" * 80)
    print("RIPA AUDIENCES DEMOGRAPHICS COMPARISON")
    print("=" * 80)
    
    # Set schema
    set_schema('RIPA_GS')
    
    # Get all RIPA audiences
    ripa_audiences = get_ripa_audiences()
    
    print(f"\nFound {len(ripa_audiences)} RIPA audiences:")
    for team_key, info in ripa_audiences.items():
        print(f"  • {info['name']}: {info['community_name']}")
    
    # Define demographic dimensions to compare
    dimensions = [
        ('GENDER', 'Gender'),
        ('GENERATION', 'Generation'),
        ('INCOME_LEVELS', 'Income Level'),
        ('ETHNIC_GROUP', 'Ethnicity'),
        ('EDUCATION', 'Education'),
        ('CHILDREN_HH', 'Children in Household'),
        ('OCCUPATION_CATEGORY', 'Occupation')
    ]
    
    # Collect all comparison data
    all_comparisons = []
    
    for dim_column, dim_label in dimensions:
        print(f"\nProcessing {dim_label}...")
        
        # Get data for each audience
        dim_data = {}
        for team_key, info in ripa_audiences.items():
            df = get_demographic_breakdown(info['community_name'], dim_column)
            if not df.empty:
                dim_data[info['name']] = df
                print(f"  ✓ {info['name']}: {len(df)} segments")
        
        if not dim_data:
            print(f"  ⚠️  No data found for {dim_label}")
            continue
        
        # Get all unique segments across all audiences
        all_segments = set()
        for df in dim_data.values():
            all_segments.update(df['SEGMENT'].tolist())
        
        # Create comparison rows for this dimension
        for segment in sorted(all_segments):
            row = {
                'Demographic': dim_label,
                'Segment': segment if segment else '(Unknown)'
            }
            
            for audience_name, df in dim_data.items():
                segment_data = df[df['SEGMENT'] == segment]
                if not segment_data.empty:
                    pct = segment_data['PERCENTAGE'].values[0]
                    row[f'{audience_name} %'] = f"{pct:.1f}%"
                else:
                    row[f'{audience_name} %'] = "0.0%"
            
            all_comparisons.append(row)
    
    if not all_comparisons:
        print("\n❌ No demographic data found!")
        return
    
    # Create DataFrame
    comparison_df = pd.DataFrame(all_comparisons)
    
    # Save to CSV
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_dir = Path('output') / 'comparisons'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / f'ripa_demographics_comparison_{timestamp}.csv'
    comparison_df.to_csv(output_file, index=False)
    
    print(f"\n{'=' * 80}")
    print(f"✅ SUCCESS!")
    print(f"{'=' * 80}")
    print(f"\n📁 Output file: {output_file}")
    
    # Print preview for each demographic
    print(f"\n📊 Preview by Demographic:")
    for dim_column, dim_label in dimensions:
        dim_rows = comparison_df[comparison_df['Demographic'] == dim_label]
        if not dim_rows.empty:
            print(f"\n{dim_label}:")
            print(dim_rows.to_string(index=False))
    
    # Print summary insights
    print(f"\n📈 Summary:")
    print(f"   • Audiences compared: {len(ripa_audiences)}")
    print(f"   • Demographic dimensions: {len(dimensions)}")
    print(f"   • Total comparison rows: {len(comparison_df)}")
    
    return output_file


if __name__ == "__main__":
    try:
        create_demographics_comparison()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


