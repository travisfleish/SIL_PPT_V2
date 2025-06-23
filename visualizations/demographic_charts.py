
# visualizations/demographic_charts.py
"""
Create demographic visualizations for PowerPoint slides
Generates charts matching the style from the sample PPT
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path

# Set style for professional appearance
plt.style.use('default')  # Use default style
plt.rcParams['figure.facecolor'] = 'white'
plt.rcParams['axes.facecolor'] = 'white'
plt.rcParams['axes.edgecolor'] = 'black'
plt.rcParams['grid.alpha'] = 0.3
plt.rcParams['font.size'] = 10


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
                    ax.text(bar.get_x() + bar.get_width() / 2., height, f'{height:.0f}%',
                            ha='center', va='bottom', fontsize=self.label_size)

        ax.set_xlabel('')
        ax.set_ylabel(ylabel, fontsize=self.font_size)
        ax.set_title(title, fontsize=self.title_size, fontweight='bold', pad=20)
        ax.set_xticks(indices)
        ax.set_xticklabels(data.index, rotation=rotation, ha='right' if rotation else 'center')
        max_value = data.max().max()
        ax.set_ylim(0, (max_value if pd.notna(max_value) and max_value > 0 else 100) * 1.15)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.grid(True, axis='y', alpha=0.3)
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
                                              textprops={'fontsize': self.font_size})
            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_fontweight('bold')
            ax.set_title(community, fontsize=self.font_size, pad=20)
        fig.suptitle(title, fontsize=self.title_size, fontweight='bold')
        plt.tight_layout()
        return fig

    def create_generation_chart(self, data: pd.DataFrame) -> plt.Figure:
        return self.create_grouped_bar_chart(data, title='Generation', ylabel='Balanced Pct')

    def create_income_chart(self, data: pd.DataFrame) -> plt.Figure:
        return self.create_grouped_bar_chart(data, title='Household Income', ylabel='Balanced Pct', figsize=(12, 6))

    def create_occupation_chart(self, data: pd.DataFrame) -> plt.Figure:
        return self.create_grouped_bar_chart(data, title='Occupation Category', ylabel='% of Total Customer Count', figsize=(12, 6))

    def create_children_chart(self, data: pd.DataFrame) -> plt.Figure:
        return self.create_grouped_bar_chart(data, title='Children in Household', ylabel='% of Total Customer Count', figsize=(8, 6))

    def create_all_demographic_charts(self, demographic_data: Dict[str, Any],
                                      output_dir: Optional[Path] = None) -> Dict[str, plt.Figure]:
        charts = {}
        demographics = demographic_data['demographics']

        for demo_type, demo_data in demographics.items():
            data_dict = demo_data['data']

            if demo_data['chart_type'] == 'grouped_bar':
                if isinstance(data_dict, dict) and all(isinstance(v, dict) for v in data_dict.values()):
                    df = pd.DataFrame(data_dict)
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

                if demo_type == 'generation':
                    fig = self.create_generation_chart(df)
                elif demo_type == 'income':
                    fig = self.create_income_chart(df)
                elif demo_type == 'occupation':
                    fig = self.create_occupation_chart(df)
                elif demo_type == 'children':
                    fig = self.create_children_chart(df)
                else:
                    fig = self.create_grouped_bar_chart(df, demo_data['title'])

                charts[demo_type] = fig

            elif demo_data['chart_type'] == 'pie' and demo_type == 'gender':
                fig = self.create_pie_charts(data_dict, title='Gender')
                charts[demo_type] = fig

        if output_dir:
            output_dir = Path(output_dir)
            output_dir.mkdir(exist_ok=True)
            for chart_name, fig in charts.items():
                output_path = output_dir / f'{chart_name}_chart.png'
                fig.savefig(output_path, bbox_inches='tight', dpi=self.fig_dpi)
                hires_path = output_dir / f'{chart_name}_chart_hires.png'
                fig.savefig(hires_path, bbox_inches='tight', dpi=600)

        return charts
