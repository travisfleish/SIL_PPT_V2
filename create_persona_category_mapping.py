#!/usr/bin/env python3
"""
Create a JSON mapping file for persona categories
This helps ensure we're using the correct subcategory names from Snowflake
"""

import json
from data_processors.snowflake_connector import query_to_dataframe
from parse_persona_categories import get_persona_category_mappings


def get_all_subcategories_for_persona(persona: str):
    """
    Get all available subcategories for a persona from Snowflake
    
    Args:
        persona: The audience/persona name
        
    Returns:
        List of available subcategory names
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
    SELECT DISTINCT 
        CATEGORY,
        SUBCATEGORY,
        PERC_INDEX
    FROM SILAB.TEST_LAB_INTERNS.TF_Q1_PERSONA_SUBCATEGORY_INDEXING_ALL_TIME
    WHERE AUDIENCE = '{snowflake_audience}'
    ORDER BY PERC_INDEX DESC
    """
    
    df = query_to_dataframe(query)
    
    # Return as list of dicts with category and subcategory
    return df.to_dict('records')


def find_matching_subcategory(desired_name: str, available_subcategories: list) -> str:
    """
    Try to find a matching subcategory from Snowflake based on the desired name
    
    Args:
        desired_name: The name from the CSV
        available_subcategories: List of dicts with CATEGORY and SUBCATEGORY
        
    Returns:
        Best matching subcategory name or None
    """
    desired_lower = desired_name.lower().strip()
    
    # First, try exact match (case insensitive)
    for item in available_subcategories:
        if item['SUBCATEGORY'].lower() == desired_lower:
            return item['SUBCATEGORY']
    
    # Try partial match - if desired name is contained in subcategory
    for item in available_subcategories:
        if desired_lower in item['SUBCATEGORY'].lower():
            return item['SUBCATEGORY']
    
    # Try reverse - if subcategory is contained in desired name
    for item in available_subcategories:
        if item['SUBCATEGORY'].lower() in desired_lower:
            return item['SUBCATEGORY']
    
    # Try matching on key words
    desired_words = set(desired_lower.replace('-', ' ').split())
    best_match = None
    best_score = 0
    
    for item in available_subcategories:
        subcat_words = set(item['SUBCATEGORY'].lower().replace('-', ' ').split())
        match_score = len(desired_words & subcat_words)
        if match_score > best_score:
            best_score = match_score
            best_match = item['SUBCATEGORY']
    
    return best_match if best_score > 0 else None


def is_category_level(csv_subcategory: str) -> bool:
    """
    Determine if this is a category-level (aggregate all subcategories) or subcategory-level (specific)
    
    Category-level examples: "Fitness", "Beauty", "Auto", "Travel", "Streaming", "Athleisure", "Pets"
    Subcategory-level examples: "Retailers - Flowers", "Auto - Auto Services", "Streaming - OTT"
    """
    # If it doesn't have a " - " separator, it's likely category-level
    if " - " not in csv_subcategory:
        return True
    
    # Some specific cases that should be category-level even with separators
    category_level_patterns = [
        "Lodging & Accommodation",  # This is actually category-level
    ]
    
    for pattern in category_level_patterns:
        if csv_subcategory.startswith(pattern):
            return True
    
    return False


def get_all_subcategories_for_category(category_name: str, available_subcats: list) -> list:
    """
    Get all subcategories that belong to a specific category
    
    Args:
        category_name: The category name (e.g., "Fitness", "Beauty")
        available_subcats: List of all available subcategories
        
    Returns:
        List of subcategory names that match the category
    """
    matching_subcats = []
    
    for item in available_subcats:
        subcat = item['SUBCATEGORY']
        # Match if subcategory starts with the category name
        # E.g., "Fitness - Home Fitness" matches category "Fitness"
        if subcat.startswith(category_name + " - "):
            matching_subcats.append(subcat)
    
    return matching_subcats


def create_persona_mapping_json(output_file: str = "persona_category_mapping.json"):
    """
    Create a JSON file with persona-to-category mappings
    """
    # Get CSV mappings
    csv_personas = get_persona_category_mappings()
    
    # Build comprehensive mapping
    mapping = {}
    
    for persona, categories in csv_personas.items():
        print(f"\n{'='*80}")
        print(f"Processing {persona}")
        print(f"{'='*80}")
        
        # Get all available subcategories from Snowflake
        available_subcats = get_all_subcategories_for_persona(persona)
        print(f"Found {len(available_subcats)} subcategories in Snowflake")
        
        persona_categories = []
        
        for display_name, clean_name, csv_subcategory in categories:
            # Determine if this is category-level or subcategory-level
            is_cat_level = is_category_level(csv_subcategory)
            
            category_info = {
                "display_name": display_name,
                "clean_name": clean_name,
                "csv_subcategory": csv_subcategory,
                "mapping_type": "CATEGORY" if is_cat_level else "SUBCATEGORY"
            }
            
            if is_cat_level:
                # Category-level: find all subcategories under this category
                matching_subcats = get_all_subcategories_for_category(csv_subcategory, available_subcats)
                
                if matching_subcats:
                    category_info['snowflake_subcategories'] = matching_subcats
                    category_info['match_status'] = "MATCHED"
                    category_info['subcategory_count'] = len(matching_subcats)
                    
                    # Print status
                    print(f"✅ {display_name:35} | Category: {csv_subcategory:30} | Found {len(matching_subcats)} subcategories")
                else:
                    category_info['match_status'] = "NOT_FOUND"
                    print(f"❌ {display_name:35} | Category: {csv_subcategory:30} | No subcategories found")
            else:
                # Subcategory-level: find specific match
                matched_subcat = find_matching_subcategory(csv_subcategory, available_subcats)
                
                if matched_subcat:
                    category_info['snowflake_subcategory'] = matched_subcat
                    category_info['match_status'] = "MATCHED"
                    
                    # Add index info
                    for item in available_subcats:
                        if item['SUBCATEGORY'] == matched_subcat:
                            category_info['perc_index'] = float(item['PERC_INDEX'])
                            break
                    
                    print(f"✅ {display_name:35} | Subcategory: {csv_subcategory:30} | Match: {matched_subcat}")
                else:
                    category_info['match_status'] = "NOT_FOUND"
                    print(f"❌ {display_name:35} | Subcategory: {csv_subcategory:30} | No match found")
            
            persona_categories.append(category_info)
        
        mapping[persona] = {
            "categories": persona_categories,
            "total_categories": len(persona_categories),
            "matched_categories": sum(1 for c in persona_categories if c['match_status'] == 'MATCHED'),
            "available_in_snowflake": len(available_subcats)
        }
    
    # Save to JSON
    with open(output_file, 'w') as f:
        json.dump(mapping, f, indent=2)
    
    print(f"\n{'='*80}")
    print(f"Saved mapping to {output_file}")
    print(f"{'='*80}")
    
    # Print summary
    print("\nSUMMARY:")
    print("-"*80)
    for persona, data in mapping.items():
        matched = data['matched_categories']
        total = data['total_categories']
        match_pct = (matched / total * 100) if total > 0 else 0
        print(f"{persona:30} | {matched}/{total} matched ({match_pct:.1f}%)")
    
    return mapping


if __name__ == "__main__":
    print("Creating persona category mapping from Snowflake data...")
    mapping = create_persona_mapping_json()
    print("\n✅ Complete! Review persona_category_mapping.json and edit as needed.")

