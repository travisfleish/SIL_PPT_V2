# slide_generators/category_slide.py
"""
Generate category analysis slides for PowerPoint presentations
Formats category spending data into professional slides matching SIL template
"""

from pathlib import Path
from typing import Dict, Optional, Any, List, Tuple
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR, MSO_AUTO_SIZE
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.dml import MSO_THEME_COLOR
import pandas as pd
import logging

from .base_slide import BaseSlide
from data_processors.category_analyzer import CategoryAnalyzer, CategoryMetrics

logger = logging.getLogger(__name__)

# Default font
DEFAULT_FONT_FAMILY = "Red Hat Display"


class CategorySlide(BaseSlide):
    """Generate category analysis slides with insights, subcategory stats, and merchant rankings"""

    def __init__(self, presentation: Presentation = None):
        """
        Initialize category slide generator

        Args:
            presentation: Existing presentation to add slide to
        """
        super().__init__(presentation)
        self.default_font = DEFAULT_FONT_FAMILY

        # Colors for the slide
        self.colors = {
            'header_bg': RGBColor(240, 240, 240),
            'header_border': RGBColor(200, 200, 200),
            'table_header': RGBColor(217, 217, 217),
            'table_border': RGBColor(0, 0, 0),
            'positive': RGBColor(0, 176, 80),  # Green
            'negative': RGBColor(255, 0, 0),  # Red
            'neutral': RGBColor(0, 0, 0)  # Black
        }

    def generate(self,
                 analysis_results: Dict[str, Any],
                 team_config: Dict[str, Any],
                 slide_index: Optional[int] = None) -> Presentation:
        """
        Generate the complete category analysis slide

        Args:
            analysis_results: Results from CategoryAnalyzer.analyze_category()
            team_config: Team configuration with colors, names, etc.
            slide_index: Where to insert slide (None = append)

        Returns:
            Updated presentation object
        """
        # Extract team info
        team_name = team_config.get('team_name', 'Team')
        team_short = team_config.get('team_name_short', team_name.split()[-1])

        # FIX 2: Use blank layout with no automatic placeholders
        slide = self.presentation.slides.add_slide(self.blank_layout)

        # Add header
        self._add_header(slide, team_name, analysis_results['slide_title'])

        # Add title
        self._add_title(slide, analysis_results['slide_title'])

        # Add category insights (left side) - UPDATED TO SHOW ALL INSIGHTS
        self._add_category_insights(slide, analysis_results, team_short, team_config)

        # Add category metrics table (top right) - pass results for category name
        self._add_category_table(slide, analysis_results)

        # Add subcategory table (middle right) - adjusted for 16:9
        self._add_subcategory_table(slide, analysis_results['subcategory_stats'])

        # Add NBA comparison note
        self._add_nba_comparison(slide, team_config['league'])

        logger.info(f"Generated {analysis_results['display_name']} slide")
        return self.presentation

    def generate_brand_slide(self,
                             analysis_results: Dict[str, Any],
                             team_config: Dict[str, Any],
                             slide_index: Optional[int] = None) -> Presentation:
        """
        Generate the brand analysis slide (second slide for category)

        Args:
            analysis_results: Results from CategoryAnalyzer
            team_config: Team configuration
            slide_index: Where to insert slide

        Returns:
            Updated presentation
        """
        # Extract team info
        team_name = team_config.get('team_name', 'Team')
        team_short = team_config.get('team_name_short', team_name.split()[-1])

        # Use blank layout
        slide = self.presentation.slides.add_slide(self.blank_layout)

        # Add header - brand slide uses category name + " Brands"
        header_title = f"{analysis_results['display_name']} Sponsor Analysis"
        self._add_header(slide, team_name, header_title)

        # Add title
        title = f"{analysis_results['display_name']} Sponsor Analysis"
        self._add_title(slide, title)

        # Add brand logos (numbered circles) - adjusted for 16:9
        self._add_brand_logos(slide, analysis_results['merchant_stats'])

        # Add brand insights (left side)
        self._add_brand_insights(slide, analysis_results, team_name)

        # Add brand table (right side) - adjusted for 16:9
        self._add_brand_table(slide, analysis_results['merchant_stats'])

        # Add sponsorship recommendation
        self._add_sponsor_recommendation(slide, analysis_results['recommendation'], team_config)

        logger.info(f"Generated {analysis_results['display_name']} brand slide")
        return self.presentation

    def _add_header(self, slide, team_name: str, slide_title: str):
        """Add header with team name and slide title"""
        # Team name (left)
        team_text = slide.shapes.add_textbox(
            Inches(0.5), Inches(0.05),
            Inches(4), Inches(0.3)
        )
        team_text.text_frame.text = team_name
        p = team_text.text_frame.paragraphs[0]
        p.font.name = self.default_font  # Red Hat Display
        p.font.size = Pt(12)

        # Slide title (right) - adjusted position for 16:9
        title_text = slide.shapes.add_textbox(
            Inches(6.333), Inches(0.05),  # Moved right for 16:9
            Inches(6.8), Inches(0.3)  # Wider for 16:9
        )
        title_text.text_frame.text = slide_title
        p = title_text.text_frame.paragraphs[0]
        p.font.name = self.default_font  # Red Hat Display
        p.alignment = PP_ALIGN.RIGHT
        p.font.size = Pt(12)

    def _add_title(self, slide, title: str):
        """Add main slide title"""
        title_box = slide.shapes.add_textbox(
            Inches(0.5), Inches(0.6),
            Inches(12.333), Inches(0.5)  # Adjusted for 16:9 width
        )
        title_box.text_frame.text = title
        p = title_box.text_frame.paragraphs[0]
        p.font.name = self.default_font  # Red Hat Display
        p.font.size = Pt(28)
        p.font.bold = True
        p.font.color.rgb = RGBColor(85, 85, 85)

    def _add_category_insights(self, slide, results: Dict[str, Any], team_short: str, team_config: Dict[str, Any]):
        """Add category insights section - UPDATED TO SHOW ALL INSIGHTS"""
        # Insights title
        insights_title = slide.shapes.add_textbox(
            Inches(0.5), Inches(1.5),
            Inches(4), Inches(0.3)
        )
        insights_title.text_frame.text = "Category Insights:"
        p = insights_title.text_frame.paragraphs[0]
        p.font.name = self.default_font  # Red Hat Display
        p.font.size = Pt(14)
        p.font.bold = True

        # Insights list - adjusted height to accommodate all insights
        insights_box = slide.shapes.add_textbox(
            Inches(0.7), Inches(1.9),
            Inches(4.5), Inches(4.0)  # Increased height from 3.5 to 4.0
        )

        text_frame = insights_box.text_frame
        text_frame.word_wrap = True

        # Add ALL insights (not limited to 4)
        for i, insight in enumerate(results['insights'], 1):
            p = text_frame.add_paragraph() if i > 1 else text_frame.paragraphs[0]
            p.text = f"{i}. {insight}"
            p.font.name = self.default_font  # Red Hat Display
            p.font.size = Pt(11)
            p.line_spacing = 1.2

        # Add NBA comparison label if there are NBA insights
        if any("NBA" in insight for insight in results['insights']):
            # Add a subtle label for the NBA comparison section
            nba_label = slide.shapes.add_textbox(
                Inches(0.5), Inches(6.0),
                Inches(4), Inches(0.3)
            )
            nba_label.text_frame.text = f"{team_config.get('league', 'NBA')} Fans vs. {team_config.get('league', 'NBA')} Fans"
            p = nba_label.text_frame.paragraphs[0]
            p.font.name = self.default_font
            p.font.size = Pt(11)
            p.font.bold = True
            p.font.italic = True

    def _add_category_table(self, slide, results: Dict[str, Any]):
        """Add category metrics table (adjusted for 16:9)"""
        # Extract metrics from results
        metrics = results['category_metrics']

        # Table position - adjusted to prevent bleeding
        left = Inches(5.8)  # Moved left to fit better
        top = Inches(1.5)
        width = Inches(6.8)  # Adjusted width to fit within slide
        height = Inches(0.8)  # Reduced height for better proportions

        # Create table
        table_shape = slide.shapes.add_table(2, 4, left, top, width, height)
        table = table_shape.table

        # Set column widths - better distribution
        table.columns[0].width = Inches(1.3)  # Category
        table.columns[1].width = Inches(1.6)  # Percent of Fans
        table.columns[2].width = Inches(2.0)  # How likely
        table.columns[3].width = Inches(1.9)  # Purchases

        # Header row
        headers = ['Category', 'Percent of Fans\nWho Spend', 'How likely fans are to\nspend vs. gen pop',
                   'How many more purchases\nper fan v gen pop']

        for i, header in enumerate(headers):
            cell = table.cell(0, i)
            cell.text = header
            self._format_header_cell(cell)

        # Data row - extract category name properly
        category_name = results.get('display_name', 'Category')
        table.cell(1, 0).text = category_name
        table.cell(1, 1).text = metrics.format_percent_fans()
        table.cell(1, 2).text = metrics.format_likelihood()
        table.cell(1, 3).text = metrics.format_purchases()

        # Format data cells
        for i in range(4):
            self._format_data_cell(table.cell(1, i))

    def _add_subcategory_table(self, slide, subcategory_stats: pd.DataFrame):
        """Add subcategory statistics table (adjusted for 16:9)"""
        if subcategory_stats.empty:
            return

        # Table position - adjusted to prevent bleeding
        left = Inches(5.8)  # Moved left to fit better
        top = Inches(2.7)  # Adjusted vertical position
        width = Inches(6.8)  # Adjusted width to fit within slide

        # Create table with header + data rows
        rows = min(len(subcategory_stats), 5) + 1  # Max 5 subcategories + header
        table_shape = slide.shapes.add_table(rows, 4, left, top, width, Inches(0.3 * rows))
        table = table_shape.table

        # Set column widths - better distribution
        table.columns[0].width = Inches(1.6)  # Sub-Category
        table.columns[1].width = Inches(1.5)  # Percent of Fans
        table.columns[2].width = Inches(1.9)  # How likely
        table.columns[3].width = Inches(1.8)  # Purchases

        # Headers
        headers = ['Sub-Category', 'Percent of Fans\nWho Spend', 'How likely fans are to\nspend vs. gen pop',
                   'How many more purchases\nper fan v gen pop']

        for i, header in enumerate(headers):
            cell = table.cell(0, i)
            cell.text = header
            self._format_header_cell(cell)

        # Data rows
        for row_idx, (_, row) in enumerate(subcategory_stats.iterrows(), 1):
            if row_idx >= rows:
                break

            table.cell(row_idx, 0).text = row['Subcategory']
            table.cell(row_idx, 1).text = row['Percent of Fans Who Spend']
            table.cell(row_idx, 2).text = row['How likely fans are to spend vs. gen pop']
            table.cell(row_idx, 3).text = row['Purchases per fan vs. gen pop']

            # Format cells
            for col in range(4):
                self._format_data_cell(table.cell(row_idx, col))

    def _add_nba_comparison(self, slide, league: str):
        """Add NBA/League comparison note"""
        comparison_box = slide.shapes.add_textbox(
            Inches(0.5), Inches(5.8),
            Inches(4), Inches(0.5)
        )
        comparison_box.text_frame.text = f"{league} Fans vs. {league} Fans"
        p = comparison_box.text_frame.paragraphs[0]
        p.font.name = self.default_font  # Red Hat Display
        p.font.size = Pt(12)
        p.font.bold = True

    def _add_brand_logos(self, slide, merchant_stats: Tuple[pd.DataFrame, List[str]]):
        """Add brand logo placeholders (numbered circles) - adjusted for 16:9"""
        merchant_df, top_merchants = merchant_stats

        if merchant_df.empty:
            return

        # Position for logos - adjusted spacing for 16:9
        start_x = Inches(0.5)
        y = Inches(1.2)
        spacing = Inches(2.4)  # Wider spacing for 16:9

        # Add numbered circles for top 5 brands
        for i in range(min(5, len(merchant_df))):
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
            p.font.name = self.default_font  # Red Hat Display
            p.alignment = PP_ALIGN.CENTER
            p.font.size = Pt(48)
            p.font.color.rgb = RGBColor(150, 150, 150)

    def _add_brand_insights(self, slide, results: Dict[str, Any], team_name: str):
        """Add brand-specific insights"""
        # Top Brand Insights section
        insights_title = slide.shapes.add_textbox(
            Inches(0.5), Inches(2.8),
            Inches(4), Inches(0.3)
        )
        insights_title.text_frame.text = "Top Brand Insights"
        p = insights_title.text_frame.paragraphs[0]
        p.font.name = self.default_font  # Red Hat Display
        p.font.size = Pt(14)
        p.font.bold = True
        p.font.style = 'Italic'  # Match the sample

        # Insights
        insights_box = slide.shapes.add_textbox(
            Inches(0.7), Inches(3.2),
            Inches(4.5), Inches(1.6)  # Reduced height to make room for Top Brand Target
        )

        text_frame = insights_box.text_frame
        text_frame.word_wrap = True

        # Add merchant insights
        for i, insight in enumerate(results['merchant_insights'][:4], 1):
            p = text_frame.add_paragraph() if i > 1 else text_frame.paragraphs[0]
            p.text = f"{i}. {insight}"
            p.font.name = self.default_font  # Red Hat Display
            p.font.size = Pt(10)
            p.line_spacing = 1.0

    def _add_brand_table(self, slide, merchant_stats: Tuple[pd.DataFrame, List[str]]):
        """Add brand ranking table - adjusted for 16:9"""
        merchant_df, _ = merchant_stats

        if merchant_df.empty:
            return

        # Create table - adjusted position and size for 16:9
        rows = min(len(merchant_df) + 1, 6)  # Header + max 5 brands
        cols = 5
        left = Inches(5.833)  # Moved right for 16:9
        top = Inches(1.2)
        width = Inches(7.0)  # Wider for 16:9
        height = Inches(0.35 * rows)

        table = slide.shapes.add_table(rows, cols, left, top, width, height).table

        # Headers
        headers = ['Rank (by\npercent of\nfans who\nspend)', 'Brand',
                   'Percent of\nFans Who\nSpend',
                   'How likely\nfans are to\nspend vs.\ngen pop',
                   'Purchases\nPer Fan\n(vs. Gen\nPop)']

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
            table.cell(row_idx, 2).text = row['Percent of Fans Who Spend']
            table.cell(row_idx, 3).text = row['How likely fans are to spend vs. gen pop']
            table.cell(row_idx, 4).text = row['Purchases Per Fan (vs. Gen Pop)']

            # Format cells
            for col in range(5):
                self._format_data_cell(table.cell(row_idx, col), small=True)

    def _add_sponsor_recommendation(self, slide, recommendation: Optional[Dict[str, Any]], team_config: Dict[str, Any]):
        """Add Top Brand Target and sponsorship recommendation"""
        if not recommendation:
            return

        # Top Brand Target header
        target_title = slide.shapes.add_textbox(
            Inches(0.5), Inches(5.0),
            Inches(4), Inches(0.3)
        )
        target_title.text_frame.text = "Top Brand Target"
        p = target_title.text_frame.paragraphs[0]
        p.font.name = self.default_font  # Red Hat Display
        p.font.size = Pt(14)
        p.font.bold = True

        # Recommendation content
        rec_box = slide.shapes.add_textbox(
            Inches(0.7), Inches(5.4),
            Inches(6), Inches(1.2)
        )

        text_frame = rec_box.text_frame
        text_frame.word_wrap = True

        # Main recommendation with team name
        team_name = team_config.get('team_name', 'Team')
        p1 = text_frame.paragraphs[0]
        p1.text = f"1. The {team_name} should target {recommendation['merchant']} for a sponsorship based on having the highest composite index"
        p1.font.name = self.default_font  # Red Hat Display
        p1.font.size = Pt(11)
        p1.line_spacing = 1.2

        # Second paragraph - explanation (indented)
        p2 = text_frame.add_paragraph()
        p2.text = f"      a.    {recommendation['explanation']}"
        p2.font.name = self.default_font  # Red Hat Display
        p2.font.size = Pt(11)
        p2.line_spacing = 1.2

    def _add_merchant_table(self, slide, merchant_stats: Tuple[pd.DataFrame, List[str]]):
        """Add top merchants table (adjusted for 16:9)"""
        merchant_df, _ = merchant_stats

        if merchant_df.empty:
            return

        # Table position - adjusted to prevent bleeding
        left = Inches(5.5)  # Moved left to fit better
        top = Inches(3.0)
        width = Inches(7.3)  # Adjusted width to fit within slide

        # Create table
        rows = min(len(merchant_df), 5) + 1  # Max 5 merchants + header
        table_shape = slide.shapes.add_table(rows, 5, left, top, width, Inches(0.35 * rows))
        table = table_shape.table

        # Set column widths - better distribution for readability
        table.columns[0].width = Inches(0.7)  # Rank
        table.columns[1].width = Inches(1.8)  # Brand
        table.columns[2].width = Inches(1.3)  # % Fans
        table.columns[3].width = Inches(1.7)  # Likelihood
        table.columns[4].width = Inches(1.8)  # Purchases

        # Headers with proper text wrapping
        headers = ['Rank (by\npercent of\nfans who\nspend)', 'Brand', 'Percent of\nFans Who\nSpend',
                   'How likely\nfans are to\nspend vs.\ngen pop', 'Purchases\nPer Fan\n(vs. Gen\nPop)']

        for i, header in enumerate(headers):
            cell = table.cell(0, i)
            cell.text = header
            self._format_header_cell(cell)

        # Data rows
        for row_idx in range(min(5, len(merchant_df))):
            row = merchant_df.iloc[row_idx]

            table.cell(row_idx + 1, 0).text = str(row['Rank'])
            table.cell(row_idx + 1, 1).text = row['Brand']
            table.cell(row_idx + 1, 2).text = row['Percent of Fans Who Spend']
            table.cell(row_idx + 1, 3).text = row['How likely fans are to spend vs. gen pop']
            table.cell(row_idx + 1, 4).text = row['Purchases Per Fan (vs. Gen Pop)']

            # Format cells
            for col in range(5):
                self._format_data_cell(table.cell(row_idx + 1, col))

    def _format_header_cell(self, cell, small: bool = False):
        """Format table header cell"""
        cell.fill.solid()
        cell.fill.fore_color.rgb = self.colors['table_header']

        # Format text
        text_frame = cell.text_frame
        text_frame.margin_left = Inches(0.05)
        text_frame.margin_right = Inches(0.05)
        text_frame.margin_top = Inches(0.03)
        text_frame.margin_bottom = Inches(0.03)
        text_frame.word_wrap = True

        # Format all paragraphs in the cell (for multi-line headers)
        for paragraph in text_frame.paragraphs:
            paragraph.font.name = self.default_font  # Red Hat Display
            paragraph.font.size = Pt(8) if small else Pt(10)  # Smaller font for compact tables
            paragraph.font.bold = True
            paragraph.alignment = PP_ALIGN.CENTER
            paragraph.line_spacing = 1.0  # Tighter line spacing for headers

        # Vertical alignment
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE

    def _format_data_cell(self, cell, small: bool = False):
        """Format table data cell"""
        # Format text
        text_frame = cell.text_frame
        text_frame.margin_left = Inches(0.05)
        text_frame.margin_right = Inches(0.05)
        text_frame.margin_top = Inches(0.03)
        text_frame.margin_bottom = Inches(0.03)
        text_frame.word_wrap = True

        # Format all paragraphs in the cell
        for paragraph in text_frame.paragraphs:
            paragraph.font.name = self.default_font  # Red Hat Display
            paragraph.font.size = Pt(8) if small else Pt(11)  # Consistent data font size
            paragraph.alignment = PP_ALIGN.CENTER

            # Color coding for More/Less
            if 'More' in cell.text or 'more' in cell.text:
                paragraph.font.color.rgb = self.colors['positive']
            elif 'Less' in cell.text or 'less' in cell.text or 'fewer' in cell.text:
                paragraph.font.color.rgb = self.colors['negative']

        # Vertical alignment
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE


# Convenience functions
def create_category_slides(analysis_results: Dict[str, Any],
                           team_config: Dict[str, Any],
                           presentation: Optional[Presentation] = None) -> Presentation:
    """
    Create both category slides (analysis + brands) for a category

    Args:
        analysis_results: Results from CategoryAnalyzer
        team_config: Team configuration
        presentation: Existing presentation (creates new if None)

    Returns:
        Presentation with both slides added
    """
    generator = CategorySlide(presentation)

    # Generate category analysis slide
    presentation = generator.generate(analysis_results, team_config)

    # Generate brand analysis slide
    presentation = generator.generate_brand_slide(analysis_results, team_config)

    return presentation