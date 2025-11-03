"""
Create a table-style visualization for "Winning Mobile Provider by Team".

Inputs: CSV with columns (case-insensitive, flexible names supported):
  - team: Team name
  - provider: Winning mobile provider (e.g., VERIZON, AT&T)
  - percent: Percent of fans with the top provider (0-100 or 0-1)
  - index: Index vs. local gen pop (integer/float)
  - spend: Spend per person (dollars)

The script will:
  - Sort rows by percent descending by default (configurable)
  - Color the Percent column cell by provider color (e.g., Verizon red, AT&T blue)
  - Format percent, index, and currency consistently
  - Add title and legend matching the example layout
  - Save as a high-DPI PNG (default: output/mobile_provider_table.png)

CLI usage:
  python -m visualizations.mobile_provider_table --input path/to.csv --output output/table.png \
      --title "Winning Mobile Provider by Team" --sort percent_desc
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import pandas as pd

from visualizations.base_chart import BaseChart
from utils.font_manager import font_manager


# Default provider color palette (tuned to match common brand colors)
DEFAULT_PROVIDER_COLORS: Dict[str, str] = {
    'VERIZON': '#EE2E24',  # Verizon red
    'AT&T': '#00A8E0',     # AT&T blue
    'ATT': '#00A8E0',      # common variant
    'T-MOBILE': '#E20074',
    'TMOBILE': '#E20074',
    'SPRINT': '#FFCD00',
    'US CELLULAR': '#2F66B0',
}


@dataclass
class TableStyle:
    figure_size: Tuple[float, float] = (4.2, 11.0)  # tall/skinny like example
    dpi: int = 300
    header_bg: str = '#000000'
    header_fg: str = '#FFFFFF'
    column_header_bg: str = '#F2F2F2'
    grid_color: str = '#DDDDDD'
    text_color: str = '#111111'
    row_alt_bg: str = '#FFFFFF'
    row_alt_bg2: str = '#FAFAFA'
    legend_border: str = '#DDDDDD'
    border_color: str = '#CCCCCC'
    cell_edge_color: str = '#FFFFFF'
    font_family: Optional[str] = None
    title_font_size: int = 14
    header_font_size: int = 12
    cell_font_size: int = 9
    legend_font_size: int = 9


class MobileProviderTable(BaseChart):
    def __init__(self, provider_colors: Optional[Dict[str, str]] = None, style: Optional[TableStyle] = None):
        super().__init__()

        # Configure fonts via font_manager
        fm_family = font_manager.get_font_family('Overpass')
        plt.rcParams['font.family'] = fm_family

        self.style = style or TableStyle(font_family=fm_family)
        self.provider_colors = {k.upper(): v for k, v in (provider_colors or DEFAULT_PROVIDER_COLORS).items()}

        # Make the default figure a bit taller and skinnier for this chart
        self.default_figsize = self.style.figure_size
        self.fig_dpi = self.style.dpi

    def _format_percent(self, value: float) -> str:
        if value is None or pd.isna(value):
            return ''
        # Accept 0-1 and 0-100 inputs
        if 0 <= float(value) <= 1:
            pct = value * 100
        else:
            pct = value
        return f"{pct:.0f}%"

    def _format_currency(self, value: float) -> str:
        if value is None or pd.isna(value):
            return ''
        return f"${float(value):,.0f}"

    def _normalize_provider(self, provider: str) -> str:
        if provider is None or (isinstance(provider, float) and pd.isna(provider)):
            return ''
        p = str(provider).strip().upper().replace('&', 'AND').replace('’', "'")
        p = p.replace('Ã©', 'é')  # Defensive for possible encoding issues
        if p == 'AT&T':
            return 'AT&T'
        if p == 'ATT':
            return 'AT&T'
        return p

    def _get_provider_color(self, provider: str) -> str:
        key = self._normalize_provider(provider)
        return self.provider_colors.get(key, '#D9D9D9')

    def create(self,
               data: pd.DataFrame,
               output_path: Optional[Path] = None,
               title: str = 'Winning Mobile Provider by Team',
               sort: str = 'percent_desc') -> Path:
        """
        Render the table visualization from a DataFrame.

        Expected columns (case-insensitive, will fuzzy-match):
          team, provider, percent, index, spend
        """
        # Column normalization
        cols = {c.lower().strip(): c for c in data.columns}

        def col(*options: str) -> str:
            for o in options:
                if o in cols:
                    return cols[o]
            raise KeyError(f"Missing column, tried aliases: {options}")

        team_col = col('team')
        provider_col = col('provider', 'top_provider', 'winning_provider')
        percent_col = col('percent', 'pct', 'percent_top_provider', 'pct_top')
        index_col = col('index', 'idx', 'index_vs_gsp', 'index_vs_local_gen_pop')
        spend_col = col('spend', 'spend_per_person', 'avg_spend', 'avg_spend_per_person')

        # Sorting
        df = data.copy()
        # Convert percent for sorting consistently
        pct_for_sort = df[percent_col].astype(float).where(df[percent_col] <= 1, df[percent_col] / 100.0)
        if sort == 'percent_desc':
            df = df.assign(_pct=pct_for_sort).sort_values('_pct', ascending=False).drop(columns=['_pct'])
        elif sort == 'percent_asc':
            df = df.assign(_pct=pct_for_sort).sort_values('_pct', ascending=True).drop(columns=['_pct'])
        else:
            # no-op or sort by provided order
            pass

        # Build table content
        column_headers = ['Team', '% of Fans by Top Provider', 'Index vs\nGSP', 'Spend\nPer Person']
        rows: List[List[str]] = []
        provider_bg_colors: List[str] = []
        for _, r in df.iterrows():
            rows.append([
                str(r[team_col]),
                self._format_percent(r[percent_col]),
                f"{float(r[index_col]):.0f}" if pd.notna(r[index_col]) else '',
                self._format_currency(r[spend_col]),
            ])
            provider_bg_colors.append(self._get_provider_color(r[provider_col]))

        # Build figure
        fig = plt.figure(figsize=self.default_figsize, dpi=self.fig_dpi, facecolor='white')
        ax = fig.add_subplot(111)
        ax.axis('off')

        # Title header bar
        title_box = fig.add_axes([0.05, 0.93, 0.9, 0.055])
        title_box.axis('off')
        title_box.add_patch(plt.Rectangle((0, 0), 1, 1, color=self.style.header_bg, transform=title_box.transAxes))
        title_box.text(0.5, 0.5, title, color=self.style.header_fg,
                       ha='center', va='center', fontsize=self.style.title_font_size,
                       fontweight='bold', family=self.style.font_family)

        # Column headers area (small bar under title)
        colhdr_box = fig.add_axes([0.05, 0.89, 0.9, 0.035])
        colhdr_box.axis('off')
        colhdr_box.add_patch(plt.Rectangle((0, 0), 1, 1, color=self.style.column_header_bg, transform=colhdr_box.transAxes))
        # Render column headers spaced according to column widths
        # Column relative widths: Team=0.47, Percent=0.18, Index=0.16, Spend=0.19
        col_xs = [0.02, 0.49, 0.68, 0.84]
        for text, x in zip(column_headers, col_xs):
            colhdr_box.text(x, 0.5, text, ha='left', va='center', color=self.text_color if hasattr(self, 'text_color') else self.style.text_color,
                            fontsize=self.style.header_font_size, fontweight='bold', family=self.style.font_family)

        # Table area
        table_top = 0.09  # bottom margin for legend
        table_height = 0.78
        left = 0.05
        width = 0.9
        table_ax = fig.add_axes([left, table_top, width, table_height])
        table_ax.axis('off')

        cell_text = rows
        # Column widths as fractions of the axes width
        col_widths = [0.47, 0.18, 0.16, 0.19]

        table = table_ax.table(cellText=cell_text,
                               colWidths=col_widths,
                               cellLoc='left',
                               loc='upper left')

        table.auto_set_font_size(False)
        table.set_fontsize(self.style.cell_font_size)

        # Styling cells
        n_rows = len(rows)
        for row_idx in range(n_rows):
            # Alternate row backgrounds for readability
            bg = self.style.row_alt_bg if row_idx % 2 == 0 else self.style.row_alt_bg2
            for col_idx in range(4):
                cell = table[(row_idx, col_idx)]
                cell.set_edgecolor(self.style.cell_edge_color)
                cell.set_linewidth(0.6)
                if col_idx == 1:
                    # Provider-colored percent cell
                    cell.set_facecolor(provider_bg_colors[row_idx])
                    cell.get_text().set_color('#FFFFFF')
                    cell.get_text().set_ha('center')
                else:
                    cell.set_facecolor(bg)
                    cell.get_text().set_color(self.style.text_color)
                    if col_idx == 0:
                        cell.get_text().set_ha('left')
                    else:
                        cell.get_text().set_ha('center')

        # Adjust row heights for compactness
        # Use the axes height to approximate target rows per height
        base_height = 0.03  # good default for ~30-32 rows
        for row_idx in range(n_rows):
            table[(row_idx, 0)].set_height(base_height)

        # Grid line under column headers
        table_ax.add_line(plt.Line2D([0, 1], [1, 1], color=self.style.grid_color, linewidth=1, transform=table_ax.transAxes))

        # Legend at the very bottom
        legend_ax = fig.add_axes([0.3, 0.02, 0.4, 0.05])
        legend_ax.axis('off')

        # Build legend entries from providers present in the data (preserve order: Verizon, AT&T, others alpha)
        present_providers = [self._normalize_provider(p) for p in df[provider_col].astype(str).tolist()]
        unique_providers = []
        for p in present_providers:
            if p and p not in unique_providers:
                unique_providers.append(p)

        def provider_sort_key(p: str) -> Tuple[int, str]:
            if p == 'VERIZON':
                return (0, '')
            if p in ('AT&T', 'ATT'):
                return (1, '')
            return (2, p)

        unique_providers.sort(key=provider_sort_key)

        legend_handles = [
            Patch(facecolor=self._get_provider_color(p), label=p)
            for p in unique_providers
        ]

        if legend_handles:
            legend = legend_ax.legend(handles=legend_handles,
                                      loc='center', ncol=min(3, len(legend_handles)),
                                      frameon=True, fancybox=True, shadow=False,
                                      prop={'family': self.style.font_family, 'size': self.style.legend_font_size})
            legend.get_frame().set_edgecolor(self.style.legend_border)

        # Tight layout and save
        plt.tight_layout()

        if output_path is None:
            output_path = Path('output') / 'mobile_provider_table.png'
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=self.fig_dpi, bbox_inches='tight', facecolor='white', edgecolor='none')
        plt.close(fig)
        return output_path


def _read_csv(input_path: Path) -> pd.DataFrame:
    df = pd.read_csv(input_path)
    return df


def build_from_csv(input_csv: Path,
                   output_path: Optional[Path] = None,
                   title: str = 'Winning Mobile Provider by Team',
                   sort: str = 'percent_desc') -> Path:
    df = _read_csv(Path(input_csv))
    chart = MobileProviderTable()
    return chart.create(df, output_path=output_path, title=title, sort=sort)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Render "Winning Mobile Provider by Team" table graphic from CSV')
    parser.add_argument('--input', required=True, type=Path, help='Path to input CSV')
    parser.add_argument('--output', required=False, type=Path, default=Path('output/mobile_provider_table.png'), help='Output PNG path')
    parser.add_argument('--title', required=False, default='Winning Mobile Provider by Team', help='Chart title')
    parser.add_argument('--sort', required=False, default='percent_desc', choices=['percent_desc', 'percent_asc', 'none'], help='Sort ordering')
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    path = build_from_csv(args.input, output_path=args.output, title=args.title, sort=args.sort)
    print(f"Saved table graphic to: {path}")


if __name__ == '__main__':
    main()



