# visualizations/test_demo_slide.py
"""
Simple test for complete demographics slide using existing charts
"""

from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Circle, FancyBboxPatch
from PIL import Image
import numpy as np


def create_complete_slide():
    """Create a complete demographics slide from existing charts"""

    # Setup paths - look in the correct location
    chart_dir = Path('../visualizations/utah_jazz_demographic_charts')

    if not chart_dir.exists():
        # Try alternative paths
        chart_dir = Path('visualizations/utah_jazz_demographic_charts')
        if not chart_dir.exists():
            chart_dir = Path('utah_jazz_demographic_charts')

    if not chart_dir.exists():
        print(f"❌ Chart directory not found")
        print(f"Looking for: {chart_dir.absolute()}")
        print(f"Current directory: {Path.cwd()}")

        # Try to find where the charts actually are
        possible_paths = [
            Path('../visualizations/utah_jazz_demographic_charts'),
            Path('../../visualizations/utah_jazz_demographic_charts'),
            Path('./visualizations/utah_jazz_demographic_charts'),
            Path('./utah_jazz_demographic_charts'),
        ]

        for p in possible_paths:
            if p.exists():
                print(f"✅ Found charts at: {p}")
                chart_dir = p
                break
        else:
            print("\nTried these paths:")
            for p in possible_paths:
                print(f"  - {p.absolute()}")
            return

    print(f"✅ Found chart directory: {chart_dir}")

    # Team configuration
    team_name = 'Utah Jazz'
    team_short = 'Jazz'
    colors = {
        'primary': '#002B5C',  # Jazz blue
        'secondary': '#F9A01B',  # Jazz yellow
        'accent': '#808080'  # Gray for NBA
    }

    # Create figure with PowerPoint slide dimensions
    fig = plt.figure(figsize=(13.33, 7.5), dpi=150)  # Lower DPI for testing
    fig.patch.set_facecolor('white')

    # Title
    fig.text(0.5, 0.96, f"Fan Demographics: How Are {team_name} Fans Unique",
             ha='center', va='top', fontsize=18, fontweight='bold')

    # Create layout
    # Left side - logo and text (we'll just use text for now)
    ax_logo = fig.add_axes([0.02, 0.5, 0.15, 0.3])
    ax_logo.axis('off')
    circle = Circle((0.5, 0.5), 0.4, transform=ax_logo.transAxes,
                    facecolor=colors['primary'],
                    edgecolor=colors['secondary'], linewidth=3)
    ax_logo.add_patch(circle)
    ax_logo.text(0.5, 0.5, team_short, transform=ax_logo.transAxes,
                 ha='center', va='center', fontsize=20, color='white',
                 fontweight='bold')

    # Insight text
    ax_insight = fig.add_axes([0.02, 0.15, 0.15, 0.25])
    ax_insight.axis('off')
    insight_text = (f"{team_short} fans are\nyounger, and more\n"
                    f"likely to be parents\nwho are working\n"
                    f"professionals\nversus the Utah gen\npop.")
    ax_insight.text(0.1, 0.5, insight_text, transform=ax_insight.transAxes,
                    fontsize=12, fontweight='bold', va='center',
                    color=colors['primary'])

    # Chart positions [left, bottom, width, height]
    chart_positions = {
        'generation': [0.2, 0.5, 0.2, 0.35],
        'income': [0.42, 0.5, 0.25, 0.35],
        'gender': [0.69, 0.5, 0.28, 0.35],
        'occupation': [0.2, 0.12, 0.35, 0.33],
        'children': [0.57, 0.12, 0.25, 0.33]
    }

    # Add charts
    for chart_type, pos in chart_positions.items():
        ax = fig.add_axes(pos)
        ax.axis('off')

        # Try hires first, then regular
        chart_path = chart_dir / f'{chart_type}_chart_hires.png'
        if not chart_path.exists():
            chart_path = chart_dir / f'{chart_type}_chart.png'

        if chart_path.exists():
            try:
                img = Image.open(chart_path)
                ax.imshow(img)
                print(f"  ✅ Added {chart_type} chart")
            except Exception as e:
                print(f"  ❌ Error loading {chart_type}: {e}")
                ax.text(0.5, 0.5, f"{chart_type.title()}",
                        transform=ax.transAxes,
                        ha='center', va='center')
        else:
            print(f"  ⚠️  {chart_type} chart not found")
            ax.text(0.5, 0.5, f"{chart_type.title()}\n(Not Found)",
                    transform=ax.transAxes,
                    ha='center', va='center')

    # Add KEY box
    ax_key = fig.add_axes([0.2, 0.02, 0.35, 0.08])
    ax_key.axis('off')
    box = FancyBboxPatch((0, 0), 1, 1,
                         boxstyle="round,pad=0.02",
                         facecolor='white',
                         edgecolor='black',
                         linewidth=1,
                         transform=ax_key.transAxes)
    ax_key.add_patch(box)

    key_text = (f"KEY\n"
                f"-{team_name} Fans\n"
                f"- Utah Gen Pop (state level, excluding Jazz Fans)\n"
                f"- NBA Fans Total (excluding Jazz fans)")
    ax_key.text(0.05, 0.5, key_text, transform=ax_key.transAxes,
                fontsize=8, va='center')

    # Add Ethnicity box
    ax_eth = fig.add_axes([0.57, 0.02, 0.4, 0.08])
    ax_eth.axis('off')
    box2 = FancyBboxPatch((0, 0), 1, 1,
                          boxstyle="round,pad=0.02",
                          facecolor='#f5f5f5',
                          edgecolor='black',
                          linewidth=1,
                          transform=ax_eth.transAxes)
    ax_eth.add_patch(box2)
    ax_eth.text(0.5, 0.5, "Ethnicity", transform=ax_eth.transAxes,
                ha='center', va='center', fontsize=12)

    # Save
    output_path = chart_dir / 'complete_demographics_slide.png'
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()

    print(f"\n✅ Complete slide saved to: {output_path}")

    # Also save high-res
    fig = plt.figure(figsize=(13.33, 7.5), dpi=300)
    # ... (repeat the above code for high-res, or refactor into a function)

    return output_path


if __name__ == "__main__":
    print("Creating complete demographics slide...")
    create_complete_slide()