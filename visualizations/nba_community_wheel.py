"""
Standalone generator for an NBA-wide fan wheel using the project's
fan wheel visualization logic. This script renders a wheel of ten
audience communities with their index values (vs. Gen Pop) and saves
the image to the `output/` directory.

Run from project root:
  python3 -m visualizations.nba_community_wheel
"""

from pathlib import Path
from typing import List, Dict

import numpy as np
import pandas as pd
from matplotlib.patches import Wedge

from visualizations.fan_wheel import FanWheel


class FanWheelNoLogos(FanWheel):
    """Fan wheel variant that omits logos and renders index distinctly."""

    def _add_merchant_logo(self, ax, merchant: str, x: float, y: float) -> bool:  # type: ignore[override]
        # Intentionally do nothing and report success so no placeholders are drawn
        return True

    def _add_segment_content(self, ax, wheel_data: pd.DataFrame, angle_step: float):  # type: ignore[override]
        """Render interior index (e.g., 1.49X) and outer community label."""
        from textwrap import wrap

        # Draw an inner ring for index contrast
        colors = self.team_config.get("colors", {})
        ring_color = colors.get("index_ring", "#0E2A5E")
        # Span ring from the inner circle to just below the logo radius
        ring_inner = self.inner_radius  # touch the center badge
        ring_outer = self.logo_radius + 0.2  # extend outward a bit for comfortable height

        index_ring = Wedge(
            (0, 0),
            r=ring_outer,
            theta1=0,
            theta2=360,
            width=ring_outer - ring_inner,
            facecolor=ring_color,
            edgecolor="none",
            zorder=3,
        )
        ax.add_patch(index_ring)

        for i, (_, row) in enumerate(wheel_data.iterrows()):
            center_angle = i * angle_step + angle_step / 2 - 90
            angle_rad = np.deg2rad(center_angle)

            # Community label near outer ring
            community_radius = self.outer_radius - 0.9
            cx = community_radius * np.cos(angle_rad)
            cy = community_radius * np.sin(angle_rad)

            community_text = row["COMMUNITY"]
            # Force a tidy 3-line layout for this long label
            if "Fans of Women" in community_text:
                wrapped = "Fans of\nWomen’s\nSports"
            else:
                wrapped = "\n".join(
                    wrap(community_text, width=14, break_long_words=False)
                )

            ax.text(
                cx,
                cy,
                wrapped,
                ha="center",
                va="center",
                fontsize=20,
                fontweight="bold",
                fontfamily=self.font_family,
                color="white",
                linespacing=0.95,
                zorder=8,
            )

            # Index number farther inside (toward center), above the community text
            index_radius = (ring_inner + ring_outer) / 2.0  # center of the ring
            ix = index_radius * np.cos(angle_rad)
            iy = index_radius * np.sin(angle_rad)

            # Convert index (where 100 = baseline) to signed percentage vs baseline
            # Example: 160 -> +60%, 370 -> +270%
            index_ratio = float(row["PERC_INDEX"]) / 100.0
            percent_delta = (index_ratio - 1.0) * 100.0
            # Round to the nearest 1% per request
            idx_text = f"{percent_delta:+.0f}%"

            ax.text(
                ix,
                iy,
                idx_text,
                ha="center",
                va="center",
                fontsize=30,
                fontweight="bold",
                fontfamily=self.font_family,
                color="black",
                zorder=12,
            )


def _get_team_config() -> Dict[str, object]:
    """Return NBA branding using the requested palette."""
    return {
        "team_name": "NBA",
        "team_name_short": "NBA",
        "colors": {
            # Requested palette: inner band = yellow/green, outer ring = blue
            "primary": "#DBF66F",
            "secondary": "#0A08D9",
            "accent": "#0A08D9",
            # Inner band behind index numbers
            "index_ring": "#DBF66F",
        },
    }


def _source_data() -> List[Dict[str, object]]:
    """Structured input data for the wheel.

    Fields:
      - RANK: display order (low to high clockwise)
      - COMMUNITY: audience community name
      - INDEX: index vs. gen pop (int)
      - INSIGHT: optional descriptive text (not rendered on wheel)
    """
    return [
        {
            "RANK": 1,
            "COMMUNITY": "Fans of Women’s Sports",
            "INDEX": 374,
            "INSIGHT": "Deep engagement with equality-driven and purpose-led fandoms; crossover with WNBA and NWSL audiences.",
        },
        {
            "RANK": 2,
            "COMMUNITY": "Pickleball Fans",
            "INDEX": 259,
            "INSIGHT": "Fitness-oriented and experience-seeking consumers; active spenders in recreational categories.",
        },
        {
            "RANK": 3,
            "COMMUNITY": "Emerging Sports Fans",
            "INDEX": 216,
            "INSIGHT": "Curious, multi-league followers discovering sports through digital and streaming platforms.",
        },
        {
            "RANK": 4,
            "COMMUNITY": "Sports Merchandise Shoppers",
            "INDEX": 201,
            "INSIGHT": "High spenders on licensed apparel and memorabilia; key segment for retail activations.",
        },
        {
            "RANK": 5,
            "COMMUNITY": "Gamers & Esports Enthusiasts",
            "INDEX": 188,
            "INSIGHT": "Strong digital overlap with Twitch, Discord, and mobile gaming ecosystems.",
        },
        {
            "RANK": 6,
            "COMMUNITY": "Streaming Superfans",
            "INDEX": 174,
            "INSIGHT": "Heavy users of OTT and DTC sports subscriptions; twice as likely to use multiple streaming platforms.",
        },
        {
            "RANK": 7,
            "COMMUNITY": "Sports Bettors",
            "INDEX": 162,
            "INSIGHT": "High real-time engagement; strong opportunity for moment-based activations.",
        },
        {
            "RANK": 8,
            "COMMUNITY": "Lifestyle Spenders",
            "INDEX": 158,
            "INSIGHT": "Over-index in athleisure, dining, and travel; fandom blends seamlessly with lifestyle expression.",
        },
        {
            "RANK": 9,
            "COMMUNITY": "Music & Culture Seekers",
            "INDEX": 149,
            "INSIGHT": "Use basketball as a cultural gateway; over-index in live events and festival spending.",
        },
        {
            "RANK": 10,
            "COMMUNITY": "Community & Cause-Driven Fans",
            "INDEX": 145,
            "INSIGHT": "Purpose-oriented; spend with sustainability and social-impact brands.",
        },
    ]


def _build_fan_wheel_dataframe(rows: List[Dict[str, object]]) -> pd.DataFrame:
    """Convert the source rows into the schema expected by `FanWheel.create`.

    The fan wheel expects columns: COMMUNITY, MERCHANT, behavior, PERC_INDEX.
    We render each wedge label as "<Community>\n<Index>" and omit logos.
    """
    df = pd.DataFrame(rows)
    df = df.sort_values("RANK", ascending=True).reset_index(drop=True)

    # Build required columns
    df_out = pd.DataFrame(
        {
            "COMMUNITY": df["COMMUNITY"],
            # Merchant is unused; keep minimal placeholder to satisfy API
            "MERCHANT": ["" for _ in range(len(df))],
            # Behavior text will be the community label; index is rendered separately
            "behavior": df["COMMUNITY"],
            "PERC_INDEX": df["INDEX"],
        }
    )
    return df_out


def generate_wheel(output: Path | None = None) -> Path:
    """Create and save the NBA communities fan wheel image."""
    team_config = _get_team_config()
    data = _build_fan_wheel_dataframe(_source_data())

    if output is None:
        output = Path("output/nba_communities_fan_wheel.png")
    output.parent.mkdir(parents=True, exist_ok=True)

    wheel = FanWheelNoLogos(team_config, enable_logos=False)
    return wheel.create(data, output_path=output)


def main() -> None:
    path = generate_wheel()
    print(f"NBA communities fan wheel saved to: {path}")


if __name__ == "__main__":
    main()


