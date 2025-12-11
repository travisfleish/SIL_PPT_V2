#!/usr/bin/env python3
"""
Crop REI and SKIMS logos to circles
"""

from pathlib import Path
from PIL import Image, ImageDraw
import numpy as np

def crop_skims_text_only(img_path, output_path, size=400):
    """Crop SKIMS logo focusing exclusively on text, removing black borders, white background"""
    img = Image.open(img_path).convert("RGB")
    
    # Convert to numpy array
    img_array = np.array(img)
    
    # Find pixels that are NOT black (text and white background)
    # Black is very dark (RGB all < 50)
    # We want white background and text (which might be dark but not pure black)
    # Exclude pure black borders (RGB all < 30)
    is_not_black = (img_array[:, :, 0] > 30) | (img_array[:, :, 1] > 30) | (img_array[:, :, 2] > 30)
    
    # Find bounding box of non-black content
    rows = np.any(is_not_black, axis=1)
    cols = np.any(is_not_black, axis=0)
    
    if rows.any() and cols.any():
        top, bottom = np.where(rows)[0][[0, -1]]
        left, right = np.where(cols)[0][[0, -1]]
        
        # Add padding
        padding = 10
        top = max(0, top - padding)
        left = max(0, left - padding)
        bottom = min(img.height, bottom + padding + 1)
        right = min(img.width, right + padding + 1)
        
        # Crop to content area
        img = img.crop((left, top, right, bottom))
    
    # Convert black pixels to white (remove black borders)
    img_array = np.array(img)
    # Find black pixels (all channels < 50)
    black_mask = (img_array[:, :, 0] < 50) & (img_array[:, :, 1] < 50) & (img_array[:, :, 2] < 50)
    # Replace black with white
    img_array[black_mask] = [255, 255, 255]
    img = Image.fromarray(img_array)
    
    # Make it square (use the larger dimension)
    width, height = img.size
    max_dim = max(width, height)
    
    # Create square image with white background
    square_img = Image.new('RGB', (max_dim, max_dim), (255, 255, 255))
    
    # Center the cropped image
    paste_x = (max_dim - width) // 2
    paste_y = (max_dim - height) // 2
    square_img.paste(img, (paste_x, paste_y))
    
    # Resize to desired size
    square_img = square_img.resize((size, size), Image.Resampling.LANCZOS)
    
    # Convert to RGBA for circular mask
    square_img = square_img.convert('RGBA')
    
    # Create circular mask
    mask = Image.new('L', (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, size, size), fill=255)
    
    # Apply mask
    output = Image.new('RGBA', (size, size), (255, 255, 255, 255))  # White background
    output.paste(square_img, (0, 0))
    output.putalpha(mask)
    
    # Save as PNG
    output.save(output_path, 'PNG')
    print(f"✓ Cropped and saved: {output_path.name}")

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
    """Crop REI and SKIMS logos"""
    logo_dir = Path(__file__).parent / "assets" / "logos" / "merchants"
    
    # Process REI
    rei_path = logo_dir / "rei.png"
    if rei_path.exists():
        print("🎨 Cropping REI logo to circle...\n")
        try:
            remove_border_and_crop_to_circle(rei_path, rei_path, size=400)
            print(f"✅ REI logo processed\n")
        except Exception as e:
            print(f"❌ Error processing rei.png: {e}")
            import traceback
            traceback.print_exc()
    else:
        print(f"⚠️  File not found: rei.png")
    
    # Process SKIMS (handle both .jpg and .png) - use specialized text-only cropping
    skims_paths = [
        logo_dir / "skims.jpg",
        logo_dir / "skims.png"
    ]
    
    skims_processed = False
    for skims_path in skims_paths:
        if skims_path.exists():
            print("🎨 Cropping SKIMS logo to circle (text only, white background)...\n")
            try:
                # Always save as PNG, use specialized SKIMS cropping
                output_path = logo_dir / "skims.png"
                crop_skims_text_only(skims_path, output_path, size=400)
                print(f"✅ SKIMS logo processed (text only, white background)\n")
                skims_processed = True
                
                # If original was JPG, remove it
                if skims_path.suffix.lower() == '.jpg' and skims_path != output_path:
                    skims_path.unlink()
                    print(f"✓ Removed original JPG file\n")
                break
            except Exception as e:
                print(f"❌ Error processing {skims_path.name}: {e}")
                import traceback
                traceback.print_exc()
    
    if not skims_processed:
        print(f"⚠️  SKIMS logo file not found (checked skims.jpg and skims.png)")
    
    print("✨ Done!")

if __name__ == "__main__":
    main()

