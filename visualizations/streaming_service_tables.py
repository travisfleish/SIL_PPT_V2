"""
Render grouped tables for streaming services (e.g., Disney+/ESPN+/Hulu, Peacock TV, Prime Video, YouTube TV)
in a multi-column grid matching the provided example image.

Input CSV (case-insensitive column names, aliases supported):
  - service: Streaming brand/group label for the section
  - team: Team name
  - index_vs_gen_pop: numeric
  - spc_index: numeric (or any second index metric)

The graphic will group by service, each with:
  - Small colored header with brand swatch and title
  - Column headers: Team | Index vs Gen Pop | SPC Index
  - Light grid lines and alternating row background
  - 2-column layout (services fill left to right, then wrap)

CLI:
  python -m visualizations.streaming_service_tables --input path/to.csv --output output/streaming_tables.png \
      --cols 2 --title "" --sort index_desc
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import pandas as pd

from utils.font_manager import font_manager


# Brand color hints (swatch at left of each header)
DEFAULT_SERVICE_COLORS: Dict[str, str] = {
    'DISNEY+ (DISNEY / ESPN / HULU BUNDLE)': '#1F8ED6',
    'DISNEY+': '#1F8ED6',
    'ESPN+': '#E2212A',
    'HULU / HULU LIVE TV': '#1CE783',
    'HULU': '#1CE783',
    'PEACOCK TV': '#00A650',
    'PRIME VIDEO': '#00A8E1',
    'YOUTUBE TV': '#FF0000',
}


@dataclass
class Style:
    fig_size: Tuple[float, float] = (10.5, 3.5)  # Wide banner-like layout
    dpi: int = 300
    bg: str = '#FFFFFF'
    header_bg: str = '#F7F7F7'
    header_text: str = '#1A1A1A'
    swatch_border: str = '#CCCCCC'
    grid: str = '#E5E5E5'
    row_alt1: str = '#FFFFFF'
    row_alt2: str = '#FAFAFA'
    text: str = '#222222'
    subheader_text: str = '#555555'
    font_family: Optional[str] = None
    title_font_size: int = 12
    header_font_size: int = 11
    cell_font_size: int = 9


class StreamingServiceTables:
    def __init__(self, style: Optional[Style] = None, service_colors: Optional[Dict[str, str]] = None):
        self.style = style or Style()
        fm_family = font_manager.get_font_family('Overpass')
        self.style.font_family = fm_family
        plt.rcParams['font.family'] = fm_family
        self.service_colors = {k.upper(): v for k, v in (service_colors or DEFAULT_SERVICE_COLORS).items()}

    def _service_color(self, service: str) -> str:
        if not service:
            return '#D9D9D9'
        s = str(service).strip().upper()
        return self.service_colors.get(s, '#D9D9D9')

    def _format_int(self, v) -> str:
        if v is None or pd.isna(v):
            return ''
        try:
            return f"{int(round(float(v)))}"
        except Exception:
            return str(v)

    def create(self,
               df: pd.DataFrame,
               output: Optional[Path] = None,
               cols: int = 2,
               title: str = '',
               sort: str = 'index_desc') -> Path:
        # Normalize columns
        cols_map = {c.lower().strip(): c for c in df.columns}

        def col(*names: str) -> str:
            for n in names:
                if n in cols_map:
                    return cols_map[n]
            raise KeyError(f"Missing column; tried {names}")

        service_col = col('service', 'platform', 'brand')
        team_col = col('team')
        index_col = col('index', 'index_vs_gen_pop', 'index_vs_gsp')
        spc_col = col('spc_index', 'spc', 'spcidx', 'index2')

        # Sorting within each service group
        df_proc = df.copy()
        if sort == 'index_desc':
            df_proc = df_proc.sort_values([service_col, index_col], ascending=[True, False])
        elif sort == 'index_asc':
            df_proc = df_proc.sort_values([service_col, index_col], ascending=[True, True])
        else:
            df_proc = df_proc.sort_values([service_col])

        groups = [(name, g.copy()) for name, g in df_proc.groupby(service_col, sort=False)]
        n_groups = len(groups)

        # Layout: grid with `cols` columns
        rows = (n_groups + cols - 1) // cols
        fig = plt.figure(figsize=self.style.fig_size, dpi=self.style.dpi, facecolor=self.style.bg)

        # Optionally add a top title
        top_offset = 0.0
        if title:
            title_ax = fig.add_axes([0.01, 0.93, 0.98, 0.06])
            title_ax.axis('off')
            title_ax.text(0.0, 0.5, title, ha='left', va='center', fontsize=self.style.title_font_size,
                          fontweight='bold', color=self.style.header_text, family=self.style.font_family)
            top_offset = 0.06

        # Compute cell box sizes
        grid_left, grid_right = 0.01, 0.99
        grid_top = 0.92 - top_offset
        grid_bottom = 0.04
        grid_width = grid_right - grid_left
        grid_height = grid_top - grid_bottom
        cell_w = grid_width / cols
        cell_h = grid_height / rows

        # For each service group, render a mini-table box
        for idx, (service_name, g) in enumerate(groups):
            c = idx % cols
            r = idx // cols

            left = grid_left + c * cell_w
            top = grid_top - r * cell_h
            # Box for this group
            ax = fig.add_axes([left, top - cell_h, cell_w, cell_h])
            ax.axis('off')

            # Header row with swatch and service label
            header_ax = fig.add_axes([left, top - 0.12 * cell_h, cell_w, 0.12 * cell_h])
            header_ax.axis('off')
            header_ax.add_patch(plt.Rectangle((0, 0), 1, 1, color=self.style.header_bg, transform=header_ax.transAxes))
            # Color swatch
            swatch_color = self._service_color(service_name)
            header_ax.add_patch(plt.Rectangle((0.005, 0.15), 0.02, 0.7, color=swatch_color, transform=header_ax.transAxes))
            header_ax.text(0.03, 0.5, str(service_name), ha='left', va='center', color=self.style.header_text,
                           fontsize=self.style.header_font_size, fontweight='bold', family=self.style.font_family)

            # Column headers
            colhdr_ax = fig.add_axes([left, top - 0.24 * cell_h, cell_w, 0.10 * cell_h])
            colhdr_ax.axis('off')
            colhdr_ax.add_patch(plt.Rectangle((0, 0), 1, 1, color='#FFFFFF', transform=colhdr_ax.transAxes))
            colhdr_ax.add_line(plt.Line2D([0, 1], [0, 0], color=self.style.grid, linewidth=0.8, transform=colhdr_ax.transAxes))
            colhdr_ax.text(0.01, 0.5, 'Team', ha='left', va='center', fontsize=self.style.cell_font_size,
                           color=self.style.subheader_text, family=self.style.font_family)
            colhdr_ax.text(0.64, 0.5, 'Index vs Gen Pop', ha='center', va='center', fontsize=self.style.cell_font_size,
                           color=self.style.subheader_text, family=self.style.font_family)
            colhdr_ax.text(0.88, 0.5, 'SPC Index', ha='center', va='center', fontsize=self.style.cell_font_size,
                           color=self.style.subheader_text, family=self.style.font_family)

            # Body rows
            body_ax = fig.add_axes([left, top - cell_h, cell_w, 0.64 * cell_h])
            body_ax.axis('off')

            # Build rows as text; compute y steps based on number of rows
            n = len(g)
            if n == 0:
                continue
            y_step = 1.0 / (n + 0.2)
            y = 1.0 - y_step * 0.5

            for i, (_, row) in enumerate(g.iterrows()):
                # Alternating background bands
                bg = self.style.row_alt1 if i % 2 == 0 else self.style.row_alt2
                body_ax.add_patch(plt.Rectangle((0, y - y_step * 0.5), 1, y_step, color=bg, transform=body_ax.transAxes))

                body_ax.text(0.01, y, str(row[team_col]), ha='left', va='center', fontsize=self.style.cell_font_size,
                             color=self.style.text, family=self.style.font_family)
                body_ax.text(0.64, y, self._format_int(row[index_col]), ha='center', va='center', fontsize=self.style.cell_font_size,
                             color=self.style.text, family=self.style.font_family)
                body_ax.text(0.88, y, self._format_int(row[spc_col]), ha='center', va='center', fontsize=self.style.cell_font_size,
                             color=self.style.text, family=self.style.font_family)

                # next row position
                y -= y_step

        # Save
        if output is None:
            output = Path('output/streaming_tables.png')
        output = Path(output)
        output.parent.mkdir(parents=True, exist_ok=True)
        plt.tight_layout()
        plt.savefig(output, dpi=self.style.dpi, bbox_inches='tight', facecolor=self.style.bg, edgecolor='none')
        plt.close(fig)
        return output


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def build_from_csv(input_csv: Path, output: Optional[Path] = None, cols: int = 2, title: str = '', sort: str = 'index_desc') -> Path:
    df = _read_csv(Path(input_csv))
    viz = StreamingServiceTables()
    return viz.create(df, output=output, cols=cols, title=title, sort=sort)


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Render streaming service grouped tables from CSV')
    p.add_argument('--input', required=True, type=Path)
    p.add_argument('--output', required=False, type=Path, default=Path('output/streaming_tables.png'))
    p.add_argument('--cols', required=False, type=int, default=2)
    p.add_argument('--title', required=False, default='')
    p.add_argument('--sort', required=False, default='index_desc', choices=['index_desc', 'index_asc', 'none'])
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    path = build_from_csv(args.input, output=args.output, cols=args.cols, title=args.title, sort=args.sort)
    print(f"Saved streaming tables graphic to: {path}")


if __name__ == '__main__':
    main()



