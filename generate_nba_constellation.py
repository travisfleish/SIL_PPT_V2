#!/usr/bin/env python3
"""
Create merchant constellation for top NBA brands
- Aggregated across all NBA teams
- Sized by COMPOSITE_INDEX
- Circular logos arranged in golden spiral pattern
- Transparent background
"""

import sys
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from PIL import Image, ImageDraw
import numpy as np
import logging
import os
import random
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))

from data_processors.snowflake_connector import query_to_dataframe

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_all_aggregated_merchants(top_n: int = 20, min_perc_audience: float = 0.20) -> pd.DataFrame:
    """
    Get top merchants for NBA All Fans audience
    
    Args:
        top_n: Number of top merchants to return
        min_perc_audience: Minimum PERC_AUDIENCE threshold (default 20%)
    
    Returns:
        DataFrame with merchant metrics
    """
    logger.info(f"🔍 Getting top {top_n} NBA merchants (AUDIENCE='NBA All Fans', PERC_AUDIENCE>{min_perc_audience*100:.0f}%)...")
    
    # Temporarily set schema
    original_schema = os.getenv('SNOWFLAKE_SCHEMA')
    os.environ['SNOWFLAKE_SCHEMA'] = 'NBA_LEAGUE_INSIGHTS'
    
    try:
        query = """
        SELECT 
            MERCHANT,
            PARENT_MERCHANT,
            CATEGORY,
            SUBCATEGORY,
            COMPARISON_POPULATION,
            PERC_AUDIENCE,
            PERC_INDEX,
            SPC_INDEX,
            SPP_INDEX,
            PPC_INDEX,
            COMPOSITE_INDEX
        FROM SILAB_DATA_SHARING.NBA_LEAGUE_INSIGHTS.V_NBA_LEAGUE_GENIUS_SPORTS_MERCHANT_INDEXING_ALL_TIME
        WHERE AUDIENCE = 'NBA All Fans'
        AND COMPARISON_POPULATION = 'General Population'
        AND MERCHANT != 'LEVELUP'  -- Exclude LEVELUP
        AND UPPER(MERCHANT) != 'LEVY RESTAURANTS'  -- Exclude Levy Restaurants
        AND UPPER(MERCHANT) != 'ARAMARK'  -- Exclude ARAMARK
        AND UPPER(MERCHANT) NOT LIKE '%NBA%'
        AND UPPER(PARENT_MERCHANT) NOT LIKE '%NBA%'
        AND PERC_AUDIENCE > {min_perc}
        ORDER BY PERC_INDEX DESC
        LIMIT {top_n}
        """
        
        query = query.format(min_perc=min_perc_audience, top_n=top_n)
        df = query_to_dataframe(query)
        
        logger.info(f"✅ Found {len(df)} merchants")
        return df
    finally:
        # Restore original schema
        if original_schema:
            os.environ['SNOWFLAKE_SCHEMA'] = original_schema


def get_all_available_logos():
    """Get list of all available logo files"""
    logo_dir = Path(__file__).parent / "assets" / "logos" / "merchants"
    logo_files = []
    logo_files.extend(list(logo_dir.glob("*.png")))
    logo_files.extend(list(logo_dir.glob("*.jpg")))
    logo_files.extend(list(logo_dir.glob("*.jpeg")))
    return logo_files


def get_logo_path(merchant_name, available_logos=None):
    """Try to find logo file for merchant, or return random placeholder"""
    logo_dir = Path(__file__).parent / "assets" / "logos" / "merchants"
    
    # Try various filename formats - handle spaces, hyphens, apostrophes
    base = merchant_name.lower()
    formats = [
        base.replace(' ', '_').replace('-', '_').replace("'", ""),  # baskin_robbins, innout_burger
        base.replace(' ', '_').replace('-', '').replace("'", ""),   # baskinrobbins, innout_burger
        base.replace(' ', '').replace('-', '').replace("'", ""),   # baskinrobbins, innoutburger
        base.replace(' ', '_').replace("'", ""),                    # jimmy_johns, peets_coffee
        base.replace(' ', '-').replace("'", ""),                    # jimmy-johns
        base.replace(' ', '_'),                                     # le_pain_quotidien
        base.replace(' ', '-'),                                     # le-pain-quotidien
        base.replace("'", ""),                                      # peets_coffee
        base.replace(' ', ''),                                      # safeway
    ]
    
    # Remove duplicates while preserving order
    seen = set()
    unique_formats = []
    for fmt in formats:
        if fmt not in seen:
            seen.add(fmt)
            unique_formats.append(fmt)
    
    for format_name in unique_formats:
        for ext in ['.png', '.jpg', '.jpeg']:
            logo_path = logo_dir / f"{format_name}{ext}"
            if logo_path.exists():
                return logo_path
    
    # If not found and we have available logos, return a random one as placeholder
    if available_logos and len(available_logos) > 0:
        return random.choice(available_logos)
    
    return None


def crop_image_to_circle(img_path, size=200):
    """Crop an image to a perfect circle with transparent background"""
    img = Image.open(img_path).convert("RGBA")
    
    # Make it square first
    min_dim = min(img.size)
    left = (img.width - min_dim) // 2
    top = (img.height - min_dim) // 2
    img = img.crop((left, top, left + min_dim, top + min_dim))
    
    # Resize to desired size
    img = img.resize((size, size), Image.Resampling.LANCZOS)
    
    # Create circular mask
    mask = Image.new('L', (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, size, size), fill=255)
    
    # Apply mask
    output = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    output.paste(img, (0, 0))
    output.putalpha(mask)
    
    return output


def create_nba_constellation(df, output_path, top_n=20):
    """
    Create constellation from top NBA merchants by PERC_INDEX
    Sized by COMPOSITE_INDEX
    """
    logger.info(f"📊 Loaded {len(df)} merchants")
    if len(df) == 0:
        logger.error("❌ No merchants found!")
        return
    
    logger.info(f"   Top merchant: {df.iloc[0]['MERCHANT']} (PERC_INDEX: {df.iloc[0]['PERC_INDEX']:.1f}, PERC_AUDIENCE: {df.iloc[0]['PERC_AUDIENCE']*100:.2f}%)")
    
    # Take top N merchants
    top_merchants = df.head(top_n)
    
    logger.info(f"\n🎨 Creating constellation with top {len(top_merchants)} merchants by PERC_INDEX...")
    logger.info(f"   Sizing by: PERC_INDEX\n")
    
    # Get all available logos for placeholders
    available_logos = get_all_available_logos()
    logger.info(f"   Found {len(available_logos)} available logos for placeholders\n")
    
    # Create figure with transparent background
    fig, ax = plt.subplots(figsize=(16, 16), facecolor='none')
    ax.set_facecolor('none')
    ax.set_aspect('equal')
    ax.set_xlim(-1.5, 1.5)
    ax.set_ylim(-1.5, 1.5)
    ax.axis('off')
    
    # Calculate positions in spiral/circular pattern
    n_merchants = len(top_merchants)
    
    # Use golden angle for optimal spacing
    golden_angle = np.pi * (3 - np.sqrt(5))
    
    # Normalize PERC_INDEX values for sizing
    max_perc_index = top_merchants['PERC_INDEX'].max()
    min_perc_index = top_merchants['PERC_INDEX'].min()
    
    for i, (_, row) in enumerate(top_merchants.iterrows()):
        merchant = row['MERCHANT']
        perc_index = row['PERC_INDEX']
        
        # Calculate position using golden spiral
        angle = i * golden_angle
        # Vary radius based on rank (earlier rank = closer to center)
        radius = 0.3 + (i / n_merchants) * 0.9
        
        x = radius * np.cos(angle)
        y = radius * np.sin(angle)
        
        # Size based on PERC_INDEX with more variation (0.15 to 0.45)
        normalized_perc_index = (perc_index - min_perc_index) / (max_perc_index - min_perc_index) if max_perc_index != min_perc_index else 0.5
        size = 0.15 + (normalized_perc_index * 0.30)
        
        # Draw connection line to center (black for white background)
        ax.plot([0, x], [0, y], color='black', alpha=0.3, linewidth=1, zorder=1)
        
        # Try to load and display logo (with random placeholder if not found)
        # First check if the real logo exists
        real_logo_path = get_logo_path(merchant, available_logos=None)
        logo_path = get_logo_path(merchant, available_logos)
        
        if logo_path:
            try:
                # Create circular logo
                circular_logo = crop_image_to_circle(logo_path, size=400)
                
                # Convert to array for display
                logo_array = np.array(circular_logo)
                
                # Z-order based on rank: higher importance = higher z-order (renders on top)
                logo_zorder = 100 - i  # First merchant gets 100, last gets 100-n
                
                # Display the circular logo
                extent = [x - size/2, x + size/2, y - size/2, y + size/2]
                ax.imshow(logo_array, extent=extent, zorder=logo_zorder, aspect='auto')
                
                # Add very thin black border around logo
                border_circle = Circle((x, y), size/2, facecolor='none', 
                                      edgecolor='black', linewidth=1, zorder=logo_zorder+1)
                ax.add_patch(border_circle)
                
                if real_logo_path:
                    logger.info(f"  ✓ Added logo for {merchant}")
                else:
                    logger.info(f"  🎲 Using placeholder logo for {merchant}")
                
            except Exception as e:
                logger.warning(f"  ✗ Error loading logo for {merchant}: {e}")
                # Fallback: draw a white circle with thin black border
                logo_zorder = 100 - i
                circle = Circle((x, y), size/2, facecolor='white', alpha=0.8, 
                              edgecolor='black', linewidth=1, zorder=logo_zorder)
                ax.add_patch(circle)
        else:
            logger.warning(f"  ⚠️  No logo available for {merchant}")
            # Draw a white circle with thin black border as placeholder
            logo_zorder = 100 - i
            circle = Circle((x, y), size/2, facecolor='white', alpha=0.8,
                          edgecolor='black', linewidth=1, zorder=logo_zorder)
            ax.add_patch(circle)
    
    # Add central point (constellation anchor) - black for white background
    center_circle = Circle((0, 0), 0.08, color='black', alpha=0.9, zorder=10)
    ax.add_patch(center_circle)
    
    # Add subtle outer glow effect - black for white background
    for i in range(5):
        glow_circle = Circle((0, 0), 0.08 + i*0.02, color='black', 
                            alpha=0.1/(i+1), fill=False, linewidth=2, zorder=9-i)
        ax.add_patch(glow_circle)
    
    # Save with transparent background
    plt.savefig(output_path, dpi=300, facecolor='none', edgecolor='none', 
                bbox_inches='tight', transparent=True)
    logger.info(f"\n✅ Saved NBA constellation: {output_path}")
    plt.close()


def main():
    """Generate NBA merchant constellation"""
    logger.info("="*80)
    logger.info("NBA TOP BRANDS CONSTELLATION")
    logger.info("="*80)
    
    # Get top merchants for NBA All Fans
    df = get_all_aggregated_merchants(top_n=20, min_perc_audience=0.20)
    
    if len(df) == 0:
        logger.error("❌ No merchants found!")
        return
    
    # Display top merchants
    logger.info("\n📊 Top 20 Merchants by PERC_INDEX (PERC_AUDIENCE > 20%):")
    logger.info("-"*80)
    for idx, (_, row) in enumerate(df.head(20).iterrows(), 1):
        logger.info(f"   {idx:2d}. {row['MERCHANT']:<40} "
                   f"PERC_INDEX: {row['PERC_INDEX']:>6.1f} | "
                   f"PERC_AUDIENCE: {row['PERC_AUDIENCE']*100:>5.2f}%")
    
    # Create constellation
    output_path = Path('nba_top_brands_constellation.png')
    create_nba_constellation(df, output_path, top_n=20)
    
    logger.info("\n" + "="*80)
    logger.info("✨ Constellation Complete!")
    logger.info("="*80)


if __name__ == "__main__":
    main()

