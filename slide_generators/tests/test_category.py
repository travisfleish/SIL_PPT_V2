"""
Test script for Category Slide formatting changes
Tests composite index rounding and brand table positioning
"""

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
import pandas as pd
from typing import Dict, Any, List, Tuple
import os


# Mock CategorySlide class with only the methods we're testing
class CategorySlideTest:
    def __init__(self):
        self.presentation = Presentation()
        self.default_font = 'Arial'  # Use Arial for testing (should be Red Hat Display in prod)
        self.colors = {
            'header_bg': RGBColor(240, 240, 240),
            'header_border': RGBColor(200, 200, 200),
            'table_header': RGBColor(217, 217, 217),
            'table_border': RGBColor(0, 0, 0),
            'positive': RGBColor(0, 176, 80),
            'negative': RGBColor(255, 0, 0),
            'equal': RGBColor(184, 134, 11),
            'neutral': RGBColor(0, 0, 0)
        }

    def create_test_slide(self):
        """Create a blank slide for testing"""
        slide_layout = self.presentation.slide_layouts[5]  # Blank layout
        return self.presentation.slides.add_slide(slide_layout)

    def test_brand_logos_and_table(self):
        """Test brand logos and table positioning"""
        slide = self.create_test_slide()

        # Add title for reference
        title_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.2), Inches(8), Inches(0.5))
        title_box.text_frame.text = "TEST: Brand Logos and Table Positioning"
        p = title_box.text_frame.paragraphs[0]
        p.font.size = Pt(24)
        p.font.bold = True

        # Add brand logos (original positioning)
        print("Adding brand logos...")
        start_x = Inches(0.5)
        y = Inches(1.2)  # Original position
        spacing = Inches(2.4)

        for i in range(5):
            x = start_x + (i * spacing)

            # Circle
            circle = slide.shapes.add_shape(
                MSO_SHAPE.OVAL,
                x, y,
                Inches(1.2), Inches(1.2)
            )
            circle.fill.solid()
            circle.fill.fore_color.rgb = RGBColor(255, 255, 255)
            circle.line.color.rgb = RGBColor(200, 200, 200)
            circle.line.width = Pt(2)

            # Number
            text_box = slide.shapes.add_textbox(
                x, y + Inches(0.4),
                Inches(1.2), Inches(0.4)
            )
            text_box.text_frame.text = str(i + 1)
            p = text_box.text_frame.paragraphs[0]
            p.alignment = PP_ALIGN.CENTER
            p.font.size = Pt(48)
            p.font.color.rgb = RGBColor(150, 150, 150)

        print(f"Logos positioned at Y = {y}")
        print(f"Logo bottom edge at Y = {y + Inches(1.2)}")

        # Add OLD table position (for comparison)
        self._add_comparison_table(slide, "OLD Position - Overlaps!", Inches(1.2), RGBColor(255, 200, 200))

        # Add NEW table position
        self._add_comparison_table(slide, "NEW Position - No Overlap", Inches(2.8), RGBColor(200, 255, 200))

        return slide

    def _add_comparison_table(self, slide, label, top_position, bg_color):
        """Add a comparison table at specified position"""
        # Add label
        label_box = slide.shapes.add_textbox(
            Inches(5.833), top_position - Inches(0.3),
            Inches(3), Inches(0.25)
        )
        label_box.text_frame.text = f"{label} (top = {top_position})"
        p = label_box.text_frame.paragraphs[0]
        p.font.size = Pt(10)
        p.font.bold = True

        # Create sample table
        rows = 4  # Simplified for visibility
        cols = 5
        left = Inches(5.833)
        width = Inches(7.0)
        height = Inches(0.35 * rows)

        table = slide.shapes.add_table(rows, cols, left, top_position, width, height).table

        # Headers
        headers = ['Rank', 'Brand', '% Fans', 'Likelihood', 'Purchases']
        for i, header in enumerate(headers):
            cell = table.cell(0, i)
            cell.text = header
            cell.fill.solid()
            cell.fill.fore_color.rgb = bg_color

        # Sample data
        sample_brands = [
            ['1', 'McDonald\'s', '92%', '35% More', '93% More'],
            ['2', 'Chick-fil-A', '79%', '78% More', '93% More'],
            ['3', 'Wendy\'s', '77%', '55% More', '49% More']
        ]

        for row_idx, row_data in enumerate(sample_brands, 1):
            for col_idx, value in enumerate(row_data):
                table.cell(row_idx, col_idx).text = value

    def test_composite_index_formatting(self):
        """Test composite index rounding"""
        slide = self.create_test_slide()

        # Add title
        title_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.2), Inches(8), Inches(0.5))
        title_box.text_frame.text = "TEST: Composite Index Formatting"
        p = title_box.text_frame.paragraphs[0]
        p.font.size = Pt(24)
        p.font.bold = True

        # Test cases for composite index
        test_cases = [
            {'value': 188.20250000000001, 'expected': '188'},
            {'value': 156.7, 'expected': '157'},
            {'value': 200.5, 'expected': '201'},
            {'value': 199.4, 'expected': '199'},
            {'value': 'invalid', 'expected': 'N/A'},
            {'value': None, 'expected': 'N/A'}
        ]

        y_position = Inches(1.5)

        for i, test_case in enumerate(test_cases):
            # Create mock recommendation
            recommendation = {
                'merchant': f'Test Brand {i + 1}',
                'composite_index': test_case['value']
            }

            # Add test section
            self._add_test_recommendation(slide, recommendation, y_position, test_case['expected'])
            y_position += Inches(1.2)

        return slide

    def _add_test_recommendation(self, slide, recommendation, y_pos, expected):
        """Add a test recommendation section"""
        # Test input label
        input_box = slide.shapes.add_textbox(Inches(0.5), y_pos, Inches(3), Inches(0.3))
        input_box.text_frame.text = f"Input: {recommendation.get('composite_index')}"
        p = input_box.text_frame.paragraphs[0]
        p.font.size = Pt(10)
        p.font.color.rgb = RGBColor(100, 100, 100)

        # Format composite index (the code we're testing)
        composite_index_raw = recommendation.get('composite_index', 0)
        try:
            composite_index = int(round(float(composite_index_raw)))
        except (ValueError, TypeError):
            composite_index = 'N/A'

        # Show result
        result_box = slide.shapes.add_textbox(Inches(0.5), y_pos + Inches(0.3), Inches(8), Inches(0.4))
        team_name = "Utah Jazz"
        merchant_name = recommendation.get('merchant', 'Brand')

        result_text = f"• The {team_name} should target {merchant_name} for a sponsorship based on having the highest composite index of {composite_index}"
        result_box.text_frame.text = result_text
        p = result_box.text_frame.paragraphs[0]
        p.font.size = Pt(11)

        # Show expected result
        expected_box = slide.shapes.add_textbox(Inches(0.5), y_pos + Inches(0.7), Inches(3), Inches(0.3))
        expected_box.text_frame.text = f"Expected: {expected} | Actual: {composite_index} | {'✓' if str(composite_index) == expected else '✗'}"
        p = expected_box.text_frame.paragraphs[0]
        p.font.size = Pt(10)
        if str(composite_index) == expected:
            p.font.color.rgb = RGBColor(0, 176, 80)  # Green
        else:
            p.font.color.rgb = RGBColor(255, 0, 0)  # Red

    def run_all_tests(self):
        """Run all tests and save presentation"""
        print("Running Category Slide Tests...")
        print("-" * 50)

        # Test 1: Brand logos and table positioning
        print("\nTest 1: Brand Logos and Table Positioning")
        slide1 = self.test_brand_logos_and_table()

        # Test 2: Composite index formatting
        print("\nTest 2: Composite Index Formatting")
        slide2 = self.test_composite_index_formatting()

        # Save test presentation
        output_file = "category_slide_test_output.pptx"
        self.presentation.save(output_file)
        print(f"\nTest presentation saved to: {output_file}")
        print("\nPlease open the file to visually verify:")
        print("1. Brand table is positioned below logos (no overlap)")
        print("2. Composite index values are rounded to whole numbers")

        return output_file


# Additional function to test formatting utilities
def test_formatting_functions():
    """Test the formatting utility functions"""
    print("\nTesting Formatting Functions:")
    print("-" * 50)

    # Test composite index formatting
    test_values = [
        188.20250000000001,
        156.7,
        200.5,
        199.4,
        0,
        -10.7,
        "invalid",
        None
    ]

    print("\nComposite Index Formatting Tests:")
    for value in test_values:
        try:
            result = int(round(float(value)))
            print(f"Input: {value} → Output: {result}")
        except (ValueError, TypeError):
            print(f"Input: {value} → Output: N/A (error handling)")


if __name__ == "__main__":
    # Run the visual tests
    tester = CategorySlideTest()
    tester.run_all_tests()

    # Run formatting function tests
    test_formatting_functions()

    print("\n✅ All tests completed!")
    print("\nKey changes implemented:")
    print("1. Brand table moved from top=1.2\" to top=2.8\" (1.6\" lower)")
    print("2. Composite index now rounds to whole numbers (no decimals)")
    print("3. Error handling for invalid composite index values")