# data_processors/category_fan_wheel_data.py
"""
Data retrieval for category-based fan wheel
Gets top N categories by PERC_INDEX
"""

import pandas as pd
from typing import Optional
import logging
from data_processors.snowflake_connector import query_to_dataframe

logger = logging.getLogger(__name__)


class CategoryFanWheelData:
    """Get data for category-based fan wheel"""
    
    def __init__(self, view_prefix: str, audience_name: str, comparison_population: str = None):
        """
        Initialize category fan wheel data retriever
        
        Args:
            view_prefix: View prefix (e.g., "V_F1_RACING_FANS")
            audience_name: Audience name (e.g., "F1 Racing Fans")
            comparison_population: Comparison population name (e.g., "General Population")
        """
        self.view_prefix = view_prefix
        self.audience_name = audience_name
        self.comparison_population = comparison_population or "General Population"
        
        self.category_view = f"{view_prefix}_CATEGORY_INDEXING_ALL_TIME"
    
    def get_fan_wheel_data(self, top_n_categories: int = 10) -> pd.DataFrame:
        """
        Get fan wheel data with top categories by PERC_INDEX
        
        Args:
            top_n_categories: Number of top categories to include (default: 10)
            
        Returns:
            DataFrame with columns: CATEGORY, PERC_INDEX, and other available metrics
        """
        category_query = f"""
        SELECT 
            TRIM(CATEGORY) as CATEGORY,
            PERC_INDEX,
            PERC_AUDIENCE,
            COMPOSITE_INDEX,
            SPC_INDEX,
            SPP_INDEX,
            PPC_INDEX
        FROM {self.category_view}
        WHERE AUDIENCE = '{self.audience_name}'
          AND COMPARISON_POPULATION = '{self.comparison_population}'
          AND CATEGORY IS NOT NULL
          AND TRIM(CATEGORY) != ''
        ORDER BY PERC_INDEX DESC
        LIMIT {top_n_categories}
        """
        
        logger.info(f"Fetching top {top_n_categories} categories by PERC_INDEX...")
        logger.info(f"  View: {self.category_view}")
        logger.info(f"  Audience: {self.audience_name}")
        logger.info(f"  Comparison: {self.comparison_population}")
        
        wheel_data = query_to_dataframe(category_query)
        
        if wheel_data.empty:
            logger.warning("No categories found")
            return pd.DataFrame()
        
        logger.info(f"Found {len(wheel_data)} categories")
        logger.info(f"PERC_INDEX range: {wheel_data['PERC_INDEX'].min():.2f} - {wheel_data['PERC_INDEX'].max():.2f}")
        
        return wheel_data

