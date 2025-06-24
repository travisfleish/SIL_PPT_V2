# slide_generators/tests/test_category_slide.py
"""
Test script for category slide generation
Generates sample category slides using real data
"""

import sys
from pathlib import Path

# Add parent directories to path
sys.path.append(str(Path(__file__).parent.parent))
sys.path.append(str(Path(__file__).parent.parent.parent))

from pptx import Presentation
from slide_generators.category_slide import CategorySlide, create_category_slides
from data_processors.category_analyzer import CategoryAnalyzer
from data_processors.snowflake_connector import query_to_dataframe, test_connection
from utils.team_config_manager import TeamConfigManager
import logging

logging.basicConfig(level=logging.INFO)


def test_category_slide_with_real_data(team_key: str = 'utah_jazz',
                                       category_key: str = 'restaurants'):
    """
    Test category slide generation with real Snowflake data

    Args:
        team_key: Team identifier
        category_key: Category to test (e.g., 'restaurants', 'auto')
    """
    print(f"\n{'=' * 60}")
    print(f"CATEGORY SLIDE TEST - {team_key} - {category_key}")
    print(f"{'=' * 60}")

    try:
        # 1. Test connection
        print("\n1. Testing Snowflake connection...")
        if not test_connection():
            print("❌ Failed to connect to Snowflake")
            return None
        print("✅ Connected to Snowflake")

        # 2. Get team configuration
        print("\n2. Loading team configuration...")
        config_manager = TeamConfigManager()
        team_config = config_manager.get_team_config(team_key)
        view_prefix = team_config['view_prefix']
        print(f"✅ Team: {team_config['team_name']}")

        # 3. Initialize category analyzer
        print("\n3. Initializing category analyzer...")
        analyzer = CategoryAnalyzer(
            team_name=team_config['team_name'],
            team_short=team_config['team_name_short'],
            league=team_config['league']
        )

        # 4. Load category data
        print(f"\n4. Loading {category_key} data from Snowflake...")

        # Get category configuration
        cat_config = analyzer.categories.get(category_key, {})
        cat_names = cat_config.get('category_names_in_data', [])

        if not cat_names:
            print(f"❌ No category configuration found for {category_key}")
            return None

        # Build WHERE clause
        category_where = " OR ".join([f"TRIM(CATEGORY) = '{cat}'" for cat in cat_names])

        # Load data
        category_df = query_to_dataframe(f"""
            SELECT * FROM {view_prefix}_CATEGORY_INDEXING_ALL_TIME 
            WHERE {category_where}
        """)

        subcategory_df = query_to_dataframe(f"""
            SELECT * FROM {view_prefix}_SUBCATEGORY_INDEXING_ALL_TIME 
            WHERE {category_where}
        """)

        merchant_df = query_to_dataframe(f"""
            SELECT * FROM {view_prefix}_MERCHANT_INDEXING_ALL_TIME 
            WHERE {category_where}
            AND AUDIENCE = '{analyzer.audience_name}'
            ORDER BY PERC_AUDIENCE DESC
            LIMIT 100
        """)

        print(f"✅ Loaded data:")
        print(f"   - Category: {len(category_df)} rows")
        print(f"   - Subcategory: {len(subcategory_df)} rows")
        print(f"   - Merchant: {len(merchant_df)} rows")

        # 5. Run analysis
        print(f"\n5. Analyzing {category_key}...")
        results = analyzer.analyze_category(
            category_key=category_key,
            category_df=category_df,
            subcategory_df=subcategory_df,
            merchant_df=merchant_df,
            validate=False
        )

        print("✅ Analysis completed")

        # Display some results
        metrics = results['category_metrics']
        print(f"\nCategory Metrics:")
        print(f"  - {metrics.format_percent_fans()} of fans spend")
        print(f"  - {metrics.format_likelihood()} likely vs gen pop")
        print(f"  - {metrics.format_purchases()} purchases vs gen pop")

        # 6. Create PowerPoint slides
        print(f"\n6. Generating PowerPoint slides...")
        presentation = create_category_slides(results, team_config)

        # 7. Save presentation
        output_path = Path(f"{team_key}_{category_key}_slides.pptx")
        presentation.save(str(output_path))

        print(f"\n✅ SUCCESS! Slides saved to: {output_path.absolute()}")
        print(f"\nPresentation contains:")
        print(f"  • Slide 1: {category_key.title()} category analysis")
        print(f"  • Slide 2: {category_key.title()} brand analysis")

        return output_path

    except Exception as e:
        print(f"\n❌ ERROR: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def test_with_mock_data():
    """Test category slide with mock data for quick validation"""

    print("\n" + "=" * 60)
    print("CATEGORY SLIDE TEST - MOCK DATA")
    print("=" * 60)

    # Create mock analysis results
    import pandas as pd
    from data_processors.category_analyzer import CategoryMetrics

    mock_results = {
        'category_key': 'restaurants',
        'display_name': 'Restaurants',
        'slide_title': 'Restaurant Sponsor Analysis',
        'category_metrics': CategoryMetrics(
            percent_fans=0.99,
            percent_likely=22,
            percent_purchases=150,
            composite_index=287,
            total_spend=1500000,
            spc=3311.45,
            audience_count=45000,
            comparison_population="Local Gen Pop (Excl. Jazz)"
        ),
        'subcategory_stats': pd.DataFrame([
            {
                'Subcategory': 'QSR & Fast Casual',
                'Percent of Fans Who Spend': '99%',
                'How likely fans are to spend vs. gen pop': '25% More',
                'Purchases per fan vs. gen pop': '140% More'
            },
            {
                'Subcategory': 'Casual',
                'Percent of Fans Who Spend': '76%',
                'How likely fans are to spend vs. gen pop': '82% More',
                'Purchases per fan vs. gen pop': '68% More'
            },
            {
                'Subcategory': 'Online Delivery',
                'Percent of Fans Who Spend': '45%',
                'How likely fans are to spend vs. gen pop': '130% More',
                'Purchases per fan vs. gen pop': '14% More'
            },
            {
                'Subcategory': 'Fine Dining',
                'Percent of Fans Who Spend': '5.7%',
                'How likely fans are to spend vs. gen pop': '330% More',
                'Purchases per fan vs. gen pop': '37% More'
            }
        ]),
        'insights': [
            "Jazz Fans are 22% MORE likely to spend on Restaurants than the Local Gen Pop (Excl. Jazz)",
            "Jazz Fans make an average of 150% more purchases per fan on Restaurants than the Local Gen Pop (Excl. Jazz)",
            "Jazz Fans are more than 3X more likely to spend on Fine Dining Restaurants vs. the Local Gen Pop (Excl. Jazz)",
            "Jazz fans spend an average of $487.29 per fan per year on QSR and Fast Casual Restaurants"
        ],
        'merchant_stats': (
            pd.DataFrame([
                {
                    'Rank': 1,
                    'Brand': "MCDONALD'S",
                    'Percent of Fans Who Spend': '92%',
                    'How likely fans are to spend vs. gen pop': '35% More',
                    'Purchases Per Fan (vs. Gen Pop)': '93% More'
                },
                {
                    'Rank': 2,
                    'Brand': 'CHICK-FIL-A',
                    'Percent of Fans Who Spend': '79%',
                    'How likely fans are to spend vs. gen pop': '78% More',
                    'Purchases Per Fan (vs. Gen Pop)': '93% More'
                },
                {
                    'Rank': 3,
                    'Brand': "WENDY'S",
                    'Percent of Fans Who Spend': '77%',
                    'How likely fans are to spend vs. gen pop': '55% More',
                    'Purchases Per Fan (vs. Gen Pop)': '49% More'
                },
                {
                    'Rank': 4,
                    'Brand': 'TACO BELL',
                    'Percent of Fans Who Spend': '68%',
                    'How likely fans are to spend vs. gen pop': '77% More',
                    'Purchases Per Fan (vs. Gen Pop)': '60% More'
                },
                {
                    'Rank': 5,
                    'Brand': 'PANDA EXPRESS',
                    'Percent of Fans Who Spend': '56%',
                    'How likely fans are to spend vs. gen pop': '64% More',
                    'Purchases Per Fan (vs. Gen Pop)': '33% More'
                }
            ]),
            ["MCDONALD'S", "CHICK-FIL-A", "WENDY'S", "TACO BELL", "PANDA EXPRESS"]
        ),
        'merchant_insights': [
            "92% of Utah Jazz fans spent at MCDONALD'S",
            "Utah Jazz fans average 14 purchases per year per fan at MCDONALD'S",
            "Utah Jazz fans spent an average of $160 per fan on WENDY'S per year",
            "Utah Jazz fans are 58% more likely to spend on PANDA EXPRESS than NBA Fans."
        ],
        'recommendation': {
            'merchant': 'CHICK-FIL-A',
            'composite_index': 385.2,
            'explanation': "Fans are more likely to spend with CHICK-FIL-A and more likely to spend MORE per consumer vs. the Local Gen Pop (Excl. Jazz) on CHICK-FIL-A"
        }
    }

    # Mock team config
    team_config = {
        'team_name': 'Utah Jazz',
        'team_name_short': 'Jazz',
        'league': 'NBA',
        'colors': {
            'primary': '#002B5C',
            'secondary': '#F9A01B',
            'accent': '#00471B'
        }
    }

    # Generate slides
    print("\nGenerating slides with mock data...")
    presentation = create_category_slides(mock_results, team_config)

    # Save
    output_path = Path('mock_category_slides.pptx')
    presentation.save(str(output_path))

    print(f"\n✅ Mock slides saved to: {output_path}")

    return output_path


def test_multiple_categories(team_key: str = 'utah_jazz'):
    """Test generating slides for multiple categories"""

    print("\n" + "=" * 60)
    print("MULTIPLE CATEGORY SLIDES TEST")
    print("=" * 60)

    categories = ['restaurants', 'auto', 'athleisure', 'finance']

    # Create new presentation
    presentation = Presentation()

    # Add title slide
    slide = presentation.slides.add_slide(presentation.slide_layouts[5])
    title_box = slide.shapes.add_textbox(
        Path.inches(2), Path.inches(3),
        Path.inches(6), Path.inches(1)
    )
    title_box.text = f"{team_key.replace('_', ' ').title()} Category Analysis"

    successful = []

    for category in categories:
        print(f"\n📊 Processing {category}...")
        try:
            # Get team config
            config_manager = TeamConfigManager()
            team_config = config_manager.get_team_config(team_key)

            # Run analysis and generate slides...
            # (Similar to test_category_slide_with_real_data but appending to existing presentation)

            successful.append(category)
            print(f"✅ Added {category} slides")

        except Exception as e:
            print(f"❌ Failed to process {category}: {str(e)}")

    if successful:
        output_path = Path(f"{team_key}_all_categories.pptx")
        presentation.save(str(output_path))
        print(f"\n✅ Created presentation with {len(successful)} categories: {output_path}")

    return successful


def main():
    """Main test function"""
    print("\n🎯 CATEGORY SLIDE GENERATOR TEST")
    print("This will create PowerPoint slides from category analysis data")

    # First test with mock data
    print("\nStep 1: Testing with mock data...")
    mock_result = test_with_mock_data()

    if mock_result:
        print("\n✅ Mock test successful!")

        # Then test with real data
        user_input = input("\n\nTest with real Snowflake data? (y/n): ")
        if user_input.lower() == 'y':

            # Test single category
            category = input("Which category to test? (restaurants/auto/athleisure/finance): ").lower()
            if category in ['restaurants', 'auto', 'athleisure', 'finance']:
                test_category_slide_with_real_data('utah_jazz', category)
            else:
                print("Invalid category. Testing with restaurants...")
                test_category_slide_with_real_data('utah_jazz', 'restaurants')

            # Test multiple categories
            user_input = input("\n\nAlso test multiple categories? (y/n): ")
            if user_input.lower() == 'y':
                test_multiple_categories('utah_jazz')

    print("\n✨ Test complete!")


if __name__ == "__main__":
    main()