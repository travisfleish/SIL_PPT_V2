#!/usr/bin/env python3
"""
Create a comprehensive CSV with all audiences, categories, and top merchants
"""

import json
import pandas as pd
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


def get_top_merchant_for_subcategory(persona: str, subcategory: str):
    """Get the top merchant for a specific subcategory by audience percentage"""
    snowflake_audience = get_persona_snowflake_name(persona)
    
    query = f"""
    SELECT 
        MERCHANT,
        PERC_INDEX,
        PERC_AUDIENCE
    FROM SILAB.TEST_LAB_INTERNS.TF_Q1_PERSONA_MERCHANT_INDEXING_ALL_TIME
    WHERE AUDIENCE = '{snowflake_audience}'
        AND SUBCATEGORY = '{subcategory}'
    ORDER BY PERC_AUDIENCE DESC
    LIMIT 1
    """
    
    try:
        df = query_to_dataframe(query)
        if len(df) > 0:
            return {
                'merchant': df.iloc[0]['MERCHANT'],
                'merchant_perc_index': float(df.iloc[0]['PERC_INDEX']),
                'merchant_perc_audience': float(df.iloc[0]['PERC_AUDIENCE'])
            }
        else:
            return {
                'merchant': None,
                'merchant_perc_index': None,
                'merchant_perc_audience': None
            }
    except Exception as e:
        logger.error(f"Error getting merchant for {persona} - {subcategory}: {e}")
        return {
            'merchant': None,
            'merchant_perc_index': None,
            'merchant_perc_audience': None
        }


def get_top_merchant_for_category(persona: str, subcategories: list):
    """Get the top merchant across multiple subcategories by audience percentage"""
    snowflake_audience = get_persona_snowflake_name(persona)
    
    subcategory_list = "','".join(subcategories)
    
    query = f"""
    SELECT 
        MERCHANT,
        PERC_INDEX,
        PERC_AUDIENCE
    FROM SILAB.TEST_LAB_INTERNS.TF_Q1_PERSONA_MERCHANT_INDEXING_ALL_TIME
    WHERE AUDIENCE = '{snowflake_audience}'
        AND SUBCATEGORY IN ('{subcategory_list}')
    ORDER BY PERC_AUDIENCE DESC
    LIMIT 1
    """
    
    try:
        df = query_to_dataframe(query)
        if len(df) > 0:
            return {
                'merchant': df.iloc[0]['MERCHANT'],
                'merchant_perc_index': float(df.iloc[0]['PERC_INDEX']),
                'merchant_perc_audience': float(df.iloc[0]['PERC_AUDIENCE'])
            }
        else:
            return {
                'merchant': None,
                'merchant_perc_index': None,
                'merchant_perc_audience': None
            }
    except Exception as e:
        logger.error(f"Error getting merchant for category: {e}")
        return {
            'merchant': None,
            'merchant_perc_index': None,
            'merchant_perc_audience': None
        }


def get_subcategory_metrics(persona: str, subcategory: str):
    """Get metrics for a specific subcategory"""
    snowflake_audience = get_persona_snowflake_name(persona)
    
    query = f"""
    SELECT 
        PERC_AUDIENCE,
        PERC_INDEX
    FROM SILAB.TEST_LAB_INTERNS.TF_Q1_PERSONA_SUBCATEGORY_INDEXING_ALL_TIME
    WHERE AUDIENCE = '{snowflake_audience}'
        AND SUBCATEGORY = '{subcategory}'
    """
    
    try:
        df = query_to_dataframe(query)
        if len(df) > 0:
            return {
                'category_perc_audience': float(df.iloc[0]['PERC_AUDIENCE']),
                'category_perc_index': float(df.iloc[0]['PERC_INDEX'])
            }
        else:
            return {
                'category_perc_audience': None,
                'category_perc_index': None
            }
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        return {
            'category_perc_audience': None,
            'category_perc_index': None
        }


def create_comprehensive_csv(mapping_file: str = "persona_category_mapping.json", 
                             output_file: str = "audience_category_merchant_mapping.csv"):
    """
    Create comprehensive CSV with all audiences, categories, and merchants
    """
    # Load mapping
    with open(mapping_file, 'r') as f:
        mapping = json.load(f)
    
    logger.info(f"Processing {len(mapping)} personas")
    
    all_rows = []
    
    for persona, data in mapping.items():
        logger.info(f"\nProcessing {persona}...")
        categories = data['categories']
        
        for cat in categories:
            display_name = cat['display_name']
            clean_name = cat.get('clean_name', display_name)  # Use clean name if available
            csv_subcategory = cat['csv_subcategory']
            mapping_type = cat['mapping_type']
            match_status = cat['match_status']
            
            logger.info(f"  {display_name} ({mapping_type})")
            
            if match_status != 'MATCHED':
                logger.warning(f"    Skipping - not matched")
                continue
            
            if mapping_type == 'CATEGORY':
                # Category-level: aggregate across subcategories
                subcategories = cat['snowflake_subcategories']
                
                # Get top merchant across all subcategories
                merchant_info = get_top_merchant_for_category(persona, subcategories)
                
                # For category-level, we'll create one row showing it aggregates multiple subcategories
                row = {
                    'audience': persona,
                    'display_name': display_name,
                    'clean_name': clean_name,
                    'csv_subcategory': csv_subcategory,
                    'mapping_type': mapping_type,
                    'snowflake_subcategories': ', '.join(subcategories),
                    'subcategory_count': len(subcategories),
                    'category_perc_audience': None,  # Would need to aggregate
                    'category_perc_index': None,
                    'top_merchant': merchant_info['merchant'],
                    'merchant_perc_index': merchant_info['merchant_perc_index'],
                    'merchant_perc_audience': merchant_info['merchant_perc_audience']
                }
                all_rows.append(row)
                
            else:
                # Subcategory-level: specific match
                subcategory = cat['snowflake_subcategory']
                
                # Get category metrics
                metrics = get_subcategory_metrics(persona, subcategory)
                
                # Get top merchant
                merchant_info = get_top_merchant_for_subcategory(persona, subcategory)
                
                row = {
                    'audience': persona,
                    'display_name': display_name,
                    'clean_name': clean_name,
                    'csv_subcategory': csv_subcategory,
                    'mapping_type': mapping_type,
                    'snowflake_subcategories': subcategory,
                    'subcategory_count': 1,
                    'category_perc_audience': metrics['category_perc_audience'],
                    'category_perc_index': metrics['category_perc_index'],
                    'top_merchant': merchant_info['merchant'],
                    'merchant_perc_index': merchant_info['merchant_perc_index'],
                    'merchant_perc_audience': merchant_info['merchant_perc_audience']
                }
                all_rows.append(row)
    
    # Create DataFrame
    df = pd.DataFrame(all_rows)
    
    # Reorder columns for better readability
    column_order = [
        'audience',
        'display_name',
        'clean_name',
        'mapping_type',
        'csv_subcategory',
        'snowflake_subcategories',
        'subcategory_count',
        'category_perc_audience',
        'category_perc_index',
        'top_merchant',
        'merchant_perc_index',
        'merchant_perc_audience'
    ]
    df = df[column_order]
    
    # Sort by audience and then by category_perc_audience (descending)
    df = df.sort_values(['audience', 'category_perc_audience'], 
                        ascending=[True, False], 
                        na_position='last')
    
    # Save to CSV
    df.to_csv(output_file, index=False)
    
    logger.info(f"\n✅ Saved comprehensive mapping to {output_file}")
    logger.info(f"Total rows: {len(df)}")
    
    # Print summary
    print("\n" + "="*100)
    print("SUMMARY BY AUDIENCE")
    print("="*100)
    for persona in df['audience'].unique():
        persona_df = df[df['audience'] == persona]
        print(f"\n{persona}: {len(persona_df)} categories")
        print(f"  Category-level: {len(persona_df[persona_df['mapping_type'] == 'CATEGORY'])}")
        print(f"  Subcategory-level: {len(persona_df[persona_df['mapping_type'] == 'SUBCATEGORY'])}")
    
    return df


if __name__ == "__main__":
    logger.info("Creating comprehensive audience-category-merchant mapping CSV...")
    df = create_comprehensive_csv()
    
    # Display sample
    print("\n" + "="*100)
    print("SAMPLE ROWS (first 10)")
    print("="*100)
    print(df.head(10).to_string())
    
    print("\n✅ Complete!")

