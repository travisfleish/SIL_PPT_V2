# visualizations/demographic_charts_fixed.py
"""
Fixed demographic visualization with proper text scaling and correct aspect ratios
Matches PowerPoint placeholder dimensions exactly
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
    """Generate demographic charts with guaranteed legible text and correct aspect ratios"""

    def __init__(self, team_colors: Optional[Dict[str, str]] = None):
        self.colors = team_colors or {
            'primary': '#002244',
            'secondary': '#FFB612',
            'accent': '#8B8B8B'
        }

        # CRITICAL: Higher DPI but with explicit size control
        self.fig_dpi = 100  # Lower DPI prevents auto-scaling

        # Font sizes adjusted for small PowerPoint display dimensions
        self.font_size = 10
        self.title_size = 12
        self.label_size = 8  # Bar value labels (the percentages on bars)
        self.axis_label_size = 10  # Axis titles
        self.tick_label_size = 8  # Axis tick labels
        self.pie_text_size = 10  # Pie chart percentages
        self.legend_size = 9

        # Font family - try Overpass Light first, fallback to Arial
        try:
            # Check if Overpass Light is available
            import matplotlib.font_manager as fm

            # Get all available font names
            available_fonts = sorted(set([f.name for f in fm.fontManager.ttflist]))

            # Debug: Print available fonts that contain "Overpass"
            overpass_fonts = [f for f in available_fonts if 'Overpass' in f.lower()]
            if overpass_fonts:
                print(f"Found Overpass fonts: {overpass_fonts}")

            # Try different variations of Overpass
            if 'Overpass Light' in available_fonts:
                self.font_family = 'Overpass Light'
                print("Using: Overpass Light")
            elif 'Overpass-Light' in available_fonts:
                self.font_family = 'Overpass-Light'
                print("Using: Overpass-Light")
            elif 'Overpass' in available_fonts:
                self.font_family = 'Overpass'
                # Try to use light weight
                plt.rcParams['font.weight'] = 'light'
                print("Using: Overpass (with light weight)")
            else:
                # Fallback to Arial if Overpass not found
                self.font_family = 'Arial'
                print(
                    f"Warning: Overpass font not found in system. Available fonts containing 'over': {[f for f in available_fonts if 'over' in f.lower()][:5]}")
                print("Using Arial as fallback. To use Overpass Light:")
                print("1. Download from: https://fonts.google.com/specimen/Overpass")
                print("2. Install the font on your system")
                print("3. Clear matplotlib cache: import matplotlib; matplotlib.font_manager._rebuild()")
                print("4. Restart your Python environment")
        except Exception as e:
            self.font_family = 'Arial'  # Fallback
            print(f"Font detection error: {e}")
            print("Using Arial as fallback")

        # Chart colors
        self.community_colors = [
            self.colors['primary'],
            self.colors['secondary'],
            self.colors['accent']
        ]

        # CRITICAL: Disable all auto-layout
        plt.rcParams['figure.autolayout'] = False
        plt.rcParams['axes.autolimit_mode'] = 'data'

        # Configure font settings
        plt.rcParams['font.family'] = self.font_family
        if 'Overpass' in self.font_family:
            plt.rcParams['font.weight'] = 'light'

    def _format_income_label(self, label: str) -> str:
        """Format income labels to be extremely concise for small charts"""
        label = str(label).strip()

        # Handle "X or more" cases
        if "or more" in label.lower():
            import re
            numbers = re.findall(r'[\d,]+', label)
            if numbers:
                num = int(numbers[0].replace(',', ''))
                if num >= 1000:
                    formatted = f"${num // 1000}K+"
                else:
                    formatted = f"${num}+"
                return formatted

        # Handle ranges - make them ultra-compact
        if " to " in label or "-" in label:
            import re
            numbers = re.findall(r'[\d,]+', label)
            if len(numbers) >= 2:
                start = int(numbers[0].replace(',', ''))
                end = int(numbers[1].replace(',', ''))

                # Ultra-compact format
                if start < 1000:
                    start_fmt = f"<1"
                else:
                    start_fmt = f"{start // 1000}"

                if end >= 1000:
                    end_fmt = f"{end // 1000}K"
                else:
                    end_fmt = f"{end}"

                # Special cases for common ranges
                if start == 10000 and end == 49999:
                    return "10-50K"
                elif start == 50000 and end == 74999:
                    return "50-75K"
                elif start == 75000 and end == 99999:
                    return "75-100K"
                elif start == 100000 and end == 149999:
                    return "100-150K"
                elif start == 150000 and end == 199999:
                    return "150-200K"
                else:
                    return f"{start_fmt}-{end_fmt}"

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

        for full_name, short_name in generation_map.items():
            if full_name.lower() in cleaned.lower():
                return short_name

        return cleaned.strip()

    def _format_occupation_label(self, label: str) -> str:
        """Format occupation labels to be more concise"""
        label = str(label).strip()

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
                                 figsize: Tuple[float, float] = (4.5, 2.5),  # Default to match PPT
                                 rotation: int = 0,
                                 show_legend: bool = False,
                                 chart_type: str = None) -> plt.Figure:
        """Create grouped bar chart with fixed text sizing and smart label formatting"""

        # Create figure with explicit size and positioning
        fig = plt.figure(figsize=figsize, dpi=self.fig_dpi)

        # CRITICAL: Adjusted margins for small chart sizes - more aggressive
        bottom_margin = 0.25 if rotation else 0.18
        left_margin = 0.18  # More room for y-axis labels
        ax = fig.add_subplot(111)
        fig.subplots_adjust(left=left_margin, right=0.97, top=0.94, bottom=bottom_margin)

        n_groups = len(data.index)
        n_bars = len(data.columns)
        bar_width = 0.15  # Further reduced for more spacing between groups
        indices = np.arange(n_groups)

        # Create bars and track values for each group
        bar_groups = []
        for i, (community, color) in enumerate(zip(data.columns, self.community_colors)):
            positions = indices + (i - n_bars / 2 + 0.5) * bar_width
            bars = ax.bar(positions, data[community], bar_width,
                          label=community, color=color, alpha=0.8)
            bar_groups.append((bars, data[community].values))

        # Add value labels only for the highest bar in each group
        for group_idx in range(n_groups):
            # Find which community has the highest value for this group
            max_value = 0
            max_bar = None
            max_community_idx = 0

            for comm_idx, (bars, values) in enumerate(bar_groups):
                if values[group_idx] > max_value:
                    max_value = values[group_idx]
                    max_bar = bars[group_idx]
                    max_community_idx = comm_idx

            # Only add label to the highest bar
            if max_bar and max_value > 0:
                ax.text(max_bar.get_x() + max_bar.get_width() / 2., max_value,
                        f'{int(round(max_value))}%',
                        ha='center', va='bottom',
                        fontsize=self.label_size,
                        fontfamily=self.font_family,
                        fontweight='bold',  # Bold for visibility
                        clip_on=False)

        # Set labels with explicit font settings
        ax.set_xlabel('', fontsize=self.axis_label_size,
                      fontfamily=self.font_family, fontweight='bold')
        ax.set_ylabel(ylabel, fontsize=self.axis_label_size,
                      fontfamily=self.font_family, fontweight='bold')

        # Title only if requested
        if title:
            ax.set_title(title, fontsize=self.title_size, fontweight='bold',
                         pad=10, fontfamily=self.font_family)

        # Format labels based on chart type before setting
        original_labels = list(data.index)
        if chart_type:
            formatted_labels = self._format_labels_for_chart_type(original_labels, chart_type)
        else:
            formatted_labels = original_labels

        # Force larger x-axis labels and prevent auto-compression
        ax.set_xticks(indices)

        # Adjust font size based on number of categories and chart width
        if n_groups > 8:
            x_label_size = 7  # Very small for many categories
            rotation = 45  # Force rotation for crowded labels
        elif n_groups > 6:
            x_label_size = 8  # Smaller for many categories
        else:
            x_label_size = 9  # Slightly larger for fewer categories

        ax.set_xticklabels(formatted_labels, rotation=rotation,
                           ha='right' if rotation else 'center',
                           fontfamily=self.font_family,
                           fontsize=x_label_size,
                           fontweight='bold')  # Bold for better readability

        # Explicitly set tick parameters
        ax.tick_params(axis='x', which='major', labelsize=x_label_size, pad=3)  # Minimal padding

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

        # Explicitly set y-tick label fonts
        for label in ax.get_yticklabels():
            label.set_fontfamily(self.font_family)
            label.set_fontsize(self.tick_label_size)

        return fig

    def create_gender_chart(self, data: Dict[str, Dict[str, float]],
                            title: str = 'Gender',
                            figsize: Tuple[float, float] = (1.5, 2.5)) -> plt.Figure:
        """Create horizontal stacked bars for gender distribution - ALREADY CORRECT SIZE"""
        # Set matplotlib parameters for better rendering
        plt.rcParams['text.antialiased'] = True
        plt.rcParams['axes.linewidth'] = 0.8

        fig = plt.figure(figsize=figsize, dpi=self.fig_dpi)
        ax = fig.add_subplot(111)

        # Enable better rendering
        ax.set_rasterization_zorder(0)  # Rasterize background only

        # Get communities in the expected order
        communities = list(data.keys())
        n_communities = len(communities)

        # Bar parameters
        bar_height = 0.6
        y_positions = np.arange(n_communities)

        # Use consistent colors for all bars
        male_color = self.community_colors[0]  # Primary color (blue)
        female_color = self.community_colors[1]  # Secondary color (yellow)

        # Define edge properties for crisp rendering (without alpha)
        edge_props = dict(linewidth=0.5, edgecolor='#666666')  # Gray edge for subtlety

        # Simplified community labels
        community_labels = []
        for community in communities:
            if "Jazz Fans" in community and "NBA" not in community:
                community_labels.append("Jazz Fans")
            elif "Local Gen Pop" in community:
                community_labels.append("Local Gen Pop")
            elif "NBA Fans" in community or "League" in community:
                community_labels.append("NBA Fans")
            else:
                community_labels.append(community)  # Fallback

        # Track male/female positions for top labels
        male_positions = []
        female_positions = []

        for idx, community in enumerate(communities):
            values = data[community]
            male_pct = values.get('Male', 0)
            female_pct = values.get('Female', 0)

            # Draw stacked horizontal bar with consistent colors and edges
            # Male portion (blue)
            ax.barh(y_positions[idx], male_pct, bar_height,
                    left=0, color=male_color, alpha=0.8, **edge_props)

            # Female portion (yellow)
            ax.barh(y_positions[idx], female_pct, bar_height,
                    left=male_pct, color=female_color, alpha=0.8, **edge_props)

            # Store positions for top labels
            if idx == 0:
                male_positions.append(male_pct / 2)
                female_positions.append(male_pct + female_pct / 2)

            # Add percentage labels
            if male_pct > 5:
                ax.text(male_pct / 2, y_positions[idx], f'{int(male_pct)}%',
                        ha='center', va='center', fontweight='bold',
                        color='white', fontsize=self.label_size,
                        fontfamily=self.font_family)

            if female_pct > 5:
                ax.text(male_pct + female_pct / 2, y_positions[idx], f'{int(female_pct)}%',
                        ha='center', va='center', fontweight='bold',
                        color='black', fontsize=self.label_size,
                        fontfamily=self.font_family)

            # Add community label below each bar
            ax.text(50, y_positions[idx] - 0.4, community_labels[idx],
                    ha='center', va='top', fontsize=10,
                    fontfamily=self.font_family, color='black')

        # Add "Male" and "Female" labels at the top - centered on entire chart
        top_y = n_communities - 0.5 + 0.15  # Moved closer to top bar (was 0.4)

        # Center positions for visual balance - centered on the entire chart width
        chart_center = 50  # Center of 0-100 scale
        label_offset = 20  # Distance from center for each label

        male_center = chart_center - label_offset
        female_center = chart_center + label_offset

        ax.text(male_center, top_y, 'Male',
                ha='center', va='bottom', fontweight='bold',  # Bold
                fontsize=self.axis_label_size + 1, fontfamily=self.font_family,  # Slightly larger
                color='black')

        ax.text(female_center, top_y, 'Female',
                ha='center', va='bottom', fontweight='bold',  # Bold
                fontsize=self.axis_label_size + 1, fontfamily=self.font_family,  # Slightly larger
                color='black')

        # Formatting - minimal design with space for labels
        ax.set_ylim(-0.8, n_communities - 0.5 + 0.6)
        ax.set_xlim(0, 100)

        # Remove ALL axes and labels
        ax.set_yticks([])
        ax.set_xticks([])
        ax.set_xlabel('')
        ax.set_ylabel('')

        # Remove ALL spines for clean look
        for spine in ax.spines.values():
            spine.set_visible(False)

        ax.grid(False)
        plt.tight_layout()

        return fig

    def create_ethnicity_chart(self, data: pd.DataFrame) -> plt.Figure:
        """Create ethnicity grouped bar chart with correct aspect ratio"""
        # PowerPoint size: 4.5" x 2.5" = 1.8 aspect ratio
        return self.create_grouped_bar_chart(data, chart_type='ethnicity', figsize=(4.5, 2.5))

    def create_generation_chart(self, data: pd.DataFrame) -> plt.Figure:
        """Create generation chart with correct aspect ratio"""
        # PowerPoint size: 4.5" x 2.5" = 1.8 aspect ratio
        return self.create_grouped_bar_chart(data, chart_type='generation', ylabel='Balanced Pct', figsize=(4.5, 2.5))

    def create_income_chart(self, data: pd.DataFrame) -> plt.Figure:
        """Create income chart with correct aspect ratio"""
        # PowerPoint size: 4.8" x 2.5" = 1.92 aspect ratio
        return self.create_grouped_bar_chart(data, chart_type='income', ylabel='Balanced Pct', figsize=(4.8, 2.5))

    def create_occupation_chart(self, data: pd.DataFrame) -> plt.Figure:
        """Create occupation chart with correct aspect ratio"""
        # PowerPoint size: 5.6" x 2.5" = 2.24 aspect ratio
        return self.create_grouped_bar_chart(data, chart_type='occupation', ylabel='% of Total Customer Count',
                                             figsize=(5.6, 2.5))

    def create_children_chart(self, data: pd.DataFrame) -> plt.Figure:
        """Create children chart with correct aspect ratio"""
        # PowerPoint size: 3.0" x 2.5" = 1.2 aspect ratio
        return self.create_grouped_bar_chart(data, chart_type='children', ylabel='% of Total Customer Count',
                                             figsize=(3.0, 2.5))

    def save_chart_for_powerpoint(self, fig: plt.Figure, filename: str,
                                  output_dir: Path, width_inches: float = None,
                                  height_inches: float = None) -> Path:
        """Save chart optimized for PowerPoint insertion"""

        # Use the figure's current size if not specified
        if width_inches is None or height_inches is None:
            current_size = fig.get_size_inches()
            width_inches = width_inches or current_size[0]
            height_inches = height_inches or current_size[1]

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

        # Also save a high-res version for better quality
        hires_path = output_dir / f'{filename}_hires.png'
        fig.savefig(hires_path,
                    dpi=300,  # Extra high DPI
                    bbox_inches='tight',
                    facecolor='white',
                    edgecolor='none',
                    pad_inches=0.1)

        return output_path

    def create_all_demographic_charts(self, demographic_data: Dict[str, Any],
                                      output_dir: Optional[Path] = None) -> Dict[str, plt.Figure]:
        """Create all demographic charts with correct PowerPoint aspect ratios"""
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

                    # Create appropriate chart with correct aspect ratio
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
                    # Use horizontal bars for gender
                    fig = self.create_gender_chart(data_dict)
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
                    # Get the actual figure dimensions
                    current_size = fig.get_size_inches()
                    width_inches = current_size[0]
                    height_inches = current_size[1]

                    # Special handling for gender chart - save at higher DPI
                    if chart_name == 'gender':
                        # Save gender chart at higher DPI for better text clarity
                        output_path = output_dir / f'{chart_name}_chart.png'
                        fig.savefig(output_path,
                                    dpi=300,  # Higher DPI for gender chart
                                    bbox_inches='tight',
                                    facecolor='white',
                                    edgecolor='none',
                                    pad_inches=0.05)

                        hires_path = output_dir / f'{chart_name}_chart_hires.png'
                        fig.savefig(hires_path,
                                    dpi=400,  # Extra high DPI
                                    bbox_inches='tight',
                                    facecolor='white',
                                    edgecolor='none',
                                    pad_inches=0.05)
                    else:
                        # Save other charts normally
                        output_path = self.save_chart_for_powerpoint(
                            fig, f'{chart_name}_chart', output_dir,
                            width_inches=width_inches,
                            height_inches=height_inches
                        )
                    print(f"Saved {chart_name} chart to {output_path} at {width_inches:.1f}x{height_inches:.1f} inches")

                except Exception as e:
                    print(f"Error saving {chart_name} chart: {str(e)}")

        return charts