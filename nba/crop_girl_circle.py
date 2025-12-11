#!/usr/bin/env python3
"""
Crop girl.png to circle with thin black border
"""

from pathlib import Path
from PIL import Image, ImageDraw
import numpy as np

def crop_to_circle_with_border(img_path, output_path, size=400, border_width=3):
    """Crop image to circle with thin black border"""
    img = Image.open(img_path).convert("RGBA")
    
    # Make it square first (use the smaller dimension to avoid cropping important parts)
    width, height = img.size
    min_dim = min(width, height)
    
    # Center crop
    left = (width - min_dim) // 2
    top = (height - min_dim) // 2
    img = img.crop((left, top, left + min_dim, top + min_dim))
    
    # Resize to desired size
    img = img.resize((size, size), Image.Resampling.LANCZOS)
    
    # Create circular mask
    mask = Image.new('L', (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, size, size), fill=255)
    
    # Apply mask to create circular image
    circular_img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    circular_img.paste(img, (0, 0))
    circular_img.putalpha(mask)
    
    # Create image with border (larger canvas)
    border_size = size + (border_width * 2)
    output = Image.new('RGBA', (border_size, border_size), (0, 0, 0, 0))
    
    # Draw black border circle
    border_draw = ImageDraw.Draw(output)
    border_draw.ellipse((0, 0, border_size, border_size), fill=(0, 0, 0, 255))
    
    # Draw white/transparent inner circle (slightly smaller to create border effect)
    inner_size = border_size - (border_width * 2)
    inner_mask = Image.new('L', (inner_size, inner_size), 0)
    inner_draw = ImageDraw.Draw(inner_mask)
    inner_draw.ellipse((0, 0, inner_size, inner_size), fill=255)
    
    # Paste the circular image in the center
    paste_x = border_width
    paste_y = border_width
    output.paste(circular_img, (paste_x, paste_y), circular_img)
    
    # Save as PNG
    output.save(output_path, 'PNG')
    print(f"✓ Cropped and saved: {output_path.name} (size: {border_size}x{border_size}, border: {border_width}px)")

def main():
    """Crop girl.png to circle with border"""
    girl_path = Path("girl.png")
    output_path = Path("girl.png")  # Overwrite original
    
    if not girl_path.exists():
        print(f"⚠️  File not found: {girl_path}")
        return
    
    print("🎨 Cropping girl.png to circle with thin black border...\n")
    
    try:
        crop_to_circle_with_border(girl_path, output_path, size=400, border_width=3)
        print("\n✨ Done!")
    except Exception as e:
        print(f"❌ Error processing girl.png: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

