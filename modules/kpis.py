"""Template KPIs (yield, recovery rate, ...) computed from the current flows.

Pure functions, no Streamlit. A KPI spec is a dict:
    {"label": "Overall yield",
     "numerator": "Finished goods shipped",     # node whose inflow is counted
     "denominator": "ENTERING",                  # node name, or "ENTERING" for
                                                 # the total entering the system
     "help": "tooltip text"}
Because KPIs are recalculated from the table, they update when the user edits
a flow. If a node named in a spec no longer exists (renamed or deleted) or the
denominator is zero, that KPI is simply skipped.
"""

from __future__ import annotations

from .flows import node_balance, system_totals

ENTERING = "ENTERING"


def compute_kpis(flows, specs) -> list[dict]:
    """Return [{"label", "value" (0-1 fraction), "text" ('81.0%'), "help"}]."""
    if not flows or not specs:
        return []
    inflow = {r["Node"]: r["Inflow"] for r in node_balance(flows)}
    entering = system_totals(flows)["entering"]
    out = []
    for spec in specs:
        num_node, den_node = spec["numerator"], spec["denominator"]
        if num_node not in inflow:
            continue
        if den_node == ENTERING:
            den = entering
        elif den_node in inflow:
            den = inflow[den_node]
        else:
            continue
        if den <= 0:
            continue
        value = inflow[num_node] / den
        out.append(
            {
                "label": spec["label"],
                "value": value,
                "text": f"{value * 100:.1f}%",
                "help": spec.get("help", ""),
            }
        )
    return out
