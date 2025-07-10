# align_right_edges.py
"""
Make occupation stretch so its right edge aligns with children's right edge
"""

from pathlib import Path
import re


def calculate_edge_aligned_layout():
    """Calculate layout with right edges aligned"""

    # From looking at the current layout, let's determine the positions
    # Children appears to end around the right side of the slide

    # Standard slide dimensions
    slide_width = 13.33  # Standard 16:9 slide width
    left_margin = 0.5
    right_margin = 0.5
    space_between = 0.2

    # Fixed dimensions we want to keep
    gender_width = 1.5  # Keep narrow
    income_width = 4.8  # Keep current size
    children_width = 3.0  # Keep compact

    # Calculate where children should end (near right edge)
    children_right_edge = slide_width - right_margin
    children_left = children_right_edge - children_width

    # Now work backwards to place occupation
    # Occupation should end at the same place as children
    occupation_right_edge = children_right_edge

    # Calculate occupation left edge
    gender_left = left_margin
    income_left = gender_left + gender_width + space_between
    occupation_left = income_left + income_width + space_between

    # Occupation width = right edge - left edge
    occupation_width = occupation_right_edge - occupation_left

    # For bottom row: ethnicity and generation share space before children
    available_bottom_width = children_left - left_margin - space_between
    ethnicity_generation_width = (available_bottom_width - space_between) / 2

    ethnicity_left = left_margin
    generation_left = ethnicity_left + ethnicity_generation_width + space_between

    layout = {
        'top_row': {
            'gender': (gender_left, gender_width),
            'income': (income_left, income_width),
            'occupation': (occupation_left, occupation_width)
        },
        'bottom_row': {
            'ethnicity': (ethnicity_left, ethnicity_generation_width),
            'generation': (generation_left, ethnicity_generation_width),
            'children': (children_left, children_width)
        }
    }

    print(f"Right-edge aligned layout:")
    print(f"  Slide width: {slide_width:.1f}\"")
    print(f"")
    print(f"  Top row:")
    print(f"    Gender: {gender_width:.1f}\" (x={gender_left:.1f} to {gender_left + gender_width:.1f})")
    print(f"    Income: {income_width:.1f}\" (x={income_left:.1f} to {income_left + income_width:.1f})")
    print(
        f"    Occupation: {occupation_width:.1f}\" (x={occupation_left:.1f} to {occupation_left + occupation_width:.1f})")
    print(f"")
    print(f"  Bottom row:")
    print(
        f"    Ethnicity: {ethnicity_generation_width:.1f}\" (x={ethnicity_left:.1f} to {ethnicity_left + ethnicity_generation_width:.1f})")
    print(
        f"    Generation: {ethnicity_generation_width:.1f}\" (x={generation_left:.1f} to {generation_left + ethnicity_generation_width:.1f})")
    print(f"    Children: {children_width:.1f}\" (x={children_left:.1f} to {children_left + children_width:.1f})")
    print(f"")
    print(f"  ✅ RIGHT EDGE ALIGNMENT CHECK:")
    print(f"    Occupation ends at: {occupation_left + occupation_width:.1f}\"")
    print(f"    Children ends at:   {children_left + children_width:.1f}\"")
    print(f"    Difference: {abs((occupation_left + occupation_width) - (children_left + children_width)):.1f}\"")

    return layout


def update_slide_layout_aligned():
    """Update slide layout with right-edge alignment"""

    slide_file = Path('slide_generators/demographics_slide.py')

    if not slide_file.exists():
        print(f"❌ File not found: {slide_file}")
        return False

    print(f"📝 Updating slide layout for right-edge alignment...")

    # Calculate aligned positions
    layout = calculate_edge_aligned_layout()

    # Read the file
    with open(slide_file, 'r') as f:
        content = f.read()

    # Update chart positions
    old_positions = r"chart_positions = \[(.*?)\]"

    new_positions = f'''chart_positions = [
            # Top row - RIGHT-EDGE ALIGNED: Occupation right edge = Children right edge
            ('gender_chart', {layout['top_row']['gender'][0]:.1f}, 1.2, {layout['top_row']['gender'][1]:.1f}, 2.2),      # {layout['top_row']['gender'][1]:.1f}" wide
            ('income_chart', {layout['top_row']['income'][0]:.1f}, 1.2, {layout['top_row']['income'][1]:.1f}, 2.2),       # {layout['top_row']['income'][1]:.1f}" wide
            ('occupation_chart', {layout['top_row']['occupation'][0]:.1f}, 1.2, {layout['top_row']['occupation'][1]:.1f}, 2.2),  # {layout['top_row']['occupation'][1]:.1f}" wide (ALIGNED RIGHT)

            # Bottom row - Ethnicity & Generation equal, Children right-aligned
            ('ethnicity_chart', {layout['bottom_row']['ethnicity'][0]:.1f}, 3.9, {layout['bottom_row']['ethnicity'][1]:.1f}, 2.2),    # {layout['bottom_row']['ethnicity'][1]:.1f}" wide
            ('generation_chart', {layout['bottom_row']['generation'][0]:.1f}, 3.9, {layout['bottom_row']['generation'][1]:.1f}, 2.2),   # {layout['bottom_row']['generation'][1]:.1f}" wide
            ('children_chart', {layout['bottom_row']['children'][0]:.1f}, 3.9, {layout['bottom_row']['children'][1]:.1f}, 2.2)      # {layout['bottom_row']['children'][1]:.1f}" wide (RIGHT ALIGNED)
        ]'''

    if re.search(old_positions, content, re.DOTALL):
        content = re.sub(old_positions, new_positions, content, flags=re.DOTALL)
        print("✅ Updated chart positions - right edges now aligned")
    else:
        print("❌ Could not find chart_positions to update")
        return False

    # Update header positions to match
    old_headers = r"headers = \[(.*?)\]"

    new_headers = f'''headers = [
            # Top row headers - matching right-edge aligned chart positions
            ("GENDER", {layout['top_row']['gender'][0]:.1f}, 0.95, {layout['top_row']['gender'][1]:.1f}),             # {layout['top_row']['gender'][1]:.1f}" wide
            ("HOUSEHOLD INCOME", {layout['top_row']['income'][0]:.1f}, 0.95, {layout['top_row']['income'][1]:.1f}),   # {layout['top_row']['income'][1]:.1f}" wide
            ("OCCUPATION CATEGORY", {layout['top_row']['occupation'][0]:.1f}, 0.95, {layout['top_row']['occupation'][1]:.1f}), # {layout['top_row']['occupation'][1]:.1f}" wide (ALIGNED)

            # Bottom row headers - matching alignment
            ("ETHNICITY", {layout['bottom_row']['ethnicity'][0]:.1f}, 3.65, {layout['bottom_row']['ethnicity'][1]:.1f}),          # {layout['bottom_row']['ethnicity'][1]:.1f}" wide
            ("GENERATION", {layout['bottom_row']['generation'][0]:.1f}, 3.65, {layout['bottom_row']['generation'][1]:.1f}),         # {layout['bottom_row']['generation'][1]:.1f}" wide
            ("CHILDREN IN HOUSEHOLD", {layout['bottom_row']['children'][0]:.1f}, 3.65, {layout['bottom_row']['children'][1]:.1f})  # {layout['bottom_row']['children'][1]:.1f}" wide
        ]'''

    if re.search(old_headers, content, re.DOTALL):
        content = re.sub(old_headers, new_headers, content, flags=re.DOTALL)
        print("✅ Updated header positions to match")

    # Write back
    with open(slide_file, 'w') as f:
        f.write(content)

    return True


def clear_cache():
    """Clear cache for fresh generation"""
    print("\n🗑️  Clearing cache...")

    import shutil
    import sys

    # Clear directories
    cache_dirs = [Path(p) for p in ['test_output', 'simple_test_output', 'final_test', 'test_regeneration']]
    for cache_dir in cache_dirs:
        if cache_dir.exists():
            shutil.rmtree(cache_dir)

    # Clear timestamped directories
    for path in Path('.').glob('test_output_*'):
        if path.is_dir():
            shutil.rmtree(path)

    # Clear Python cache
    modules_to_clear = [
        'visualizations.demographic_charts',
        'slide_generators.demographics_slide'
    ]

    for module in modules_to_clear:
        if module in sys.modules:
            del sys.modules[module]

    print("✅ Cache cleared")


def main():
    """Main execution"""
    print("🎯 ALIGNING RIGHT EDGES")
    print("=" * 50)
    print("Making occupation's right edge align with children's right edge")
    print()

    # Show the alignment calculation
    layout = calculate_edge_aligned_layout()

    # Update slide layout
    if not update_slide_layout_aligned():
        return False

    # Clear cache
    clear_cache()

    print("\n✅ RIGHT EDGES ALIGNED!")
    print("Now the layout should have:")
    print(f"  • Occupation: {layout['top_row']['occupation'][1]:.1f}\" wide - stretches to right edge")
    print(f"  • Children: {layout['bottom_row']['children'][1]:.1f}\" wide - aligned to right edge")
    print("  • Perfect vertical alignment between top and bottom rows")
    print("\nRun your demographics test to see the aligned layout!")

    return True


if __name__ == "__main__":
    main()