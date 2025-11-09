#!/usr/bin/env python3
"""
Generate fan wheels using the persona_category_mapping.json file
Handles both category-level (aggregate) and subcategory-level mappings
"""

import json
import pandas as pd
from typing import Dict, List, Tuple
from data_processors.snowflake_connector import query_to_dataframe
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_persona_snowflake_name(persona: str) -> str:
    """Map persona display names to Snowflake audience names"""
    persona_mapping = {
        'College Basketball Fan': 'College Basketball Fan',
        'MLB Fan': 'MLB Fans',
        'Super Bowl Fan': 'Super Bowl Fan',
        'NWSL Fan': 'NWSL Fans',
        'MLS Fan': 'MLS Fans'
    }
    return persona_mapping.get(persona, persona)


def get_aggregated_category_data(persona: str, subcategories: List[str]) -> Tuple[float, float]:
    """
    Get aggregated percentage and index for multiple subcategories
    
    Args:
        persona: The audience/persona name
        subcategories: List of subcategory names to aggregate
        
    Returns:
        Tuple of (avg_perc_audience, avg_perc_index)
    """
    snowflake_audience = get_persona_snowflake_name(persona)
    
    # Build IN clause
    subcategory_list = "','".join(subcategories)
    
    query = f"""
    SELECT 
        AVG(PERC_AUDIENCE) as avg_perc_audience,
        AVG(PERC_INDEX) as avg_perc_index
    FROM SILAB.TEST_LAB_INTERNS.TF_Q1_PERSONA_SUBCATEGORY_INDEXING_ALL_TIME
    WHERE AUDIENCE = '{snowflake_audience}'
        AND SUBCATEGORY IN ('{subcategory_list}')
    """
    
    df = query_to_dataframe(query)
    
    if len(df) > 0:
        return float(df.iloc[0]['AVG_PERC_AUDIENCE']), float(df.iloc[0]['AVG_PERC_INDEX'])
    else:
        return None, None


def get_subcategory_data(persona: str, subcategory: str) -> Tuple[float, float]:
    """
    Get percentage and index for a specific subcategory
    
    Args:
        persona: The audience/persona name
        subcategory: The subcategory name
        
    Returns:
        Tuple of (perc_audience, perc_index)
    """
    snowflake_audience = get_persona_snowflake_name(persona)
    
    query = f"""
    SELECT 
        PERC_AUDIENCE,
        PERC_INDEX
    FROM SILAB.TEST_LAB_INTERNS.TF_Q1_PERSONA_SUBCATEGORY_INDEXING_ALL_TIME
    WHERE AUDIENCE = '{snowflake_audience}'
        AND SUBCATEGORY = '{subcategory}'
    """
    
    df = query_to_dataframe(query)
    
    if len(df) > 0:
        return float(df.iloc[0]['PERC_AUDIENCE']), float(df.iloc[0]['PERC_INDEX'])
    else:
        return None, None


def get_top_merchant_for_subcategories(persona: str, subcategories: List[str]) -> Tuple[str, float]:
    """
    Get the top merchant across multiple subcategories (for category-level aggregation)
    
    Args:
        persona: The audience/persona name
        subcategories: List of subcategory names
        
    Returns:
        Tuple of (merchant_name, perc_index)
    """
    snowflake_audience = get_persona_snowflake_name(persona)
    
    subcategory_list = "','".join(subcategories)
    
    query = f"""
    SELECT 
        MERCHANT,
        PERC_INDEX
    FROM SILAB.TEST_LAB_INTERNS.TF_Q1_PERSONA_MERCHANT_INDEXING_ALL_TIME
    WHERE AUDIENCE = '{snowflake_audience}'
        AND SUBCATEGORY IN ('{subcategory_list}')
    ORDER BY PERC_INDEX DESC
    LIMIT 1
    """
    
    try:
        df = query_to_dataframe(query)
        if len(df) > 0:
            return df.iloc[0]['MERCHANT'], float(df.iloc[0]['PERC_INDEX'])
        else:
            return None, None
    except Exception as e:
        logger.error(f"Error getting merchant: {e}")
        return None, None


def get_top_merchant_for_subcategory(persona: str, subcategory: str) -> Tuple[str, float]:
    """
    Get the top merchant for a specific subcategory
    
    Args:
        persona: The audience/persona name
        subcategory: The subcategory name
        
    Returns:
        Tuple of (merchant_name, perc_index)
    """
    snowflake_audience = get_persona_snowflake_name(persona)
    
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
            return df.iloc[0]['MERCHANT'], float(df.iloc[0]['PERC_INDEX'])
        else:
            return None, None
    except Exception as e:
        logger.error(f"Error getting merchant: {e}")
        return None, None


def generate_fan_wheel_for_persona(persona: str, mapping_file: str = "persona_category_mapping.json") -> pd.DataFrame:
    """
    Generate fan wheel data for a single persona using the JSON mapping
    
    Args:
        persona: The persona name (e.g., "MLS Fan")
        mapping_file: Path to the JSON mapping file
        
    Returns:
        DataFrame with fan wheel data
    """
    # Load mapping
    with open(mapping_file, 'r') as f:
        mapping = json.load(f)
    
    if persona not in mapping:
        logger.error(f"Persona '{persona}' not found in mapping file")
        return pd.DataFrame()
    
    persona_data = mapping[persona]
    categories = persona_data['categories']
    
    logger.info(f"Generating fan wheel for {persona}")
    logger.info(f"Processing {len(categories)} categories")
    
    fan_wheel_data = []
    
    for cat in categories:
        display_name = cat['display_name']
        mapping_type = cat['mapping_type']
        match_status = cat['match_status']
        
        if match_status != 'MATCHED':
            logger.warning(f"Skipping {display_name} - not matched in Snowflake")
            continue
        
        logger.info(f"Processing {display_name} ({mapping_type})")
        
        if mapping_type == 'CATEGORY':
            # Category-level: aggregate across all subcategories
            subcategories = cat['snowflake_subcategories']
            
            # Get aggregated percentage (use as community_index)
            avg_perc_audience, avg_perc_index = get_aggregated_category_data(persona, subcategories)
            
            if avg_perc_audience is None:
                logger.warning(f"No data found for category {display_name}")
                continue
            
            # Get top merchant across all subcategories
            merchant, merchant_index = get_top_merchant_for_subcategories(persona, subcategories)
            
            fan_wheel_data.append({
                'COMMUNITY': display_name,
                'COMMUNITY_INDEX': avg_perc_audience,  # Use PERC_AUDIENCE as the index
                'MERCHANT': merchant if merchant else 'N/A',
                'MERCHANT_INDEX': merchant_index if merchant_index else 0,
                'PERC_AUDIENCE': avg_perc_audience
            })
            
            logger.info(f"  ✅ {display_name}: PercAudience={avg_perc_audience:.4f}, Merchant={merchant}")
            
        else:
            # Subcategory-level: specific match
            subcategory = cat['snowflake_subcategory']
            
            # Get percentage data (use as community_index)
            perc_audience, perc_index = get_subcategory_data(persona, subcategory)
            
            if perc_audience is None:
                logger.warning(f"No data found for subcategory {display_name} ({subcategory})")
                continue
            
            # Get top merchant
            merchant, merchant_index = get_top_merchant_for_subcategory(persona, subcategory)
            
            fan_wheel_data.append({
                'COMMUNITY': display_name,
                'COMMUNITY_INDEX': perc_audience,  # Use PERC_AUDIENCE as the index
                'MERCHANT': merchant if merchant else 'N/A',
                'MERCHANT_INDEX': merchant_index if merchant_index else 0,
                'PERC_AUDIENCE': perc_audience
            })
            
            logger.info(f"  ✅ {display_name}: PercAudience={perc_audience:.4f}, Merchant={merchant}")
    
    # Convert to DataFrame
    df = pd.DataFrame(fan_wheel_data)
    
    # Sort by COMMUNITY_INDEX descending
    df = df.sort_values('COMMUNITY_INDEX', ascending=False).reset_index(drop=True)
    
    logger.info(f"Generated fan wheel with {len(df)} categories")
    
    return df


if __name__ == "__main__":
    import sys
    
    # Get persona from command line or default to MLS Fan
    persona = sys.argv[1] if len(sys.argv) > 1 else "MLS Fan"
    
    logger.info(f"Generating fan wheel for: {persona}")
    
    # Generate fan wheel
    df = generate_fan_wheel_for_persona(persona)
    
    if len(df) > 0:
        # Save to CSV
        safe_filename = persona.lower().replace(' ', '_')
        output_path = f"{safe_filename}_fan_wheel_v2.csv"
        df.to_csv(output_path, index=False)
        
        print(f"\n{'='*100}")
        print(f"{persona} Fan Wheel:")
        print('='*100)
        print(df.to_string(index=False))
        print(f"\n✅ Saved to {output_path}")
    else:
        print(f"\n❌ No data generated for {persona}")

