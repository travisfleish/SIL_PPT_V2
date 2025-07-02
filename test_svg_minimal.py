# test_svg_minimal.py
"""
Minimal test script to convert and display lululemon SVG
"""

from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from PIL import Image
import cairosvg
import io


def test_svg_conversion():
    """Test SVG to PNG conversion and display"""

    # File paths
    svg_path = Path("assets/logos/merchants/lululemon.svg")

    if not svg_path.exists():
        print(f"❌ SVG file not found: {svg_path}")
        return False

    print(f"✅ Found SVG file: {svg_path}")

    try:
        # Convert SVG to PNG in memory
        png_data = cairosvg.svg2png(url=str(svg_path), output_width=200, output_height=200)

        # Load PNG data into PIL Image
        image = Image.open(io.BytesIO(png_data))

        print(f"✅ Successfully converted SVG to image")
        print(f"   Image size: {image.size}")
        print(f"   Image mode: {image.mode}")

        # Display the image
        fig, ax = plt.subplots(1, 1, figsize=(6, 6))
        ax.imshow(image)
        ax.axis('off')
        ax.set_title('Lululemon Logo Test', fontsize=14, fontweight='bold')

        # Add a border for context
        border = Rectangle((0, 0), image.width - 1, image.height - 1,
                           linewidth=2, edgecolor='gray', facecolor='none')
        ax.add_patch(border)

        plt.tight_layout()
        plt.show()

        print("✅ Test completed successfully!")
        return True

    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("   Install with: pip install cairosvg pillow matplotlib")
        return False
    except Exception as e:
        print(f"❌ Error converting SVG: {e}")
        return False


def check_dependencies():
    """Check if required packages are installed"""
    required_packages = {
        'cairosvg': 'cairosvg',
        'PIL': 'pillow',
        'matplotlib': 'matplotlib'
    }

    missing_packages = []

    for module, package in required_packages.items():
        try:
            __import__(module)
            print(f"✅ {package} is installed")
        except ImportError:
            print(f"❌ {package} is missing")
            missing_packages.append(package)

    if missing_packages:
        print(f"\nInstall missing packages with:")
        print(f"pip install {' '.join(missing_packages)}")
        return False

    return True


if __name__ == "__main__":
    print("🔍 Checking dependencies...")
    if check_dependencies():
        print("\n🚀 Running SVG test...")
        test_svg_conversion()
    else:
        print("\n❌ Please install missing dependencies first")