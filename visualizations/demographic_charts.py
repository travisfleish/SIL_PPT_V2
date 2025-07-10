# visualizations/demographic_charts_fixed.py
"""
Fixed demographic visualization with proper text scaling
Uses explicit positioning and removes auto-layout conflicts
Updated with optimized gender pie chart layout and wider bar charts
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path
import matplotlib.font_manager as fm
import os


class DemographicCharts:
    """Generate demographic charts with guaranteed legible text"""

    def __init__(self, team_colors: Optional[Dict[str, str]] = None):
        self.colors = team_colors or {
            'primary': '#002244',
            'secondary': '#FFB612',
            'accent': '#8B8B8B'
        }

        # CRITICAL: Higher DPI but with explicit size control
        self.fig_dpi = 100  # Lower DPI prevents auto-scaling

        # Font sizes designed for PowerPoint readability
        self.font_size = 16
        self.title_size = 20
        self.label_size = 14  # Bar value labels
        self.axis_label_size = 16  # Axis titles
        self.tick_label_size = 12  # Axis tick labels
        self.pie_text_size = 18  # Pie chart percentages
        self.legend_size = 14

        # Font family
        self.font_family = 'Arial'  # More reliable than Red Hat Display

        # Chart colors
        self.community_colors = [
            self.colors['primary'],
            self.colors['secondary'],
            self.colors['accent']
        ]

        # CRITICAL: Disable all auto-layout
        plt.rcParams['figure.autolayout'] = False
        plt.rcParams['axes.autolimit_mode'] = 'data'

    def _format_income_label(self, label: str) -> str:
        """Format income labels to be more concise"""
        # Handle income ranges like "10,000-49,999" -> "$10K-$50K"
        # Handle income ranges like "$10,000 to $49,999" -> "$10K-$50K"
        # Handle single values like "200,000 or more" -> "$200K+"

        label = str(label).strip()

        # Handle "X or more" cases
        if "or more" in label.lower():
            # Extract number and convert
            import re
            numbers = re.findall(r'[\d,]+', label)
            if numbers:
                num = int(numbers[0].replace(',', ''))
                if num >= 1000:
                    formatted = f"${num // 1000}K+"
                else:
                    formatted = f"${num}+"
                return formatted

        # Handle ranges with "to"
        if " to " in label:
            parts = label.split(" to ")
            if len(parts) == 2:
                # Extract numbers from both parts
                import re
                start_nums = re.findall(r'[\d,]+', parts[0])
                end_nums = re.findall(r'[\d,]+', parts[1])

                if start_nums and end_nums:
                    start = int(start_nums[0].replace(',', ''))
                    end = int(end_nums[0].replace(',', ''))

                    # Format both numbers
                    start_fmt = f"${start // 1000}K" if start >= 1000 else f"${start}"
                    end_fmt = f"${end // 1000}K" if end >= 1000 else f"${end}"

                    return f"{start_fmt}-{end_fmt}"

        # Handle ranges with dash
        if "-" in label and any(char.isdigit() for char in label):
            import re
            numbers = re.findall(r'[\d,]+', label)
            if len(numbers) == 2:
                start = int(numbers[0].replace(',', ''))
                end = int(numbers[1].replace(',', ''))

                start_fmt = f"${start // 1000}K" if start >= 1000 else f"${start}"
                end_fmt = f"${end // 1000}K" if end >= 1000 else f"${end}"

                return f"{start_fmt}-{end_fmt}"

        # If no pattern matches, return original
        return label

    def _format_generation_label(self, label: str) -> str:
        """Format generation labels to remove year ranges"""
        label = str(label).strip()

        # Remove anything in parentheses (year ranges)
        import re
        cleaned = re.sub(r'\s*\([^)]*\)', '', label)

        # Handle specific generation mappings
        generation_map = {
            'Millennials and Gen Z': 'Millennials & Gen Z',
            'Generation X': 'Gen X',
            'Baby Boomers': 'Boomers',
            'Post-WWII': 'Post-WWII',
            'Millennials': 'Millennials',
            'Gen Z': 'Gen Z'
        }

        # Check if the cleaned label matches any known generation
        for full_name, short_name in generation_map.items():
            if full_name.lower() in cleaned.lower():
                return short_name

        return cleaned.strip()

    def _format_occupation_label(self, label: str) -> str:
        """Format occupation labels to be more concise"""
        label = str(label).strip()

        # Occupation mappings for shorter labels
        occupation_map = {
            'Blue Collar': 'Blue Collar',
            'Homemaker': 'Homemaker',
            'Lower Management': 'Lower Mgmt',
            'Professional': 'Professional',
            'Upper Management': 'Upper Mgmt',
            'White Collar Worker': 'White Collar',
            'Retired': 'Retired',
            'Other': 'Other'
        }

        return occupation_map.get(label, label)

    def _format_ethnicity_label(self, label: str) -> str:
        """Format ethnicity labels to be more concise"""
        label = str(label).strip()

        # Ethnicity mappings for shorter labels
        ethnicity_map = {
            'African American': 'African American',
            'Hispanic': 'Hispanic',
            'White': 'White',
            'Asian': 'Asian',
            'Other': 'Other',
            'American Indian': 'Native American',
            'Pacific Islander': 'Pacific Islander'
        }

        return ethnicity_map.get(label, label)

    def _format_children_label(self, label: str) -> str:
        """Format children labels to be more concise"""
        label = str(label).strip()

        # Children mappings
        children_map = {
            'No Children in HH': 'No Children',
            'At least 1 Child in HH': 'Has Children',
            'No Children': 'No Children',
            'Has Children': 'Has Children'
        }

        return children_map.get(label, label)

    def _format_labels_for_chart_type(self, labels: List[str], chart_type: str) -> List[str]:
        """Format labels based on the chart type"""
        if chart_type == 'income':
            return [self._format_income_label(label) for label in labels]
        elif chart_type == 'generation':
            return [self._format_generation_label(label) for label in labels]
        elif chart_type == 'occupation':
            return [self._format_occupation_label(label) for label in labels]
        elif chart_type == 'ethnicity':
            return [self._format_ethnicity_label(label) for label in labels]
        elif chart_type == 'children':
            return [self._format_children_label(label) for label in labels]
        else:
            return labels

    def create_grouped_bar_chart(self, data: pd.DataFrame, title: str = None,
                                 ylabel: str = '% of Total Customer Count',
                                 figsize: Tuple[float, float] = (16, 10),  # Larger base size
                                 rotation: int = 0,
                                 show_legend: bool = False,
                                 chart_type: str = None) -> plt.Figure:
        """Create grouped bar chart with fixed text sizing and smart label formatting"""

        # Create figure with explicit size and positioning
        fig = plt.figure(figsize=figsize, dpi=self.fig_dpi)

        # CRITICAL: More room for x-axis labels
        bottom_margin = 0.25 if rotation != 0 else 0.20
        ax = fig.add_subplot(111)
        fig.subplots_adjust(left=0.12, right=0.95, top=0.90, bottom=bottom_margin)

        n_groups = len(data.index)
        n_bars = len(data.columns)
        bar_width = 0.25
        indices = np.arange(n_groups)

        # Create bars
        for i, (community, color) in enumerate(zip(data.columns, self.community_colors)):
            positions = indices + (i - n_bars / 2 + 0.5) * bar_width
            bars = ax.bar(positions, data[community], bar_width,
                          label=community, color=color, alpha=0.8)

            # Add value labels with explicit font settings
            for bar in bars:
                height = bar.get_height()
                if height > 0:
                    ax.text(bar.get_x() + bar.get_width() / 2., height,
                            f'{int(round(height))}%',
                            ha='center', va='bottom',
                            fontsize=self.label_size,
                            fontfamily=self.font_family,
                            fontweight='bold',
                            clip_on=False)

        # Set labels with explicit font settings
        ax.set_xlabel('', fontsize=self.axis_label_size,
                      fontfamily=self.font_family, fontweight='bold')
        ax.set_ylabel(ylabel, fontsize=self.axis_label_size,
                      fontfamily=self.font_family, fontweight='bold')

        # Title only if requested
        if title:
            ax.set_title(title, fontsize=self.title_size, fontweight='bold',
                         pad=20, fontfamily=self.font_family)

        # CRITICAL: Format labels based on chart type before setting
        original_labels = list(data.index)
        if chart_type:
            formatted_labels = self._format_labels_for_chart_type(original_labels, chart_type)
        else:
            formatted_labels = original_labels

        # CRITICAL: Force larger x-axis labels and prevent auto-compression
        ax.set_xticks(indices)
        ax.set_xticklabels(formatted_labels, rotation=rotation,
                           ha='right' if rotation else 'center',
                           fontfamily=self.font_family,
                           fontsize=18,  # Much larger!
                           fontweight='bold')

        # CRITICAL: Explicitly set tick parameters
        ax.tick_params(axis='x', which='major', labelsize=18, pad=10)

        # Legend only if requested
        if show_legend:
            ax.legend(loc='upper right', frameon=True,
                      fontsize=self.legend_size,
                      prop={'family': self.font_family, 'size': self.legend_size})

        # Set axis limits and formatting
        max_value = data.max().max()
        ax.set_ylim(0, (max_value if pd.notna(max_value) and max_value > 0 else 100) * 1.15)

        # Style the chart
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.grid(True, axis='y', alpha=0.3)

        # Format y-axis
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{int(y)}%'))

        # CRITICAL: Explicitly set y-tick label fonts
        for label in ax.get_yticklabels():
            label.set_fontfamily(self.font_family)
            label.set_fontsize(self.tick_label_size)

        return fig

    def create_pie_charts(self, data: Dict[str, Dict[str, float]],
                          title: str = 'Gender',
                          figsize: Tuple[float, float] = (4, 8)) -> plt.Figure:  # NARROWER
        """Create vertically stacked pie charts with minimal white space"""
        n_communities = len(data)
        fig = plt.figure(figsize=figsize, dpi=self.fig_dpi)

        # Manual positioning with minimal margins
        pie_radius = 0.15
        pie_spacing = 0.35
        start_y = 0.75

        for idx, (community, values) in enumerate(data.items()):
            # Calculate position
            center_y = start_y - (idx * pie_spacing)
            center_x = 0.5

            # Create tight axes
            ax_left = center_x - pie_radius
            ax_bottom = center_y - pie_radius
            ax_width = pie_radius * 2
            ax_height = pie_radius * 2

            ax = fig.add_axes([ax_left, ax_bottom, ax_width, ax_height])

            percentages = list(values.values())
            colors = ['#4472C4', '#FFC000']  # Blue for male, yellow for female

            # Create pie chart
            wedges, texts, autotexts = ax.pie(percentages, labels=None, colors=colors,
                                              autopct='%1.0f%%', startangle=90,
                                              textprops={'fontsize': 14,  # Larger font for percentages
                                                         'fontfamily': self.font_family})

            # Style the percentage text
            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_fontweight('bold')
                autotext.set_fontfamily(self.font_family)
                autotext.set_fontsize(16)  # Even larger for visibility

            ax.axis('equal')
            ax.set_xlim(-1.1, 1.1)
            ax.set_ylim(-1.1, 1.1)

        # Remove all padding
        fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
        return fig

    def create_ethnicity_chart(self, data: pd.DataFrame) -> plt.Figure:
        """Create ethnicity grouped bar chart with formatted labels"""
        return self.create_grouped_bar_chart(data, chart_type='ethnicity', figsize=(16, 10))

    def create_generation_chart(self, data: pd.DataFrame) -> plt.Figure:
        """Create generation chart with wider layout"""
        return self.create_grouped_bar_chart(data, chart_type='generation', ylabel='Balanced Pct', figsize=(18, 8))

    def create_income_chart(self, data: pd.DataFrame) -> plt.Figure:
        """Create income chart with wider layout for better readability"""
        return self.create_grouped_bar_chart(data, chart_type='income', ylabel='Balanced Pct', figsize=(24, 8))

    def create_occupation_chart(self, data: pd.DataFrame) -> plt.Figure:
        """Create occupation chart with wider layout for better readability"""
        return self.create_grouped_bar_chart(data, chart_type='occupation', ylabel='% of Total Customer Count',
                                             figsize=(24, 8))

    def create_children_chart(self, data: pd.DataFrame) -> plt.Figure:
        """Create children chart with wider layout"""
        return self.create_grouped_bar_chart(data, chart_type='children', ylabel='% of Total Customer Count',
                                             figsize=(12, 8))

    def save_chart_for_powerpoint(self, fig: plt.Figure, filename: str,
                                  output_dir: Path, width_inches: float = 12,
                                  height_inches: float = 8) -> Path:
        """Save chart optimized for PowerPoint insertion"""

        # Set exact size for PowerPoint
        fig.set_size_inches(width_inches, height_inches)

        # Save with high DPI for crisp text
        output_path = output_dir / f'{filename}.png'
        fig.savefig(output_path,
                    dpi=200,  # High enough for crisp text
                    bbox_inches='tight',
                    facecolor='white',
                    edgecolor='none',
                    pad_inches=0.1)  # Small padding

        return output_path

    def create_all_demographic_charts(self, demographic_data: Dict[str, Any],
                                      output_dir: Optional[Path] = None) -> Dict[str, plt.Figure]:
        """Create all demographic charts with guaranteed legible text"""
        charts = {}
        demographics = demographic_data.get('demographics', {})

        for demo_type, demo_data in demographics.items():
            try:
                data_dict = demo_data['data']

                if demo_data['chart_type'] == 'grouped_bar':
                    if isinstance(data_dict, dict) and all(isinstance(v, dict) for v in data_dict.values()):
                        df = pd.DataFrame(data_dict)

                        # Ensure categories are in the correct order
                        if 'categories' in demo_data:
                            existing_categories = [cat for cat in demo_data['categories'] if cat in df.index]
                            if existing_categories:
                                df = df.reindex(existing_categories)

                    # Create appropriate chart with chart_type parameter
                    if demo_type == 'generation':
                        fig = self.create_generation_chart(df)
                    elif demo_type == 'income':
                        fig = self.create_income_chart(df)
                    elif demo_type == 'occupation':
                        fig = self.create_occupation_chart(df)
                    elif demo_type == 'children':
                        fig = self.create_children_chart(df)
                    elif demo_type == 'ethnicity':
                        fig = self.create_ethnicity_chart(df)
                    else:
                        fig = self.create_grouped_bar_chart(df, chart_type=demo_type)

                    charts[demo_type] = fig

                elif demo_data['chart_type'] == 'pie' and demo_type == 'gender':
                    fig = self.create_pie_charts(data_dict)
                    charts[demo_type] = fig

            except Exception as e:
                print(f"Error creating {demo_type} chart: {str(e)}")
                import traceback
                traceback.print_exc()

        # Save charts optimized for PowerPoint
        if output_dir:
            output_dir = Path(output_dir)
            output_dir.mkdir(exist_ok=True)

            for chart_name, fig in charts.items():
                try:
                    # Save for PowerPoint insertion
                    output_path = self.save_chart_for_powerpoint(
                        fig, f'{chart_name}_chart', output_dir)
                    print(f"Saved {chart_name} chart to {output_path}")

                except Exception as e:
                    print(f"Error saving {chart_name} chart: {str(e)}")

        return charts


# Additional utility for testing text visibility
def test_text_visibility():
    """Test function to verify text is legible at different sizes"""

    fig, axes = plt.subplots(2, 2, figsize=(16, 12), dpi=100)
    fig.subplots_adjust(left=0.1, right=0.9, top=0.9, bottom=0.1,
                        wspace=0.3, hspace=0.3)

    font_sizes = [10, 12, 14, 16]
    test_text = "Sample Text 123%"

    for i, (ax, size) in enumerate(zip(axes.flat, font_sizes)):
        ax.text(0.5, 0.5, f"{test_text}\nFont Size: {size}pt",
                ha='center', va='center', fontsize=size,
                fontfamily='Arial', transform=ax.transAxes)
        ax.set_title(f"Font Size {size}pt", fontsize=size + 2)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)

    return fig


def test_label_formatting():
    """Test function to verify label formatting works correctly"""

    charter = DemographicCharts()

    # Test income formatting
    income_labels = [
        "10,000-49,999",
        "$50,000 to $74,999",
        "$100,000 to $149,999",
        "$200,000 or more"
    ]

    print("Income Label Formatting:")
    for label in income_labels:
        formatted = charter._format_income_label(label)
        print(f"  '{label}' -> '{formatted}'")

    # Test generation formatting
    generation_labels = [
        "1. Millennials and Gen Z (1982 and after)",
        "2. Generation X (1961-1981)",
        "3. Baby Boomers (1943-1960)",
        "4. Post-WWII (1942 and before)"
    ]

    print("\nGeneration Label Formatting:")
    for label in generation_labels:
        formatted = charter._format_generation_label(label)
        print(f"  '{label}' -> '{formatted}'")

    # Test occupation formatting
    occupation_labels = [
        "Blue Collar",
        "Lower Management",
        "Upper Management",
        "White Collar Worker"
    ]

    print("\nOccupation Label Formatting:")
    for label in occupation_labels:
        formatted = charter._format_occupation_label(label)
        print(f"  '{label}' -> '{formatted}'")

    return True


def test_formatted_charts():
    """Test charts with formatted labels"""

    # Sample data with realistic labels that need formatting
    income_data = pd.DataFrame({
        'Utah Jazz Fans': {
            '10,000-49,999': 25,
            '$50,000 to $74,999': 24,
            '$75,000 to $99,999': 17,
            '$100,000 to $149,999': 21,
            '$150,000 to $199,999': 23,
            '$200,000 or more': 12
        },
        'Local Gen Pop': {
            '10,000-49,999': 20,
            '$50,000 to $74,999': 17,
            '$75,000 to $99,999': 17,
            '$100,000 to $149,999': 14,
            '$150,000 to $199,999': 15,
            '$200,000 or more': 6
        }
    })

    generation_data = pd.DataFrame({
        'Utah Jazz Fans': {
            '1. Millennials and Gen Z (1982 and after)': 51,
            '2. Generation X (1961-1981)': 37,
            '3. Baby Boomers (1943-1960)': 10,
            '4. Post-WWII (1942 and before)': 2
        },
        'Local Gen Pop': {
            '1. Millennials and Gen Z (1982 and after)': 45,
            '2. Generation X (1961-1981)': 34,
            '3. Baby Boomers (1943-1960)': 17,
            '4. Post-WWII (1942 and before)': 4
        }
    })

    charter = DemographicCharts()

    # Create charts with formatted labels
    income_fig = charter.create_income_chart(income_data)
    generation_fig = charter.create_generation_chart(generation_data)

    # Save test charts
    income_fig.savefig('income_formatted_test.png', dpi=200, bbox_inches='tight')
    generation_fig.savefig('generation_formatted_test.png', dpi=200, bbox_inches='tight')

    print("Created test charts with formatted labels:")
    print("- income_formatted_test.png")
    print("- generation_formatted_test.png")

    return income_fig, generation_fig


if __name__ == "__main__":
    # Test text visibility
    test_fig = test_text_visibility()
    test_fig.savefig('text_visibility_test.png', dpi=200, bbox_inches='tight')
    print("Text visibility test saved as 'text_visibility_test.png'")

    # Test with mock data
    mock_data = {
        'team_name': 'Utah Jazz',
        'demographics': {
            'gender': {
                'chart_type': 'pie',
                'title': 'Gender',
                'data': {
                    'Utah Jazz Fans': {'Male': 54, 'Female': 46},
                    'NBA Fans': {'Male': 52, 'Female': 48}
                }
            },
            'ethnicity': {
                'chart_type': 'grouped_bar',
                'title': 'Ethnicity',
                'categories': ['White', 'Hispanic', 'African American', 'Asian', 'Other'],
                'data': {
                    'Utah Jazz Fans': {
                        'White': 65,
                        'Hispanic': 18,
                        'African American': 8,
                        'Asian': 5,
                        'Other': 4
                    },
                    'Local Gen Pop (Excl. Jazz)': {
                        'White': 70,
                        'Hispanic': 15,
                        'African American': 5,
                        'Asian': 7,
                        'Other': 3
                    }
                }
            }
        }
    }

    # Create charts
    charter = DemographicCharts()
    charts = charter.create_all_demographic_charts(mock_data, Path('./test_output'))
    print(f"Generated {len(charts)} charts with legible text")