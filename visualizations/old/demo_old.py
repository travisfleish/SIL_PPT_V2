# visualizations/demographic_charts.py
"""
Create demographic visualizations for PowerPoint slides
Generates charts matching the style from the sample PPT
Now includes ethnicity chart support and Red Hat Display font
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path
import matplotlib.font_manager as fm
import os


# Add Red Hat Display fonts to matplotlib when this module is imported
def _setup_fonts():
    """Add Red Hat Display fonts to matplotlib"""
    font_dir = os.path.expanduser('~/Library/Fonts')
    if os.path.exists(font_dir):
        for font_file in os.listdir(font_dir):
            if 'RedHatDisplay' in font_file and font_file.endswith('.ttf'):
                try:
                    font_path = os.path.join(font_dir, font_file)
                    fm.fontManager.addfont(font_path)
                except:
                    pass


# Run font setup on import
_setup_fonts()

# Set style for professional appearance
plt.style.use('default')  # Use default style
plt.rcParams['figure.facecolor'] = 'white'
plt.rcParams['axes.facecolor'] = 'white'
plt.rcParams['axes.edgecolor'] = 'black'
plt.rcParams['grid.alpha'] = 0.3
plt.rcParams['font.size'] = 10

# Force matplotlib to use Red Hat Display
plt.rcParams['font.family'] = 'Red Hat Display'
plt.rcParams['font.sans-serif'] = ['Red Hat Display', 'Arial', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False  # Proper minus sign rendering


class DemographicCharts:
    """Generate demographic charts for sports team presentations"""

    def __init__(self, team_colors: Optional[Dict[str, str]] = None):
        self.colors = team_colors or {
            'primary': '#002244',
            'secondary': '#FFB612',
            'accent': '#8B8B8B'
        }

        self.fig_dpi = 300
        self.font_size = 10
        self.title_size = 12
        self.label_size = 9

        # Set font family
        self.font_family = 'Red Hat Display'

        self.community_colors = [
            self.colors['primary'],
            self.colors['secondary'],
            self.colors['accent']
        ]

    def create_grouped_bar_chart(self, data: pd.DataFrame, title: str,
                                 ylabel: str = '% of Total Customer Count',
                                 figsize: Tuple[float, float] = (10, 6),
                                 rotation: int = 0) -> plt.Figure:
        fig, ax = plt.subplots(figsize=figsize, dpi=self.fig_dpi)
        n_groups = len(data.index)
        n_bars = len(data.columns)
        bar_width = 0.25
        indices = np.arange(n_groups)

        for i, (community, color) in enumerate(zip(data.columns, self.community_colors)):
            positions = indices + (i - n_bars / 2 + 0.5) * bar_width
            bars = ax.bar(positions, data[community], bar_width, label=community, color=color, alpha=0.8)
            for bar in bars:
                height = bar.get_height()
                if height > 0:
                    text = ax.text(bar.get_x() + bar.get_width() / 2., height, f'{int(round(height))}%',
                                   ha='center', va='bottom', fontsize=self.label_size,
                                   fontfamily=self.font_family)

        ax.set_xlabel('')
        ax.set_ylabel(ylabel, fontsize=self.font_size, fontfamily=self.font_family)
        ax.set_title(title, fontsize=self.title_size, fontweight='bold', pad=20, fontfamily=self.font_family)
        ax.set_xticks(indices)
        ax.set_xticklabels(data.index, rotation=rotation, ha='right' if rotation else 'center',
                           fontfamily=self.font_family)

        # Add legend with font
        legend = ax.legend(loc='upper right', frameon=True, fontsize=self.font_size,
                           prop={'family': self.font_family})

        max_value = data.max().max()
        ax.set_ylim(0, (max_value if pd.notna(max_value) and max_value > 0 else 100) * 1.15)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.grid(True, axis='y', alpha=0.3)

        # Format y-axis as percentages without decimals
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{int(y)}%'))

        # Set font for y-axis tick labels
        for label in ax.get_yticklabels():
            label.set_fontfamily(self.font_family)

        plt.tight_layout()
        return fig

    def create_pie_charts(self, data: Dict[str, Dict[str, float]],
                          title: str = 'Gender',
                          figsize: Tuple[float, float] = (12, 4)) -> plt.Figure:
        n_communities = len(data)
        fig, axes = plt.subplots(1, n_communities, figsize=figsize, dpi=self.fig_dpi)
        if n_communities == 1:
            axes = [axes]

        for idx, (community, values) in enumerate(data.items()):
            ax = axes[idx]
            percentages = list(values.values())
            colors = ['#4472C4', '#FFC000']
            wedges, texts, autotexts = ax.pie(percentages, labels=None, colors=colors,
                                              autopct='%1.0f%%', startangle=90,
                                              textprops={'fontsize': self.font_size,
                                                         'fontfamily': self.font_family})
            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_fontweight('bold')
                autotext.set_fontfamily(self.font_family)

            # Set title with font
            ax.set_title(community, fontsize=self.font_size, pad=20, fontfamily=self.font_family)

        # Set main title with font
        fig.suptitle(title, fontsize=self.title_size, fontweight='bold', fontfamily=self.font_family)
        plt.tight_layout()
        return fig

    def create_generation_chart(self, data: pd.DataFrame) -> plt.Figure:
        return self.create_grouped_bar_chart(data, title='Generation', ylabel='Balanced Pct')

    def create_income_chart(self, data: pd.DataFrame) -> plt.Figure:
        return self.create_grouped_bar_chart(data, title='Household Income', ylabel='Balanced Pct', figsize=(12, 6))

    def create_occupation_chart(self, data: pd.DataFrame) -> plt.Figure:
        return self.create_grouped_bar_chart(data, title='Occupation Category', ylabel='% of Total Customer Count',
                                             figsize=(12, 6))

    def create_children_chart(self, data: pd.DataFrame) -> plt.Figure:
        return self.create_grouped_bar_chart(data, title='Children in Household', ylabel='% of Total Customer Count',
                                             figsize=(8, 6))

    def create_ethnicity_chart(self, data: pd.DataFrame) -> plt.Figure:
        """Create ethnicity grouped bar chart"""
        fig, ax = plt.subplots(figsize=(10, 5), dpi=self.fig_dpi)

        # Get data
        x = np.arange(len(data.index))
        width = 0.35

        # Plot bars for each community
        communities = data.columns.tolist()
        team_fans = communities[0] if len(communities) > 0 else 'Team Fans'
        gen_pop = communities[1] if len(communities) > 1 else 'Gen Pop'

        # Team fans bars
        bars1 = ax.bar(x - width / 2, data[team_fans], width,
                       label=team_fans,
                       color=self.colors.get('primary', '#1f77b4'),
                       alpha=0.8)

        # General population bars
        bars2 = ax.bar(x + width / 2, data[gen_pop], width,
                       label=gen_pop,
                       color=self.colors.get('secondary', '#ff7f0e'),
                       alpha=0.8)

        # Add value labels on bars (rounded to whole numbers)
        for bars in [bars1, bars2]:
            for bar in bars:
                height = bar.get_height()
                if height > 0:  # Only show label if there's a value
                    ax.annotate(f'{int(round(height))}%',
                                xy=(bar.get_x() + bar.get_width() / 2, height),
                                xytext=(0, 3),
                                textcoords="offset points",
                                ha='center', va='bottom',
                                fontsize=self.label_size,
                                fontfamily=self.font_family)

        # Styling with fonts
        ax.set_xlabel('Ethnicity', fontsize=self.font_size, fontweight='bold', fontfamily=self.font_family)
        ax.set_ylabel('Percentage of Community', fontsize=self.font_size, fontweight='bold',
                      fontfamily=self.font_family)
        ax.set_title('Ethnicity', fontsize=self.title_size, fontweight='bold', pad=20, fontfamily=self.font_family)
        ax.set_xticks(x)
        ax.set_xticklabels(data.index, fontsize=self.font_size, fontfamily=self.font_family)

        # Set font for y-axis tick labels
        for label in ax.get_yticklabels():
            label.set_fontfamily(self.font_family)

        # Legend with font
        legend = ax.legend(loc='upper right', frameon=True, fontsize=self.font_size,
                           prop={'family': self.font_family})

        # Remove top and right spines
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

        # Add y-axis percentage formatting (no decimals)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{int(y)}%'))

        # Set y-axis limits
        max_value = data.max().max()
        ax.set_ylim(0, (max_value if pd.notna(max_value) and max_value > 0 else 100) * 1.15)

        # Add gridlines
        ax.grid(True, axis='y', alpha=0.3, linestyle='--')
        ax.set_axisbelow(True)

        plt.tight_layout()
        return fig

    def create_all_demographic_charts(self, demographic_data: Dict[str, Any],
                                      output_dir: Optional[Path] = None) -> Dict[str, plt.Figure]:
        """Create all demographic charts including ethnicity"""
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
                            else:
                                print(f"Warning: Categories mismatch for {demo_type}")
                                print(f"Expected: {demo_data['categories']}")
                                print(f"Found: {df.index.tolist()}")
                    else:
                        print(f"Warning: Unexpected data structure for {demo_type}")
                        continue

                    # Create appropriate chart based on type
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
                        fig = self.create_grouped_bar_chart(df, demo_data['title'])

                    charts[demo_type] = fig

                elif demo_data['chart_type'] == 'pie' and demo_type == 'gender':
                    fig = self.create_pie_charts(data_dict, title='Gender')
                    charts[demo_type] = fig

            except Exception as e:
                print(f"Error creating {demo_type} chart: {str(e)}")
                import traceback
                traceback.print_exc()

        # Save charts if output directory provided
        if output_dir:
            output_dir = Path(output_dir)
            output_dir.mkdir(exist_ok=True)

            for chart_name, fig in charts.items():
                try:
                    # Standard resolution
                    output_path = output_dir / f'{chart_name}_chart.png'
                    fig.savefig(output_path, bbox_inches='tight', dpi=self.fig_dpi)

                    # High resolution version
                    hires_path = output_dir / f'{chart_name}_chart_hires.png'
                    fig.savefig(hires_path, bbox_inches='tight', dpi=600)

                    print(f"Saved {chart_name} chart to {output_path}")
                except Exception as e:
                    print(f"Error saving {chart_name} chart: {str(e)}")

        return charts


# Example usage
if __name__ == "__main__":
    # Test with mock data
    mock_data = {
        'team_name': 'Utah Jazz',
        'demographics': {
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
    charts = charter.create_all_demographic_charts(mock_data)
    print(f"Generated {len(charts)} charts")