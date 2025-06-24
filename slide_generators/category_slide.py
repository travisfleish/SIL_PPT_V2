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


class CategorySlide(BaseSlide):
    """Generate category analysis slides with insights, subcategory stats, and merchant rankings"""

    def __init__(self, presentation: Presentation = None):
        """
        Initialize category slide generator

        Args:
            presentation: Existing presentation to add slide to
        """
        super().__init__(presentation)

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
            team_config: Team configuration
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

        # Add category insights (left side)
        self._add_category_insights(slide, analysis_results, team_short)

        # Add category metrics table (top right) - adjusted for 16:9
        self._add_category_table(slide, analysis_results['category_metrics'])

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
        category_name = analysis_results['display_name']

        # FIX 2: Use blank layout with no automatic placeholders
        slide = self.presentation.slides.add_slide(self.blank_layout)

        # Add header
        self._add_header(slide, team_name, f"Sponsor Spending Analysis: {category_name} Brands")

        # Add title
        self._add_title(slide, f"{category_name} Sponsor Analysis")

        # Add brand logos placeholder (numbered circles) - adjusted for 16:9
        self._add_brand_logos(slide, analysis_results['merchant_stats'])

        # Add brand insights (left side)
        self._add_brand_insights(slide, analysis_results, team_name)

        # Add merchant table (right side) - adjusted for 16:9
        self._add_merchant_table(slide, analysis_results['merchant_stats'])

        logger.info(f"Generated {category_name} brand slide")
        return self.presentation

    def _add_header(self, slide, team_name: str, slide_title: str):
        """Add header with team name and slide title (adjusted for 16:9)"""
        # Header background
        header_rect = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE,
            Inches(0), Inches(0),
            Inches(13.333), Inches(0.4)  # Full 16:9 width
        )
        header_rect.fill.solid()
        header_rect.fill.fore_color.rgb = self.colors['header_bg']
        header_rect.line.color.rgb = self.colors['header_border']
        header_rect.line.width = Pt(0.5)

        # Team name (left)
        team_text = slide.shapes.add_textbox(
            Inches(0.2), Inches(0.05),
            Inches(3), Inches(0.3)
        )
        team_text.text_frame.text = team_name
        team_text.text_frame.paragraphs[0].font.size = Pt(12)
        team_text.text_frame.paragraphs[0].font.bold = True

        # Slide title (right) - adjusted position for 16:9
        title_text = slide.shapes.add_textbox(
            Inches(6.333), Inches(0.05),  # Moved right for 16:9
            Inches(6.8), Inches(0.3)      # Wider for 16:9
        )
        title_text.text_frame.text = slide_title
        title_text.text_frame.paragraphs[0].alignment = PP_ALIGN.RIGHT
        title_text.text_frame.paragraphs[0].font.size = Pt(12)

    def _add_title(self, slide, title: str):
        """Add main slide title"""
        title_box = slide.shapes.add_textbox(
            Inches(0.5), Inches(0.6),
            Inches(12.333), Inches(0.5)  # Adjusted for 16:9 width
        )
        title_box.text_frame.text = title
        title_box.text_frame.paragraphs[0].font.size = Pt(28)
        title_box.text_frame.paragraphs[0].font.bold = True
        title_box.text_frame.paragraphs[0].font.color.rgb = RGBColor(85, 85, 85)

    def _add_category_insights(self, slide, results: Dict[str, Any], team_short: str):
        """Add category insights section"""
        # Insights title
        insights_title = slide.shapes.add_textbox(
            Inches(0.5), Inches(1.5),
            Inches(4), Inches(0.3)
        )
        insights_title.text_frame.text = "Category Insights:"
        insights_title.text_frame.paragraphs[0].font.size = Pt(14)
        insights_title.text_frame.paragraphs[0].font.bold = True

        # Insights list
        insights_box = slide.shapes.add_textbox(
            Inches(0.7), Inches(1.9),
            Inches(4.5), Inches(3.5)
        )

        text_frame = insights_box.text_frame
        text_frame.word_wrap = True

        # Add each insight as a numbered item
        for i, insight in enumerate(results['insights'][:4], 1):  # Max 4 insights
            p = text_frame.add_paragraph() if i > 1 else text_frame.paragraphs[0]
            p.text = f"{i}.    {insight}"
            p.font.size = Pt(11)
            p.line_spacing = 1.2

            # Bold the team name in insights
            if team_short in p.text:
                # This is simplified - in production you'd want more sophisticated text formatting
                p.font.bold = False

    def _add_category_table(self, slide, metrics: CategoryMetrics):
        """Add category metrics table (adjusted for 16:9)"""
        # Table position - moved right for 16:9
        left = Inches(6.5)  # Moved right
        top = Inches(1.5)
        width = Inches(6.333)  # Wider for 16:9
        height = Inches(1.2)

        # Create table
        table_shape = slide.shapes.add_table(2, 4, left, top, width, height)
        table = table_shape.table

        # Set column widths - adjusted for wider table
        table.columns[0].width = Inches(1.2)
        table.columns[1].width = Inches(1.7)
        table.columns[2].width = Inches(1.8)
        table.columns[3].width = Inches(1.633)

        # Header row
        headers = ['Category', 'Percent of Fans\nWho Spend', 'How likely fans are to\nspend vs. gen pop',
                   'How many more purchases\nper fan v gen pop']

        for i, header in enumerate(headers):
            cell = table.cell(0, i)
            cell.text = header
            self._format_header_cell(cell)

        # Data row
        table.cell(1, 0).text = metrics.comparison_population.split('(')[0].strip()  # e.g., "Auto"
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

        # Table position - moved right for 16:9
        left = Inches(6.5)  # Moved right
        top = Inches(3.2)
        width = Inches(6.333)  # Wider for 16:9

        # Create table with header + data rows
        rows = min(len(subcategory_stats), 5) + 1  # Max 5 subcategories + header
        table_shape = slide.shapes.add_table(rows, 4, left, top, width, Inches(0.3 * rows))
        table = table_shape.table

        # Set column widths - adjusted for wider table
        table.columns[0].width = Inches(1.5)
        table.columns[1].width = Inches(1.4)
        table.columns[2].width = Inches(1.7)
        table.columns[3].width = Inches(1.733)

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
        comparison_box.text_frame.paragraphs[0].font.size = Pt(12)
        comparison_box.text_frame.paragraphs[0].font.bold = True

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
            text_box.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
            text_box.text_frame.paragraphs[0].font.size = Pt(48)
            text_box.text_frame.paragraphs[0].font.color.rgb = RGBColor(150, 150, 150)

    def _add_brand_insights(self, slide, results: Dict[str, Any], team_name: str):
        """Add brand-specific insights"""
        # Top Brand Insights section
        insights_title = slide.shapes.add_textbox(
            Inches(0.5), Inches(2.8),
            Inches(4), Inches(0.3)
        )
        insights_title.text_frame.text = "Top Brand Insights"
        insights_title.text_frame.paragraphs[0].font.size = Pt(14)
        insights_title.text_frame.paragraphs[0].font.bold = True

        # Insights
        insights_box = slide.shapes.add_textbox(
            Inches(0.7), Inches(3.2),
            Inches(4.5), Inches(2.0)
        )

        text_frame = insights_box.text_frame
        text_frame.word_wrap = True

        # Add merchant insights
        for i, insight in enumerate(results['merchant_insights'][:4], 1):
            p = text_frame.add_paragraph() if i > 1 else text_frame.paragraphs[0]
            p.text = f"{i}.    {insight}"
            p.font.size = Pt(11)
            p.line_spacing = 1.2

        # Top Brand Target section
        if results['recommendation']:
            target_title = slide.shapes.add_textbox(
                Inches(0.5), Inches(5.4),
                Inches(4), Inches(0.3)
            )
            target_title.text_frame.text = "Top Brand Target"
            target_title.text_frame.paragraphs[0].font.size = Pt(14)
            target_title.text_frame.paragraphs[0].font.bold = True

            # Recommendation
            rec_box = slide.shapes.add_textbox(
                Inches(0.7), Inches(5.8),
                Inches(4.5), Inches(1.5)
            )

            rec = results['recommendation']
            rec_text = f"1.    The {team_name} should target {rec['merchant']} for a sponsorship based on having the highest composite index\n"
            rec_text += f"      a.    {rec['explanation']}"

            rec_box.text_frame.text = rec_text
            rec_box.text_frame.word_wrap = True
            rec_box.text_frame.paragraphs[0].font.size = Pt(11)

    def _add_merchant_table(self, slide, merchant_stats: Tuple[pd.DataFrame, List[str]]):
        """Add top merchants table (adjusted for 16:9)"""
        merchant_df, _ = merchant_stats

        if merchant_df.empty:
            return

        # Table position - moved right and wider for 16:9
        left = Inches(6.333)  # Moved right
        top = Inches(3.0)
        width = Inches(6.5)   # Wider for 16:9

        # Create table
        rows = min(len(merchant_df), 5) + 1  # Max 5 merchants + header
        table_shape = slide.shapes.add_table(rows, 5, left, top, width, Inches(0.35 * rows))
        table = table_shape.table

        # Set column widths - adjusted for wider table
        table.columns[0].width = Inches(0.6)   # Rank
        table.columns[1].width = Inches(1.5)   # Brand
        table.columns[2].width = Inches(1.2)   # % Fans
        table.columns[3].width = Inches(1.5)   # Likelihood
        table.columns[4].width = Inches(1.7)   # Purchases

        # Headers
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

    def _format_header_cell(self, cell):
        """Format table header cell"""
        cell.fill.solid()
        cell.fill.fore_color.rgb = self.colors['table_header']

        # Format text
        text_frame = cell.text_frame
        text_frame.margin_left = Inches(0.05)
        text_frame.margin_right = Inches(0.05)
        text_frame.margin_top = Inches(0.02)
        text_frame.margin_bottom = Inches(0.02)

        p = text_frame.paragraphs[0]
        p.font.size = Pt(9)
        p.font.bold = True
        p.alignment = PP_ALIGN.CENTER

    def _format_data_cell(self, cell):
        """Format table data cell"""
        # Format text
        text_frame = cell.text_frame
        text_frame.margin_left = Inches(0.05)
        text_frame.margin_right = Inches(0.05)
        text_frame.margin_top = Inches(0.02)
        text_frame.margin_bottom = Inches(0.02)

        p = text_frame.paragraphs[0]
        p.font.size = Pt(10)
        p.alignment = PP_ALIGN.CENTER

        # Color coding for More/Less
        if 'More' in cell.text:
            p.font.color.rgb = self.colors['positive']
        elif 'Less' in cell.text:
            p.font.color.rgb = self.colors['negative']


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