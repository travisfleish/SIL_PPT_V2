#!/usr/bin/env python3
"""
Parser for fan_wheel_categories.csv to extract persona-to-category mappings
"""

import csv
import pandas as pd
from typing import Dict, List, Tuple


def parse_persona_categories(csv_path: str = "fan_wheel_categories.csv") -> Dict[str, List[Dict]]:
    """
    Parse the fan_wheel_categories.csv file to extract persona-to-category mappings
    
    Returns:
        Dictionary mapping persona names to list of category definitions
        {
            "College Basketball Fan": [
                {"display_name": "Fitness", "subcategory": "Fitness"},
                {"display_name": "Beauty", "subcategory": "Beauty"},
                ...
            ],
            ...
        }
    """
    
    personas = {}
    current_persona = None
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        
        for row_num, row in enumerate(reader, 1):
            # Skip empty rows
            if not any(row):
                continue
            
            # Check if this is a persona header 
            # Some have ":", some don't (e.g., "NWSL Fan", "MLS Fan")
            if row[0] and 'Fan' in row[0]:
                # Check if it's actually a persona name and not a category
                # Persona names are: "College Basketball Fan:", "MLB Fan:", "Super Bowl Fan", "NWSL Fan", "MLS Fan"
                potential_persona = row[0].replace(':', '').strip()
                
                # Only set as current persona if it matches exactly one of the expected ones
                if potential_persona in ['College Basketball Fan', 'MLB Fan', 'Super Bowl Fan', 'NWSL Fan', 'MLS Fan']:
                    current_persona = potential_persona
                    personas[current_persona] = []
                    print(f"Found persona: {current_persona}")
                    continue
            
            # If we have a current persona and this row has category data
            if current_persona and row[0] and row[0].strip():
                display_name = row[0].strip()
                
                # Skip certain rows
                if display_name.startswith('Remade') or display_name.startswith('TIME FRAME'):
                    continue
                
                # Skip rows that look like they might be comments or headers
                if display_name.startswith(',') or 'Segements' in display_name:
                    continue
                
                # Column 1 has the clean name
                clean_name = row[1].strip() if len(row) > 1 and row[1] else display_name
                
                # Column 3 (index 3) has the subcategory mapping
                subcategory = row[3].strip() if len(row) > 3 and row[3] else None
                
                # If no subcategory in column 3, try column 2 (Category)
                if not subcategory and len(row) > 2 and row[2]:
                    subcategory = row[2].strip()
                
                # Skip if no valid subcategory or it's a header/special marker
                if not subcategory or subcategory == 'DUPLICATE' or subcategory == 'Subcategory:' or subcategory == 'Category':
                    continue
                
                # Add to persona
                personas[current_persona].append({
                    'display_name': display_name,
                    'clean_name': clean_name,
                    'subcategory': subcategory
                })
    
    return personas


def map_display_to_snowflake_subcategories() -> Dict[str, str]:
    """
    Create a mapping from display names to exact Snowflake subcategory names
    This helps with matching since the CSV might have slightly different naming
    """
    return {
        'Fitness': 'Fitness',
        'Beauty': 'Beauty',
        'Flowers': 'Retailers - Flowers',
        'Tax & Legal Services': 'Business Services - Tax & Legal Services',
        'Beverages - Coffee & Tea': 'Beverages - Coffee & Tea',
        'Home Improvement': 'Home - Home Improvement & Hardware',
        'Beverages - Alcohol': 'Beverages - Alcohol',
        'Auto Services': 'Auto - Auto Services',
        'Sports Betting': 'Gambling - Online',
        'Streaming': 'Streaming',
        'Food Delivery': 'Restaurants - Online Delivery',
        'QSR': 'Restaurants - QSR & Fast Casual',
        'Apparel - Sneakers': 'Athleisure - Sneakers Plus',
        'Sober Curious': 'Beverages - Non-Alcoholic',
        'Travel - Airlines': 'Travel - Airlines',
        'Youth Sports': 'Amateur Sports - Youth Sports',
        'Streaming OTT': 'Streaming - OTT',
        'Pets - Retail': 'Pets - Retail',
        'Outdoor Retailers': 'Specialty Retailers - Outdoor',
        'Beverages Coffee & Tea': 'Beverages - Coffee & Tea',
        'Gaming - Publisher': 'Gaming - Publisher',
        'Health & Fitness': 'Fitness',
        'Travel - Lodging & Accommodation': 'Lodging & Accommodation',
        'Auto': 'Auto',
        'Entertainment & Music': 'Entertainment & News - Musicians',
        'Boutique Fitness': 'Fitness',
        'Athleisure': 'Athleisure',
        'Travel': 'Travel',
        'Beauty - cosmetics & skincare': 'Beauty - Cosmetics & Skincare',
        'Home Decor': 'Home Furnishings & Goods - Retail',
        'Pets': 'Pets',
        'E-tailers': 'Retailers - Online E-Tail',
        'Dollar Stores': 'Retailers - Dollar & Discount Stores',
        'Theme Parks': 'Attractions - Theme Parks',
        'Movie theaters': 'Entertainment & News - Movies',
    }


def get_persona_category_mappings(csv_path: str = "fan_wheel_categories.csv") -> Dict[str, List[Tuple[str, str, str]]]:
    """
    Get clean persona-to-category mappings
    
    Returns:
        Dictionary mapping persona to list of (display_name, clean_name, subcategory) tuples
    """
    personas = parse_persona_categories(csv_path)
    
    # Clean up and validate
    cleaned_personas = {}
    
    for persona, categories in personas.items():
        cleaned_categories = []
        for cat in categories:
            display_name = cat['display_name']
            clean_name = cat['clean_name']
            subcategory = cat['subcategory']
            
            if display_name and subcategory:
                cleaned_categories.append((display_name, clean_name, subcategory))
        
        if cleaned_categories:
            cleaned_personas[persona] = cleaned_categories
    
    return cleaned_personas


if __name__ == "__main__":
    # Test the parser
    print("="*100)
    print("PARSING PERSONA CATEGORIES FROM CSV")
    print("="*100)
    
    personas = get_persona_category_mappings()
    
    for persona, categories in personas.items():
        print(f"\n{persona}:")
        print("-"*100)
        for display_name, clean_name, subcategory in categories:
            print(f"  {display_name:<40} | Clean: {clean_name:<20} | → {subcategory}")
        print(f"\n  Total categories: {len(categories)}")

