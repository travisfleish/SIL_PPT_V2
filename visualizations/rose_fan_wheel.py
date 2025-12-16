"""
visualizations/rose_fan_wheel.py

Rose-diagram (polar bar) "fan wheel" visualization for category -> merchant picks.

Design guidance is intentionally borrowed from `visualizations/fan_wheel.py`:
- Category labels sit *inside* the wedges
- Directional arrows appear between segments (prefer arrow logo if present)
- Merchant logos are loaded via `utils/logo_manager.py` (with fallbacks)
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from matplotlib.patches import Circle, Wedge
from PIL import Image
from textwrap import wrap

from utils.font_manager import font_manager
from utils.logo_manager import LogoManager


@dataclass
class RoseFanWheelStyle:
    # Use transparent background by default (savefig uses transparent=True)
    background: str = "none"
    # Requested palette
    segment_fill: str = "#0010dc"        # main wheel
    bar_fill: str = "#0c1226"            # inner/bars
    divider: str = "#ffffff"
    text: str = "#ffffff"
    marker_fill: str = "#ffffff"
    marker_text: str = "#1b1f27"
    inner_ring_fill: str = "#ff6a00"
    arrow_circle_fill: str = "#ffffff"


class RoseFanWheel:
    def __init__(
        self,
        style: Optional[RoseFanWheelStyle] = None,
        *,
        enable_logos: bool = True,
        logo_dir: Optional[Path] = None,
        logo_size: Tuple[int, int] = (120, 120),
        center_image_path: Optional[Path] = None,
    ):
        self.style = style or RoseFanWheelStyle()
        self.font_family = font_manager.get_font_family("Red Hat Display")
        self.enable_logos = enable_logos
        self.logo_size = logo_size
        self.logo_manager = LogoManager(logo_dir) if enable_logos else None
        self.arrow_logo = self._load_arrow_logo()
        self.center_image_path = Path(center_image_path) if center_image_path else None
        # Geometry aligned to `visualizations/fan_wheel.py`
        self.outer_radius = 5.0
        self.logo_radius = 2.8
        self.inner_radius = 1.6

    @staticmethod
    def _short_merchant_label(merchant: str, max_len: int = 14) -> str:
        m = (merchant or "").strip()
        if not m:
            return ""
        # Prefer first word unless it's too short.
        first = m.split()[0]
        label = first if len(first) >= 4 else m
        label = label.replace("&", "and")
        return (label[: max_len - 1] + "…") if len(label) > max_len else label

    @staticmethod
    def _load_arrow_logo() -> Optional[Image.Image]:
        """Load arrow logo if it exists (same search strategy as FanWheel)."""
        current_file = Path(__file__).resolve()
        project_root = current_file.parent.parent

        arrow_paths = [
            project_root / "assets" / "logos" / "general" / "arrow.png",
            Path.cwd() / "assets" / "logos" / "general" / "arrow.png",
        ]
        for p in arrow_paths:
            if p.exists():
                try:
                    img = Image.open(p)
                    if img.mode != "RGBA":
                        img = img.convert("RGBA")
                    return img
                except Exception:
                    continue
        return None

    def _get_logo_image(self, merchant: str) -> Image.Image:
        """Return merchant logo or a fallback circular logo."""
        if self.logo_manager:
            img = self.logo_manager.get_logo(merchant, self.logo_size)
            if img is not None:
                return img
            return self.logo_manager.create_fallback_logo(
                merchant, self.logo_size, bg_color="white", text_color="#888888"
            )

        # Logos disabled: return a fallback rendered via LogoManager rules, but with a local temporary manager.
        temp = LogoManager(Path(__file__).resolve().parent.parent / "assets" / "logos" / "merchants")
        return temp.create_fallback_logo(merchant, self.logo_size, bg_color="white", text_color="#888888")

    @staticmethod
    def _crop_to_circle_rgba(img: Image.Image, size_px: int = 1024) -> Image.Image:
        """Center-crop square, resize, and apply circular alpha mask."""
        img = img.convert("RGBA")
        w, h = img.size
        side = min(w, h)
        left = (w - side) // 2
        top = (h - side) // 2
        img = img.crop((left, top, left + side, top + side))
        if size_px:
            img = img.resize((size_px, size_px), Image.Resampling.LANCZOS)

        # circular alpha
        mask = Image.new("L", (img.size[0], img.size[1]), 0)
        from PIL import ImageDraw

        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, img.size[0], img.size[1]), fill=255)
        img.putalpha(mask)
        return img

    def create(
        self,
        wheel_df: pd.DataFrame,
        output_path: Path,
        *,
        bar_value_col: str = "MERCHANT_PERC_INDEX",
    ) -> Path:
        """
        Render a rose-diagram fan wheel.

        Expected columns:
        - CATEGORY
        - MERCHANT
        - bar_value_col (default MERCHANT_PERC_INDEX) numeric (optional, used for bar heights)
        """
        df = wheel_df.copy()
        for col in ["CATEGORY", "MERCHANT"]:
            if col not in df.columns:
                raise ValueError(f"wheel_df missing required column: {col}")

        df["CATEGORY"] = df["CATEGORY"].astype(str)
        df["MERCHANT"] = df["MERCHANT"].astype(str)

        n = len(df)
        if n == 0:
            raise ValueError("wheel_df is empty")

        angle_step = 360.0 / n

        # Bar values (normalize -> heights)
        if bar_value_col in df.columns:
            values = pd.to_numeric(df[bar_value_col], errors="coerce").to_numpy()
        else:
            values = np.full(n, np.nan)

        finite = np.isfinite(values)
        if finite.any():
            vmin = float(np.nanmin(values))
            vmax = float(np.nanmax(values))
            if vmax == vmin:
                norm = np.full(n, 0.6, dtype=float)
            else:
                norm = (values - vmin) / (vmax - vmin)
                norm = np.clip(norm, 0, 1)
        else:
            norm = np.full(n, 0.6, dtype=float)

        # If some rows have missing metric values, keep them renderable.
        norm = np.where(np.isfinite(norm), norm, 0.6)

        # Map normalized values to a "bar" radial thickness drawn as a Wedge width.
        # Keep within the outer wheel boundary.
        bar_min = 0.55
        bar_max = 1.55
        bar_widths = bar_min + norm * (bar_max - bar_min)

        # Figure / axis (cartesian) so dividing lines + arrows can be identical to `fan_wheel.py`
        fig = plt.figure(figsize=(12, 12), facecolor="none", dpi=160)
        ax = fig.add_subplot(111, aspect="equal")
        ax.set_facecolor("none")
        margin = 0.3
        limit = self.outer_radius + margin
        ax.set_xlim(-limit, limit)
        ax.set_ylim(-limit, limit)
        ax.axis("off")

        # Draw segments (full background wedge + bar overlay)
        # Bars should emanate from the edge of the inner circle
        bar_base = self.inner_radius

        for i in range(n):
            start_angle = i * angle_step - 90
            end_angle = (i + 1) * angle_step - 90

            # Base segment
            base_wedge = Wedge(
                (0, 0),
                self.outer_radius,
                start_angle,
                end_angle,
                width=self.outer_radius,
                facecolor=self.style.segment_fill,
                edgecolor="none",
                zorder=1,
            )
            ax.add_patch(base_wedge)

            # Bar overlay (rose bar)
            bar_outer = min(self.outer_radius, bar_base + float(bar_widths[i]))
            bar = Wedge(
                (0, 0),
                bar_outer,
                start_angle,
                end_angle,
                width=bar_outer - bar_base,
                facecolor=self.style.bar_fill,
                edgecolor="none",
                zorder=3,
                alpha=1.0,
            )
            ax.add_patch(bar)

        # Dividing lines EXACTLY like `fan_wheel.py` (between wedges at boundaries)
        for i in range(n):
            angle = i * angle_step - 90
            angle_rad = np.deg2rad(angle)
            x_inner = self.inner_radius * np.cos(angle_rad)
            y_inner = self.inner_radius * np.sin(angle_rad)
            x_outer = self.outer_radius * np.cos(angle_rad)
            y_outer = self.outer_radius * np.sin(angle_rad)
            ax.plot([x_inner, x_outer], [y_inner, y_outer], color="white", linewidth=8, zorder=15)

        # Arrows EXACTLY like `fan_wheel.py`
        if self.arrow_logo is None:
            # Fallback: no arrow logo; skip (existing fan wheel falls back to programmatic arrows,
            # but in this rose version we prefer the logo for design parity)
            pass
        else:
            arrow_size_pixels = 50
            for i in range(n):
                arrow_angle_deg = i * angle_step - 90
                arrow_angle = np.deg2rad(arrow_angle_deg)

                # Arrow position (same radius as fan wheel)
                arrow_r = 4.0
                arrow_x = arrow_r * np.cos(arrow_angle)
                arrow_y = arrow_r * np.sin(arrow_angle)

                # White circle background
                circle_bg = Circle((arrow_x, arrow_y), 0.3, facecolor="white", edgecolor="none", zorder=16)
                ax.add_patch(circle_bg)

                arrow_copy = self.arrow_logo.copy()
                arrow_copy.thumbnail((arrow_size_pixels, arrow_size_pixels), Image.Resampling.LANCZOS)
                arrow_copy = arrow_copy.transpose(Image.FLIP_LEFT_RIGHT)
                rotation_angle = 90 + arrow_angle_deg + 30
                arrow_rotated = arrow_copy.rotate(rotation_angle, expand=True, fillcolor=(0, 0, 0, 0))
                arrow_array = np.array(arrow_rotated)
                imagebox = OffsetImage(arrow_array, zoom=0.4)
                ab = AnnotationBbox(imagebox, (arrow_x, arrow_y), frameon=False, pad=0, zorder=17)
                ax.add_artist(ab)

        # Center circle (dark)
        center_circle = Circle(
            (0, 0),
            self.inner_radius,
            facecolor="#0b0e13",
            edgecolor="white",
            linewidth=2.0,
            zorder=20,
        )
        ax.add_patch(center_circle)

        # Optional: center photo clipped to the inner circle
        if self.center_image_path and self.center_image_path.exists():
            try:
                img = Image.open(self.center_image_path)
                img = self._crop_to_circle_rgba(img, size_px=1024)
                arr = np.array(img)
                im = ax.imshow(
                    arr,
                    extent=[-self.inner_radius, self.inner_radius, -self.inner_radius, self.inner_radius],
                    zorder=21,
                )
                im.set_clip_path(center_circle)
            except Exception:
                # If anything goes wrong, we keep the solid center circle.
                pass

        # Merchant logos (same placement logic as fan wheel)
        for i, (_, row) in enumerate(df.iterrows()):
            center_angle = i * angle_step + angle_step / 2 - 90
            angle_rad = np.deg2rad(center_angle)
            # Move logos slightly outward
            # Keep logos outside the max bar radius (inner_radius + bar_max ~= 3.15)
            # Default: slightly closer in than before, but still clear of the bars.
            # Special-case Streaming to keep extra separation from the tallest bar in that segment.
            category = str(row.get("CATEGORY", ""))
            logo_r = 3.60
            if category.strip().lower() == "streaming":
                logo_r = 3.80
            logo_x = logo_r * np.cos(angle_rad)
            logo_y = logo_r * np.sin(angle_rad)

            merchant = str(row["MERCHANT"])
            logo_img = self._get_logo_image(merchant)
            logo_array = np.array(logo_img)
            # Slightly smaller logo
            imagebox = OffsetImage(logo_array, zoom=0.58)
            ab = AnnotationBbox(imagebox, (logo_x, logo_y), frameon=False, pad=0, zorder=15)
            ax.add_artist(ab)

        # Category labels INSIDE wedges (same wrapping strategy as fan wheel)
        for i, (_, row) in enumerate(df.iterrows()):
            category = str(row["CATEGORY"])
            center_angle = i * angle_step + angle_step / 2 - 90
            angle_rad = np.deg2rad(center_angle)
            # Move text outward toward the edge (but still inside wedge)
            # Keep labels near the rim so they don't collide with the merchant logo band.
            # Slightly closer in than before to better balance with logo placement.
            text_radius = self.outer_radius - 0.45
            text_x = text_radius * np.cos(angle_rad)
            text_y = text_radius * np.sin(angle_rad)

            word_count = len(category.split())
            if word_count >= 4 or len(category) > 20:
                wrapped_text = "\n".join(wrap(category, width=10, break_long_words=False))
            elif word_count == 3 or len(category) > 12:
                wrapped_text = "\n".join(wrap(category, width=11, break_long_words=False))
            else:
                wrapped_text = category

            lines = wrapped_text.split("\n")
            if len(lines) == 2 and len(category) > 18:
                wrapped_text = "\n".join(wrap(category, width=9, break_long_words=False))

            # Orient text around the wheel (tangential), like the reference image.
            # Tangent direction is +90 degrees from radial.
            rotation = center_angle + 90
            # Keep text upright
            if 90 < (rotation % 360) < 270:
                rotation += 180
            # Requested: flip specific categories to face the opposite direction
            if category.strip().lower() in {"business services", "home goods"}:
                rotation += 180

            ax.text(
                text_x,
                text_y,
                wrapped_text,
                ha="center",
                va="center",
                fontsize=20,
                fontweight="bold",
                fontfamily=self.font_family,
                color="white",
                rotation=rotation,
                rotation_mode="anchor",
                linespacing=0.9,
                zorder=7,
            )

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.tight_layout()
        plt.savefig(
            output_path,
            bbox_inches="tight",
            facecolor="none",
            edgecolor="none",
            pad_inches=0.05,
            transparent=True,
        )
        plt.close(fig)
        return output_path


