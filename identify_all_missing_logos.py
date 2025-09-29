#!/usr/bin/env python3
"""
Comprehensive script to identify ALL missing merchant logos for a team's PowerPoint report.
Includes fan wheel merchants and all category merchants (fixed and custom).
Uses the exact same logic as PowerPointBuilder.
"""

import sys
from pathlib import Path
import logging

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from utils.team_config_manager import TeamConfigManager
from utils.logo_manager import LogoManager
from data_processors.category_analyzer import CategoryAnalyzer
from data_processors.merchant_ranker import MerchantRanker
from data_processors.snowflake_connector import query_to_dataframe, test_connection

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def get_merchants_for_category(analyzer, team_config, category_key, is_custom=False, custom_cat_info=None):
    """Get the top 5 merchants for a specific category using the same logic as PowerPointBuilder"""
    
    try:
        # Use the EXACT same logic as PowerPointBuilder._create_category_slide()
        if is_custom:
            # For custom categories, create the config and use the display name
            cat_config = analyzer.create_custom_category_config(category_key)
            cat_names = [category_key]  # Use the category_key (display name) directly
        else:
            # For fixed categories, get from config
            cat_config = analyzer.categories.get(category_key, {})
            cat_names = cat_config.get('category_names_in_data', [])
        
        if not cat_names:
            return []
        
        # Build WHERE clause - same as PowerPointBuilder
        category_where = " OR ".join([f"TRIM(CATEGORY) = '{cat.strip()}'" for cat in cat_names])
        
        # Load data - EXACT same queries as PowerPointBuilder._create_category_slide()
        category_df = query_to_dataframe(f"""
            SELECT * FROM {team_config['view_prefix']}_CATEGORY_INDEXING_ALL_TIME 
            WHERE {category_where}
        """)
        
        subcategory_df = query_to_dataframe(f"""
            SELECT * FROM {team_config['view_prefix']}_SUBCATEGORY_INDEXING_ALL_TIME 
            WHERE {category_where}
        """)
        
        merchant_df = query_to_dataframe(f"""
            SELECT * FROM {team_config['view_prefix']}_MERCHANT_INDEXING_ALL_TIME 
            WHERE {category_where}
            AND AUDIENCE = '{analyzer.audience_name}'
            ORDER BY PERC_AUDIENCE DESC
        """)
        
        # Load LAST_FULL_YEAR data - same as PowerPointBuilder
        subcategory_last_year_df = query_to_dataframe(f"""
            SELECT * FROM {team_config['view_prefix']}_SUBCATEGORY_INDEXING_LAST_FULL_YEAR 
            WHERE {category_where}
        """)
        
        merchant_last_year_df = query_to_dataframe(f"""
            SELECT * FROM {team_config['view_prefix']}_MERCHANT_INDEXING_LAST_FULL_YEAR 
            WHERE {category_where}
            AND AUDIENCE = '{analyzer.audience_name}'
            ORDER BY PERC_AUDIENCE DESC
        """)
        
        # Use the EXACT same analysis as PowerPointBuilder
        if not merchant_df.empty:
            # Add config for custom categories temporarily (same as PowerPointBuilder)
            if is_custom:
                analyzer.categories[category_key] = cat_config
            
            # Call CategoryAnalyzer.analyze_category() - same as PowerPointBuilder
            analysis = analyzer.analyze_category(
                category_key=category_key,
                category_df=category_df,
                subcategory_df=subcategory_df,
                merchant_df=merchant_df,
                subcategory_last_year_df=subcategory_last_year_df,
                merchant_last_year_df=merchant_last_year_df,
                validate=False
            )
            
            # Clean up temporary config (same as PowerPointBuilder)
            if is_custom:
                del analyzer.categories[category_key]
            
            if analysis and 'merchant_stats' in analysis:
                merchant_stats, top_merchants = analysis['merchant_stats']
                return top_merchants
            else:
                return []
        else:
            return []
            
    except Exception as e:
        logger.error(f"Error processing category {category_key}: {e}")
        return []

def get_fan_wheel_merchants(merchant_ranker):
    """Get merchants from fan wheel data using the same logic as PowerPointBuilder"""
    try:
        # Get fan wheel data - same as PowerPointBuilder
        wheel_data = merchant_ranker.get_fan_wheel_data(
            min_audience_pct=0.20,
            top_n_communities=10
        )
        
        if not wheel_data.empty:
            merchants = wheel_data['MERCHANT'].unique().tolist()
            return merchants, wheel_data
        else:
            return [], None
            
    except Exception as e:
        logger.error(f"Error extracting fan wheel merchants: {e}")
        return [], None

def get_hot_brand_targets(analyzer, team_config, all_categories, custom_cat_info_list, category_mode):
    """Get Hot Brand Targets for each category using the same logic as the preview API"""
    hot_brand_targets = {}
    
    try:
        # Load data from Snowflake
        view_prefix = team_config['view_prefix']
        
        category_df = query_to_dataframe(f"SELECT * FROM {view_prefix}_CATEGORY_INDEXING_ALL_TIME")
        merchant_df = query_to_dataframe(f"SELECT * FROM {view_prefix}_MERCHANT_INDEXING_ALL_TIME")
        subcategory_df = query_to_dataframe(f"SELECT * FROM {view_prefix}_SUBCATEGORY_INDEXING_ALL_TIME")
        
        if category_df.empty or merchant_df.empty:
            logger.warning("No data available for Hot Brand Target selection")
            return hot_brand_targets
        
        # Process each category
        for category_key in all_categories:
            try:
                logger.info(f"   Finding Hot Brand Target for: {category_key}")
                
                if category_mode == 'custom':
                    # Custom mode - use the category_key directly
                    category_names = [category_key]
                    display_name = category_key
                else:
                    # Standard mode - determine if fixed or custom
                    is_custom = category_key in [cat['category_key'] for cat in custom_cat_info_list] if custom_cat_info_list else False
                    
                    if is_custom:
                        # Find the custom category info
                        custom_cat_info = next((cat for cat in custom_cat_info_list if cat['category_key'] == category_key), None)
                        if custom_cat_info:
                            category_names = custom_cat_info['category_names_in_data']
                            display_name = custom_cat_info['display_name']
                        else:
                            continue
                    else:
                        # Fixed category
                        category_config = analyzer.categories.get(category_key, {})
                        category_names = category_config.get('category_names_in_data', [])
                        display_name = category_config.get('display_name', category_key)
                
                if not category_names:
                    continue
                
                # Strip whitespace from category names
                category_names_clean = [name.strip() for name in category_names]
                
                # Get merchants for this category
                category_merchant_df = merchant_df[
                    merchant_df['CATEGORY'].isin(category_names_clean)
                ].copy()
                
                if category_merchant_df.empty:
                    logger.debug(f"No merchants found for Hot Brand Target category {category_key}")
                    continue
                
                # Apply subcategory filtering (same as preview API)
                if is_custom and custom_cat_info:
                    # Create a minimal category config for custom categories
                    custom_cat_config = {
                        'display_name': display_name,
                        'category_names_in_data': category_names_clean,
                        'subcategories': custom_cat_info.get('subcategories', {'include': [], 'exclude': []}),
                        'is_custom': True
                    }
                    filtered_merchant_df = analyzer._filter_merchants_by_subcategory(
                        category_merchant_df,
                        subcategory_df,
                        custom_cat_config
                    )
                else:
                    # Fixed category - use existing config
                    category_config = analyzer.categories.get(category_key, {})
                    filtered_merchant_df = analyzer._filter_merchants_by_subcategory(
                        category_merchant_df,
                        subcategory_df,
                        category_config
                    )
                
                if filtered_merchant_df.empty:
                    logger.warning(f"All merchants filtered out for Hot Brand Target category {category_key}")
                    continue
                
                # Find top merchant by composite index (same as preview API)
                team_merchants = filtered_merchant_df[
                    (filtered_merchant_df['AUDIENCE'] == analyzer.audience_name) &
                    (filtered_merchant_df['COMPARISON_POPULATION'] == analyzer.comparison_pop) &
                    (filtered_merchant_df['COMPOSITE_INDEX'] > 0) &
                    (filtered_merchant_df['PERC_AUDIENCE'] >= 0.01)
                ]
                
                if team_merchants.empty:
                    logger.debug(f"No merchants meet criteria for Hot Brand Target category {category_key}")
                    continue
                
                # Get top merchant by composite index
                top_merchant_row = team_merchants.nlargest(1, 'COMPOSITE_INDEX').iloc[0]
                hot_brand_targets[category_key] = {
                    'merchant': top_merchant_row['MERCHANT'],
                    'display_name': display_name,
                    'composite_index': top_merchant_row['COMPOSITE_INDEX'],
                    'audience_pct': top_merchant_row['PERC_AUDIENCE'] * 100,
                    'is_custom': is_custom if category_mode != 'custom' else True
                }
                
                logger.info(f"     Hot Brand Target: {top_merchant_row['MERCHANT']} (index: {top_merchant_row['COMPOSITE_INDEX']:.0f})")
                
            except Exception as e:
                logger.error(f"   Error finding Hot Brand Target for {category_key}: {e}")
                continue
        
        return hot_brand_targets
        
    except Exception as e:
        logger.error(f"Error getting Hot Brand Targets: {e}")
        return hot_brand_targets

def identify_all_missing_logos(team_key: str):
    """Identify ALL missing logos for a team's PowerPoint report"""
    
    print(f"🔍 Identifying ALL missing logos for {team_key}")
    
    # Test Snowflake connection
    if not test_connection():
        raise Exception("Failed to connect to Snowflake")
    print("✅ Connected to Snowflake")
    
    # Get team config
    config_manager = TeamConfigManager()
    team_config = config_manager.get_team_config(team_key)
    
    print(f"\nTeam: {team_config['team_name']}")
    print(f"League: {team_config['league']}")
    print(f"Category Mode: {team_config.get('category_mode', 'standard')}")
    
    # Create analyzers
    analyzer = CategoryAnalyzer(
        team_name=team_config['team_name'],
        team_short=team_config['team_name_short'],
        league=team_config['league'],
        comparison_population=team_config.get('comparison_population'),
        audience_name=team_config.get('audience_name')
    )
    
    merchant_ranker = MerchantRanker(
        team_view_prefix=team_config['view_prefix'],
        comparison_population=team_config.get('comparison_population')
    )
    
    # Initialize logo manager
    logo_manager = LogoManager()
    
    # Get all merchants using the exact same logic as PowerPointBuilder
    all_merchants = set()
    merchants_by_source = {}
    
    # 1. Get fan wheel merchants
    print(f"\n📊 Extracting merchants from fan wheel data...")
    fan_wheel_merchants, wheel_data = get_fan_wheel_merchants(merchant_ranker)
    all_merchants.update(fan_wheel_merchants)
    merchants_by_source['fan_wheel'] = fan_wheel_merchants
    print(f"   Found {len(fan_wheel_merchants)} merchants in fan wheel")
    
    if wheel_data is not None:
        print(f"   Communities analyzed: {len(wheel_data['COMMUNITY'].unique())}")
    
    # 2. Get category merchants
    print(f"\n📊 Extracting merchants from category slides...")
    
    # Determine categories based on team config
    category_mode = team_config.get('category_mode', 'standard')
    is_womens = 'women' in team_config['team_name'].lower()
    
    if category_mode == 'custom':
        # Custom mode - use team's selected categories
        custom_categories = team_config.get('custom_categories', {}).get('selected_categories', [])
        fixed_categories = []
        all_categories = custom_categories
        custom_cat_info_list = []
    else:
        # Standard mode - use fixed + custom categories
        fixed_categories = ['restaurants', 'athleisure', 'finance', 'gambling', 'travel', 'auto']
        if is_womens:
            fixed_categories.extend(['beauty', 'health'])
        
        # Get custom categories dynamically
        print(f"   Loading data to select custom categories...")
        
        # Load category and merchant data
        category_view = f"{team_config['view_prefix']}_CATEGORY_INDEXING_ALL_TIME"
        merchant_view = f"{team_config['view_prefix']}_MERCHANT_INDEXING_ALL_TIME"
        
        category_df = query_to_dataframe(f"SELECT * FROM {category_view}")
        merchant_df = query_to_dataframe(f"SELECT * FROM {merchant_view}")
        
        if category_df.empty or merchant_df.empty:
            print("❌ No data available for custom category selection")
            return
        
        # Get custom categories using the same method as PowerPointBuilder
        custom_categories = analyzer.get_custom_categories(
            category_df=category_df,
            merchant_df=merchant_df,
            is_womens_team=is_womens,
            existing_categories=fixed_categories
        )
        
        custom_cat_info_list = custom_categories
        all_categories = fixed_categories + [cat['category_key'] for cat in custom_categories]
    
    # Process all categories
    category_merchants = []
    merchants_by_category = {}
    
    for category_key in all_categories:
        try:
            print(f"   Processing category: {category_key}")
            
            if category_mode == 'custom':
                # Custom mode - process as custom
                merchants = get_merchants_for_category(analyzer, team_config, category_key, is_custom=True)
            else:
                # Standard mode - determine if fixed or custom
                is_custom = category_key in [cat['category_key'] for cat in custom_cat_info_list] if custom_cat_info_list else False
                
                if is_custom:
                    # Find the custom category info
                    custom_cat_info = next((cat for cat in custom_cat_info_list if cat['category_key'] == category_key), None)
                    if custom_cat_info:
                        merchants = get_merchants_for_category(analyzer, team_config, custom_cat_info['display_name'], is_custom=True)
                    else:
                        merchants = []
                else:
                    merchants = get_merchants_for_category(analyzer, team_config, category_key, is_custom=False)
            
            category_merchants.extend(merchants)
            merchants_by_category[category_key] = merchants
            print(f"     Found {len(merchants)} merchants in {category_key}")
            
        except Exception as e:
            logger.error(f"   Error processing category {category_key}: {e}")
            continue
    
    # Add category merchants to overall set
    all_merchants.update(category_merchants)
    merchants_by_source['categories'] = list(set(category_merchants))
    
    # 3. Get Hot Brand Targets
    print(f"\n📊 Extracting Hot Brand Targets...")
    hot_brand_targets = get_hot_brand_targets(analyzer, team_config, all_categories, custom_cat_info_list, category_mode)
    hot_brand_merchants = [target['merchant'] for target in hot_brand_targets.values()]
    all_merchants.update(hot_brand_merchants)
    merchants_by_source['hot_brand_targets'] = hot_brand_merchants
    print(f"   Found {len(hot_brand_merchants)} Hot Brand Targets")
    
    print(f"\n📊 Total unique merchants found: {len(all_merchants)}")
    
    # Check logo availability using LogoManager
    print(f"\n🖼️  Checking logo availability...")
    merchants_list = list(all_merchants)
    logo_report = logo_manager.add_missing_logos_report(merchants_list)
    
    # Generate comprehensive report
    print(f"\n{'='*80}")
    print(f"COMPREHENSIVE MISSING LOGO REPORT FOR {team_config['team_name'].upper()}")
    print(f"{'='*80}")
    
    with_logos = sum(logo_report.values())
    missing_count = len(merchants_list) - with_logos
    coverage = (with_logos / len(merchants_list)) * 100 if merchants_list else 0
    
    print(f"\n📊 OVERALL SUMMARY:")
    print(f"   Total merchants found: {len(merchants_list)}")
    print(f"   With logos: {with_logos}")
    print(f"   Missing logos: {missing_count}")
    print(f"   Coverage: {coverage:.1f}%")
    
    # List missing logos
    missing_merchants = [merchant for merchant, has_logo in logo_report.items() if not has_logo]
    
    if missing_merchants:
        print(f"\n❌ ALL MISSING LOGOS ({len(missing_merchants)}):")
        for i, merchant in enumerate(sorted(missing_merchants), 1):
            print(f"   {i:2d}. {merchant}")
    else:
        print(f"\n✅ ALL MERCHANTS HAVE LOGOS!")
    
    # Breakdown by source
    print(f"\n📋 BREAKDOWN BY SOURCE:")
    
    # Fan wheel breakdown
    fan_wheel_missing = [merchant for merchant in merchants_by_source['fan_wheel'] if not logo_report.get(merchant, True)]
    print(f"   Fan Wheel:")
    print(f"     Total: {len(merchants_by_source['fan_wheel'])}")
    print(f"     With logos: {len(merchants_by_source['fan_wheel']) - len(fan_wheel_missing)}")
    print(f"     Missing: {len(fan_wheel_missing)}")
    if fan_wheel_missing:
        print(f"     Missing: {', '.join(fan_wheel_missing)}")
    
    # Categories breakdown
    category_missing = [merchant for merchant in merchants_by_source['categories'] if not logo_report.get(merchant, True)]
    print(f"   Categories:")
    print(f"     Total: {len(merchants_by_source['categories'])}")
    print(f"     With logos: {len(merchants_by_source['categories']) - len(category_missing)}")
    print(f"     Missing: {len(category_missing)}")
    if category_missing:
        print(f"     Missing: {', '.join(category_missing)}")
    
    # Hot Brand Targets breakdown
    hot_brand_missing = [merchant for merchant in merchants_by_source['hot_brand_targets'] if not logo_report.get(merchant, True)]
    print(f"   Hot Brand Targets:")
    print(f"     Total: {len(merchants_by_source['hot_brand_targets'])}")
    print(f"     With logos: {len(merchants_by_source['hot_brand_targets']) - len(hot_brand_missing)}")
    print(f"     Missing: {len(hot_brand_missing)}")
    if hot_brand_missing:
        print(f"     Missing: {', '.join(hot_brand_missing)}")
    
    # Detailed category breakdown
    print(f"\n📋 DETAILED CATEGORY BREAKDOWN:")
    for category_key, merchants in merchants_by_category.items():
        if merchants:
            category_missing = [m for m in merchants if not logo_report.get(m, True)]
            print(f"   {category_key.upper()}:")
            print(f"     Total: {len(merchants)}")
            print(f"     With logos: {len(merchants) - len(category_missing)}")
            print(f"     Missing: {len(category_missing)}")
            if category_missing:
                print(f"     Missing: {', '.join(category_missing)}")
    
    # Fan wheel community breakdown
    if wheel_data is not None:
        print(f"\n🏘️  FAN WHEEL COMMUNITY BREAKDOWN:")
        community_data = wheel_data.groupby('COMMUNITY')['MERCHANT'].apply(list).to_dict()
        
        for community, merchants in community_data.items():
            community_missing = [m for m in merchants if not logo_report.get(m, True)]
            print(f"   {community}:")
            print(f"     Merchants: {len(merchants)}")
            print(f"     Missing logos: {len(community_missing)}")
            if community_missing:
                print(f"     Missing: {', '.join(community_missing)}")
    
    # Hot Brand Target breakdown
    if hot_brand_targets:
        print(f"\n🎯 HOT BRAND TARGET BREAKDOWN:")
        for category_key, target_info in hot_brand_targets.items():
            merchant = target_info['merchant']
            has_logo = logo_report.get(merchant, True)
            status = "✅" if has_logo else "❌"
            print(f"   {category_key.upper()}:")
            print(f"     Hot Brand Target: {status} {merchant}")
            print(f"     Composite Index: {target_info['composite_index']:.0f}")
            print(f"     Audience: {target_info['audience_pct']:.1f}%")
            print(f"     Type: {'Custom' if target_info['is_custom'] else 'Fixed'}")
    
    return {
        'total_merchants': len(merchants_list),
        'with_logos': with_logos,
        'missing_logos': missing_count,
        'coverage': coverage,
        'missing_merchants': missing_merchants,
        'logo_report': logo_report,
        'merchants_by_source': merchants_by_source,
        'merchants_by_category': merchants_by_category,
        'hot_brand_targets': hot_brand_targets
    }

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python identify_all_missing_logos.py <team_key>")
        print("Example: python identify_all_missing_logos.py detroit_tigers")
        sys.exit(1)
    
    team_key = sys.argv[1]
    
    try:
        result = identify_all_missing_logos(team_key)
        print(f"\n✅ Comprehensive analysis complete!")
        print(f"   Missing logos: {result['missing_logos']} out of {result['total_merchants']} merchants")
        print(f"   Coverage: {result['coverage']:.1f}%")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
