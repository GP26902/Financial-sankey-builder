"""Plotly figure construction for the Sankey (no Streamlit imports)."""

from __future__ import annotations

import hashlib

import plotly.graph_objects as go

from modules.flows import format_value, list_nodes, node_balance

PALETTE = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
    "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
]


def node_colour(name: str) -> str:
    """Colour chosen from the node's name, so it never changes when other
    flows are added or deleted."""
    digest = hashlib.md5(name.casefold().encode("utf-8")).digest()
    return PALETTE[digest[0] % len(PALETTE)]


def hex_to_rgba(hex_str: str, alpha: float = 0.4) -> str:
    h = hex_str.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6:
        raise ValueError(f"Expected a 3- or 6-digit hex colour, got '{hex_str}'")
    r, g, b = (int(h[i : i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r}, {g}, {b}, {alpha})"


def node_label(row: dict, unit: str) -> str:
    """Label text for a node.

    Balanced / source / sink nodes show one number. A node whose inflow and
    outflow differ shows both, so the gap is visible on the chart.
    """
    name = row["Node"]
    if row["Status"] in ("Unallocated", "Over-allocated"):
        return (
            f"{name} (in {format_value(row['Inflow'], unit)} / "
            f"out {format_value(row['Outflow'], unit)})"
        )
    total = row["Outflow"] if row["Status"] == "Source" else row["Inflow"]
    return f"{name} ({format_value(total, unit)})"


def build_sankey(flows, unit: str = "", title: str = "Flow breakdown") -> go.Figure:
    """Build the Sankey figure. Assumes flows already passed validate_flows."""
    nodes = list_nodes(flows)
    index = {n: i for i, n in enumerate(nodes)}
    rows = {r["Node"]: r for r in node_balance(flows)}

    colours = [node_colour(n) for n in nodes]
    link_colours = [hex_to_rgba(colours[index[f["Source"]]], 0.45) for f in flows]

    fig = go.Figure(
        go.Sankey(
            node=dict(
                pad=20,
                thickness=25,
                line=dict(color="rgba(0,0,0,0.3)", width=0.5),
                label=[node_label(rows[n], unit) for n in nodes],
                color=colours,
            ),
            link=dict(
                source=[index[f["Source"]] for f in flows],
                target=[index[f["Target"]] for f in flows],
                value=[float(f["Value"]) for f in flows],
                color=link_colours,
                customdata=[format_value(float(f["Value"]), unit) for f in flows],
                hovertemplate=(
                    "%{source.label} → %{target.label}<br>%{customdata}"
                    "<extra></extra>"
                ),
            ),
        )
    )
    fig.update_layout(
        title_text=title,
        font_size=12,
        height=600,
        margin=dict(l=20, r=20, t=40, b=20),
    )
    return fig
