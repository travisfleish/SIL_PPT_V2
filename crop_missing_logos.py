#!/usr/bin/env python3
"""
Crop the 9 missing logos to circles and save them
"""

from pathlib import Path
from PIL import Image, ImageDraw

def crop_image_to_circle(img_path, output_path, size=400):
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
    
    # Save as PNG (to preserve transparency)
    output.save(output_path, 'PNG')
    print(f"✓ Cropped and saved: {output_path.name}")

def main():
    """Crop all 9 missing logos to circles"""
    logo_dir = Path(__file__).parent / "assets" / "logos" / "merchants"
    
    # List of logos to crop (with their actual filenames)
    logos_to_crop = [
        "crumbl_cookies.jpeg",
        "h&m.jpeg",
        "ikea.png",
        "raising_cane's.jpeg",
        "wingstop.jpeg",
        "five_guys.jpeg",
        "whole_foods_market.jpeg",
        "spotify.jpeg",
        "trader_joe's.jpeg"
    ]
    
    print("🎨 Cropping logos to circles...\n")
    
    for logo_file in logos_to_crop:
        logo_path = logo_dir / logo_file
        
        if not logo_path.exists():
            print(f"⚠️  File not found: {logo_file}")
            continue
        
        # Create output filename (change extension to .png)
        output_filename = logo_path.stem + ".png"
        output_path = logo_dir / output_filename
        
        try:
            crop_image_to_circle(logo_path, output_path, size=400)
        except Exception as e:
            print(f"❌ Error processing {logo_file}: {e}")
    
    print("\n✨ Done!")

if __name__ == "__main__":
    main()

