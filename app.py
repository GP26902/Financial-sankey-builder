import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Financial Sankey Builder", layout="wide")

st.title("💸 Financial Flow Sankey Builder")
st.markdown(
    "Build your pipeline, view values on the chart, and download your data"
    " anytime as a CSV!"
)

# 1. Initialize default flows
if "flows" not in st.session_state:
  st.session_state.flows = [
      {"Source": "January", "Target": "Housing", "Value": 2000},
      {"Source": "January", "Target": "Groceries", "Value": 500},
      {"Source": "January", "Target": "Utilities", "Value": 300},
      {"Source": "February", "Target": "Housing", "Value": 2000},
      {"Source": "February", "Target": "Groceries", "Value": 600},
      {"Source": "February", "Target": "Utilities", "Value": 250},
  ]

# Master list of standard categories & months
master_categories = [
    "Salary",
    "Business Income",
    "Side Hustle",
    "Taxes",
    "Housing",
    "Rent",
    "Utilities",
    "Groceries",
    "Dining & Coffee",
    "Transportation",
    "Savings & Investments",
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
    "NRE Account",
    "Miscellaneous",
]

all_nodes_set = set(master_categories)
for f in st.session_state.flows:
  all_nodes_set.add(f["Source"])
  all_nodes_set.add(f["Target"])
available_categories = sorted(list(all_nodes_set))

# 2. Form Section for Adding Flows
st.subheader("1. Add or Connect a Flow")

col1, col2, col3, col4 = st.columns([2, 2, 2, 1])

with col1:
  source_option = st.selectbox(
      "Source (From)", available_categories, key="src_select"
  )
  custom_source = st.text_input(
      "Or type custom source:",
      placeholder="e.g., January",
      key="custom_src_box",
  )
  final_source = (
      custom_source.strip()
      if custom_source and custom_source.strip()
      else source_option
  )

with col2:
  target_option = st.selectbox(
      "Target (To)", available_categories, key="tgt_select"
  )
  custom_target = st.text_input(
      "Or type custom target:",
      placeholder="e.g., Groceries",
      key="custom_tgt_box",
  )
  final_target = (
      custom_target.strip()
      if custom_target and custom_target.strip()
      else target_option
  )

with col3:
  amount_input = st.number_input(
      "Amount ($)", min_value=0.0, value=500.0, step=50.0, key="flow_amount"
  )

with col4:
  st.write("")
  st.write("")
  add_button = st.button("Add Flow", use_container_width=True)

if add_button:
  if final_source and final_target:
    st.session_state.flows.append(
        {"Source": final_source, "Target": final_target, "Value": amount_input}
    )
    st.success(
        f"Added: {final_source} ➡️ {final_target} (${amount_input:,.2f})"
    )
    st.rerun()
  else:
    st.error("Please provide both a Source and a Target.")

# 3. Section to Manage, Delete, and Export Flows
if st.session_state.flows:
  st.markdown("---")
  st.subheader("2. Manage & Export Flows")

  flow_labels = [
      f"{f['Source']} ➡️️ {f['Target']} (${f['Value']:,.2f})"
      for f in st.session_state.flows
  ]

  col_m1, col_m2 = st.columns([3, 1])
  with col_m1:
    flows_to_delete = st.multiselect(
        "Select any flows/branches you want to remove:", flow_labels
    )
  with col_m2:
    st.write("")
    st.write("")
    if st.button("Delete Selected", type="primary"):
      if flows_to_delete:
        st.session_state.flows = [
            f for f, label in zip(st.session_state.flows, flow_labels)
            if label not in flows_to_delete
        ]
        st.success("Successfully deleted selected branches!")
        st.rerun()
      else:
        st.warning("Select at least one flow to delete.")

  # Action buttons row (Reset and CSV Download)
  col_act1, col_act2 = st.columns([1, 1])
  with col_act1:
    if st.button("Reset All Flows"):
      st.session_state.flows = []
      st.rerun()

  with col_act2:
    df_export = pd.DataFrame(st.session_state.flows)
    csv_data = df_export.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Download Data as CSV",
        data=csv_data,
        file_name="financial_flows.csv",
        mime="text/csv",
        use_container_width=True,
    )

  # 4. Process and Render Diagram with Values in Labels
  df = pd.DataFrame(st.session_state.flows)

  all_nodes = list(pd.unique(df[["Source", "Target"]].values.ravel()))
  node_dict = {node: i for i, node in enumerate(all_nodes)}

  node_outgoing = {}
  node_incoming = {}
  for _, row in df.iterrows():
    node_outgoing[row["Source"]] = (
        node_outgoing.get(row["Source"], 0) + row["Value"]
    )
    node_incoming[row["Target"]] = (
        node_incoming.get(row["Target"], 0) + row["Value"]
    )


  def get_node_total(node):
    if node in node_outgoing and node_outgoing[node] > 0:
      return node_outgoing[node]
    return node_incoming.get(node, 0)


  node_labels_with_values = [
      f"{node} (${get_node_total(node):,.0f})" for node in all_nodes
  ]

  source_indices = df["Source"].map(node_dict).tolist()
  target_indices = df["Target"].map(node_dict).tolist()
  values = df["Value"].astype(float).tolist()

  palette = [
      "#1f77b4",
      "#ff7f0e",
      "#2ca02c",
      "#d62728",
      "#9467bd",
      "#8c564b",
      "#e377c2",
      "#7f7f7f",
      "#bcbd22",
      "#17becf",
  ]


  def hex_to_rgba(hex_str, alpha=0.4):
    hex_str = hex_str.lstrip("#")
    lv = len(hex_str)
    rgb = tuple(
        int(hex_str[i : i + lv // 3], 16) for i in range(0, lv, lv // 3)
    )
    return f"rgba({rgb[0]}, {rgb[1]}, {rgb[2]}, {alpha})"


  node_colors = [palette[i % len(palette)] for i in range(len(all_nodes))]
  link_colors = [
      hex_to_rgba(node_colors[src_idx], alpha=0.45) for src_idx in source_indices
  ]

  fig = go.Figure(
      data=[
          go.Sankey(
              node=dict(
                  pad=20,
                  thickness=25,
                  line=dict(color="rgba(0,0,0,0.3)", width=0.5),
                  label=node_labels_with_values,
                  color=node_colors,
              ),
              link=dict(
                  source=source_indices,
                  target=target_indices,
                  value=values,
                  color=link_colors,
              ),
          )
      ]
  )

  fig.update_layout(
      title_text="Cash Flow Breakdown",
      font_size=12,
      height=600,
      margin=dict(l=20, r=20, t=40, b=20),
  )

  st.markdown("---")
  st.subheader("3. Visual Pipeline Output")
  st.plotly_chart(fig, use_container_width=True)
else:
  st.info(
      "No flows added yet. Use the inputs above to start building your chart!"
  )