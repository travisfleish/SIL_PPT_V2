#!/usr/bin/env python3
"""
Crop Shake Shack and ARAMARK logos to circles, removing borders
"""

from pathlib import Path
from PIL import Image, ImageDraw
import numpy as np

def remove_border_and_crop_to_circle(img_path, output_path, size=400, border_threshold=30):
    """Remove border and crop to circle"""
    img = Image.open(img_path).convert("RGBA")
    
    # Convert to numpy array for easier processing
    img_array = np.array(img)
    
    # Find the bounding box of non-transparent, non-black content
    # Get alpha channel
    alpha = img_array[:, :, 3] if img_array.shape[2] == 4 else np.ones((img_array.shape[0], img_array.shape[1]))
    
    # Find where there's actual content (not transparent and not too dark)
    # Check if pixel is not too dark (RGB values > threshold)
    if img_array.shape[2] == 4:
        rgb = img_array[:, :, :3]
        # Check if any RGB channel is above threshold (not black/dark border)
        has_content = (rgb.max(axis=2) > border_threshold) & (alpha > 0)
    else:
        has_content = (img_array.max(axis=2) > border_threshold) & (alpha > 0)
    
    # Find bounding box
    rows = np.any(has_content, axis=1)
    cols = np.any(has_content, axis=0)
    
    if rows.any() and cols.any():
        top, bottom = np.where(rows)[0][[0, -1]]
        left, right = np.where(cols)[0][[0, -1]]
        
        # Add small padding
        padding = 5
        top = max(0, top - padding)
        left = max(0, left - padding)
        bottom = min(img.height, bottom + padding + 1)
        right = min(img.width, right + padding + 1)
        
        # Crop to content area
        img = img.crop((left, top, right, bottom))
    
    # Make it square (use the larger dimension)
    width, height = img.size
    max_dim = max(width, height)
    
    # Create square image with transparent background
    square_img = Image.new('RGBA', (max_dim, max_dim), (0, 0, 0, 0))
    
    # Center the cropped image
    paste_x = (max_dim - width) // 2
    paste_y = (max_dim - height) // 2
    square_img.paste(img, (paste_x, paste_y), img if img.mode == 'RGBA' else None)
    
    # Resize to desired size
    square_img = square_img.resize((size, size), Image.Resampling.LANCZOS)
    
    # Create circular mask
    mask = Image.new('L', (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, size, size), fill=255)
    
    # Apply mask
    output = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    output.paste(square_img, (0, 0))
    output.putalpha(mask)
    
    # Save as PNG
    output.save(output_path, 'PNG')
    print(f"✓ Cropped and saved: {output_path.name}")

def main():
    """Crop Shake Shack and ARAMARK logos"""
    logo_dir = Path(__file__).parent / "assets" / "logos" / "merchants"
    
    logos_to_crop = [
        ("shake_shack", 30),  # Shake Shack with threshold 30
        ("aramark", 30),       # ARAMARK with threshold 30 (to remove thick black border)
    ]
    
    print("🎨 Cropping logos to circles (removing borders)...\n")
    
    for logo_name, threshold in logos_to_crop:
        # Try different file extensions
        found = False
        for ext in ['.png', '.jpeg', '.jpg']:
            logo_path = logo_dir / f"{logo_name}{ext}"
            if logo_path.exists():
                output_path = logo_dir / f"{logo_name}.png"
                try:
                    remove_border_and_crop_to_circle(logo_path, output_path, size=400, border_threshold=threshold)
                    found = True
                    break
                except Exception as e:
                    print(f"❌ Error processing {logo_path.name}: {e}")
                    import traceback
                    traceback.print_exc()
        
        if not found:
            print(f"⚠️  File not found: {logo_name}.*")
    
    print("\n✨ Done!")

if __name__ == "__main__":
    main()

