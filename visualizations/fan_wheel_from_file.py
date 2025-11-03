"""
Render a fan wheel from a user-provided JSON or CSV file (no Snowflake).

Usage examples (from project root):
  python3 -m visualizations.fan_wheel_from_file --input /absolute/path/to/data.json --output output/custom_fan_wheel.png --team "Utah Jazz"
  python3 -m visualizations.fan_wheel_from_file --input /absolute/path/to/data.csv --no-logos

Input schema options (detected automatically):
  Minimal schema (recommended):
    - COMMUNITY: str (required)
    - behavior: str (required)
    - MERCHANT: str (optional, used only for logos)
    - PERC_INDEX: int|float (optional; defaults to 100 if missing)

  Alternate schema (common in raw lists):
    - community, text, merchant, index  (auto-mapped to the required names)

If --no-logos is passed, logos are skipped and placeholders are not drawn.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List, Any

import pandas as pd
import numpy as np

from visualizations.fan_wheel import FanWheel
from utils.team_config_manager import TeamConfigManager


def _infer_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Map common alternate column names to the expected schema.

    Expected: COMMUNITY, MERCHANT, behavior, PERC_INDEX
    """
    col_map_candidates = [
        {"COMMUNITY": "COMMUNITY", "MERCHANT": "MERCHANT", "behavior": "behavior", "PERC_INDEX": "PERC_INDEX"},
        {"COMMUNITY": "community", "MERCHANT": "merchant", "behavior": "behavior", "PERC_INDEX": "index"},
        {"COMMUNITY": "Community", "MERCHANT": "Merchant", "behavior": "Text", "PERC_INDEX": "Index"},
        # Common community index column name from exported tables
        {"COMMUNITY": "COMMUNITY", "MERCHANT": "MERCHANT", "behavior": "behavior", "PERC_INDEX": "COMMUNITY_INDEX"},
    ]

    df_cols = {c.lower(): c for c in df.columns}

    def resolve(name: str) -> str | None:
        # Find a column by case-insensitive name
        lowered = name.lower()
        return df_cols.get(lowered)

    # Try each candidate mapping; use the first that fully resolves
    for candidate in col_map_candidates:
        mapped: Dict[str, str] = {}
        ok = True
        for target, source in candidate.items():
            src_col = resolve(source) if source not in df.columns else source
            if src_col is None and target in ("MERCHANT", "PERC_INDEX"):
                # Optional fields are allowed to be missing
                continue
            if src_col is None:
                ok = False
                break
            mapped[target] = src_col
        if ok:
            out = pd.DataFrame()
            out["COMMUNITY"] = df[mapped.get("COMMUNITY", "COMMUNITY")].astype(str)
            # behavior: default to COMMUNITY if not present
            behavior_src = mapped.get("behavior")
            if behavior_src and behavior_src in df.columns:
                out["behavior"] = df[behavior_src].astype(str)
            else:
                out["behavior"] = out["COMMUNITY"].astype(str)
            # merchant optional
            merchant_src = mapped.get("MERCHANT")
            out["MERCHANT"] = df[merchant_src].astype(str) if merchant_src else ""
            # index optional
            idx_src = mapped.get("PERC_INDEX")
            out["PERC_INDEX"] = pd.to_numeric(df[idx_src], errors="coerce").fillna(100).astype(float) if idx_src else 100
            return out

    # Fallback: if minimum required columns exist by exact name
    # Fallback: minimal requirements (COMMUNITY). behavior defaults to COMMUNITY
    if "COMMUNITY" in df.columns:
        out = pd.DataFrame()
        out["COMMUNITY"] = df["COMMUNITY"].astype(str)
        out["behavior"] = df["behavior"].astype(str) if "behavior" in df.columns else out["COMMUNITY"].astype(str)
        out["MERCHANT"] = df["MERCHANT"].astype(str) if "MERCHANT" in df.columns else ""
        if "PERC_INDEX" in df.columns:
            out["PERC_INDEX"] = pd.to_numeric(df["PERC_INDEX"], errors="coerce").fillna(100).astype(float)
        elif "COMMUNITY_INDEX" in df.columns:
            out["PERC_INDEX"] = pd.to_numeric(df["COMMUNITY_INDEX"], errors="coerce").fillna(100).astype(float)
        else:
            out["PERC_INDEX"] = 100
        return out

    raise ValueError("Input file must include COMMUNITY; behavior defaults to COMMUNITY if absent.")


def _load_table(input_path: Path) -> pd.DataFrame:
    if input_path.suffix.lower() in (".json", ".ndjson"):
        with input_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        # Accept either a list of dicts or an object with a top-level key
        if isinstance(data, dict):
            # choose the first list-like value
            for v in data.values():
                if isinstance(v, list):
                    data = v
                    break
        if not isinstance(data, list):
            raise ValueError("JSON must be a list of objects or contain a list value.")
        df = pd.DataFrame(data)
        return df

    if input_path.suffix.lower() in (".csv", ".tsv"):
        sep = "," if input_path.suffix.lower() == ".csv" else "\t"
        return pd.read_csv(input_path, sep=sep)

    raise ValueError("Unsupported input format. Use .json, .csv, or .tsv")


def _get_team_config(
    team: str | None,
    league: str | None,
    primary: str | None,
    secondary: str | None,
    accent: str | None,
) -> Dict[str, Any]:
    base_cfg: Dict[str, Any] | None = None
    if team:
        try:
            manager = TeamConfigManager()
            base_cfg = manager.get_team_config(team)
        except Exception:
            base_cfg = None

    if base_cfg is None:
        base_cfg = {
            "team_name": team or "Custom Team",
            "team_name_short": (team or "Custom").split()[-1],
            "league": league or "Custom",
            "colors": {
                "primary": "#17408B",
                "secondary": "#C9082A",
                "accent": "#1D428A",
            },
        }

    # Apply color overrides if provided
    colors = dict(base_cfg.get("colors", {}))
    if primary:
        colors["primary"] = primary
    if secondary:
        colors["secondary"] = secondary
    if accent:
        colors["accent"] = accent
    base_cfg["colors"] = colors
    return base_cfg


class CustomTextFanWheel(FanWheel):
    def __init__(self, *args, center_text: str | None = None, **kwargs):
        self.center_text_override = center_text
        super().__init__(*args, **kwargs)

    def _draw_center_circle(self, ax, team_logo=None):  # type: ignore[override]
        from matplotlib.patches import Circle
        # Draw center circle (simplified, text-only)
        center_circle = Circle((0, 0), self.inner_radius,
                               facecolor='black',
                               edgecolor=self.secondary_color,
                               linewidth=5,
                               zorder=20)
        ax.add_patch(center_circle)

        text = self.center_text_override or f"THE {self.team_short.upper()} FAN"
        # Respect provided casing; do not force uppercase if override given
        ax.text(0, 0,
                text,
                ha='center', va='center',
                fontsize=28,
                fontweight='bold',
                fontfamily=self.font_family,
                color='white', zorder=22, linespacing=0.9)


class ConfigurableFanWheel(FanWheel):
    def __init__(self, *args, label_font_overrides: Dict[str, int] | None = None, **kwargs):
        self.label_font_overrides = { (k or '').strip().lower(): v for k, v in (label_font_overrides or {}).items() }
        super().__init__(*args, **kwargs)

    def _add_segment_content(self, ax, wheel_data: pd.DataFrame, angle_step: float):  # type: ignore[override]
        from textwrap import wrap

        missing_logos: List[str] = []

        for i, (_, row) in enumerate(wheel_data.iterrows()):
            center_angle = i * angle_step + angle_step / 2 - 90
            angle_rad = np.deg2rad(center_angle)

            # Logo position
            logo_x = self.logo_radius * np.cos(angle_rad)
            logo_y = self.logo_radius * np.sin(angle_rad)

            merchant_name = row['MERCHANT']
            logo_added = self._add_merchant_logo(ax, merchant_name, logo_x, logo_y)
            if not logo_added:
                missing_logos.append(merchant_name)

            # Behavior text
            text_radius = self.outer_radius - 0.9
            text_x = text_radius * np.cos(angle_rad)
            text_y = text_radius * np.sin(angle_rad)

            behavior_text = row['behavior']

            # Wrapping
            word_count = len(behavior_text.split())
            if word_count >= 4 or len(behavior_text) > 20:
                wrapped_text = '\n'.join(wrap(behavior_text, width=10, break_long_words=False))
            elif word_count == 3 or len(behavior_text) > 12:
                wrapped_text = '\n'.join(wrap(behavior_text, width=11, break_long_words=False))
            else:
                wrapped_text = behavior_text

            lines = wrapped_text.split('\n')
            if len(lines) == 2 and len(behavior_text) > 18:
                wrapped_text = '\n'.join(wrap(behavior_text, width=9, break_long_words=False))

            # Font size override by label
            override_key = behavior_text.strip().lower()
            fontsize = self.label_font_overrides.get(override_key, 22)

            ax.text(text_x, text_y, wrapped_text,
                    ha='center', va='center',
                    fontsize=fontsize,
                    fontweight='bold',
                    fontfamily=self.font_family,
                    color=self.segment_text_color,
                    rotation=0,
                    linespacing=0.9,
                    zorder=7)

        if missing_logos and self.enable_logos:
            logger.debug(f"Missing logos for: {', '.join(missing_logos)}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Render a fan wheel from a JSON/CSV file (no Snowflake)")
    parser.add_argument("--input", required=True, type=Path, help="Absolute path to input JSON/CSV/TSV")
    parser.add_argument("--output", type=Path, help="Output image path (PNG)")
    parser.add_argument("--team", type=str, help="Team key from config/team_config.yaml or free text")
    parser.add_argument("--league", type=str, help="Optional league label when using --team as free text")
    parser.add_argument("--no-logos", action="store_true", help="Disable logo rendering")
    parser.add_argument("--transparent", action="store_true", help="Transparent background")
    # Branding overrides
    parser.add_argument("--primary-color", type=str, help="Primary hex color (e.g. #0A08D9)")
    parser.add_argument("--secondary-color", type=str, help="Secondary hex color (e.g. #DBF66F)")
    parser.add_argument("--accent-color", type=str, help="Accent hex color")
    parser.add_argument("--center-text", type=str, help='Custom center text (e.g., "The NBA Fan")')
    # Layout tweaks
    parser.add_argument("--swap", type=str, help='Swap two communities by name, e.g., "Sneakerheads,Skate"')
    parser.add_argument("--shrink", action='append', help='Set label font size like "Label=18"; can repeat')

    args = parser.parse_args()

    input_path: Path = args.input
    if not input_path.is_file():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    raw = _load_table(input_path)
    wheel_df = _infer_columns(raw)

    # Optional swap of two communities' positions
    if args.swap:
        try:
            a, b = [s.strip() for s in args.swap.split(',', 1)]
            a_idx = wheel_df.index[wheel_df['COMMUNITY'].str.strip().str.lower() == a.strip().lower()].tolist()
            b_idx = wheel_df.index[wheel_df['COMMUNITY'].str.strip().str.lower() == b.strip().lower()].tolist()
            if a_idx and b_idx:
                ai, bi = a_idx[0], b_idx[0]
                temp = wheel_df.loc[ai].copy()
                wheel_df.loc[ai] = wheel_df.loc[bi]
                wheel_df.loc[bi] = temp
                wheel_df.reset_index(drop=True, inplace=True)
        except Exception:
            pass

    # Parse shrink overrides
    label_font_overrides: Dict[str, int] = {}
    if args.shrink:
        for item in args.shrink:
            if '=' in item:
                k, v = item.split('=', 1)
                k = k.strip()
                try:
                    label_font_overrides[k] = int(v.strip())
                except ValueError:
                    continue
    if wheel_df.empty:
        raise ValueError("No rows found after parsing input data.")

    team_config = _get_team_config(
        args.team,
        args.league,
        args.primary_color,
        args.secondary_color,
        args.accent_color,
    )

    # Choose output
    output_path = args.output or Path("output/custom_fan_wheel.png")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Choose wheel class based on options
    if args.center_text:
        base = CustomTextFanWheel(team_config, enable_logos=(not args.no_logos), center_text=args.center_text)
    else:
        base = FanWheel(team_config, enable_logos=(not args.no_logos))

    # Wrap with configurable font overrides if provided
    if label_font_overrides:
        # Recreate with overrides (rely on same team config/colors)
        fan_wheel = ConfigurableFanWheel(team_config, enable_logos=base.enable_logos, label_font_overrides=label_font_overrides)
    else:
        fan_wheel = base
    result = fan_wheel.create(wheel_df, output_path=output_path, team_logo=None, transparent=args.transparent)
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


