#!/usr/bin/env python3
"""
Test script for the minimal null fix in demographics processing
This script applies the minimal fix to handle null values in ETHNIC_GROUP
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
import pandas as pd
import logging

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from pptx import Presentation
from data_processors.demographic_processor import DemographicsProcessor
from data_processors.snowflake_connector import query_to_dataframe
from visualizations.demographic_charts import DemographicCharts
from slide_generators.demographics_slide import DemographicsSlide
from utils.team_config_manager import TeamConfigManager

# Set up logging to see what's happening
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DemographicsProcessorNullFix(DemographicsProcessor):
    """
    Modified DemographicsProcessor with minimal null fix for testing
    """

    def process_ethnicity(self) -> Dict[str, Any]:
        """Process ethnicity distribution using ETHNIC_GROUP column - WITH NULL FIX"""

        logger.info("🔧 STARTING ETHNICITY PROCESSING WITH NULL FIX")

        # Check if ETHNIC_GROUP column exists
        if 'ETHNIC_GROUP' not in self.data.columns:
            logger.warning("ETHNIC_GROUP column not found in data")
            return None

        # MINIMAL NULL FIX: Handle nulls before processing
        logger.info("🧹 Cleaning ETHNIC_GROUP data...")
        null_count = self.data['ETHNIC_GROUP'].isnull().sum()
        logger.info(f"Found {null_count:,} null values in ETHNIC_GROUP")

        if null_count > 0:
            logger.info(f"Replacing {null_count:,} null values with 'Unknown'")
            # Create a copy to avoid modifying original data
            clean_data = self.data.copy()
            clean_data['ETHNIC_GROUP'] = clean_data['ETHNIC_GROUP'].fillna('Unknown')

            # Show before/after
            logger.info("Before cleaning:")
            logger.info(f"  Unique values: {sorted(self.data['ETHNIC_GROUP'].dropna().unique())}")
            logger.info("After cleaning:")
            logger.info(f"  Unique values: {sorted(clean_data['ETHNIC_GROUP'].unique())}")

            # Temporarily replace self.data for this calculation
            original_data = self.data
            self.data = clean_data
            logger.info("✅ Temporarily using cleaned data for ethnicity calculation")
        else:
            logger.info("✅ No null values found, proceeding with original data")

        # Get unique ethnic groups from data
        unique_groups = self.data['ETHNIC_GROUP'].dropna().unique()
        logger.info(f"Found ethnic groups: {unique_groups}")

        try:
            # Calculate raw percentages for all groups
            logger.info("🔢 Calculating raw percentages...")
            raw_percentages = self._calculate_percentages('ETHNIC_GROUP')
            logger.info(f"✅ Raw percentages calculated for {len(raw_percentages)} communities")

            # Show raw results for debugging
            for community, data in raw_percentages.items():
                logger.info(f"  {community}: {len(data)} ethnic groups")
                for group, pct in data.items():
                    logger.info(f"    {group}: {pct}%")

        except Exception as e:
            logger.error(f"❌ Error calculating raw percentages: {e}")
            # Restore original data before re-raising
            if null_count > 0:
                self.data = original_data
            raise

        # Restore original data if we modified it
        if null_count > 0:
            self.data = original_data
            logger.info("📁 Restored original data")

        # Aggregate data into standard categories
        logger.info("🏷️  Aggregating into standard ethnicity categories...")
        aggregated = {}
        for community, data in raw_percentages.items():
            aggregated[community] = {cat: 0.0 for cat in self.ETHNICITY_ORDER}

            for group, percentage in data.items():
                # Map groups to standard categories
                if group == 'Unknown':
                    logger.info(f"  Skipping 'Unknown' group for {community} ({percentage}%)")
                    continue  # Skip unknown ethnicity in final aggregation
                elif 'White' in group or 'Caucasian' in group:
                    aggregated[community]['White'] += percentage
                elif 'Hispanic' in group or 'Latino' in group:
                    aggregated[community]['Hispanic'] += percentage
                elif 'African' in group or 'Black' in group:
                    aggregated[community]['African American'] += percentage
                elif 'Asian' in group:
                    aggregated[community]['Asian'] += percentage
                else:
                    aggregated[community]['Other'] += percentage

        logger.info("✅ Ethnicity aggregation complete")
        for community, data in aggregated.items():
            total_pct = sum(data.values())
            logger.info(f"  {community}: {total_pct:.1f}% total")

        return {
            'chart_type': 'grouped_bar',
            'title': 'Ethnicity',
            'categories': self.ETHNICITY_ORDER,
            'communities': self.communities,
            'data': aggregated,
            'insights': self._generate_ethnicity_insights(aggregated)
        }


def test_minimal_null_fix(team_key: str = 'utah_jazz', save_charts_only: bool = False):
    """
    Test the minimal null fix for ethnicity processing

    Args:
        team_key: Team to test with
        save_charts_only: If True, only generate charts without PowerPoint
    """

    print("\n" + "=" * 80)
    print("🧪 TESTING MINIMAL NULL FIX FOR ETHNICITY PROCESSING")
    print("=" * 80)
    print("Testing:")
    print("  ✓ Null value handling in ETHNIC_GROUP column")
    print("  ✓ Dtype preservation during calculations")
    print("  ✓ Successful ethnicity chart generation")
    print("=" * 80)

    try:
        # 1. Setup
        print("\n1. 🔧 Setting up...")
        config_manager = TeamConfigManager()
        team_config = config_manager.get_team_config(team_key)
        team_name = team_config['team_name']
        print(f"   Team: {team_name}")
        print(f"   Colors: {team_config.get('colors', {})}")

        # 2. Create output directory
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_dir = Path(f"test_null_fix_{team_key}_{timestamp}")
        output_dir.mkdir(exist_ok=True)
        print(f"   Output directory: {output_dir}")

        # 3. Fetch and analyze data
        print("\n2. 📊 Fetching demographic data...")
        demographics_view = config_manager.get_view_name(team_key, 'demographics')
        query = f"SELECT * FROM {demographics_view}"
        df = query_to_dataframe(query)
        print(f"   ✅ Loaded {len(df):,} rows from {demographics_view}")

        # Analyze null situation
        print("\n   🔍 ANALYZING NULL VALUES:")
        if 'ETHNIC_GROUP' in df.columns:
            total_rows = len(df)
            null_count = df['ETHNIC_GROUP'].isnull().sum()
            null_percentage = (null_count / total_rows) * 100
            print(f"   - Total rows: {total_rows:,}")
            print(f"   - Null ETHNIC_GROUP values: {null_count:,} ({null_percentage:.1f}%)")

            # Show unique values
            unique_values = df['ETHNIC_GROUP'].dropna().unique()
            print(f"   - Non-null unique values: {len(unique_values)}")
            print(f"   - Values: {sorted(unique_values)}")

            # Show data types
            print(f"   - ETHNIC_GROUP dtype: {df['ETHNIC_GROUP'].dtype}")
            print(f"   - CUSTOMER_COUNT dtype: {df['CUSTOMER_COUNT'].dtype}")
        else:
            print("   ❌ ETHNIC_GROUP column not found!")
            return None

        # 4. Test with fixed processor
        print("\n3. 🧪 Testing with minimal null fix...")
        processor = DemographicsProcessorNullFix(
            data_source=df,
            team_name=team_name,
            league=team_config['league']
        )

        print("   Processor initialized successfully")
        print(f"   Communities: {processor.communities}")

        # Test ethnicity processing specifically
        print("\n   🎯 Testing ethnicity processing...")
        try:
            ethnicity_result = processor.process_ethnicity()
            if ethnicity_result:
                print("   ✅ Ethnicity processing SUCCESS!")
                print(f"   Chart type: {ethnicity_result.get('chart_type')}")
                print(f"   Categories: {ethnicity_result.get('categories')}")
                print(f"   Communities with data: {len(ethnicity_result.get('data', {}))}")

                # Show results
                for community, data in ethnicity_result.get('data', {}).items():
                    total_pct = sum(data.values())
                    print(f"   - {community}: {total_pct:.1f}% total ethnicity data")
            else:
                print("   ❌ Ethnicity processing returned None")
                return None

        except Exception as e:
            print(f"   ❌ Ethnicity processing FAILED: {e}")
            import traceback
            traceback.print_exc()
            return None

        # 5. Test full demographics processing
        print("\n4. 🏆 Testing full demographics processing...")
        try:
            demographic_data = processor.process_all_demographics()
            print(f"   ✅ Full demographics processing SUCCESS!")
            print("   Demographics processed:")
            for demo_type, demo_info in demographic_data['demographics'].items():
                chart_type = demo_info.get('chart_type', 'unknown')
                print(f"   - {demo_type}: {chart_type}")

        except Exception as e:
            print(f"   ❌ Full demographics processing FAILED: {e}")
            import traceback
            traceback.print_exc()
            return None

        # 6. Generate charts to verify everything works
        print("\n5. 📈 Generating charts...")
        try:
            charter = DemographicCharts(team_colors=team_config.get('colors'))
            charts = charter.create_all_demographic_charts(
                demographic_data,
                output_dir=output_dir
            )
            print(f"   ✅ Generated {len(charts)} charts successfully")

            # Check if ethnicity chart was created
            if 'ethnicity' in charts:
                print("   ✅ Ethnicity chart created successfully!")
                ethnicity_path = output_dir / 'ethnicity_chart.png'
                print(f"   Ethnicity chart saved: {ethnicity_path}")
            else:
                print("   ⚠️  No ethnicity chart found in generated charts")

        except Exception as e:
            print(f"   ❌ Chart generation FAILED: {e}")
            import traceback
            traceback.print_exc()
            return None

        # 7. Create PowerPoint if requested
        if not save_charts_only:
            print("\n6. 📄 Creating PowerPoint presentation...")
            try:
                presentation = Presentation()

                # Create demographics slide with fixed data
                demo_generator = DemographicsSlide(presentation)
                presentation = demo_generator.generate(
                    demographic_data=demographic_data,
                    chart_dir=output_dir,
                    team_config=team_config
                )

                # Save presentation
                output_file = output_dir / f"{team_key}_demographics_null_fix_test.pptx"
                presentation.save(str(output_file))
                print(f"   ✅ PowerPoint saved: {output_file}")

            except Exception as e:
                print(f"   ❌ PowerPoint creation FAILED: {e}")
                import traceback
                traceback.print_exc()
                return None

        # 8. Summary
        print("\n" + "=" * 80)
        print("🎉 TEST SUMMARY - MINIMAL NULL FIX")
        print("=" * 80)
        print(f"Team: {team_name}")
        print(f"Null values handled: {null_count:,} ({null_percentage:.1f}%)")
        print(f"Charts generated: {len(charts)}")
        print(f"Output directory: {output_dir}")

        if ethnicity_result:
            print("✅ Ethnicity processing: SUCCESS")
            ethnicity_data = ethnicity_result.get('data', {})
            for community in ethnicity_data:
                total_pct = sum(ethnicity_data[community].values())
                print(f"   - {community}: {total_pct:.1f}% ethnicity coverage")
        else:
            print("❌ Ethnicity processing: FAILED")

        if not save_charts_only:
            print(f"PowerPoint file: {output_file}")

        print("\n🔍 What to verify:")
        print("1. Check that ethnicity chart was generated successfully")
        print("2. Verify no 'Unknown' ethnicity appears in final chart")
        print("3. Confirm percentages add up correctly for each community")
        print("4. Open PowerPoint to see ethnicity section populated")

        print("\nFiles created:")
        for file in sorted(output_dir.glob('*')):
            print(f"  - {file.name}")

        return output_dir

    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    print("🚀 MINIMAL NULL FIX TEST")
    print("This test applies a minimal fix to handle null values in ETHNIC_GROUP")

    # Run test with Utah Jazz (you can change this)
    result = test_minimal_null_fix('utah_jazz', save_charts_only=False)

    if result:
        print(f"\n✅ Test completed successfully!")
        print(f"Check output directory: {result}")
    else:
        print(f"\n❌ Test failed - check error messages above")