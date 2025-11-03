#!/usr/bin/env python3
"""
Generate demographic slide for South Carolina Tourism
"""

import pandas as pd
from pathlib import Path
import sys
import logging
from pptx import Presentation
from pptx.util import Inches

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from data_processors.snowflake_connector import query_to_dataframe
from data_processors.demographic_processor import DemographicsProcessor
from slide_generators.demographics_slide import DemographicsSlide
from visualizations.demographic_charts import DemographicCharts
from utils.team_config_manager import TeamConfigManager

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Generate South Carolina Tourism demographics slide"""
    
    # Load team configuration
    config_manager = TeamConfigManager()
    team_config = config_manager.get_team_config('south_carolina_tourism')
    
    if not team_config:
        logger.error("Could not load South Carolina Tourism configuration")
        return
    
    logger.info(f"Generating demographics for: {team_config['team_name']}")
    
    # Query demographic data from Snowflake
    logger.info("Querying demographic data from Snowflake...")
    
    query = """
    SELECT *
    FROM SOUTH_CAROLINA_TOURISM.SIL_DEMOGRAPHICS_DIST
    """
    
    try:
        df = query_to_dataframe(query)
        logger.info(f"Retrieved {len(df):,} rows from Snowflake")
        
        # Create a simple CSV backup
        output_dir = Path('output')
        output_dir.mkdir(exist_ok=True)
        csv_path = output_dir / 'sc_tourism_demographics.csv'
        df.to_csv(csv_path, index=False)
        logger.info(f"Saved data to {csv_path}")
        
        # Process demographic data
        logger.info("Processing demographic data...")
        
        processor = DemographicsProcessor(
            data_source=df,
            team_name=team_config['team_name'],
            league=team_config['league'],
            use_ai_insights=False,  # Disable AI for now
            comparison_population=team_config['comparison_population'],
            communities_override=team_config.get('demographics_communities')
        )
        
        demographic_data = processor.process_all_demographics()
        logger.info("Demographic processing complete")
        
        # Create output directory for charts
        charts_dir = output_dir / 'sc_tourism_charts'
        charts_dir.mkdir(exist_ok=True)
        
        # Generate demographic charts
        logger.info("Generating demographic charts...")
        
        charts = DemographicCharts(
            team_colors=team_config['colors'],
            team_config=team_config
        )
        
        # Generate all demographic charts using the proper method
        charts.create_all_demographic_charts(
            demographic_data=demographic_data,
            output_dir=charts_dir
        )
        
        logger.info("All charts generated")
        
        # Create the PowerPoint presentation
        logger.info("Creating PowerPoint slide...")
        prs = Presentation()
        prs.slide_width = Inches(13.333)
        prs.slide_height = Inches(7.5)
        
        demographics_slide = DemographicsSlide(prs)
        demographics_slide.generate(
            demographic_data=demographic_data,
            chart_dir=charts_dir,
            team_config=team_config
        )
        
        # Save the presentation
        pptx_path = output_dir / 'sc_tourism_demographics.pptx'
        demographics_slide.save(pptx_path)
        
        logger.info(f"✅ Complete! Saved to {pptx_path}")
        logger.info(f"   - Charts directory: {charts_dir}")
        logger.info(f"   - CSV data: {csv_path}")
        
    except Exception as e:
        logger.error(f"Error generating demographics: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()

