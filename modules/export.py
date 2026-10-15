"""Chart export helpers (no Streamlit imports).

PNG/SVG export needs the `kaleido` rendering engine. If it is missing or
cannot start (for example on a host without the libraries it needs), every
function raises ExportError so the UI can fall back gracefully.
"""

from __future__ import annotations

import hashlib
import json
import re

EXPORT_WIDTH = 1400
EXPORT_HEIGHT = 700
EXPORT_SCALE = 2          # PNG is 2800 x 1400 pixels


class ExportError(RuntimeError):
    """Image export is unavailable or failed."""


def export_filename(title: str, ext: str) -> str:
    """'Monthly Budget Flow (illustrative)' -> 'monthly-budget-flow-illustrative.png'"""
    slug = re.sub(r"[^a-z0-9]+", "-", (title or "").lower()).strip("-")
    return f"{slug or 'flow-diagram'}.{ext.lstrip('.')}"


def figure_signature(flows, unit: str, title: str) -> str:
    """Short hash that changes whenever the diagram would change."""
    payload = json.dumps(
        {"flows": flows, "unit": unit, "title": title}, sort_keys=True, default=str
    )
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]


def _for_export(fig):
    """Copy of the figure with a white background and dark text, so the file
    looks the same whether the app is in light or dark mode."""
    out = type(fig)(fig)
    out.update_layout(
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(color="#222222", size=14),
        width=EXPORT_WIDTH,
        height=EXPORT_HEIGHT,
        margin=dict(l=30, r=30, t=80, b=30),
    )
    return out


def figure_to_image(fig, fmt: str = "png") -> bytes:
    """Render the figure to PNG or SVG bytes."""
    if fmt not in ("png", "svg"):
        raise ExportError(f"Unsupported image format: {fmt}")
    try:
        scale = EXPORT_SCALE if fmt == "png" else 1
        return _for_export(fig).to_image(format=fmt, scale=scale)
    except Exception as exc:  # kaleido raises several different error types
        raise ExportError(f"{type(exc).__name__}: {exc}") from exc


def figure_to_html(fig) -> bytes:
    """Standalone interactive HTML. Loads Plotly from a CDN, so the file is
    small but needs an internet connection to open."""
    return _for_export(fig).to_html(include_plotlyjs="cdn", full_html=True).encode("utf-8")
