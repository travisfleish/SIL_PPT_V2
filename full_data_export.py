#!/usr/bin/env python3
"""
Export only the data that will appear in the PowerPoint presentation
For client validation of specific numbers and content
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys
from datetime import datetime
from typing import Dict, List, Any

sys.path.append(str(Path(__file__).parent.parent))

from data_processors.snowflake_connector import query_to_dataframe, test_connection
from data_processors.demographic_processor import DemographicsProcessor
from data_processors.merchant_ranker import MerchantRanker
from data_processors.category_analyzer import CategoryAnalyzer
from utils.team_config_manager import TeamConfigManager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PresentationDataExporter:
    """Export only the data that will appear in the PowerPoint slides"""

    def __init__(self, team_key: str = 'utah_jazz'):
        self.team_key = team_key
        self.config_manager = TeamConfigManager()
        self.team_config = self.config_manager.get_team_config(team_key)
        self.view_prefix = self.team_config['view_prefix']
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Initialize processors
        self.merchant_ranker = MerchantRanker(team_view_prefix=self.view_prefix)
        self.category_analyzer = CategoryAnalyzer(
            team_name=self.team_config['team_name'],
            team_short=self.team_config['team_name_short'],
            league=self.team_config['league']
        )

    def export_presentation_data(self):
        """Export all presentation data to a single Excel file"""

        print("\n" + "=" * 80)
        print(f"POWERPOINT DATA EXPORT - {self.team_config['team_name']}")
        print("=" * 80)
        print("\nThis export contains ONLY the data that will appear in the presentation")

        # Test connection
        if not test_connection():
            print("❌ Failed to connect to Snowflake")
            return

        output_file = f"{self.team_key}_presentation_data_{self.timestamp}.xlsx"

        with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
            # 1. SLIDE 2: Demographics
            print("\n📊 Exporting Slide 2: Demographics...")
            self._export_demographics_slide_data(writer)

            # 2. SLIDE 3: Fan Behaviors
            print("\n🎯 Exporting Slide 3: Fan Behaviors...")
            self._export_behaviors_slide_data(writer)

            # 3. SLIDES 4-13: Categories (6 fixed + 4 custom)
            print("\n📦 Exporting Category Slides...")
            self._export_category_slides_data(writer)

            # 4. Add presentation overview
            self._add_presentation_overview(writer)

            # Format the workbook
            self._format_workbook(writer)

        print(f"\n✅ SUCCESS! Presentation data exported to: {output_file}")
        print("\nThe Excel file contains sheets for each slide with the exact data shown")

        return output_file

    def _export_demographics_slide_data(self, writer):
        """Export data for demographics slide"""

        # Load and process demographics
        demographics_view = self.config_manager.get_view_name(self.team_key, 'demographics')
        df = query_to_dataframe(f"SELECT * FROM {demographics_view}")

        processor = DemographicsProcessor(
            data_source=df,
            team_name=self.team_config['team_name'],
            league=self.team_config['league']
        )

        results = processor.process_all_demographics()

        # Create slide data sheet
        slide_data = []

        # Key insight
        slide_data.append({
            'Element': 'Key Insight',
            'Content': results['key_insights']
        })

        # Create individual sheets for each chart
        for demo_type, demo_info in results['demographics'].items():
            if demo_info['chart_type'] == 'grouped_bar':
                # Create DataFrame for bar charts
                chart_df = pd.DataFrame(demo_info['data'])
                sheet_name = f'Slide2_{demo_type}'
                chart_df.to_excel(writer, sheet_name=sheet_name, index=True)

                slide_data.append({
                    'Element': f'{demo_type.title()} Chart',
                    'Content': f'See sheet: {sheet_name}'
                })

            elif demo_info['chart_type'] == 'pie' and demo_type == 'gender':
                # Gender pie charts
                for community, values in demo_info['data'].items():
                    gender_df = pd.DataFrame(list(values.items()), columns=['Gender', 'Percentage'])
                    gender_df['Community'] = community
                    sheet_name = f'Slide2_gender_{community[:10]}'
                    gender_df.to_excel(writer, sheet_name=sheet_name, index=False)

        # Write slide summary
        pd.DataFrame(slide_data).to_excel(writer, sheet_name='Slide2_Demographics', index=False)
        print("   ✅ Demographics slide data exported")

    def _export_behaviors_slide_data(self, writer):
        """Export data for fan behaviors slide"""

        # 1. Fan Wheel Data (10 communities)
        wheel_data = self.merchant_ranker.get_fan_wheel_data(
            min_audience_pct=0.20,
            top_n_communities=10
        )

        wheel_data.to_excel(writer, sheet_name='Slide3_FanWheel', index=False)

        # 2. Community Index Chart Data
        communities_df = self.merchant_ranker.get_top_communities(
            min_audience_pct=0.20,
            top_n=10
        )

        # Format for chart
        chart_data = communities_df.rename(columns={
            'COMMUNITY': 'Community',
            'PERC_AUDIENCE': 'Audience_Pct',
            'COMPOSITE_INDEX': 'Composite_Index'
        })

        chart_data.to_excel(writer, sheet_name='Slide3_CommunityIndex', index=False)

        # 3. Insight text
        insight_df = pd.DataFrame({
            'Element': ['Fan Behavior Insight'],
            'Content': [self._generate_behavior_insight(wheel_data)]
        })

        insight_df.to_excel(writer, sheet_name='Slide3_Insights', index=False)

        print("   ✅ Fan behaviors slide data exported")

    def _export_category_slides_data(self, writer):
        """Export data for all category slides"""

        # Get all category data
        category_query = f"SELECT * FROM {self.view_prefix}_CATEGORY_INDEXING_ALL_TIME"
        all_category_df = query_to_dataframe(category_query)

        # Define fixed categories
        fixed_categories = ['restaurants', 'athleisure', 'finance', 'gambling', 'travel', 'auto']

        # Get custom categories
        custom_categories = self.category_analyzer.get_custom_categories(
            category_df=all_category_df,
            is_womens_team=False,
            existing_categories=fixed_categories
        )

        # Process each category (fixed + custom)
        slide_number = 4

        # Fixed categories
        for cat_key in fixed_categories:
            print(f"   - Processing {cat_key}...")
            self._export_single_category(writer, cat_key, slide_number, is_custom=False)
            slide_number += 1

        # Custom categories
        for custom_cat in custom_categories:
            cat_key = custom_cat['display_name']
            print(f"   - Processing {cat_key} [CUSTOM]...")
            self._export_single_category(writer, cat_key, slide_number, is_custom=True)
            slide_number += 1

        print(f"   ✅ Exported {slide_number - 4} category slides")

    def _export_single_category(self, writer, category_key: str, slide_num: int, is_custom: bool):
        """Export data for a single category slide"""

        # Load category data
        if is_custom:
            cat_config = self.category_analyzer.create_custom_category_config(category_key)
            cat_names = [category_key]
        else:
            cat_config = self.category_analyzer.categories.get(category_key, {})
            cat_names = cat_config.get('category_names_in_data', [])

        category_where = " OR ".join([f"TRIM(CATEGORY) = '{cat}'" for cat in cat_names])

        # Load data
        category_df = query_to_dataframe(f"""
            SELECT * FROM {self.view_prefix}_CATEGORY_INDEXING_ALL_TIME 
            WHERE {category_where}
        """)

        subcategory_df = query_to_dataframe(f"""
            SELECT * FROM {self.view_prefix}_SUBCATEGORY_INDEXING_ALL_TIME 
            WHERE {category_where}
        """)

        merchant_df = query_to_dataframe(f"""
            SELECT * FROM {self.view_prefix}_MERCHANT_INDEXING_ALL_TIME 
            WHERE {category_where}
            AND AUDIENCE = '{self.category_analyzer.audience_name}'
            ORDER BY PERC_AUDIENCE DESC
            LIMIT 1000
        """)

        # Temporarily add config for custom categories
        if is_custom:
            self.category_analyzer.categories[category_key] = cat_config

        # Analyze
        results = self.category_analyzer.analyze_category(
            category_key=category_key,
            category_df=category_df,
            subcategory_df=subcategory_df,
            merchant_df=merchant_df,
            validate=False
        )

        if is_custom:
            del self.category_analyzer.categories[category_key]

        # Export to sheets
        sheet_prefix = f'Slide{slide_num}_{category_key[:15]}'

        # 1. Category metrics
        metrics = results['category_metrics']
        metrics_df = pd.DataFrame({
            'Metric': [
                'Percent of Fans Who Spend',
                'How likely vs gen pop',
                'Purchases vs gen pop',
                'Composite Index',
                'Total Spend',
                'SPC'
            ],
            'Value': [
                metrics.format_percent_fans(),
                metrics.format_likelihood(),
                metrics.format_purchases(),
                f"{metrics.composite_index:.1f}",
                f"${metrics.total_spend:,.0f}",
                f"${metrics.spc:.2f}"
            ]
        })
        metrics_df.to_excel(writer, sheet_name=f'{sheet_prefix}_Metrics', index=False)

        # 2. Subcategory table
        if not results['subcategory_stats'].empty:
            results['subcategory_stats'].to_excel(
                writer,
                sheet_name=f'{sheet_prefix}_Subcats',
                index=False
            )

        # 3. Top 5 merchants
        merchant_df, _ = results['merchant_stats']
        if not merchant_df.empty:
            merchant_df.to_excel(
                writer,
                sheet_name=f'{sheet_prefix}_Merchants',
                index=False
            )

        # 4. Insights
        all_insights = results['insights'] + results['merchant_insights']
        if results['recommendation']:
            all_insights.append(f"Recommendation: Target {results['recommendation']['merchant']}")

        insights_df = pd.DataFrame({'Insights': all_insights})
        insights_df.to_excel(writer, sheet_name=f'{sheet_prefix}_Insights', index=False)

    def _add_presentation_overview(self, writer):
        """Add overview sheet with slide structure"""

        overview_data = [
            {'Slide': 1, 'Title': 'Title Slide',
             'Content': f'{self.team_config["team_name"]} Sponsorship Insights Report'},
            {'Slide': 2, 'Title': 'Fan Demographics',
             'Content': 'How Are Fans Unique - Age, Income, Occupation, Gender, Children'},
            {'Slide': 3, 'Title': 'Fan Behaviors', 'Content': 'Fan Wheel + Community Index Chart'},
        ]

        # Add category slides
        slide_num = 4
        for cat in ['Restaurants', 'Athleisure', 'Finance', 'Gambling', 'Travel', 'Auto']:
            overview_data.append({
                'Slide': slide_num,
                'Title': f'{cat} Analysis',
                'Content': 'Category metrics, subcategories, top 5 merchants'
            })
            slide_num += 1

        # Add custom categories
        for i in range(4):
            overview_data.append({
                'Slide': slide_num + i,
                'Title': f'Custom Category {i + 1}',
                'Content': 'Top category by composite index'
            })

        overview_df = pd.DataFrame(overview_data)
        overview_df.to_excel(writer, sheet_name='_Presentation_Overview', index=False)

    def _format_workbook(self, writer):
        """Apply formatting to the workbook"""
        workbook = writer.book

        # Define formats
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#4472C4',
            'font_color': 'white',
            'border': 1
        })

        percent_format = workbook.add_format({'num_format': '0.0%'})
        currency_format = workbook.add_format({'num_format': '$#,##0'})

        # Move overview sheet to first position
        worksheets = workbook.worksheets()
        for ws in worksheets:
            if ws.name == '_Presentation_Overview':
                workbook.worksheets_objs.remove(ws)
                workbook.worksheets_objs.insert(0, ws)

    def _generate_behavior_insight(self, wheel_data):
        """Generate the insight text for behaviors slide"""
        top_communities = wheel_data['COMMUNITY'].tolist()[:3]

        insights = []
        if 'Live Entertainment Seekers' in top_communities:
            insights.append('values-driven live entertainment seekers')
        if 'Cost Conscious' in top_communities:
            insights.append('on the lookout for a deal')
        if 'Movie Buffs' in top_communities:
            insights.append('a good movie')

        team_short = self.team_config['team_name_short']

        if len(insights) >= 3:
            return f"{team_short} fans are {insights[0]} who are {insights[1]} and {insights[2]}!"
        else:
            return f"{team_short} fans have unique behaviors that set them apart!"


def main():
    """Run the presentation data export"""
    import argparse

    parser = argparse.ArgumentParser(description='Export PowerPoint presentation data for validation')
    parser.add_argument('--team', type=str, default='utah_jazz',
                        choices=['utah_jazz', 'dallas_cowboys'],
                        help='Team to export data for')

    args = parser.parse_args()

    exporter = PresentationDataExporter(args.team)
    exporter.export_presentation_data()


if __name__ == "__main__":
    main()