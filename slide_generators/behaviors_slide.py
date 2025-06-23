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
from visualizations.test_wheel import FanWheelStandalone
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
        logger.info("Generating fan wheel visualization...")
        fan_wheel_path = self._create_fan_wheel(merchant_ranker, team_config)

        logger.info("Generating community index chart...")
        chart_path = self._create_community_chart(merchant_ranker, colors)

        # Add slide
        if slide_index is not None:
            slide = self.presentation.slides.add_slide(slide_index, self.blank_layout)
        else:
            slide = self.presentation.slides.add_slide(self.blank_layout)

        # Set slide background to white
        self._set_slide_background(slide, 'FFFFFF')

        # Add header
        self._add_header(slide, team_name)

        # Add title
        title = f"Fan Behaviors: How Are {team_name} Fans Unique"
        self._add_title(slide, title)

        # Add visualizations
        self._add_fan_wheel(slide, fan_wheel_path)
        self._add_community_chart(slide, chart_path)

        # Add insight text
        insight = self._generate_insight_text(merchant_ranker, team_short)
        self._add_insight_text(slide, insight)

        # Add footer/logo
        self._add_team_logo(slide, team_config)

        logger.info(f"Generated behaviors slide for {team_name}")
        return self.presentation

    def _create_fan_wheel(self, merchant_ranker: MerchantRanker,
                          team_config: Dict[str, Any]) -> Path:
        """Create fan wheel visualization"""
        # Get data
        wheel_data = merchant_ranker.get_fan_wheel_data(
            min_audience_pct=0.20,
            top_n_communities=10
        )

        # Create visualization
        colors = team_config['colors']
        fan_wheel = FanWheelStandalone(
            team_name=team_config['team_name_short'],
            primary_color=colors['primary'],
            secondary_color=colors['secondary'],
            accent_color=colors.get('accent', '#4169E1')
        )

        output_path = Path('temp_fan_wheel.png')
        fan_wheel.create(wheel_data, str(output_path))

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
        # Header background
        header_rect = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE,
            Inches(0), Inches(0),
            Inches(10), Inches(0.5)
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
        team_text.text_frame.paragraphs[0].font.size = Pt(14)
        team_text.text_frame.paragraphs[0].font.bold = True

        # Slide indicator (right)
        slide_text = slide.shapes.add_textbox(
            Inches(6.5), Inches(0.1),
            Inches(3.3), Inches(0.3)
        )
        slide_text.text_frame.text = "Fan Behaviors: How Are Utah Jazz Fans Unique"
        slide_text.text_frame.paragraphs[0].alignment = PP_ALIGN.RIGHT
        slide_text.text_frame.paragraphs[0].font.size = Pt(14)

    def _add_title(self, slide, title: str):
        """Add main slide title"""
        title_box = slide.shapes.add_textbox(
            Inches(0.5), Inches(0.6),
            Inches(9), Inches(0.5)
        )
        title_box.text_frame.text = title
        title_box.text_frame.paragraphs[0].font.size = Pt(24)
        title_box.text_frame.paragraphs[0].font.bold = True
        title_box.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER

    def _add_fan_wheel(self, slide, image_path: Path):
        """Add fan wheel image to slide"""
        # Position on left side
        left = Inches(0.3)
        top = Inches(1.5)
        width = Inches(4.5)

        slide.shapes.add_picture(str(image_path), left, top, width=width)

    def _add_community_chart(self, slide, image_path: Path):
        """Add community index chart to slide"""
        # Position on right side
        left = Inches(5.0)
        top = Inches(1.5)
        width = Inches(4.7)

        slide.shapes.add_picture(str(image_path), left, top, width=width)

    def _add_insight_text(self, slide, insight: str):
        """Add insight text below fan wheel"""
        text_box = slide.shapes.add_textbox(
            Inches(0.3), Inches(6.0),
            Inches(4.5), Inches(1.0)
        )
        text_box.text_frame.text = insight
        text_box.text_frame.word_wrap = True

        # Format text
        p = text_box.text_frame.paragraphs[0]
        p.font.size = Pt(16)
        p.font.bold = True
        p.alignment = PP_ALIGN.LEFT

    def _generate_insight_text(self, merchant_ranker: MerchantRanker,
                               team_short: str) -> str:
        """Generate insight text based on top communities"""
        # Get top 3 communities
        communities_df = merchant_ranker.get_top_communities(
            min_audience_pct=0.20, top_n=3
        )

        if not communities_df.empty:
            top_communities = communities_df['COMMUNITY'].tolist()

            # Create readable list
            if len(top_communities) >= 3:
                insight_parts = []

                # Map communities to descriptive phrases
                community_phrases = {
                    'Live Entertainment Seekers': 'values-driven live entertainment seekers',
                    'Cost Conscious': 'cost-conscious shoppers',
                    'Travelers': 'frequent travelers',
                    'Movie Buffs': 'movie enthusiasts',
                    'Gamers': 'gaming enthusiasts',
                    'Beauty Enthusiasts': 'beauty-conscious consumers'
                }

                for community in top_communities[:3]:
                    phrase = community_phrases.get(community, community.lower())
                    insight_parts.append(phrase)

                # Construct sentence
                if len(insight_parts) == 3:
                    insight = f"{team_short} fans are {insight_parts[0]} who are {insight_parts[1]} and {insight_parts[2]}!"
                else:
                    insight = f"{team_short} fans are {' and '.join(insight_parts)}!"

                return insight

        # Fallback
        return f"{team_short} fans have unique behaviors and preferences compared to the general population!"

    def _add_team_logo(self, slide, team_config: Dict[str, Any]):
        """Add small team logo in corner"""
        # For now, just add a small text placeholder
        logo_box = slide.shapes.add_textbox(
            Inches(9.3), Inches(0.1),
            Inches(0.6), Inches(0.3)
        )
        logo_box.text_frame.text = team_config.get('team_name_short', 'Team')
        logo_box.text_frame.paragraphs[0].font.size = Pt(10)
        logo_box.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER

    def _set_slide_background(self, slide, color_hex: str):
        """Set slide background color"""
        background = slide.background
        fill = background.fill
        fill.solid()
        fill.fore_color.rgb = RGBColor.from_string(color_hex)


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


# Test function
if __name__ == "__main__":
    from utils.team_config_manager import TeamConfigManager

    # Test with Utah Jazz
    config_manager = TeamConfigManager()
    team_config = config_manager.get_team_config('utah_jazz')

    # Initialize merchant ranker
    ranker = MerchantRanker(team_view_prefix=team_config['view_prefix'])

    # Create slide
    pres = create_behaviors_slide(ranker, team_config)

    # Save
    output_path = "test_behaviors_slide.pptx"
    pres.save(output_path)
    print(f"Saved test presentation to {output_path}")