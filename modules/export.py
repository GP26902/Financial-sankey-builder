"""Small helpers for saving the chart.

The image itself is saved by the camera icon in the Plotly toolbar (set up in
app.py), so all that is needed here is a tidy file name.
"""

import re


def export_filename(title: str, ext: str) -> str:
    """'Monthly Budget Flow (illustrative)' -> 'monthly-budget-flow-illustrative.png'"""
    slug = re.sub(r"[^a-z0-9]+", "-", (title or "").lower()).strip("-")
    return f"{slug or 'flow-diagram'}.{ext.lstrip('.')}"
