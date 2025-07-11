# slide_generators/behaviors_slide.py
"""
Generate Fan Behaviors slide for PowerPoint presentations
Combines fan wheel and community index chart with insights
"""

from pathlib import Path
from typing import Dict, Optional, Any
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
import logging

from .base_slide import BaseSlide
from data_processors.merchant_ranker import MerchantRanker
from visualizations.fan_wheel import FanWheel  # Updated to use enhanced fan wheel
from visualizations.community_index_chart import CommunityIndexChart

logger = logging.getLogger(__name__)


class BehaviorsSlide(BaseSlide):
    """Generate the Fan Behaviors slide with fan wheel and community index chart"""

    def __init__(self, presentation: Presentation = None):
        """
        Initialize behaviors slide generator

        Args:
            presentation: Existing presentation to add slide to (creates new if None)
        """
        super().__init__(presentation)

    def generate(self,
                 merchant_ranker: MerchantRanker,
                 team_config: Dict[str, Any],
                 slide_index: Optional[int] = None) -> Presentation:
        """
        Generate the complete behaviors slide

        Args:
            merchant_ranker: MerchantRanker instance with data
            team_config: Team configuration including colors and names
            slide_index: Where to insert slide (None = append)

        Returns:
            Updated presentation object
        """
        # Extract team info
        team_name = team_config.get('team_name', 'Team')
        team_short = team_config.get('team_name_short', team_name.split()[-1])
        colors = team_config.get('colors', {})

        # Create visualizations
        logger.info("Generating fan wheel visualization with logo support...")
        fan_wheel_path = self._create_fan_wheel(merchant_ranker, team_config)

        logger.info("Generating community index chart...")
        chart_path = self._create_community_chart(merchant_ranker, colors)

        # Use the content layout (SIL white layout #12)
        slide = self.add_content_slide()
        logger.info("Added behaviors slide using SIL white layout")

        # Add header
        self._add_header(slide, team_name)

        # Add title
        title = f"Fan Behaviors: How Are {team_name} Fans Unique"
        self._add_title(slide, title)

        # Add chart titles - UPDATED for swapped positions
        self._add_chart_titles(slide, team_name)

        # Add insight text - MOVED above community chart (left side)
        insight = self._generate_insight_text(merchant_ranker, team_short)
        self._add_insight_text(slide, insight)

        # Add visualizations - SWAPPED positions and 1.5x fan wheel
        self._add_community_chart(slide, chart_path)  # Now on LEFT
        self._add_fan_wheel(slide, fan_wheel_path)  # Now on RIGHT, 1.5x size

        # Add explanation text below community chart
        self._add_chart_explanation(slide)

        # Add footer/logo
        self._add_team_logo(slide, team_config)

        logger.info(f"Generated behaviors slide for {team_name}")
        return self.presentation

    def _create_fan_wheel(self, merchant_ranker: MerchantRanker,
                          team_config: Dict[str, Any]) -> Path:
        """Create fan wheel visualization with logo support"""
        # Get data
        wheel_data = merchant_ranker.get_fan_wheel_data(
            min_audience_pct=0.20,
            top_n_communities=10
        )

        if wheel_data.empty:
            raise ValueError("No fan wheel data available")

        # Create visualization with logo support enabled
        fan_wheel = FanWheel(team_config, enable_logos=True)

        # Generate logo report for debugging
        logo_report = fan_wheel.generate_logo_report(wheel_data)
        logger.info(f"Logo coverage: {logo_report['with_logos']}/{logo_report['total_merchants']} "
                    f"({logo_report['coverage_percentage']:.1f}%)")

        if logo_report['missing_list']:
            logger.debug(f"Missing logos for: {', '.join(logo_report['missing_list'])}")

        output_path = Path('temp_fan_wheel.png')
        fan_wheel.create(wheel_data, output_path)

        return output_path

    def _create_community_chart(self, merchant_ranker: MerchantRanker,
                                team_colors: Dict[str, str]) -> Path:
        """Create community index chart"""
        # Get data with COMPOSITE_INDEX
        communities_df = merchant_ranker.get_top_communities(
            min_audience_pct=0.20,
            top_n=10
        )

        # Rename columns
        data = communities_df.rename(columns={
            'COMMUNITY': 'Community',
            'PERC_AUDIENCE': 'Audience_Pct',
            'COMPOSITE_INDEX': 'Composite_Index'
        })

        # Create chart
        chart = CommunityIndexChart(team_colors)
        output_path = Path('temp_community_chart.png')
        chart.create(data, output_path)

        return output_path

    def _add_header(self, slide, team_name: str):
        """Add header with team name and slide title"""
        # Header background (adjusted for 16:9)
        header_rect = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE,
            Inches(0), Inches(0),
            Inches(13.333), Inches(0.5)  # Full 16:9 width
        )
        header_rect.fill.solid()
        header_rect.fill.fore_color.rgb = RGBColor(240, 240, 240)
        header_rect.line.color.rgb = RGBColor(200, 200, 200)
        header_rect.line.width = Pt(0.5)

        # Team name (left)
        team_text = slide.shapes.add_textbox(
            Inches(0.2), Inches(0.1),
            Inches(3), Inches(0.3)
        )
        team_text.text_frame.text = team_name
        p = team_text.text_frame.paragraphs[0]
        p.font.name = self.default_font  # Red Hat Display
        p.font.size = Pt(14)
        p.font.bold = True

        # Slide indicator (right)
        slide_text = slide.shapes.add_textbox(
            Inches(6.5), Inches(0.1),  # Adjusted for 16:9
            Inches(6.633), Inches(0.3)  # Adjusted width
        )
        slide_text.text_frame.text = f"Fan Behaviors: How Are {team_name} Fans Unique"
        p = slide_text.text_frame.paragraphs[0]
        p.font.name = self.default_font  # Red Hat Display
        p.alignment = PP_ALIGN.RIGHT
        p.font.size = Pt(14)

    def _add_title(self, slide, title: str):
        """Add main slide title"""
        # Don't add title here since it's already in the header
        pass

    def _add_chart_titles(self, slide, team_name: str):
        """Add titles above both visualizations - SWAPPED positions"""
        # Community chart title (now on LEFT)
        bar_chart_title = slide.shapes.add_textbox(
            Inches(0.5), Inches(1.1),
            Inches(5.5), Inches(0.3)
        )
        bar_chart_title.text_frame.text = f"Top Ten {team_name} Fan Communities"
        p = bar_chart_title.text_frame.paragraphs[0]
        p.font.name = self.default_font
        p.font.size = Pt(14)
        p.font.bold = True
        p.alignment = PP_ALIGN.CENTER

        # Fan wheel title (now on RIGHT)
        fan_wheel_title = slide.shapes.add_textbox(
            Inches(7.0), Inches(1.1),
            Inches(5.5), Inches(0.3)
        )
        fan_wheel_title.text_frame.text = "Top Community Fan Purchases"
        p = fan_wheel_title.text_frame.paragraphs[0]
        p.font.name = self.default_font
        p.font.size = Pt(14)
        p.font.bold = True
        p.alignment = PP_ALIGN.CENTER

    def _add_fan_wheel(self, slide, image_path: Path):
        """Add fan wheel image to slide - NOW on RIGHT side, 1.5x size, vertically centered"""
        # 1.5x scaling
        original_width = Inches(4.5)
        new_width = original_width * 1.5  # Inches(6.75)

        # Position on right side
        left = Inches(13.333) - new_width - Inches(0.3)  # Right edge minus width minus margin

        # Vertical center alignment
        slide_height = Inches(7.5)
        header_height = Inches(1.1)
        available_height = slide_height - header_height
        center_y = header_height + (available_height / 2)
        top = center_y - (new_width / 2)  # Fan wheel is roughly square

        slide.shapes.add_picture(str(image_path), left, top, width=new_width)

    def _add_community_chart(self, slide, image_path: Path):
        """Add community index chart to slide - NOW on LEFT side, vertically centered"""
        # Position on left side
        left = Inches(0.5)
        width = Inches(5.5)  # Reduced width to make room for larger fan wheel

        # Vertical center alignment - match fan wheel center
        slide_height = Inches(7.5)
        header_height = Inches(1.1)
        available_height = slide_height - header_height
        center_y = header_height + (available_height / 2)
        chart_height_estimate = Inches(4.0)  # Estimated chart height
        top = center_y - (chart_height_estimate / 2)

        slide.shapes.add_picture(str(image_path), left, top, width=width)

    def _add_chart_explanation(self, slide):
        """Add explanation text below the community index chart - LEFT side"""
        explanation_box = slide.shapes.add_textbox(
            Inches(0.5), Inches(5.8),  # Below community chart on left
            Inches(5.5), Inches(0.9)  # Same width as community chart
        )
        explanation_text = (
            "The top ten fan communities are ranked according to a composite index score "
            "of likelihood to purchase, likelihood to make more purchases per fan versus "
            "the local general population, and likelihood to spend more per fan."
        )
        explanation_box.text_frame.text = explanation_text
        explanation_box.text_frame.word_wrap = True

        p = explanation_box.text_frame.paragraphs[0]
        p.font.name = self.default_font
        p.font.size = Pt(10)
        p.alignment = PP_ALIGN.LEFT
        p.line_spacing = 1.2

    def _add_insight_text(self, slide, insight: str):
        """Add insight text ABOVE community chart on LEFT side"""
        text_box = slide.shapes.add_textbox(
            Inches(0.5), Inches(1.5),  # Above community chart, below title
            Inches(5.5), Inches(0.8)  # Same width as community chart area
        )
        text_box.text_frame.text = insight
        text_box.text_frame.word_wrap = True

        # Format text
        p = text_box.text_frame.paragraphs[0]
        p.font.name = self.default_font  # Red Hat Display
        p.font.size = Pt(16)
        p.font.bold = True
        p.alignment = PP_ALIGN.LEFT

    def _generate_insight_text(self, merchant_ranker: MerchantRanker,
                               team_short: str) -> str:
        """Generate insight text based on top communities"""
        try:
            # Get top communities
            communities = merchant_ranker.get_top_communities(
                min_audience_pct=0.20,
                top_n=3
            )

            if communities.empty:
                return f"{team_short} fans have unique behaviors that set them apart!"

            # Extract community names and convert to insights
            community_names = communities['COMMUNITY'].tolist()
            insights = []

            for community in community_names[:2]:  # Use top 2
                if 'entertainment' in community.lower() or 'live' in community.lower():
                    insights.append("values-driven live entertainment seekers")
                elif 'cost' in community.lower() or 'conscious' in community.lower():
                    insights.append("on the lookout for a deal")
                elif 'travel' in community.lower():
                    insights.append("adventure-seeking travelers")
                elif 'beauty' in community.lower():
                    insights.append("beauty enthusiasts")
                elif 'brand' in community.lower():
                    insights.append("brand-conscious shoppers")
                elif 'movie' in community.lower() or 'film' in community.lower():
                    insights.append("movie buffs")
                elif 'game' in community.lower():
                    insights.append("gaming enthusiasts")
                elif 'sports' in community.lower():
                    insights.append("sports fans")
                elif 'pet' in community.lower():
                    insights.append("pet lovers")
                elif 'streaming' in community.lower():
                    insights.append("streaming content consumers")

            # Create insight text
            if len(insights) >= 2:
                # Add movie reference for entertainment seekers
                if "entertainment" in insights[0]:
                    return f"{team_short} fans are {insights[0]} who are {insights[1]} and a good movie!"
                else:
                    return f"{team_short} fans are {insights[0]} who are {insights[1]}!"
            elif len(insights) == 1:
                if "entertainment" in insights[0]:
                    return f"{team_short} fans are {insights[0]} who love a good movie!"
                else:
                    return f"{team_short} fans are {insights[0]}!"

        except Exception as e:
            logger.warning(f"Error generating insight text: {e}")

        # Fallback
        return f"{team_short} fans have unique behaviors that set them apart from the general population!"

    def _add_team_logo(self, slide, team_config: Dict[str, Any]):
        """Add small team logo in corner"""
        # For now, just add a small text placeholder (adjusted for 16:9)
        logo_box = slide.shapes.add_textbox(
            Inches(12.533), Inches(0.1),  # Moved right for 16:9
            Inches(0.7), Inches(0.3)
        )
        logo_box.text_frame.text = team_config.get('team_name_short', 'Team')
        p = logo_box.text_frame.paragraphs[0]
        p.font.name = self.default_font  # Red Hat Display
        p.font.size = Pt(10)
        p.alignment = PP_ALIGN.CENTER


# Convenience function
def create_behaviors_slide(merchant_ranker: MerchantRanker,
                           team_config: Dict[str, Any],
                           presentation: Optional[Presentation] = None) -> Presentation:
    """
    Create a behaviors slide for the presentation

    Args:
        merchant_ranker: Data source
        team_config: Team configuration
        presentation: Existing presentation (creates new if None)

    Returns:
        Presentation with behaviors slide added
    """
    generator = BehaviorsSlide(presentation)
    return generator.generate(merchant_ranker, team_config)