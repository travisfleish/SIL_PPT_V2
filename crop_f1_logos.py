#!/usr/bin/env python3
"""
Crop F1 logos to circles and save them to the merchants folder
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
    """Crop all F1 logos to circles"""
    f1_logos_dir = Path(__file__).parent / "f1_logos"
    merchants_dir = Path(__file__).parent / "assets" / "logos" / "merchants"
    
    # Get all logo files from f1_logos directory
    logo_files = list(f1_logos_dir.glob("*"))
    logo_files = [f for f in logo_files if f.is_file() and f.suffix.lower() in ['.png', '.jpeg', '.jpg']]
    
    if not logo_files:
        print("⚠️  No logo files found in f1_logos directory")
        return
    
    print(f"🎨 Cropping {len(logo_files)} F1 logos to circles...\n")
    
    for logo_path in logo_files:
        # Create output filename (always .png, use the stem of the original file)
        output_filename = logo_path.stem + ".png"
        output_path = merchants_dir / output_filename
        
        try:
            crop_image_to_circle(logo_path, output_path, size=400)
        except Exception as e:
            print(f"❌ Error processing {logo_path.name}: {e}")
    
    print("\n✨ Done!")

if __name__ == "__main__":
    main()

