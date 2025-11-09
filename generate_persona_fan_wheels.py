#!/usr/bin/env python3
"""
Generate fan wheels for personas using fixed categories from CSV
Instead of finding top communities dynamically, we use predefined categories
"""

import pandas as pd
from typing import Dict, List, Tuple
from data_processors.snowflake_connector import query_to_dataframe
from parse_persona_categories import get_persona_category_mappings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_subcategory_data_for_persona(
    persona: str, 
    subcategories: List[str]
) -> pd.DataFrame:
    """
    Query Snowflake for subcategory index data for a specific persona
    
    Args:
        persona: The audience/persona name (e.g., "MLB Fans")
        subcategories: List of subcategory names to query
        
    Returns:
        DataFrame with subcategory index data
    """
    # Map persona display names to Snowflake audience names
    persona_mapping = {
        'College Basketball Fan': 'College Basketball Fan',
        'MLB Fan': 'MLB Fans',
        'Super Bowl Fan': 'Super Bowl Fan',
        'NWSL Fan': 'NWSL Fans',
        'MLS Fan': 'MLS Fans'
    }
    
    snowflake_audience = persona_mapping.get(persona, persona)
    
    # Build IN clause for subcategories
    subcategory_list = "','".join(subcategories)
    
    query = f"""
    SELECT 
        AUDIENCE,
        SUBCATEGORY,
        PERC_INDEX,
        AUDIENCE_COUNT,
        TOTAL_AUDIENCE_COUNT,
        PERC_AUDIENCE,
        SPC,
        SPP,
        PPC
    FROM SILAB.TEST_LAB_INTERNS.TF_Q1_PERSONA_SUBCATEGORY_INDEXING_ALL_TIME
    WHERE AUDIENCE = '{snowflake_audience}'
        AND SUBCATEGORY IN ('{subcategory_list}')
    ORDER BY PERC_INDEX DESC
    """
    
    logger.info(f"Querying subcategory data for {persona} with {len(subcategories)} categories")
    df = query_to_dataframe(query)
    logger.info(f"Retrieved {len(df)} subcategory records")
    
    return df


def get_top_merchant_for_subcategory(
    persona: str,
    subcategory: str
) -> Tuple[str, float]:
    """
    Get the top merchant (by index) for a specific subcategory and persona
    
    Args:
        persona: The audience/persona name
        subcategory: The subcategory name
        
    Returns:
        Tuple of (merchant_name, perc_index)
    """
    # Map persona display names to Snowflake audience names
    persona_mapping = {
        'College Basketball Fan': 'College Basketball Fan',
        'MLB Fan': 'MLB Fans',
        'Super Bowl Fan': 'Super Bowl Fan',
        'NWSL Fan': 'NWSL Fans',
        'MLS Fan': 'MLS Fans'
    }
    
    snowflake_audience = persona_mapping.get(persona, persona)
    
    query = f"""
    SELECT 
        MERCHANT,
        PERC_INDEX
    FROM SILAB.TEST_LAB_INTERNS.TF_Q1_PERSONA_MERCHANT_INDEXING_ALL_TIME
    WHERE AUDIENCE = '{snowflake_audience}'
        AND SUBCATEGORY = '{subcategory}'
    ORDER BY PERC_INDEX DESC
    LIMIT 1
    """
    
    try:
        df = query_to_dataframe(query)
        if len(df) > 0:
            return df.iloc[0]['MERCHANT'], df.iloc[0]['PERC_INDEX']
        else:
            logger.warning(f"No merchant found for {persona} - {subcategory}")
            return None, None
    except Exception as e:
        logger.error(f"Error getting merchant for {persona} - {subcategory}: {e}")
        return None, None


def build_fan_wheel_data(
    persona: str,
    categories: List[Tuple[str, str]]
) -> pd.DataFrame:
    """
    Build fan wheel data for a persona using fixed categories
    
    Args:
        persona: The persona name
        categories: List of (display_name, subcategory) tuples
        
    Returns:
        DataFrame with columns: COMMUNITY, COMMUNITY_INDEX, MERCHANT, MERCHANT_INDEX, PERC_AUDIENCE
    """
    # Get all subcategories for this persona
    subcategories = [cat[1] for cat in categories]
    
    # Query Snowflake for subcategory data
    subcategory_df = get_subcategory_data_for_persona(persona, subcategories)
    
    if len(subcategory_df) == 0:
        logger.warning(f"No subcategory data found for {persona}")
        return pd.DataFrame()
    
    # Build fan wheel rows
    fan_wheel_data = []
    
    for display_name, subcategory in categories:
        # Find subcategory data
        subcat_row = subcategory_df[subcategory_df['SUBCATEGORY'] == subcategory]
        
        if len(subcat_row) == 0:
            logger.warning(f"No data found for {persona} - {subcategory}")
            continue
        
        subcat_row = subcat_row.iloc[0]
        
        # Get top merchant for this subcategory
        merchant, merchant_index = get_top_merchant_for_subcategory(persona, subcategory)
        
        # Build row
        fan_wheel_data.append({
            'COMMUNITY': display_name,  # Use display name from CSV
            'COMMUNITY_INDEX': subcat_row['PERC_INDEX'],
            'MERCHANT': merchant if merchant else 'N/A',
            'MERCHANT_INDEX': merchant_index if merchant_index else 0,
            'PERC_AUDIENCE': subcat_row['PERC_AUDIENCE']
        })
    
    # Convert to DataFrame
    df = pd.DataFrame(fan_wheel_data)
    
    # Sort by COMMUNITY_INDEX descending
    df = df.sort_values('COMMUNITY_INDEX', ascending=False).reset_index(drop=True)
    
    logger.info(f"Built fan wheel data for {persona} with {len(df)} categories")
    
    return df


def generate_all_persona_fan_wheels(output_dir: str = "."):
    """
    Generate fan wheel data for all personas
    
    Args:
        output_dir: Directory to save output CSV files
    """
    # Get persona-to-category mappings from CSV
    personas = get_persona_category_mappings()
    
    logger.info(f"Generating fan wheels for {len(personas)} personas")
    
    results = {}
    
    for persona, categories in personas.items():
        logger.info(f"\n{'='*80}")
        logger.info(f"Processing {persona}")
        logger.info(f"{'='*80}")
        
        # Build fan wheel data
        fan_wheel_df = build_fan_wheel_data(persona, categories)
        
        if len(fan_wheel_df) > 0:
            # Save to CSV
            safe_filename = persona.lower().replace(' ', '_').replace('&', 'and')
            output_path = f"{output_dir}/{safe_filename}_fan_wheel.csv"
            fan_wheel_df.to_csv(output_path, index=False)
            logger.info(f"Saved fan wheel data to {output_path}")
            
            # Store in results
            results[persona] = fan_wheel_df
            
            # Print preview
            print(f"\n{persona} Fan Wheel Preview:")
            print("-"*100)
            print(fan_wheel_df.to_string(index=False))
        else:
            logger.warning(f"No fan wheel data generated for {persona}")
    
    return results


if __name__ == "__main__":
    import sys
    
    output_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    
    logger.info("Starting persona fan wheel generation")
    logger.info(f"Output directory: {output_dir}")
    
    results = generate_all_persona_fan_wheels(output_dir)
    
    logger.info(f"\nGenerated fan wheels for {len(results)} personas")
    logger.info("Complete!")


