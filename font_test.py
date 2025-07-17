import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# List all available Overpass fonts
print("Available Overpass fonts:")
for font in fm.fontManager.ttflist:
    if 'overpass' in font.name.lower():
        print(f"  {font.name} - Weight: {font.weight}")

# Test plot with forced bold
plt.rcParams['font.family'] = 'Overpass'
plt.rcParams['font.weight'] = 'bold'
plt.rcParams['axes.labelweight'] = 'bold'
plt.rcParams['axes.titleweight'] = 'bold'

fig, ax = plt.subplots(figsize=(6, 4))
ax.bar(['A', 'B', 'C'], [1, 2, 3])
ax.set_xlabel('Categories', fontweight='bold', fontsize=12)
ax.set_ylabel('Values', fontweight='bold', fontsize=12)
ax.set_title('Test Bold Text', fontweight='bold', fontsize=14)

# Force all tick labels to be bold
for label in ax.get_xticklabels():
    label.set_weight('bold')
for label in ax.get_yticklabels():
    label.set_weight('bold')

plt.tight_layout()
plt.savefig('test_bold.png', dpi=150)
plt.show()

print("\nMatplotlib font settings:")
print(f"font.family: {plt.rcParams['font.family']}")
print(f"font.weight: {plt.rcParams['font.weight']}")
print(f"Current font: {fm.findfont(fm.FontProperties())}")