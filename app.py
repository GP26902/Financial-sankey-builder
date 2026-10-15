"""Flow Sankey Builder - Streamlit UI.

All calculation, validation and chart logic lives in modules/ so it can be
tested without Streamlit. This file only handles layout and user input.
"""

import pandas as pd
import streamlit as st

from modules.chart import build_sankey
from modules.export import export_filename
from modules.flows import (
    UNIT_CHOICES,
    FlowError,
    add_flow,
    clean_name,
    delete_flows,
    format_value,
    list_nodes,
    node_balance,
    resolve_unit,
    system_totals,
    unbalanced_nodes,
    validate_flows,
)
from modules.presets import DEFAULT_PRESET, PRESETS, get_preset

st.set_page_config(page_title="Flow Sankey Builder", layout="wide")


# ---------------------------------------------------------------------------
# State and callbacks (callbacks run before the script reruns, so they may
# safely change widget values)
# ---------------------------------------------------------------------------
def _apply_preset(name):
    p = get_preset(name)
    st.session_state.flows = p["flows"]
    st.session_state.suggestions = p["suggestions"]
    st.session_state.unit_choice = p["unit"]
    st.session_state.chart_title = p["title"]
    for key in ("src_select", "tgt_select"):
        st.session_state[key] = None
    for key in ("custom_src", "custom_tgt", "custom_unit"):
        st.session_state[key] = ""
    st.session_state.delete_rows = []


if "flows" not in st.session_state:
    _apply_preset(DEFAULT_PRESET)


def _flash(kind, message):
    st.session_state.flash = (kind, message)


def on_load_preset():
    _apply_preset(st.session_state.preset_choice)
    _flash("success", f"Loaded: {st.session_state.preset_choice}")


def on_add_flow():
    source = st.session_state.custom_src.strip() or st.session_state.src_select
    target = st.session_state.custom_tgt.strip() or st.session_state.tgt_select
    try:
        st.session_state.flows = add_flow(
            st.session_state.flows, source, target, st.session_state.flow_amount
        )
    except FlowError as exc:
        _flash("error", str(exc))
        return
    added = st.session_state.flows[-1]
    unit = resolve_unit(st.session_state.unit_choice, st.session_state.get("custom_unit", ""))
    _flash(
        "success",
        f"Added: {added['Source']} → {added['Target']} "
        f"({format_value(added['Value'], unit)})",
    )
    for key in ("src_select", "tgt_select"):
        st.session_state[key] = None
    st.session_state.custom_src = ""
    st.session_state.custom_tgt = ""


def on_delete():
    rows = st.session_state.delete_rows
    if not rows:
        _flash("warning", "Select at least one flow to delete.")
        return
    st.session_state.flows = delete_flows(st.session_state.flows, rows)
    st.session_state.delete_rows = []
    _flash("success", f"Deleted {len(rows)} flow(s).")


def on_reset():
    st.session_state.flows = []
    st.session_state.delete_rows = []


# ---------------------------------------------------------------------------
# Header and settings
# ---------------------------------------------------------------------------
st.title("🔀 Flow Sankey Builder")
st.markdown(
    "Build a one-way flow diagram for **cash, material, energy or any other "
    "quantity**, check that what goes in comes out, and download the data as CSV."
)

flash = st.session_state.pop("flash", None)
if flash:
    getattr(st, flash[0])(flash[1])

with st.expander("⚙️ Settings: sample data, units, chart title", expanded=False):
    s1, s2 = st.columns([3, 1])
    with s1:
        st.selectbox("Sample data set", list(PRESETS), key="preset_choice")
    with s2:
        st.write("")
        st.write("")
        st.button("Load sample", on_click=on_load_preset, width="stretch")
    u1, u2, u3 = st.columns([1, 1, 2])
    with u1:
        st.selectbox("Unit", UNIT_CHOICES, key="unit_choice")
    with u2:
        if st.session_state.unit_choice == "Custom…":
            st.text_input("Custom unit", key="custom_unit", placeholder="e.g. pallets")
    with u3:
        st.text_input("Chart title", key="chart_title")

unit = resolve_unit(st.session_state.unit_choice, st.session_state.get("custom_unit", ""))
nodes = list_nodes(st.session_state.flows)
suggested = [s for s in st.session_state.get("suggestions", []) if s not in nodes]
dropdown_options = nodes + suggested

# ---------------------------------------------------------------------------
# 1. Add a flow
# ---------------------------------------------------------------------------
st.subheader("1. Add a Flow")
col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
with col1:
    st.selectbox(
        "Source (From)", dropdown_options, index=None,
        placeholder="Choose a source", key="src_select",
    )
    st.text_input(
        "Or type a new source (overrides the dropdown)",
        placeholder="e.g. Supplier A", key="custom_src",
    )
with col2:
    st.selectbox(
        "Target (To)", dropdown_options, index=None,
        placeholder="Choose a target", key="tgt_select",
    )
    st.text_input(
        "Or type a new target (overrides the dropdown)",
        placeholder="e.g. Assembly", key="custom_tgt",
    )
with col3:
    label = f"Amount ({unit})" if unit else "Amount"
    st.number_input(label, min_value=0.0, value=500.0, step=10.0, key="flow_amount")
with col4:
    st.write("")
    st.write("")
    st.button("Add Flow", on_click=on_add_flow, width="stretch")
st.caption(
    "Flows must be one-way: a flow that would loop back (A → B → A) or a node "
    "feeding itself is rejected. Names are matched ignoring upper/lower case."
)

# ---------------------------------------------------------------------------
# 2. Manage and export
# ---------------------------------------------------------------------------
flows = st.session_state.flows
if not flows:
    st.info("No flows yet. Add one above or load a sample data set in Settings.")
    st.stop()

st.markdown("---")
st.subheader("2. Manage & Export Flows")
df = pd.DataFrame(flows)
view = df.copy()
view.insert(0, "Row", range(1, len(view) + 1))
st.dataframe(view, hide_index=True, width="stretch")

m1, m2 = st.columns([3, 1])
with m1:
    st.multiselect(
        "Select flows to remove",
        options=list(range(len(flows))),
        format_func=lambda i: (
            f"Row {i + 1}: {flows[i]['Source']} → {flows[i]['Target']} "
            f"({format_value(flows[i]['Value'], unit)})"
        ),
        key="delete_rows",
    )
with m2:
    st.write("")
    st.write("")
    st.button("Delete Selected", type="primary", on_click=on_delete)

a1, a2 = st.columns(2)
with a1:
    st.button("Reset All Flows", on_click=on_reset)
with a2:
    st.download_button(
        "📥 Download Data as CSV",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name="flows.csv",
        mime="text/csv",
        width="stretch",
    )

# ---------------------------------------------------------------------------
# 3. Balance check
# ---------------------------------------------------------------------------
st.markdown("---")
st.subheader("3. Flow Balance Check")

problems = validate_flows(flows)
if problems:
    for p in problems:
        st.error(p)
    st.stop()

totals = system_totals(flows)
b1, b2, b3 = st.columns(3)
b1.metric("Entering the system (from sources)", format_value(totals["entering"], unit))
b2.metric("Leaving the system (to sinks)", format_value(totals["leaving"], unit))
b3.metric("Unaccounted difference", format_value(totals["difference"], unit))

gaps = unbalanced_nodes(flows)
if gaps:
    lines = [
        f"- **{g['Node']}**: in {format_value(g['Inflow'], unit)}, "
        f"out {format_value(g['Outflow'], unit)} "
        f"({g['Status'].lower()} by {format_value(abs(g['Difference (in − out)']), unit)})"
        for g in gaps
    ]
    st.warning(
        "These intermediate nodes do not send out what they receive. If that is "
        "intentional (for example, cash kept or material left in stock), add a flow "
        "to a node such as 'Retained' to show it.\n\n" + "\n".join(lines)
    )
elif any(r["Status"] == "Balanced" for r in node_balance(flows)):
    st.success("Every intermediate node is balanced: inflow equals outflow.")
else:
    st.info(
        "No intermediate nodes: every node is only a source or only a sink, so "
        "there is nothing to balance. Totals above still show what enters and leaves."
    )

with st.expander("Node-by-node balance table"):
    st.dataframe(pd.DataFrame(node_balance(flows)), hide_index=True, width="stretch")

# ---------------------------------------------------------------------------
# 4. Diagram
# ---------------------------------------------------------------------------
st.markdown("---")
st.subheader("4. Flow Diagram")
title = clean_name(st.session_state.get("chart_title", "")) or "Flow breakdown"
fig = build_sankey(flows, unit=unit, title=title)
st.plotly_chart(
    fig,
    width="stretch",
    config={
        "displaylogo": False,
        "toImageButtonOptions": {
            "format": "png",
            "filename": export_filename(title, "png").rsplit(".", 1)[0],
            "width": 1400,
            "height": 700,
            "scale": 2,
        },
    },
)
