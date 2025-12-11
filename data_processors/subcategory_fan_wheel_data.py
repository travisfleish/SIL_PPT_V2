# data_processors/subcategory_fan_wheel_data.py
"""
Data retrieval for subcategory-based fan wheel
Gets top 10 categories by blended average (50% SPC_INDEX + 50% PERC_INDEX)
Then gets top subcategory from each category using the same blended average
"""

import pandas as pd
from typing import Dict, Optional
import logging
from data_processors.snowflake_connector import query_to_dataframe

logger = logging.getLogger(__name__)


class SubcategoryFanWheelData:
    """Get data for subcategory-based fan wheel"""
    
    def __init__(self, view_prefix: str, audience_name: str, comparison_population: str = None):
        """
        Initialize subcategory fan wheel data retriever
        
        Args:
            view_prefix: View prefix (e.g., "V_NBA_LEAGUE_SIL")
            audience_name: Audience name (e.g., "NBA Fans")
            comparison_population: Comparison population name (defaults to "General Sports Fans" for F1)
        """
        self.view_prefix = view_prefix
        self.audience_name = audience_name
        # Use "General Sports Fans" as default comparison population
        self.comparison_population = comparison_population or "General Sports Fans"
        
        self.category_view = f"{view_prefix}_CATEGORY_INDEXING_ALL_TIME"
        self.subcategory_view = f"{view_prefix}_SUBCATEGORY_INDEXING_ALL_TIME"
    
    def get_fan_wheel_data(self, top_n_categories: int = 10) -> pd.DataFrame:
        """
        Get fan wheel data with top subcategory from each top category
        
        Args:
            top_n_categories: Number of top categories to include (default: 10)
            
        Returns:
            DataFrame with columns: CATEGORY, SUBCATEGORY, BLENDED_INDEX, PERC_INDEX, SPC_INDEX
        """
        # Step 1: Get top N categories by blended average (50% SPC_INDEX + 50% PERC_INDEX)
        category_query = f"""
        SELECT 
            TRIM(CATEGORY) as CATEGORY,
            PERC_INDEX,
            SPC_INDEX,
            (PERC_INDEX * 0.5 + SPC_INDEX * 0.5) as BLENDED_INDEX
        FROM {self.category_view}
        WHERE AUDIENCE = '{self.audience_name}'
          AND COMPARISON_POPULATION = '{self.comparison_population}'
          AND CATEGORY IS NOT NULL
          AND TRIM(CATEGORY) != ''
        ORDER BY BLENDED_INDEX DESC
        LIMIT {top_n_categories}
        """
        
        logger.info(f"Fetching top {top_n_categories} categories...")
        top_categories_df = query_to_dataframe(category_query)
        
        if top_categories_df.empty:
            logger.warning("No categories found")
            return pd.DataFrame()
        
        logger.info(f"Found {len(top_categories_df)} categories")
        
        # Step 2: For each category, get the top subcategory by blended average
        results = []
        
        for _, cat_row in top_categories_df.iterrows():
            category = cat_row['CATEGORY']
            
            subcategory_query = f"""
            SELECT 
                TRIM(SUBCATEGORY) as SUBCATEGORY,
                PERC_INDEX,
                SPC_INDEX,
                (PERC_INDEX * 0.5 + SPC_INDEX * 0.5) as BLENDED_INDEX
            FROM {self.subcategory_view}
            WHERE AUDIENCE = '{self.audience_name}'
              AND COMPARISON_POPULATION = '{self.comparison_population}'
              AND TRIM(CATEGORY) = '{category}'
              AND SUBCATEGORY IS NOT NULL
              AND TRIM(SUBCATEGORY) != ''
            ORDER BY BLENDED_INDEX DESC
            LIMIT 1
            """
            
            subcategory_df = query_to_dataframe(subcategory_query)
            
            if not subcategory_df.empty:
                subcat_row = subcategory_df.iloc[0]
                results.append({
                    'CATEGORY': category,
                    'SUBCATEGORY': subcat_row['SUBCATEGORY'],
                    'BLENDED_INDEX': subcat_row['BLENDED_INDEX'],
                    'PERC_INDEX': subcat_row['PERC_INDEX'],
                    'SPC_INDEX': subcat_row['SPC_INDEX'],
                    'CATEGORY_BLENDED_INDEX': cat_row['BLENDED_INDEX']
                })
                logger.info(f"  Category '{category}': Top subcategory = '{subcat_row['SUBCATEGORY']}' (blended: {subcat_row['BLENDED_INDEX']:.2f})")
            else:
                logger.warning(f"  Category '{category}': No subcategories found")
        
        if not results:
            logger.warning("No subcategories found for any categories")
            return pd.DataFrame()
        
        # Create DataFrame and sort by category blended index (to maintain top category order)
        wheel_data = pd.DataFrame(results)
        wheel_data = wheel_data.sort_values('CATEGORY_BLENDED_INDEX', ascending=False)
        
        logger.info(f"Generated fan wheel data with {len(wheel_data)} subcategories")
        return wheel_data

