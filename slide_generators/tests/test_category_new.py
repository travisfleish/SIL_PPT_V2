"""
Test script for category slide generation with mock data
Allows experimentation with formatting without needing database connection
"""

import sys
import os
from pathlib import Path
import pandas as pd
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add project root to path so we can import our modules
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Mock the imports we need
class MockCategoryMetrics:
    """Mock CategoryMetrics class to avoid importing the real one"""
    def __init__(self, percent_audience, percent_index, composite_index, spc, ppc):
        self.percent_audience = percent_audience
        self.percent_index = percent_index
        self.composite_index = composite_index
        self.spc = spc
        self.ppc = ppc

    def format_percent_fans(self):
        return f"{self.percent_audience:.1f}%"

    def format_likelihood(self):
        if self.percent_index > 0:
            return f"{int(self.percent_index)}% More likely"
        elif self.percent_index < 0:
            return f"{abs(int(self.percent_index))}% Less likely"
        else:
            return "EQUAL"

    def format_purchases(self):
        if self.ppc > 0:
            return f"{int(self.ppc)}% More purchases"
        elif self.ppc < 0:
            return f"{abs(int(self.ppc))}% Fewer purchases"
        else:
            return "EQUAL"

class MockBaseSlide:
    """Mock BaseSlide class"""
    def __init__(self, presentation=None):
        self.presentation = presentation or Presentation()
        self.default_font = 'Red Hat Display'

    def add_content_slide(self):
        """Add a blank slide"""
        # Use layout 6 which is typically blank
        slide_layout = self.presentation.slide_layouts[6]
        return self.presentation.slides.add_slide(slide_layout)

# Now we can include the actual CategorySlide code
# Copy the entire CategorySlide class from your file here
# (I'll include a simplified version that maintains all the key functionality)

# First, copy all the utility functions from the original file
def format_percentage_no_decimal(value):
    """Format percentage without decimals, handle 0% as EQUAL"""
    if isinstance(value, str):
        try:
            num = float(value.replace('%', '').strip())
        except:
            return value
    else:
        num = float(value)

    if num == 0:
        return "EQUAL"

    return f"{int(round(num))}%"

def format_percent_of_fans(value):
    """Format 'Percent of Fans Who Spend' column with <5% for small values"""
    if isinstance(value, str):
        try:
            num = float(value.replace('%', '').strip())
        except:
            return value
    else:
        num = float(value)

    if num < 5:
        return "<5%"

    return f"{int(round(num))}%"

def format_currency_no_cents(value):
    """Format currency without cents and with commas"""
    if isinstance(value, str):
        try:
            num = float(value.replace('$', '').replace(',', '').strip())
        except:
            return value
    else:
        num = float(value)

    return f"${int(round(num)):,}"

# Import your CategorySlide class here (you'll need to copy the entire class)
# For this example, I'll create a minimal version that focuses on the key elements

from pptx.enum.text import PP_ALIGN, MSO_ANCHOR, MSO_AUTO_SIZE
from pptx.enum.shapes import MSO_SHAPE

class CategorySlide(MockBaseSlide):
    """Simplified CategorySlide for testing"""

    def __init__(self, presentation=None):
        super().__init__(presentation)

        # Mock LogoManager
        self.logo_manager = None

        # Colors for the slide
        self.colors = {
            'header_bg': RGBColor(240, 240, 240),
            'header_border': RGBColor(200, 200, 200),
            'table_header': RGBColor(0, 0, 0),
            'table_border': RGBColor(0, 0, 0),
            'positive': RGBColor(0, 176, 80),
            'negative': RGBColor(255, 0, 0),
            'equal': RGBColor(184, 134, 11),
            'neutral': RGBColor(0, 0, 0),
            'emerging_bg': RGBColor(217, 217, 217)
        }

    def generate(self, analysis_results, team_config, slide_index=None):
        """Generate the complete category analysis slide"""
        # Extract team info
        team_name = team_config.get('team_name', 'Team')
        team_short = team_config.get('team_name_short', team_name.split()[-1])

        # Check if this is an emerging category
        is_emerging = analysis_results.get('is_emerging', False)

        # Use the content layout
        slide = self.add_content_slide()
        logger.info(f"Added category slide for {analysis_results['display_name']}")

        # Add header
        self._add_header(slide, team_name, analysis_results['slide_title'])

        # Add title
        if is_emerging:
            self._add_emerging_category_title(slide, analysis_results['display_name'])
        else:
            category_title = f"Category Analysis: {analysis_results['display_name']}"
            self._add_title(slide, category_title)

        # Add category insights
        self._add_category_insights(slide, analysis_results, team_short, team_config, is_emerging=is_emerging)

        # Add category metrics table
        self._add_category_table(slide, analysis_results)

        # Add subcategory table
        self._add_subcategory_table(slide, analysis_results['subcategory_stats'])

        return self.presentation

    def generate_brand_slide(self, analysis_results, team_config, slide_index=None):
        """Generate the brand analysis slide (second slide for category)"""
        # Extract team info
        team_name = team_config.get('team_name', 'Team')
        team_short = team_config.get('team_name_short', team_name.split()[-1])
        category_name = analysis_results['display_name']

        # Use the content layout
        slide = self.add_content_slide()
        logger.info(f"Added brand slide for {analysis_results['display_name']}")

        # Brand slide title format
        if category_name.upper() == "QSR":
            brand_title = f"Top QSR Brands for {team_name} Fans"
        else:
            brand_title = f"Top {category_name} Brands for {team_name} Fans"

        # Add header
        header_title = f"Sponsor Spending Analysis: {category_name} Brands"
        self._add_header(slide, team_name, header_title)

        # Add title
        self._add_title(slide, brand_title)

        # Add brand logos (numbered circles)
        self._add_brand_logos(slide, analysis_results['merchant_stats'])

        # Add brand insights (left side)
        self._add_brand_insights(slide, analysis_results, team_name, team_short, category_name)

        # Add brand table (right side)
        self._add_brand_table(slide, analysis_results['merchant_stats'])

        # Add sponsorship recommendation
        self._add_sponsor_recommendation(slide, analysis_results['recommendation'], team_config)

        return self.presentation

    def _add_header(self, slide, team_name, slide_title):
        """Add header with team name and slide title"""
        # Header background
        header_rect = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE,
            Inches(0), Inches(0),
            Inches(13.333), Inches(0.5)
        )
        header_rect.fill.solid()
        header_rect.fill.fore_color.rgb = self.colors['header_bg']
        header_rect.line.color.rgb = self.colors['header_border']
        header_rect.line.width = Pt(0.5)

        # Team name (left)
        team_text = slide.shapes.add_textbox(
            Inches(0.2), Inches(0.1),
            Inches(3), Inches(0.3)
        )
        team_text.text_frame.text = team_name
        p = team_text.text_frame.paragraphs[0]
        p.font.name = self.default_font
        p.font.size = Pt(14)
        p.font.bold = True

        # Slide indicator (right)
        slide_text = slide.shapes.add_textbox(
            Inches(6.5), Inches(0.1),
            Inches(6.633), Inches(0.3)
        )
        slide_text.text_frame.text = slide_title
        p = slide_text.text_frame.paragraphs[0]
        p.font.name = self.default_font
        p.alignment = PP_ALIGN.RIGHT
        p.font.size = Pt(14)

    def _add_title(self, slide, title):
        """Add main slide title"""
        width = Inches(5.3)

        title_box = slide.shapes.add_textbox(
            Inches(0.6), Inches(1.2),  # Y position you can adjust
            width, Inches(1.8)
        )

        text_frame = title_box.text_frame
        text_frame.word_wrap = True
        text_frame.auto_size = MSO_AUTO_SIZE.NONE

        # Remove margins
        text_frame.margin_left = Inches(0)
        text_frame.margin_right = Inches(0)
        text_frame.margin_top = Inches(0)
        text_frame.margin_bottom = Inches(0)

        # Split title for category slides
        if "Category Analysis:" in title:
            category_name = title.replace("Category Analysis: ", "")
            text_frame.text = f"Category Analysis:\n{category_name}"
        else:
            text_frame.text = title

        # Format all paragraphs
        for paragraph in text_frame.paragraphs:
            for run in paragraph.runs:
                run.font.name = "Red Hat Display"
                run.font.size = Pt(24)  # Font size you can adjust
                run.font.bold = True
                run.font.italic = True
                run.font.color.rgb = RGBColor(0, 0, 0)
            paragraph.line_spacing = 1.0

    def _add_emerging_category_title(self, slide, category_name):
        """Add special title formatting for emerging categories"""
        # Main title: "Emerging Category:"
        title_box = slide.shapes.add_textbox(
            Inches(0.6), Inches(1.2),
            Inches(5.3), Inches(0.5)
        )

        text_frame = title_box.text_frame
        text_frame.text = "Emerging Category:"

        p = text_frame.paragraphs[0]
        p.font.name = "Red Hat Display"
        p.font.size = Pt(24)
        p.font.bold = True
        p.font.italic = True
        p.font.color.rgb = RGBColor(0, 0, 0)

        # Category name on second line
        category_box = slide.shapes.add_textbox(
            Inches(0.6), Inches(1.8),
            Inches(5.3), Inches(0.6)
        )

        text_frame = category_box.text_frame
        text_frame.text = category_name

        p = text_frame.paragraphs[0]
        p.font.name = "Red Hat Display"
        p.font.size = Pt(24)
        p.font.bold = True
        p.font.italic = True
        p.font.color.rgb = RGBColor(0, 0, 0)

        # Explanatory subtext
        subtext_box = slide.shapes.add_textbox(
            Inches(0.6), Inches(2.4),
            Inches(5.3), Inches(0.6)
        )

        text_frame = subtext_box.text_frame
        text_frame.word_wrap = True
        text_frame.text = (
            "The Emerging Category is where at least 10% of your fans are "
            "spending, but where there isn't one clear brand leader, and the "
            "category has room to grow"
        )

        p = text_frame.paragraphs[0]
        p.font.name = "Red Hat Display"
        p.font.size = Pt(12)
        p.font.italic = True
        p.font.color.rgb = RGBColor(0, 0, 0)

    def _add_category_insights(self, slide, results, team_short, team_config, is_emerging=False):
        """Add category insights section"""
        # Adjust vertical position based on whether it's an emerging category
        title_y = Inches(3.2) if is_emerging else Inches(2.4)
        insights_y = Inches(3.6) if is_emerging else Inches(2.8)
        nba_label_y = Inches(5.8) if is_emerging else Inches(5.4)
        nba_box_y = Inches(6.2) if is_emerging else Inches(5.8)

        # Insights title
        insights_title = slide.shapes.add_textbox(
            Inches(0.5), title_y,
            Inches(4), Inches(0.3)
        )
        insights_title.text_frame.text = "Category Insights:"
        p = insights_title.text_frame.paragraphs[0]
        p.font.name = self.default_font
        p.font.size = Pt(14)
        p.font.bold = True

        # Regular insights box
        insights_box = slide.shapes.add_textbox(
            Inches(0.7), insights_y,
            Inches(4.5), Inches(3.0)
        )

        text_frame = insights_box.text_frame
        text_frame.word_wrap = True

        # Add regular insights
        regular_insights = results['insights'][:4]
        for i, insight in enumerate(regular_insights):
            p = text_frame.add_paragraph() if i > 0 else text_frame.paragraphs[0]
            p.text = f"• {insight}"
            p.font.name = self.default_font
            p.font.size = Pt(12)
            p.line_spacing = 1.2

        # Add NBA comparison section if needed
        if len(results['insights']) > 4:
            # NBA comparison label
            nba_label = slide.shapes.add_textbox(
                Inches(0.5), nba_label_y,
                Inches(4), Inches(0.3)
            )
            nba_label.text_frame.text = f"{team_short} Fans vs. NBA Fans:"
            p = nba_label.text_frame.paragraphs[0]
            p.font.name = self.default_font
            p.font.size = Pt(14)
            p.font.bold = True

            # NBA insights box
            nba_box = slide.shapes.add_textbox(
                Inches(0.7), nba_box_y,
                Inches(4.5), Inches(1.2)
            )

            nba_text_frame = nba_box.text_frame
            nba_text_frame.word_wrap = True

            # Add NBA insights
            for i, insight in enumerate(results['insights'][4:6]):
                p = nba_text_frame.add_paragraph() if i > 0 else nba_text_frame.paragraphs[0]
                p.text = f"• {insight}"
                p.font.name = self.default_font
                p.font.size = Pt(12)
                p.line_spacing = 1.2

    def _add_category_table(self, slide, results):
        """Add category metrics table"""
        metrics = results['category_metrics']
        is_emerging = results.get('is_emerging', False)

        # Table position
        left = Inches(6.2)
        top = Inches(1.4)
        width = Inches(6.8)

        # Table height
        row_height = Inches(0.7)
        num_rows = 2
        height = row_height * num_rows

        # Create table
        table_shape = slide.shapes.add_table(2, 4, left, top, width, height)
        table = table_shape.table

        # Set column widths
        table.columns[0].width = Inches(1.6)
        table.columns[1].width = Inches(1.5)
        table.columns[2].width = Inches(1.7)
        table.columns[3].width = Inches(1.6)

        # Header row
        headers = ['Category', 'Percent of Fans\nWho Spend', 'Likelihood to Spend\n(vs. Local Gen Pop)',
                   'Purchases Per Fan\n(vs. Local Gen Pop)']

        for i, header in enumerate(headers):
            cell = table.cell(0, i)
            cell.text = header
            self._format_header_cell(cell)

        # Data row
        category_name = results.get('display_name', 'Category')
        table.cell(1, 0).text = category_name

        percent_value = metrics.format_percent_fans()
        table.cell(1, 1).text = format_percent_of_fans(percent_value)

        table.cell(1, 2).text = metrics.format_likelihood()
        table.cell(1, 3).text = metrics.format_purchases()

        # Format data cells
        for i in range(4):
            cell = table.cell(1, i)
            self._format_data_cell(cell)

            if is_emerging and i == 0:
                cell.fill.solid()
                cell.fill.fore_color.rgb = self.colors['emerging_bg']

    def _add_subcategory_table(self, slide, subcategory_stats):
        """Add subcategory statistics table"""
        if subcategory_stats.empty:
            return

        # Table position
        left = Inches(6.2)
        top = Inches(3.0)
        width = Inches(6.8)

        # Create table
        rows = min(len(subcategory_stats), 5) + 1
        row_height = Inches(0.7)
        table_height = row_height * rows

        table_shape = slide.shapes.add_table(rows, 4, left, top, width, table_height)
        table = table_shape.table

        # Set column widths
        table.columns[0].width = Inches(1.6)
        table.columns[1].width = Inches(1.5)
        table.columns[2].width = Inches(1.7)
        table.columns[3].width = Inches(1.6)

        # Headers
        headers = ['Sub-Category', 'Percent of Fans\nWho Spend', 'Likelihood to Spend\n(vs. Local Gen Pop)',
                   'Purchases Per Fan\n(vs. Local Gen Pop)']

        for i, header in enumerate(headers):
            cell = table.cell(0, i)
            cell.text = header
            self._format_header_cell(cell)

        # Data rows
        for row_idx, (_, row) in enumerate(subcategory_stats.iterrows(), 1):
            if row_idx >= rows:
                break

            table.cell(row_idx, 0).text = row['Subcategory']
            table.cell(row_idx, 1).text = format_percent_of_fans(row['Percent of Fans Who Spend'])
            table.cell(row_idx, 2).text = row['Likelihood to spend (vs. Local Gen Pop)']
            table.cell(row_idx, 3).text = row['Purchases Per Fan (vs. Gen Pop)']

            for col in range(4):
                self._format_data_cell(table.cell(row_idx, col))

        # Add explanatory text
        explanation_top = top + table_height + Inches(0.1)
        explanation_box = slide.shapes.add_textbox(
            left, explanation_top,
            width, Inches(0.3)
        )

        text_frame = explanation_box.text_frame
        text_frame.word_wrap = True
        text_frame.text = "Subcategories shown in descending order by composite index"

        p = text_frame.paragraphs[0]
        p.font.name = self.default_font
        p.font.size = Pt(10)
        p.font.italic = True
        p.font.color.rgb = RGBColor(100, 100, 100)
        p.alignment = PP_ALIGN.LEFT

    def _format_header_cell(self, cell, small=False):
        """Format table header cell"""
        cell.fill.solid()
        cell.fill.fore_color.rgb = self.colors['table_header']

        text_frame = cell.text_frame
        text_frame.margin_left = Inches(0.05)
        text_frame.margin_right = Inches(0.05)
        text_frame.margin_top = Inches(0.03)
        text_frame.margin_bottom = Inches(0.03)
        text_frame.word_wrap = True

        for paragraph in text_frame.paragraphs:
            paragraph.font.name = self.default_font
            paragraph.font.size = Pt(8) if small else Pt(10)
            paragraph.font.bold = True
            paragraph.font.color.rgb = RGBColor(255, 255, 255)
            paragraph.alignment = PP_ALIGN.CENTER
            paragraph.line_spacing = 1.0

        cell.vertical_anchor = MSO_ANCHOR.MIDDLE

    def _add_brand_logos(self, slide, merchant_stats):
        """Add brand logos as numbered circles"""
        merchant_df, top_merchants = merchant_stats

        if merchant_df.empty:
            return

        # Align with brand table dimensions
        table_left = Inches(6.6)
        table_width = Inches(6.0)

        # Calculate logo positions
        num_logos = min(5, len(merchant_df))
        display_size = Inches(1.0)

        # Calculate spacing
        available_space = table_width - (display_size * num_logos)
        spacing_between = available_space / (num_logos - 1) if num_logos > 1 else 0

        # Position for logos
        y = Inches(1.2)

        # Add numbered circles for top 5 brands
        for i in range(num_logos):
            x = table_left + (i * (display_size + spacing_between))

            # Add circle
            circle = slide.shapes.add_shape(
                MSO_SHAPE.OVAL,
                x, y,
                display_size, display_size
            )
            circle.fill.solid()
            circle.fill.fore_color.rgb = RGBColor(255, 255, 255)
            circle.line.color.rgb = RGBColor(200, 200, 200)
            circle.line.width = Pt(1)

            # Add ranking number below each logo
            number_box = slide.shapes.add_textbox(
                x, y + display_size + Inches(0.05),
                display_size, Inches(0.3)
            )
            number_box.text_frame.text = str(i + 1)
            p = number_box.text_frame.paragraphs[0]
            p.font.name = self.default_font
            p.alignment = PP_ALIGN.CENTER
            p.font.size = Pt(24)
            p.font.bold = True
            p.font.color.rgb = RGBColor(100, 100, 100)

    def _add_brand_insights(self, slide, results, team_name, team_short, category_name):
        """Add brand-specific insights"""
        # Top Brand Insights section
        insights_title = slide.shapes.add_textbox(
            Inches(0.5), Inches(2.4),
            Inches(4), Inches(0.3)
        )
        insights_title.text_frame.text = "Top Brand Insights"
        p = insights_title.text_frame.paragraphs[0]
        p.font.name = self.default_font
        p.font.size = Pt(14)
        p.font.bold = True

        # Insights box
        insights_box = slide.shapes.add_textbox(
            Inches(0.7), Inches(2.8),
            Inches(5.5), Inches(1.6)
        )

        text_frame = insights_box.text_frame
        text_frame.word_wrap = True

        # Get merchant insights
        merchant_insights = results.get('merchant_insights', [])

        # Format insights with labels
        labels = ["Highest % of Fans: ", "Most Purchases per Fan: ", "Highest Spend per Fan: ", "Highest % of Fans Index vs NBA: "]

        for i, (label, insight) in enumerate(zip(labels, merchant_insights)):
            p = text_frame.add_paragraph() if i > 0 else text_frame.paragraphs[0]
            p.line_spacing = 1.2

            # Add bullet and label in bold
            run1 = p.add_run()
            run1.text = f"• {label}"
            run1.font.name = self.default_font
            run1.font.size = Pt(12)
            run1.font.bold = True

            # Add the insight text
            run2 = p.add_run()
            run2.text = insight
            run2.font.name = self.default_font
            run2.font.size = Pt(12)
            run2.font.bold = False

    def _add_brand_table(self, slide, merchant_stats):
        """Add brand ranking table"""
        merchant_df, _ = merchant_stats

        if merchant_df.empty:
            return

        # Create table
        rows = min(len(merchant_df) + 1, 6)
        cols = 5
        left = Inches(6.6)
        top = Inches(3.0)
        width = Inches(6.0)

        row_height = Inches(0.6)
        height = row_height * rows

        table_shape = slide.shapes.add_table(rows, cols, left, top, width, height)
        table = table_shape.table

        # Column widths
        table.columns[0].width = Inches(1.0)
        table.columns[1].width = Inches(1.4)
        table.columns[2].width = Inches(1.2)
        table.columns[3].width = Inches(1.2)
        table.columns[4].width = Inches(1.2)

        # Headers
        headers = ['Rank (by\npercent of\nfans who\nspend)', 'Brand',
                   'Percent of\nFans Who\nSpend',
                   'Likelihood to Spend\n(vs. Local Gen Pop)',
                   'Purchases Per Fan\n(vs. Local Gen Pop)']

        for i, header in enumerate(headers):
            cell = table.cell(0, i)
            cell.text = header
            self._format_header_cell(cell, small=True)

        # Data rows
        for row_idx, (_, row) in enumerate(merchant_df.iterrows(), 1):
            if row_idx >= rows:
                break

            table.cell(row_idx, 0).text = str(row['Rank'])
            table.cell(row_idx, 1).text = row['Brand']
            table.cell(row_idx, 2).text = format_percent_of_fans(row['Percent of Fans Who Spend'])
            table.cell(row_idx, 3).text = row['Likelihood to spend (vs. Local Gen Pop)']
            table.cell(row_idx, 4).text = row['Purchases Per Fan (vs. Gen Pop)']

            for col in range(5):
                self._format_data_cell(table.cell(row_idx, col), small=True)

    def _add_sponsor_recommendation(self, slide, recommendation, team_config):
        """Add Hot Brand Target and sponsorship recommendation"""
        if not recommendation:
            return

        # Hot Brand Target header
        target_title = slide.shapes.add_textbox(
            Inches(0.5), Inches(5.1),
            Inches(2.0), Inches(0.3)
        )
        target_title.text_frame.text = "Hot Brand Target:"
        p = target_title.text_frame.paragraphs[0]
        p.font.name = self.default_font
        p.font.size = Pt(14)
        p.font.bold = True

        # Add X logo placeholder
        logo_size = Inches(0.5)
        logo_x = Inches(2.4)
        logo_y = Inches(5.025)

        # Add circle for logo
        circle = slide.shapes.add_shape(
            MSO_SHAPE.OVAL,
            logo_x, logo_y,
            logo_size, logo_size
        )
        circle.fill.solid()
        circle.fill.fore_color.rgb = RGBColor(255, 255, 255)
        circle.line.color.rgb = RGBColor(200, 200, 200)
        circle.line.width = Pt(0.5)

        # Add X in the circle
        x_text = slide.shapes.add_textbox(
            logo_x, logo_y,
            logo_size, logo_size
        )
        x_text.text_frame.text = "X"
        p = x_text.text_frame.paragraphs[0]
        p.font.name = self.default_font
        p.font.size = Pt(24)
        p.font.bold = True
        p.alignment = PP_ALIGN.CENTER
        p.font.color.rgb = RGBColor(0, 0, 200)
        # Center vertically
        x_text.text_frame.margin_top = Inches(0.08)

        # Recommendation content
        rec_box = slide.shapes.add_textbox(
            Inches(0.7), Inches(5.6),
            Inches(5.5), Inches(1.2)
        )

        text_frame = rec_box.text_frame
        text_frame.word_wrap = True

        # Format recommendation
        team_short = team_config.get('team_name_short', 'Team')
        merchant_name = recommendation.get('merchant', 'Brand')
        composite_index = int(recommendation.get('composite_index', 0))

        # First bullet with bold brand name
        p1 = text_frame.paragraphs[0]

        run1 = p1.add_run()
        run1.text = f"• The {team_short} should target "
        run1.font.name = self.default_font
        run1.font.size = Pt(12)
        run1.font.bold = False

        run2 = p1.add_run()
        run2.text = merchant_name
        run2.font.name = self.default_font
        run2.font.size = Pt(12)
        run2.font.bold = True

        run3 = p1.add_run()
        run3.text = f" for a sponsorship based on having the highest composite index of {composite_index}"
        run3.font.name = self.default_font
        run3.font.size = Pt(12)
        run3.font.bold = False

        p1.line_spacing = 1.2

        # Second bullet
        p2 = text_frame.add_paragraph()
        p2.text = "• The composite index indicates a brand with significant likelihood for more fans to be spending more frequently, and at a higher spend per fan vs. other brands"
        p2.font.name = self.default_font
        p2.font.size = Pt(12)
        p2.line_spacing = 1.2
        p2.left_indent = Inches(0.25)
        p2.first_line_indent = Inches(0)

    def _format_data_cell(self, cell, small=False):
        """Format table data cell"""
        text_frame = cell.text_frame
        text_frame.margin_left = Inches(0.05)
        text_frame.margin_right = Inches(0.05)
        text_frame.margin_top = Inches(0.03)
        text_frame.margin_bottom = Inches(0.03)
        text_frame.word_wrap = True

        for paragraph in text_frame.paragraphs:
            paragraph.font.name = self.default_font
            paragraph.font.size = Pt(12)
            paragraph.alignment = PP_ALIGN.CENTER

            # Color coding
            if 'More' in cell.text or 'more' in cell.text:
                paragraph.font.color.rgb = self.colors['positive']
                paragraph.font.bold = True
            elif 'Less' in cell.text or 'less' in cell.text or 'fewer' in cell.text:
                paragraph.font.color.rgb = self.colors['negative']
                paragraph.font.bold = False
            elif 'EQUAL' in cell.text or 'Equal' in cell.text:
                paragraph.font.color.rgb = self.colors['equal']
                paragraph.font.bold = False
            else:
                paragraph.font.bold = False

        cell.vertical_anchor = MSO_ANCHOR.MIDDLE


def create_mock_data():
    """Create mock data for testing"""

    # Mock subcategory data
    subcategory_data = pd.DataFrame({
        'Subcategory': ['Hotels', 'Airlines', 'Car Rentals', 'Vacation Rentals', 'Cruises'],
        'Percent of Fans Who Spend': [22.5, 18.3, 15.7, 12.4, 8.9],
        'Likelihood to spend (vs. Local Gen Pop)': ['15% More likely', '12% More likely', '8% More likely', 'EQUAL', '5% Less likely'],
        'Purchases Per Fan (vs. Gen Pop)': ['20% More purchases', '15% More purchases', '10% More purchases', '5% More purchases', 'EQUAL']
    })

    # Mock merchant/brand data
    merchant_data = pd.DataFrame({
        'Rank': [1, 2, 3, 4, 5],
        'Brand': ['American Airlines', 'Delta', 'United Airlines', 'Budget', 'Allegiant Air'],
        'Percent of Fans Who Spend': [8.0, 4.8, 4.2, 3.5, 2.9],
        'Likelihood to spend (vs. Local Gen Pop)': ['16% Less likely', '13% Less likely', '9% More likely', '62% More likely', '108% More likely'],
        'Purchases Per Fan (vs. Gen Pop)': ['47% Less purchases', '43% Less purchases', '55% Less purchases', '18% More purchases', '9% More purchases']
    })

    # Mock category metrics
    category_metrics = MockCategoryMetrics(
        percent_audience=35.2,
        percent_index=18,
        composite_index=125,
        spc=22,
        ppc=15
    )

    # Mock recommendation
    recommendation = {
        'merchant': 'Celebrity Cruises',
        'composite_index': 194
    }

    # Mock analysis results
    analysis_results = {
        'display_name': 'Travel',
        'slide_title': 'Sponsor Spending Analysis: Travel',
        'is_emerging': False,  # Set to True to test emerging category
        'category_metrics': category_metrics,
        'subcategory_stats': subcategory_data,
        'merchant_stats': (merchant_data, merchant_data['Brand'].tolist()),
        'insights': [
            "Panthers fans spend 22% more on travel than the local gen pop",
            "Hotels represent the highest subcategory with 23% of fans spending",
            "Panthers fans make 15% more travel purchases per year compared to local gen pop",
            "Airlines show strong growth potential with 18% fan engagement",
            "Panthers fans are 25% more likely to spend on travel compared to NBA fans",
            "Average travel spend per Panthers fan is $2,450 annually vs NBA average of $1,960"
        ],
        'merchant_insights': [
            "8% of Carolina Panthers fans spend at American Airlines",
            "Panthers fans make an average of 4 purchases per year at Allegiant Air",
            "Panthers fans spent an average of $1,499 per fan on Allegiant Air per year",
            "Panthers fans are 125% more likely to spend on American Airlines than the average NBA fan"
        ],
        'recommendation': recommendation
    }

    # Mock team config
    team_config = {
        'team_name': 'Carolina Panthers',
        'team_name_short': 'Panthers',
        'league': 'NFL'
    }

    return analysis_results, team_config


def main():
    """Main function to generate test slides"""
    print("Generating test category and brand slides...")

    # Create mock data
    analysis_results, team_config = create_mock_data()

    # Create presentation
    presentation = Presentation()

    # Create slide generator
    generator = CategorySlide(presentation)

    # Generate the category analysis slide
    print("Creating category analysis slide...")
    presentation = generator.generate(analysis_results, team_config)

    # Generate the brand analysis slide
    print("Creating brand analysis slide...")
    presentation = generator.generate_brand_slide(analysis_results, team_config)

    # Save the presentation
    output_path = "test_category_slides.pptx"
    presentation.save(output_path)

    print(f"✅ Test slides saved to: {output_path}")
    print("\nYou can now:")
    print("1. Open the PowerPoint file to see both slides")
    print("2. Modify the formatting parameters in the code")
    print("3. Change the mock data to test different scenarios")
    print("4. Set 'is_emerging': True to test emerging category formatting")
    print("\nKey formatting locations:")
    print("- Title Y position: _add_title() method, Inches(1.2)")
    print("- Title font size: _add_title() method, Pt(24)")
    print("- Brand logos Y position: _add_brand_logos() method, Inches(1.2)")
    print("- Table positions: Various top parameters in table methods")


if __name__ == "__main__":
    main()