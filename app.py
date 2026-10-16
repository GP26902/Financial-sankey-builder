"""Flow Sankey Builder - Streamlit UI.

All calculation, validation and chart logic lives in modules/ so it can be
tested without Streamlit. This file only handles layout and user input.
"""

import pandas as pd
import streamlit as st

from modules.chart import build_sankey
from modules.export import export_filename
from modules.kpis import compute_kpis
from modules.flows import (
    UNIT_CHOICES,
    FlowError,
    add_flow,
    amount_text,
    clean_name,
    evaluate_amount,
    escape_markdown_dollars,
    format_value,
    list_nodes,
    node_balance,
    parse_flows_csv,
    resolve_unit,
    rows_to_flows,
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
FLOW_COLUMNS = ["Source", "Target", "Value"]


def _flows_df(flows):
    return pd.DataFrame(
        {
            "Source": pd.Series([f["Source"] for f in flows], dtype="object"),
            "Target": pd.Series([f["Target"] for f in flows], dtype="object"),
            "Value": pd.Series([float(f["Value"]) for f in flows], dtype="float64"),
        }
    )


def _set_flows(flows):
    """Replace the flows and restart the table editor from them."""
    st.session_state.flows = flows
    st.session_state.table_base = _flows_df(flows)
    st.session_state.table_version = st.session_state.get("table_version", 0) + 1


def _apply_preset(name):
    p = get_preset(name)
    _set_flows(p["flows"])
    st.session_state.suggestions = p["suggestions"]
    st.session_state.unit_choice = p["unit"]
    st.session_state.chart_title = p["title"]
    st.session_state.loaded_preset = name
    for key in ("src_select", "tgt_select"):
        st.session_state[key] = None
    for key in ("custom_src", "custom_tgt", "custom_unit"):
        st.session_state[key] = ""


if "flows" not in st.session_state:
    _apply_preset(DEFAULT_PRESET)
if "table_base" not in st.session_state:
    st.session_state.table_base = _flows_df(st.session_state.flows)


def _flash(kind, message):
    st.session_state.flash = (kind, message)


def on_load_preset():
    _apply_preset(st.session_state.preset_choice)
    _flash("success", f"Loaded: {st.session_state.preset_choice}")


def on_amount_enter():
    """Enter in the Amount box turns 800+400 into 1200 (an unreadable entry is reported)."""
    text = st.session_state.get("flow_amount", "")
    if not str(text).strip():
        return
    try:
        st.session_state.flow_amount = amount_text(evaluate_amount(text))
    except FlowError as exc:
        _flash("error", str(exc))


def on_add_flow():
    source = st.session_state.custom_src.strip() or st.session_state.src_select
    target = st.session_state.custom_tgt.strip() or st.session_state.tgt_select
    try:
        new_flows = add_flow(
            st.session_state.flows, source, target, st.session_state.get("flow_amount", "")
        )
    except FlowError as exc:
        _flash("error", str(exc))
        return
    _set_flows(new_flows)
    added = new_flows[-1]
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
    st.session_state.flow_amount = ""


def on_upload_csv(key):
    """Replace the flows with an uploaded CSV, or reject it and keep the old ones."""
    uploaded = st.session_state.get(key)
    if uploaded is None:
        return
    st.session_state.upload_version = st.session_state.get("upload_version", 0) + 1
    flows, errors, skipped = parse_flows_csv(uploaded.getvalue())
    if errors:
        _flash("error", f"Could not load {uploaded.name}. Nothing was changed.\n\n"
                        + "\n\n".join(errors))
        return
    _set_flows(flows)
    st.session_state.loaded_preset = None
    message = (
        f"Loaded {len(flows)} flows from {uploaded.name}, replacing the previous "
        "flows. The unit and chart title were not changed: check them in Settings."
    )
    if skipped:
        message += f"\n\n{skipped} row(s) with a missing cell were left out."
    _flash("success", message)


def on_reset():
    _set_flows([])
    st.session_state.loaded_preset = None


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

loaded = st.session_state.get("loaded_preset")
if loaded and PRESETS[loaded]["description"]:
    st.info(
        f"**Template: {loaded}**  \n"
        f"{escape_markdown_dollars(PRESETS[loaded]['description'])}"
    )

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
    st.text_input(
        label, key="flow_amount", placeholder="e.g. 1200 or 800+400",
        help="Type a number or simple math (+ - * / and parentheses), "
             "then press Enter to see the result.",
        on_change=on_amount_enter,
    )
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
st.markdown("---")
st.subheader("2. Manage & Export Flows")
st.caption(
    "Double-click any cell to edit it. To delete a flow, tick the checkbox at the "
    "left of its row, then click the 🗑️ icon in the table toolbar. The ➕ icon adds "
    "a row; fill in all three columns and it joins the diagram. Every edit is "
    "checked: an invalid one is rejected and the table resets."
)

table_key = f"flow_table_{st.session_state.get('table_version', 0)}"
edited = st.data_editor(
    st.session_state.table_base,
    key=table_key,
    num_rows="dynamic",
    hide_index=True,
    width="stretch",
    column_config={
        "Source": st.column_config.TextColumn("Source (From)", required=True),
        "Target": st.column_config.TextColumn("Target (To)", required=True),
        "Value": st.column_config.NumberColumn(
            f"Amount ({unit})" if unit else "Amount",
            min_value=0.0, format="%.2f", required=True,
        ),
    },
)

incomplete = 0
if not edited.equals(st.session_state.table_base):
    new_flows, errors, incomplete, renamed = rows_to_flows(edited.to_dict("records"))
    if errors:
        _flash("error", "Edit rejected.\n\n" + "\n\n".join(errors))
        _set_flows(st.session_state.flows)      # snap the table back
        st.rerun()
    changed = new_flows != st.session_state.flows
    if renamed:
        _set_flows(new_flows)                   # restart the table to show tidied names
    elif changed:
        st.session_state.flows = new_flows
    if renamed or changed:
        st.rerun()

flows = st.session_state.flows
if incomplete:
    st.caption(
        f"{incomplete} incomplete row(s) are not in the diagram yet. "
        "Fill in Source, Target and Amount to add them."
    )

a1, a2 = st.columns(2)
with a1:
    st.button("Reset All Flows", on_click=on_reset, width="stretch")
with a2:
    st.download_button(
        "📥 Download Data as CSV",
        data=pd.DataFrame(flows, columns=FLOW_COLUMNS).to_csv(index=False).encode("utf-8"),
        file_name="flows.csv",
        mime="text/csv",
        disabled=not flows,
        width="stretch",
    )

upload_key = f"csv_upload_{st.session_state.get('upload_version', 0)}"
with st.expander("📤 Upload a CSV (replaces the current flows)"):
    st.caption(
        "Use a file from the download button above: columns Source, Target, Value. "
        "Upload it, then add new rows in the table or in section 1. The CSV does not "
        "store the unit or chart title, so check them in Settings."
    )
    st.file_uploader(
        "CSV file", type=["csv"], key=upload_key,
        on_change=on_upload_csv, args=(upload_key,),
    )

if not flows:
    st.info("No flows yet. Add one above, use ➕ in the table, or load a sample in Settings.")
    st.stop()

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
kpi_specs = PRESETS[loaded]["kpis"] if loaded and "kpis" in PRESETS[loaded] else []
kpis = compute_kpis(flows, kpi_specs)
metrics = [
    ("Entering the system (from sources)", format_value(totals["entering"], unit), ""),
    ("Leaving the system (to sinks)", format_value(totals["leaving"], unit), ""),
]
metrics += [(k["label"], k["text"], k["help"]) for k in kpis]
# Entering equals leaving whenever every node balances, so the difference is
# only worth a tile when there is a gap or when no KPIs replace it.
if totals["difference"] != 0 or not kpis:
    metrics.append(("Unaccounted difference", format_value(totals["difference"], unit), ""))
for col, (label, value, help_text) in zip(st.columns(len(metrics)), metrics):
    col.metric(label, value, help=help_text or None)

gaps = unbalanced_nodes(flows)
if gaps:
    # Escape $ so two amounts in one line are not rendered as math formatting.
    lines = [
        escape_markdown_dollars(
            f"- **{g['Node']}**: in {format_value(g['Inflow'], unit)}, "
            f"out {format_value(g['Outflow'], unit)} "
            f"({g['Status'].lower()} by {format_value(abs(g['Difference (in − out)']), unit)})"
        )
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
