#!/usr/bin/env python3
"""
circle_crop_images.py
Utility to crop all fan images in the directory into circles with transparent backgrounds
Processes all images in assets/logos/fans/ and saves circular versions
"""

from pathlib import Path
from PIL import Image, ImageDraw, ImageOps
import sys
import shutil
from datetime import datetime
import argparse


def create_circular_mask(size):
    """Create a circular mask for cropping"""
    # Create a new image with transparent background
    mask = Image.new('L', size, 0)
    draw = ImageDraw.Draw(mask)

    # Draw a white circle
    draw.ellipse((0, 0) + size, fill=255)

    return mask


def crop_image_circular(image_path, output_path=None, size=None, backup=True):
    """
    Crop an image into a circle with transparent background

    Args:
        image_path: Path to input image
        output_path: Path for output (None = overwrite original)
        size: Tuple of (width, height) for output size (None = keep original)
        backup: Whether to create a backup of the original

    Returns:
        Path to the cropped image
    """
    image_path = Path(image_path)

    if not image_path.exists():
        print(f"❌ Image not found: {image_path}")
        return None

    try:
        # Open the image
        img = Image.open(image_path).convert('RGBA')
        original_size = img.size

        # Resize if requested
        if size:
            # Calculate the aspect ratio preserving resize
            aspect = min(size[0] / img.width, size[1] / img.height)
            new_size = (int(img.width * aspect), int(img.height * aspect))
            img = img.resize(new_size, Image.Resampling.LANCZOS)

            # Create a new image with the exact requested size
            final_img = Image.new('RGBA', size, (0, 0, 0, 0))
            # Paste the resized image in the center
            x = (size[0] - new_size[0]) // 2
            y = (size[1] - new_size[1]) // 2
            final_img.paste(img, (x, y))
            img = final_img

        # Get the size for the mask
        mask_size = img.size

        # Make it square (crop to center)
        if mask_size[0] != mask_size[1]:
            # Find the smaller dimension
            min_dim = min(mask_size)

            # Calculate crop box to center the square
            left = (mask_size[0] - min_dim) // 2
            top = (mask_size[1] - min_dim) // 2
            right = left + min_dim
            bottom = top + min_dim

            # Crop to square
            img = img.crop((left, top, right, bottom))
            mask_size = (min_dim, min_dim)

        # Create circular mask
        mask = create_circular_mask(mask_size)

        # Create output image with transparent background
        output = Image.new('RGBA', mask_size, (0, 0, 0, 0))
        output.paste(img, (0, 0))

        # Apply the circular mask
        output.putalpha(mask)

        # Determine output path
        if output_path is None:
            output_path = image_path

            # Create backup if requested
            if backup:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_dir = image_path.parent / 'backups'
                backup_dir.mkdir(exist_ok=True)
                backup_path = backup_dir / f"{image_path.stem}_backup_{timestamp}{image_path.suffix}"
                shutil.copy2(image_path, backup_path)
                print(f"📁 Backup created: {backup_path.name}")

        # Save the circular image
        output.save(output_path, 'PNG')  # Save as PNG to preserve transparency
        print(f"✅ Cropped: {image_path.name} -> {Path(output_path).name}")
        print(f"   Original size: {original_size} -> Final size: {mask_size}")

        return output_path

    except Exception as e:
        print(f"❌ Error processing {image_path.name}: {str(e)}")
        return None


def process_all_fan_images(project_root=None, size=None, backup=True, preview_only=False):
    """
    Process all fan images in the assets/logos/fans directory

    Args:
        project_root: Path to project root (None = auto-detect)
        size: Tuple of (width, height) for output size (None = keep original)
        backup: Whether to create backups
        preview_only: If True, only show what would be processed without making changes
    """
    # Find project root if not provided
    if project_root is None:
        current_file = Path(__file__).resolve()
        project_root = current_file.parent

        # Search for project root by looking for assets directory
        while project_root.parent != project_root:
            if (project_root / 'assets').exists():
                break
            project_root = project_root.parent

    # Find the fans directory
    fans_dir = Path(project_root) / 'assets' / 'logos' / 'fans'

    if not fans_dir.exists():
        print(f"❌ Fans directory not found: {fans_dir}")
        return

    print(f"🔍 Processing fan images in: {fans_dir}")
    print("=" * 60)

    # Find all image files
    image_extensions = ['.png', '.jpg', '.jpeg', '.PNG', '.JPG', '.JPEG']
    image_files = []

    for ext in image_extensions:
        image_files.extend(fans_dir.glob(f"*{ext}"))

    # Filter to only files containing "_Fanpic"
    fan_images = [f for f in image_files if '_Fanpic' in f.name]

    if not fan_images:
        print("❌ No fan images found (looking for files with '_Fanpic' in name)")
        return

    print(f"Found {len(fan_images)} fan images to process:")
    for img in sorted(fan_images):
        print(f"  - {img.name}")

    if preview_only:
        print("\n👁️ Preview mode - no changes will be made")
        return

    print(f"\n🎨 Starting circular crop process...")
    if size:
        print(f"📐 Target size: {size[0]}x{size[1]} pixels")
    else:
        print(f"📐 Keeping original sizes")

    if backup:
        print(f"💾 Backups will be created in 'backups' subdirectory")

    # Process each image
    success_count = 0
    for image_path in sorted(fan_images):
        print(f"\n📸 Processing {image_path.name}...")

        # For fan images, save as PNG to ensure transparency
        output_path = image_path.with_suffix('.png')

        result = crop_image_circular(
            image_path,
            output_path,
            size=size,
            backup=backup
        )

        if result:
            success_count += 1

            # If we converted from jpg to png, remove the original jpg
            if image_path.suffix.lower() in ['.jpg', '.jpeg'] and output_path != image_path:
                image_path.unlink()
                print(f"🗑️ Removed original {image_path.suffix} file")

    print(f"\n✅ Completed! Successfully processed {success_count}/{len(fan_images)} images")


def preview_image_info(project_root=None):
    """Show information about current fan images without making changes"""
    if project_root is None:
        current_file = Path(__file__).resolve()
        project_root = current_file.parent

        while project_root.parent != project_root:
            if (project_root / 'assets').exists():
                break
            project_root = project_root.parent

    fans_dir = Path(project_root) / 'assets' / 'logos' / 'fans'

    if not fans_dir.exists():
        print(f"❌ Fans directory not found: {fans_dir}")
        return

    print(f"📊 Fan Image Information")
    print("=" * 60)

    # Find all image files
    image_extensions = ['.png', '.jpg', '.jpeg', '.PNG', '.JPG', '.JPEG']

    for ext in image_extensions:
        for img_path in sorted(fans_dir.glob(f"*{ext}")):
            if '_Fanpic' in img_path.name:
                try:
                    img = Image.open(img_path)
                    print(f"\n{img_path.name}:")
                    print(f"  Size: {img.size[0]}x{img.size[1]}")
                    print(f"  Format: {img.format}")
                    print(f"  Mode: {img.mode}")
                except Exception as e:
                    print(f"\n{img_path.name}: Error reading - {str(e)}")


def main():
    """Main function with command line interface"""
    parser = argparse.ArgumentParser(
        description='Crop fan images into circles with transparent backgrounds'
    )

    parser.add_argument(
        '--size',
        type=int,
        nargs=2,
        metavar=('WIDTH', 'HEIGHT'),
        help='Target size for output images (e.g., --size 500 500)'
    )

    parser.add_argument(
        '--no-backup',
        action='store_true',
        help='Skip creating backups of original images'
    )

    parser.add_argument(
        '--preview',
        action='store_true',
        help='Preview what would be processed without making changes'
    )

    parser.add_argument(
        '--info',
        action='store_true',
        help='Show information about current fan images'
    )

    parser.add_argument(
        '--single',
        type=str,
        help='Process a single image file'
    )

    parser.add_argument(
        '--project-root',
        type=str,
        help='Path to project root directory'
    )

    args = parser.parse_args()

    if args.info:
        preview_image_info(args.project_root)
    elif args.single:
        # Process a single image
        size = tuple(args.size) if args.size else None
        crop_image_circular(
            args.single,
            size=size,
            backup=not args.no_backup
        )
    else:
        # Process all fan images
        size = tuple(args.size) if args.size else None
        process_all_fan_images(
            project_root=args.project_root,
            size=size,
            backup=not args.no_backup,
            preview_only=args.preview
        )


if __name__ == "__main__":
    main()