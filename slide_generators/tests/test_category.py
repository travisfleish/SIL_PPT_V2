# test_logo_integration.py
"""
Test script to verify logo integration in category slides
Tests logo loading, fallback generation, and slide creation
"""

import os
import sys
from pathlib import Path
import logging
import pandas as pd
from pptx import Presentation
from PIL import Image
import shutil
from datetime import datetime

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import your modules
from slide_generators.category_slide import CategorySlide, create_category_slides
from utils.logo_manager import LogoManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_test_directories():
    """Create necessary directories for testing"""
    dirs = [
        'assets/logos/merchants',
        'test_output',
        'test_logos'
    ]
    for dir_path in dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        logger.info(f"Created directory: {dir_path}")


def create_sample_logos():
    """Create sample logo images for testing"""
    logo_dir = Path('assets/logos/merchants')

    # List of test brands with different naming conventions
    test_brands = [
        ('mcdonalds.png', 'McD', (255, 199, 0)),  # McDonald's yellow
        ('chick-fil-a.png', 'CFA', (221, 0, 49)),  # Chick-fil-A red
        ('wendys.png', 'W', (221, 0, 49)),  # Wendy's red
        ('taco_bell.png', 'TB', (112, 35, 131)),  # Taco Bell purple
        ('panda_express.png', 'PE', (194, 39, 45)),  # Panda Express red
    ]

    created_logos = []

    for filename, text, color in test_brands:
        logo_path = logo_dir / filename

        # Create a simple logo image
        img = Image.new('RGBA', (200, 200), (255, 255, 255, 255))
        from PIL import ImageDraw, ImageFont
        draw = ImageDraw.Draw(img)

        # Draw colored circle
        draw.ellipse([10, 10, 190, 190], fill=color, outline=(0, 0, 0))

        # Add text
        try:
            font = ImageFont.truetype("arial.ttf", 60)
        except:
            font = ImageFont.load_default()

        # Center text
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (200 - text_width) // 2
        y = (200 - text_height) // 2

        draw.text((x, y), text, fill=(255, 255, 255), font=font)

        # Save logo
        img.save(logo_path)
        created_logos.append(str(logo_path))
        logger.info(f"Created sample logo: {logo_path}")

    return created_logos


def test_logo_manager():
    """Test LogoManager functionality"""
    print("\n" + "="*50)
    print("TESTING LOGO MANAGER")
    print("="*50)

    logo_manager = LogoManager()

    # Test 1: List available logos
    print("\n1. Available logos:")
    available = logo_manager.list_available_logos()
    for logo in available:
        print(f"   - {logo}")

    # Test 2: Test logo loading with existing logo
    print("\n2. Testing logo loading:")
    test_cases = [
        "McDonald's",  # Should find mcdonalds.png
        "Chick-fil-A",  # Should find chick-fil-a.png
        "WENDYS",  # Should find wendys.png (case insensitive)
        "Taco Bell",  # Should find taco_bell.png
        "Burger King",  # Should NOT find - will create fallback
        "Subway"  # Should NOT find - will create fallback
    ]

    for brand in test_cases:
        logo = logo_manager.get_logo(brand)
        if logo:
            print(f"   ✓ {brand}: Logo loaded (size: {logo.size})")
        else:
            print(f"   ✗ {brand}: No logo found")

    # Test 3: Test fallback logo generation
    print("\n3. Testing fallback logo generation:")
    fallback_brands = ["Burger King", "Subway", "Pizza Hut"]

    for brand in fallback_brands:
        fallback = logo_manager.create_fallback_logo(brand)
        fallback_path = Path('test_output') / f'fallback_{brand.replace(" ", "_")}.png'
        fallback.save(fallback_path)
        print(f"   - Created fallback for {brand}: {fallback_path}")

    # Test 4: Test missing logos report
    print("\n4. Testing missing logos report:")
    all_brands = test_cases + ["Little Caesars", "Jimmy John's", "Domino's"]
    report = logo_manager.add_missing_logos_report(all_brands)

    print("   Logo availability:")
    for brand, has_logo in report.items():
        status = "✓" if has_logo else "✗"
        print(f"   {status} {brand}")

    return logo_manager


def create_test_analysis_results():
    """Create mock analysis results for testing"""

    # Create mock merchant data
    merchant_data = pd.DataFrame({
        'Rank': [1, 2, 3, 4, 5],
        'Brand': ["McDonald's", "Chick-fil-A", "Wendy's", "Taco Bell", "Panda Express"],
        'Percent of Fans Who Spend': ['92%', '79%', '77%', '68%', '56%'],
        'How likely fans are to spend vs. gen pop': ['35% More', '78% More', '55% More', '77% More', '64% More'],
        'Purchases Per Fan (vs. Gen Pop)': ['93% More', '80% More', '45% More', '60% More', '33% More'],
        'COMPOSITE_INDEX': [188, 158, 144, 137, 120]
    })

    # Create mock analysis results
    analysis_results = {
        'category_name': 'restaurants',
        'display_name': 'Restaurants',
        'slide_title': 'Sponsor Spending Analysis: Restaurants',
        'category_metrics': type('obj', (object,), {
            'format_percent_fans': lambda: '92%',
            'format_likelihood': lambda: '35% More',
            'format_purchases': lambda: '93% More'
        })(),
        'insights': [
            "92% of Utah Jazz fans spent at McDonald's",
            "Jazz fans make an average of 14 purchases per year at McDonald's—more than any other top Restaurants brand",
            "Utah Jazz fans spent an average of $546 per fan on McDonald's per year",
            "Utah Jazz fans are 158% more likely to spend on Panda Express than NBA Fans"
        ],
        'merchant_insights': [
            "92% of Utah Jazz fans spent at McDonald's",
            "Jazz fans make an average of 14 purchases per year at McDonald's",
            "Utah Jazz fans spent an average of $546 per fan on McDonald's per year",
            "Utah Jazz fans are 158% more likely to spend on Panda Express than NBA Fans"
        ],
        'subcategory_stats': pd.DataFrame({
            'Subcategory': ['Fast Food', 'Casual Dining', 'Coffee Shops'],
            'Percent of Fans Who Spend': ['92%', '85%', '78%'],
            'How likely fans are to spend vs. gen pop': ['35% More', '28% More', '22% More'],
            'Purchases per fan vs. gen pop': ['93% More', '75% More', '60% More']
        }),
        'merchant_stats': (merchant_data, merchant_data['Brand'].tolist()),
        'recommendation': {
            'merchant': "McDonald's",
            'composite_index': 188
        }
    }

    return analysis_results


def test_slide_generation():
    """Test actual slide generation with logos"""
    print("\n" + "="*50)
    print("TESTING SLIDE GENERATION")
    print("="*50)

    # Create team configuration
    team_config = {
        'team_name': 'Utah Jazz',
        'team_name_short': 'Jazz',
        'league': 'NBA',
        'primary_color': RGBColor(0, 43, 92),  # Jazz navy
        'secondary_color': RGBColor(249, 160, 27)  # Jazz gold
    }

    # Create analysis results
    analysis_results = create_test_analysis_results()

    # Initialize presentation
    presentation = Presentation()

    # Create CategorySlide instance
    slide_generator = CategorySlide(presentation)

    # Test missing logos report
    print("\n1. Checking for missing logos:")
    missing = slide_generator.check_missing_logos({'restaurants': analysis_results})
    if missing:
        for category, logos in missing.items():
            print(f"   Category '{category}' missing: {', '.join(logos)}")
    else:
        print("   All logos found!")

    # Generate category analysis slide
    print("\n2. Generating category analysis slide...")
    presentation = slide_generator.generate(analysis_results, team_config)
    print("   ✓ Category analysis slide created")

    # Generate brand slide with logos
    print("\n3. Generating brand slide with logos...")
    presentation = slide_generator.generate_brand_slide(analysis_results, team_config)
    print("   ✓ Brand slide with logos created")

    # Save presentation
    output_path = Path('test_output') / f'test_slides_with_logos_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pptx'
    presentation.save(output_path)
    print(f"\n4. Presentation saved to: {output_path}")

    return str(output_path)


def test_mixed_logos():
    """Test with mix of available and missing logos"""
    print("\n" + "="*50)
    print("TESTING MIXED LOGO SCENARIOS")
    print("="*50)

    # Create analysis with mix of brands (some with logos, some without)
    merchant_data = pd.DataFrame({
        'Rank': [1, 2, 3, 4, 5],
        'Brand': ["McDonald's", "Burger King", "Wendy's", "Subway", "Taco Bell"],
        'Percent of Fans Who Spend': ['92%', '79%', '77%', '68%', '56%'],
        'How likely fans are to spend vs. gen pop': ['35% More', '78% More', '55% More', '77% More', '64% More'],
        'Purchases Per Fan (vs. Gen Pop)': ['93% More', '80% More', '45% More', '60% More', '33% More'],
        'COMPOSITE_INDEX': [188, 158, 144, 137, 120]
    })

    analysis_results = create_test_analysis_results()
    analysis_results['merchant_stats'] = (merchant_data, merchant_data['Brand'].tolist())
    analysis_results['display_name'] = 'QSR'  # Test QSR special formatting

    team_config = {
        'team_name': 'Dallas Cowboys',
        'team_name_short': 'Cowboys',
        'league': 'NFL'
    }

    # Generate slides
    presentation = Presentation()
    slide_generator = CategorySlide(presentation)

    print("\n1. Brand logo status:")
    logo_manager = slide_generator.logo_manager
    for brand in merchant_data['Brand']:
        logo = logo_manager.get_logo(brand)
        status = "Found" if logo else "Will use fallback"
        print(f"   - {brand}: {status}")

    print("\n2. Generating slides with mixed logos...")
    presentation = slide_generator.generate(analysis_results, team_config)
    presentation = slide_generator.generate_brand_slide(analysis_results, team_config)

    output_path = Path('test_output') / 'test_mixed_logos.pptx'
    presentation.save(output_path)
    print(f"\n3. Mixed logo presentation saved to: {output_path}")


def cleanup_test_files(keep_outputs=True):
    """Clean up test files"""
    print("\n" + "="*50)
    print("CLEANUP")
    print("="*50)

    if not keep_outputs:
        # Remove test outputs
        if Path('test_output').exists():
            shutil.rmtree('test_output')
            print("   - Removed test_output directory")

    # Always remove test logos (keep actual logos)
    test_logo_dir = Path('test_logos')
    if test_logo_dir.exists():
        shutil.rmtree(test_logo_dir)
        print("   - Removed test_logos directory")


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("SPORTS INNOVATION LAB - LOGO INTEGRATION TEST SUITE")
    print("="*70)

    try:
        # Setup
        create_test_directories()
        created_logos = create_sample_logos()

        # Run tests
        logo_manager = test_logo_manager()
        output_path = test_slide_generation()
        test_mixed_logos()

        # Summary
        print("\n" + "="*50)
        print("TEST SUMMARY")
        print("="*50)
        print(f"✓ Created {len(created_logos)} sample logos")
        print(f"✓ Logo Manager tested successfully")
        print(f"✓ Slides generated with logos")
        print(f"✓ Mixed logo scenarios handled")
        print(f"\nCheck the generated PowerPoint files in: test_output/")
        print("\nTo add real logos:")
        print("1. Add logo files to: assets/logos/merchants/")
        print("2. Use filenames like: mcdonalds.png, burger_king.png, etc.")
        print("3. Supported formats: .png, .jpg, .jpeg, .gif, .bmp")

    except Exception as e:
        logger.error(f"Test failed: {str(e)}", exc_info=True)
        raise
    finally:
        # Cleanup (keep outputs for inspection)
        cleanup_test_files(keep_outputs=True)


if __name__ == "__main__":
    # For missing RGBColor import in test
    from pptx.dml.color import RGBColor

    main()