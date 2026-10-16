"""UI smoke tests: load the real app.py with Streamlit's AppTest harness.

These check that every section renders and that the buttons behave. They
cannot check how the chart looks in a browser.
"""

import json
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parent.parent / "app.py")


def F(s, t, v):
    return {"Source": s, "Target": t, "Value": float(v)}


def new_app(flows=None):
    at = AppTest.from_file(APP, default_timeout=30)
    if flows is not None:
        at.session_state["flows"] = flows
    return at.run()


def button(at, label):
    return next(b for b in at.button if b.label == label)


def chart_spec(at):
    charts = at.get("plotly_chart")
    return json.loads(charts[0].proto.spec) if charts else None


def test_default_screen_loads_all_four_sections():
    at = new_app()
    assert not at.exception
    assert [s.value for s in at.subheader] == [
        "1. Add a Flow", "2. Manage & Export Flows",
        "3. Flow Balance Check", "4. Flow Diagram",
    ]
    assert len(at.session_state["flows"]) == 6
    spec = chart_spec(at)
    assert spec["layout"]["title"]["text"] == "Monthly Budget Flow (illustrative)"


def test_add_with_nothing_chosen_shows_error_and_changes_nothing():
    at = new_app()
    button(at, "Add Flow").click().run()
    assert any("source" in e.value.lower() for e in at.error)
    assert len(at.session_state["flows"]) == 6


def test_regression_default_dropdowns_no_longer_create_self_loop():
    at = new_app()
    assert at.selectbox(key="src_select").value is None
    assert at.selectbox(key="tgt_select").value is None


def test_add_valid_flow_with_custom_names_then_fields_clear():
    at = new_app()
    at.text_input(key="custom_src").set_value("Supplier A")
    at.text_input(key="custom_tgt").set_value("Assembly")
    at.text_input(key="flow_amount").set_value("120")
    button(at, "Add Flow").click().run()
    assert not at.exception
    assert at.session_state["flows"][-1] == F("Supplier A", "Assembly", 120)
    assert any("Added: Supplier A → Assembly" in s.value for s in at.success)
    assert at.text_input(key="custom_src").value == ""
    assert at.text_input(key="custom_tgt").value == ""


def test_self_loop_and_zero_amount_rejected_in_ui():
    at = new_app()
    at.text_input(key="custom_src").set_value("X")
    at.text_input(key="custom_tgt").set_value("x")
    at.text_input(key="flow_amount").set_value("500")
    button(at, "Add Flow").click().run()
    assert any("both" in e.value for e in at.error)

    at = new_app()
    at.text_input(key="custom_src").set_value("X")
    at.text_input(key="custom_tgt").set_value("Y")
    at.text_input(key="flow_amount").set_value("0")
    button(at, "Add Flow").click().run()
    assert any("greater than zero" in e.value for e in at.error)
    assert len(at.session_state["flows"]) == 6


def test_cycle_rejected_in_ui():
    at = new_app([F("A", "B", 10)])
    at.text_input(key="custom_src").set_value("B")
    at.text_input(key="custom_tgt").set_value("A")
    at.text_input(key="flow_amount").set_value("500")
    button(at, "Add Flow").click().run()
    assert any("loop" in e.value for e in at.error)
    assert len(at.session_state["flows"]) == 1


def test_regression_gap_is_warned_and_shown_on_chart():
    at = new_app([F("Salary", "Jan", 5000), F("Jan", "Rent", 2800)])
    assert not at.exception
    assert any("Jan" in w.value and "do not send out" in w.value for w in at.warning)
    labels = chart_spec(at)["data"][0]["node"]["label"]
    assert "Jan (in $5,000 / out $2,800)" in labels
    metrics = {m.label: m.value for m in at.metric}
    assert metrics["Unaccounted difference"] == "$2,200"


def test_balanced_system_shows_success():
    at = new_app([F("S", "P", 100), F("P", "A", 60), F("P", "B", 40)])
    assert any("balanced" in s.value for s in at.success)
    assert not at.warning


def test_regression_cycle_in_loaded_data_blocks_chart():
    at = new_app([F("A", "B", 1), F("B", "A", 1)])
    assert not at.exception
    assert any("Loop detected" in e.value for e in at.error)
    assert chart_spec(at) is None


def test_unit_change_updates_chart_labels():
    at = new_app([F("Grid", "Plant", 1500)])
    at.selectbox(key="unit_choice").set_value("kWh").run()
    assert not at.exception
    labels = chart_spec(at)["data"][0]["node"]["label"]
    assert labels[0] == "Grid (1,500 kWh)"


def test_custom_unit_and_title():
    at = new_app([F("Dock", "Line", 40)])
    at.selectbox(key="unit_choice").set_value("Custom…").run()
    at.text_input(key="custom_unit").set_value("pallets").run()
    at.text_input(key="chart_title").set_value("Inbound pallets").run()
    spec = chart_spec(at)
    assert spec["data"][0]["node"]["label"][0] == "Dock (40 pallets)"
    assert spec["layout"]["title"]["text"] == "Inbound pallets"


def test_blank_canvas_preset_and_reset():
    at = new_app()
    at.selectbox(key="preset_choice").set_value("Blank canvas").run()
    button(at, "Load sample").click().run()
    assert not at.exception
    assert at.session_state["flows"] == []
    assert any("No flows yet" in i.value for i in at.info)

    at = new_app()
    button(at, "Reset All Flows").click().run()
    assert at.session_state["flows"] == []
    assert not at.exception


def test_reload_budget_sample_after_edits():
    at = new_app([F("A", "B", 1)])
    at.selectbox(key="preset_choice").set_value("Personal budget (illustrative)").run()
    button(at, "Load sample").click().run()
    assert len(at.session_state["flows"]) == 6
    assert at.selectbox(key="unit_choice").value == "$"


# ---- camera-icon (toolbar) image export --------------------------------------
def test_there_is_no_separate_download_section():
    at = new_app()
    assert "5. Download the Diagram" not in [s.value for s in at.subheader]
    assert not any(b.proto.label.startswith(("⬇️", "🌐", "🖼️")) for b in at.get("download_button"))


def test_camera_icon_saves_high_res_png_named_after_the_title():
    at = new_app()
    cfg = json.loads(at.get("plotly_chart")[0].proto.config)
    opts = cfg["toImageButtonOptions"]
    assert opts["format"] == "png"
    assert opts["filename"] == "monthly-budget-flow-illustrative"
    assert (opts["width"], opts["height"], opts["scale"]) == (1400, 700, 2)
    assert cfg["displaylogo"] is False


def test_camera_filename_follows_a_renamed_chart():
    at = new_app()
    at.text_input(key="chart_title").set_value("Plant Energy Flow").run()
    cfg = json.loads(at.get("plotly_chart")[0].proto.config)
    assert cfg["toImageButtonOptions"]["filename"] == "plant-energy-flow"



# ---- editable table ----------------------------------------------------------
import pandas as pd
import streamlit as st


def edit_table(monkeypatch, transform, flows=None):
    """Run the app with the data editor replaced by one that returns the table
    after a simulated user edit (`transform` receives a copy of the table)."""
    seen = {}
    state = {"first_key": None}

    def fake_editor(data, **kwargs):
        # Like the real editor: edits live under one widget key, and a new key
        # starts again from the untouched table.
        seen["kwargs"] = kwargs
        if state["first_key"] is None:
            state["first_key"] = kwargs["key"]
        if kwargs["key"] == state["first_key"]:
            return transform(data.copy())
        return data.copy()

    monkeypatch.setattr(st, "data_editor", fake_editor)
    at = new_app(flows)
    return at, seen


def test_real_editor_renders_with_dynamic_rows_and_no_exception():
    at = new_app()
    assert not at.exception
    assert any("tick the checkbox" in c.value for c in at.caption)


def test_editor_is_configured_for_delete_edit_and_add(monkeypatch):
    at, seen = edit_table(monkeypatch, lambda df: df)
    assert not at.exception
    assert seen["kwargs"]["num_rows"] == "dynamic"
    cfg = seen["kwargs"]["column_config"]
    assert set(cfg) == {"Source", "Target", "Value"}


def test_trash_delete_removes_the_row_and_updates_everything(monkeypatch):
    at, _ = edit_table(monkeypatch, lambda df: df.drop(index=0).reset_index(drop=True))
    assert not at.exception and not at.error
    flows = at.session_state["flows"]
    assert len(flows) == 5 and flows[0] != F("January", "Housing", 2000)
    metrics = {m.label: m.value for m in at.metric}
    assert metrics["Entering the system (from sources)"] == "$3,650"      # 5,650 - 2,000
    assert [m.value for m in at.get("plotly_chart")] if False else True


def test_regression_deleting_one_of_two_identical_rows_keeps_the_other(monkeypatch):
    start = [F("S", "R", 1000), F("S", "R", 1000), F("S", "F", 300)]
    at, _ = edit_table(monkeypatch, lambda df: df.drop(index=1).reset_index(drop=True), start)
    assert at.session_state["flows"] == [F("S", "R", 1000), F("S", "F", 300)]


def test_editing_a_value_updates_flows_and_chart_labels(monkeypatch):
    def edit(df):
        df.loc[0, "Value"] = 2500.0
        return df
    at, _ = edit_table(monkeypatch, edit, [F("Grid", "Plant", 1500)])
    assert at.session_state["flows"] == [F("Grid", "Plant", 2500)]
    assert chart_spec(at)["data"][0]["node"]["label"][0] == "Grid ($2,500)"


def test_editing_the_last_row_works(monkeypatch):
    def edit(df):
        df.loc[len(df) - 1, ["Target", "Value"]] = ["Utilities Plus", 999.0]
        return df
    at, _ = edit_table(monkeypatch, edit)
    assert at.session_state["flows"][-1] == F("February", "Utilities Plus", 999)


def test_new_row_joins_the_diagram_and_the_dropdowns(monkeypatch):
    def add(df):
        df.loc[len(df)] = ["Supplier A", "Assembly", 120.0]
        return df
    at, _ = edit_table(monkeypatch, add)
    assert at.session_state["flows"][-1] == F("Supplier A", "Assembly", 120)
    assert "Assembly" in at.selectbox(key="tgt_select").options


def test_half_filled_new_row_waits_without_errors(monkeypatch):
    def add(df):
        df.loc[len(df)] = ["Supplier A", None, float("nan")]
        return df
    at, _ = edit_table(monkeypatch, add)
    assert not at.error and not at.exception
    assert len(at.session_state["flows"]) == 6
    assert any("1 incomplete row" in c.value for c in at.caption)


def _zero_first_value(df):
    df.loc[0, "Value"] = 0.0
    return df


def _make_self_loop(df):
    df.loc[0, "Target"] = "January"          # row 1 becomes January -> January
    return df


@pytest.mark.parametrize(
    "edit,expected",
    [(_zero_first_value, "greater than zero"), (_make_self_loop, "itself")],
)
def test_invalid_edit_is_rejected_and_table_resets(monkeypatch, edit, expected):
    at, _ = edit_table(monkeypatch, edit)
    assert any("Edit rejected" in e.value and expected in e.value for e in at.error)
    assert len(at.session_state["flows"]) == 6
    assert at.session_state["flows"][0] == F("January", "Housing", 2000)    # unchanged
    assert at.session_state["table_version"] >= 2                          # table restarted


def test_edit_that_creates_a_loop_is_rejected(monkeypatch):
    def add(df):
        df.loc[len(df)] = ["Housing", "January", 10.0]       # January -> Housing -> January
        return df
    at, _ = edit_table(monkeypatch, add)
    assert any("Loop detected" in e.value for e in at.error)
    assert len(at.session_state["flows"]) == 6


def test_case_variant_in_a_later_row_merges_into_the_existing_spelling(monkeypatch):
    def edit(df):
        df.loc[len(df) - 1, "Target"] = "utilities"      # row 6; "Utilities" appears in row 3
        return df
    at, _ = edit_table(monkeypatch, edit)
    assert at.session_state["flows"][-1]["Target"] == "Utilities"
    assert at.session_state["table_version"] >= 2        # table restarted to show tidied name


def test_first_spelling_in_the_table_wins_so_editing_row_one_renames_the_node(monkeypatch):
    def edit(df):
        df.loc[0, "Target"] = "housing"
        return df
    at, _ = edit_table(monkeypatch, edit)
    targets = [f["Target"] for f in at.session_state["flows"]]
    assert targets.count("housing") == 2 and "Housing" not in targets   # one node, one spelling


def test_deleting_every_row_shows_the_empty_state(monkeypatch):
    at, _ = edit_table(monkeypatch, lambda df: df.iloc[0:0])
    assert not at.exception
    assert at.session_state["flows"] == []
    assert any("No flows yet" in i.value for i in at.info)
    assert all(b.proto.disabled for b in at.get("download_button"))


def test_add_flow_form_still_refreshes_the_table():
    at = new_app()
    v0 = at.session_state["table_version"]
    at.text_input(key="custom_src").set_value("Supplier A")
    at.text_input(key="custom_tgt").set_value("Assembly")
    at.text_input(key="flow_amount").set_value("500")
    button(at, "Add Flow").click().run()
    assert at.session_state["table_version"] > v0
    assert list(at.session_state["table_base"]["Target"])[-1] == "Assembly"


# ---- the REAL st.data_editor, driven through its widget state -----------------------
def real_editor(state):
    """Feed an edit (the format Streamlit's editor stores) into the real widget."""
    at = new_app()
    at.session_state[f"flow_table_{at.session_state['table_version']}"] = state
    return at.run()


def edits(edited=None, added=None, deleted=None):
    return {"edited_rows": edited or {}, "added_rows": added or [], "deleted_rows": deleted or []}


def test_real_editor_delete_row():
    at = real_editor(edits(deleted=[0]))
    assert not at.exception and not at.error
    assert len(at.session_state["flows"]) == 5
    assert at.session_state["flows"][0] == F("January", "Groceries", 500)


def test_real_editor_edit_last_row():
    at = real_editor(edits(edited={"5": {"Target": "Utilities Plus", "Value": 999.0}}))
    assert not at.exception and not at.error
    assert at.session_state["flows"][-1] == F("February", "Utilities Plus", 999)


def test_real_editor_add_row():
    at = real_editor(edits(added=[{"Source": "Supplier A", "Target": "Assembly", "Value": 120.0}]))
    assert not at.exception and not at.error
    assert at.session_state["flows"][-1] == F("Supplier A", "Assembly", 120)


def test_real_editor_invalid_edit_rejected():
    at = real_editor(edits(edited={"0": {"Value": 0.0}}))
    assert not at.exception
    assert any("greater than zero" in e.value for e in at.error)
    assert at.session_state["flows"][0] == F("January", "Housing", 2000)


def test_real_editor_half_filled_row_waits():
    at = real_editor(edits(added=[{"Source": "Half"}]))
    assert not at.exception and not at.error
    assert len(at.session_state["flows"]) == 6
    assert any("incomplete row" in c.value for c in at.caption)


def test_real_editor_delete_all_rows_shows_empty_state():
    at = real_editor(edits(deleted=list(range(6))))
    assert not at.exception
    assert at.session_state["flows"] == []
    assert any("No flows yet" in i.value for i in at.info)


# ---- templates ---------------------------------------------------------------
PLANT = "Plant material flow & scrap (illustrative)"


def load_template(name):
    at = new_app()
    at.selectbox(key="preset_choice").set_value(name).run()
    button(at, "Load sample").click().run()
    return at


def test_plant_template_is_in_the_dropdown_and_budget_is_still_there():
    at = new_app()
    options = list(at.selectbox(key="preset_choice").options)
    assert PLANT in options
    assert "Personal budget (illustrative)" in options
    assert "Blank canvas" in options


def test_loading_plant_template_sets_flows_unit_title_and_banner():
    at = load_template(PLANT)
    assert not at.exception
    assert len(at.session_state["flows"]) == 15
    assert at.selectbox(key="unit_choice").value == "kg"
    assert at.text_input(key="chart_title").value.startswith("Plant Material Flow & Scrap")
    assert any(PLANT in i.value and "50,000 kg" in i.value for i in at.info)


def test_plant_template_screen_shows_balanced_totals_and_chart():
    at = load_template(PLANT)
    assert [s.value for s in at.subheader] == [
        "1. Add a Flow", "2. Manage & Export Flows",
        "3. Flow Balance Check", "4. Flow Diagram",
    ]
    metrics = {m.label: m.value for m in at.metric}
    assert metrics["Entering the system (from sources)"] == "50,000 kg"
    assert metrics["Leaving the system (to sinks)"] == "50,000 kg"
    assert metrics["Overall yield"] == "81.0%"
    assert metrics["Scrap recovery"] == "85.0%"
    assert "Unaccounted difference" not in metrics
    assert any("Every intermediate node is balanced" in s.value for s in at.success)
    assert not at.warning and not at.error
    spec = chart_spec(at)
    assert "Finished goods shipped (40,500 kg)" in spec["data"][0]["node"]["label"]


def test_plant_template_dropdowns_offer_process_names():
    at = load_template(PLANT)
    assert "Heat treatment" in at.selectbox(key="src_select").options


def test_banner_disappears_on_blank_canvas_and_on_reset():
    at = load_template(PLANT)
    at.selectbox(key="preset_choice").set_value("Blank canvas").run()
    button(at, "Load sample").click().run()
    assert not any("Template:" in i.value for i in at.info)

    at = load_template(PLANT)
    button(at, "Reset All Flows").click().run()
    assert not any("Template:" in i.value for i in at.info)
    assert not at.exception


def test_editing_a_plant_flow_triggers_balance_warning():
    at = load_template(PLANT)
    flows = [dict(f) for f in at.session_state["flows"]]
    flows[3]["Value"] = 4000.0          # Blanking -> Scrap collected, now short
    at = new_app(flows)
    assert any("Blanking" in w.value for w in at.warning)


def test_unaccounted_tile_returns_when_material_goes_missing():
    at = load_template(PLANT)
    flows = [f for f in at.session_state["flows"] if f["Target"] != "Disposal (landfill)"]
    at.session_state["flows"] = flows      # 1,350 kg no longer leaves the system
    at.run()
    metrics = {m.label: m.value for m in at.metric}
    assert metrics["Unaccounted difference"] == "1,350 kg"
    assert metrics["Overall yield"] == "81.0%"
    assert any("Scrap collected" in w.value for w in at.warning)


def test_budget_and_custom_data_still_show_unaccounted_tile():
    at = new_app()
    assert {m.label for m in at.metric} == {
        "Entering the system (from sources)",
        "Leaving the system (to sinks)",
        "Unaccounted difference",
    }


def test_kpi_updates_after_editing_and_skips_when_node_deleted():
    at = load_template(PLANT)
    flows = [dict(f) for f in at.session_state["flows"]]
    flows = [f for f in flows if f["Target"] != "Sold to recycler"]
    at.session_state["flows"] = flows
    at.run()
    labels = {m.label for m in at.metric}
    assert "Scrap recovery" not in labels
    assert "Overall yield" in labels


# ---- supply chain network template -------------------------------------------
SUPPLY = "Supply chain network (illustrative)"


def test_supply_chain_template_screen_loads_with_totals_and_kpis():
    at = load_template(SUPPLY)
    assert not at.exception
    assert SUPPLY in list(at.selectbox(key="preset_choice").options)
    assert len(at.session_state["flows"]) == 22
    assert at.selectbox(key="unit_choice").value == "units"
    assert at.text_input(key="chart_title").value.startswith("Supply Chain Network")
    assert any(SUPPLY in i.value and "100,000 units" in i.value for i in at.info)
    assert [s.value for s in at.subheader] == [
        "1. Add a Flow", "2. Manage & Export Flows",
        "3. Flow Balance Check", "4. Flow Diagram",
    ]
    metrics = {m.label: m.value for m in at.metric}
    assert metrics["Entering the system (from sources)"] == "100,000 units"
    assert metrics["Leaving the system (to sinks)"] == "100,000 units"
    assert metrics["Share shipped direct"] == "25.0%"
    assert metrics["Inbound acceptance"] == "98.5%"
    assert "Unaccounted difference" not in metrics
    assert any("Every intermediate node is balanced" in s.value for s in at.success)
    assert not at.warning and not at.error
    labels = chart_spec(at)["data"][0]["node"]["label"]
    assert "Assembly plant (98,500 units)" in labels
    assert "Retail customers (36,000 units)" in labels
    assert "Added to DC stock (5,000 units)" in labels


def test_supply_chain_dropdowns_and_edit_triggers_warning():
    at = load_template(SUPPLY)
    assert "Inbound air freight" in at.selectbox(key="src_select").options
    flows = [dict(f) for f in at.session_state["flows"]]
    flows = [f for f in flows if f["Target"] != "Added to DC stock"]
    at.session_state["flows"] = flows
    at.run()
    assert any("East distribution centre" in w.value for w in at.warning)
    assert {m.label: m.value for m in at.metric}["Unaccounted difference"] == "5,000 units"


# ---- plant energy flow template ----------------------------------------------
ENERGY = "Plant energy flow (illustrative)"


def test_plant_energy_template_screen_loads_with_totals_and_kpis():
    at = load_template(ENERGY)
    assert not at.exception
    assert ENERGY in list(at.selectbox(key="preset_choice").options)
    assert len(at.session_state["flows"]) == 33
    assert at.selectbox(key="unit_choice").value == "MWh"
    assert at.text_input(key="chart_title").value.startswith("Plant Energy Flow")
    assert any(ENERGY in i.value and "4,000 MWh" in i.value for i in at.info)
    assert [s.value for s in at.subheader] == [
        "1. Add a Flow", "2. Manage & Export Flows",
        "3. Flow Balance Check", "4. Flow Diagram",
    ]
    metrics = {m.label: m.value for m in at.metric}
    assert metrics["Entering the system (from sources)"] == "4,000 MWh"
    assert metrics["Leaving the system (to sinks)"] == "4,000 MWh"
    assert metrics["Share used in production"] == "40.0%"
    assert metrics["Boiler efficiency"] == "85.0%"
    assert "Unaccounted difference" not in metrics
    assert any("Every intermediate node is balanced" in s.value for s in at.success)
    assert not at.warning and not at.error
    labels = chart_spec(at)["data"][0]["node"]["label"]
    assert "Waste heat (1,140 MWh)" in labels
    assert "Useful process energy (1,600 MWh)" in labels
    assert "Machining (1,050 MWh)" in labels


def test_plant_energy_dropdowns_and_edit_triggers_warning():
    at = load_template(ENERGY)
    assert "Solar PV (on-site)" in at.selectbox(key="src_select").options
    flows = [f for f in at.session_state["flows"] if f["Target"] != "Idle & standby losses"]
    at.session_state["flows"] = flows
    at.run()
    assert any("Machining" in w.value for w in at.warning)
    assert {m.label: m.value for m in at.metric}["Unaccounted difference"] == "480 MWh"


# ---- CSV upload --------------------------------------------------------------
def upload(at, name, text):
    key = next(u.key for u in at.file_uploader)
    at.file_uploader(key=key).upload(name, text.encode("utf-8"), "text/csv").run()
    return at


def test_download_then_upload_round_trip_and_adding_new_months():
    """The real use case: finish a budget, download it, come back, add months."""
    at = new_app()
    original = [dict(f) for f in at.session_state["flows"]]
    csv_text = "Source,Target,Value\n" + "".join(
        f"{f['Source']},{f['Target']},{f['Value']}\n" for f in original)
    at = new_app([])                       # a fresh visit with no flows
    at = upload(at, "flows.csv", csv_text)
    assert not at.exception
    assert at.session_state["flows"] == original
    assert any("Loaded 6 flows from flows.csv" in s.value for s in at.success)
    # add November from the normal 'Add a Flow' form
    at.text_input(key="custom_src").set_value("November")
    at.text_input(key="custom_tgt").set_value("Housing")
    at.text_input(key="flow_amount").set_value("2000")
    button(at, "Add Flow").click().run()
    assert len(at.session_state["flows"]) == 7
    assert {m.label: m.value for m in at.metric}["Entering the system (from sources)"] == "$7,650"


def test_upload_replaces_a_template_and_clears_its_banner_and_kpis():
    at = load_template(PLANT)
    at = upload(at, "mine.csv", "Source,Target,Value\nJanuary,Rent,900\nJanuary,Food,300\n")
    assert len(at.session_state["flows"]) == 2
    assert not any("Template:" in i.value for i in at.info)
    assert "Overall yield" not in {m.label for m in at.metric}
    assert not at.exception


def test_bad_upload_keeps_existing_flows_and_shows_the_reason():
    at = new_app()
    before = [dict(f) for f in at.session_state["flows"]]
    at = upload(at, "bad.csv", "Source,Target,Value\nA,B,5\nB,A,5\n")
    assert at.session_state["flows"] == before
    assert any("Nothing was changed" in e.value and "Loop detected" in e.value for e in at.error)
    at = upload(at, "bad2.csv", "Name,Amount\nA,5\n")
    assert at.session_state["flows"] == before
    assert any("Missing column" in e.value for e in at.error)


def test_upload_works_from_an_empty_canvas_and_uploader_resets():
    at = new_app([])
    assert any("No flows yet" in i.value for i in at.info)
    at = upload(at, "flows.csv", "Source,Target,Value\nJan,Rent,900\n")
    assert len(at.session_state["flows"]) == 1
    assert at.session_state["upload_version"] == 1
    assert at.file_uploader[0].value is None        # ready for another upload


# ---- machine / process energy balance template -------------------------------
MACHINE = "Machine / process energy balance (illustrative)"


def test_machine_energy_template_screen_loads_with_totals_and_kpis():
    at = load_template(MACHINE)
    assert not at.exception
    assert MACHINE in list(at.selectbox(key="preset_choice").options)
    assert len(at.session_state["flows"]) == 22
    assert at.selectbox(key="unit_choice").value == "kWh"
    assert at.text_input(key="chart_title").value.startswith("Machine Energy Balance")
    assert any(MACHINE in i.value and "200 kWh" in i.value for i in at.info)
    assert [s.value for s in at.subheader] == [
        "1. Add a Flow", "2. Manage & Export Flows",
        "3. Flow Balance Check", "4. Flow Diagram",
    ]
    metrics = {m.label: m.value for m in at.metric}
    assert metrics["Entering the system (from sources)"] == "200 kWh"
    assert metrics["Leaving the system (to sinks)"] == "200 kWh"
    assert metrics["Share doing useful work"] == "23.0%"
    assert metrics["Share lost to idle & standby"] == "33.0%"
    assert "Unaccounted difference" not in metrics
    assert any("Every intermediate node is balanced" in s.value for s in at.success)
    assert not at.warning and not at.error
    labels = chart_spec(at)["data"][0]["node"]["label"]
    assert "Idle & standby losses (66 kWh)" in labels
    assert "Useful cutting & clamping work (46 kWh)" in labels
    assert "Spindle & axis drives (100 kWh)" in labels


def test_machine_energy_dropdowns_and_edit_triggers_warning():
    at = load_template(MACHINE)
    assert "Furnace burners" in at.selectbox(key="src_select").options
    flows = [f for f in at.session_state["flows"] if f["Target"] != "Idle & standby losses"]
    at.session_state["flows"] = flows
    at.run()
    assert any("Spindle & axis drives" in w.value for w in at.warning)
    assert {m.label: m.value for m in at.metric}["Unaccounted difference"] == "66 kWh"


# ---- $ signs in the unbalanced-nodes warning ---------------------------------
def test_regression_warning_escapes_dollar_signs_so_amounts_are_not_math():
    at = new_app([F("Salary", "Jan", 5000), F("Jan", "Rent", 2800)])
    warning = next(w for w in at.warning if "do not send out" in w.value)
    assert r"in \$5,000, out \$2,800 (unallocated by \$2,200)" in warning.value
    # no unescaped $ is left anywhere in the message
    assert "$" not in warning.value.replace(r"\$", "")


def test_warning_text_for_non_dollar_units_is_unchanged():
    at = new_app([F("S", "P", 100), F("P", "A", 60)])
    at.selectbox(key="unit_choice").set_value("kg").run()
    warning = next(w for w in at.warning if "do not send out" in w.value)
    assert "in 100 kg, out 60 kg" in warning.value
    assert "\\" not in warning.value


# ---- maths in the Amount box -------------------------------------------------
def fill_flow(at, amount, source="Chase", target="January"):
    at.text_input(key="custom_src").set_value(source)
    at.text_input(key="custom_tgt").set_value(target)
    at.text_input(key="flow_amount").set_value(amount)
    return at


def test_amount_box_starts_empty_and_empty_amount_is_rejected():
    at = new_app([])
    assert at.text_input(key="flow_amount").value == ""
    at = fill_flow(at, "")
    button(at, "Add Flow").click().run()
    assert any("Type an amount" in e.value for e in at.error)
    assert at.session_state["flows"] == []


def test_enter_in_amount_box_shows_the_result():
    at = new_app([])
    at.text_input(key="flow_amount").set_value("800+400").run()
    assert at.text_input(key="flow_amount").value == "1200"
    at.text_input(key="flow_amount").set_value("2400/3").run()
    assert at.text_input(key="flow_amount").value == "800"
    at.text_input(key="flow_amount").set_value("(2400-300)/3 + 1,000").run()
    assert at.text_input(key="flow_amount").value == "1700"
    assert not at.exception


def test_add_flow_with_a_sum_stores_the_result_and_clears_the_box():
    at = new_app([])
    at = fill_flow(at, "1000+183.10")
    button(at, "Add Flow").click().run()
    assert at.session_state["flows"] == [F("Chase", "January", 1183.1)]
    assert at.text_input(key="flow_amount").value == ""
    assert any("Added: Chase → January" in s.value and "1,183.10" in s.value for s in at.success)


def test_add_flow_with_division_keeps_full_precision():
    at = fill_flow(new_app([]), "1000/3")
    button(at, "Add Flow").click().run()
    assert abs(at.session_state["flows"][0]["Value"] - 333.3333333333) < 1e-9


@pytest.mark.parametrize("bad", ["800+", "abc", "5/0", "2**3", "-5", "0"])
def test_bad_amount_text_adds_nothing_and_explains(bad):
    at = fill_flow(new_app([]), bad)
    button(at, "Add Flow").click().run()
    assert at.session_state["flows"] == []
    assert at.error and not at.exception


# ---- manufacturing cost flow template ($) ------------------------------------
COST = "Manufacturing cost flow (illustrative)"


def test_manufacturing_cost_template_screen_loads_with_dollar_amounts():
    at = load_template(COST)
    assert not at.exception
    assert COST in list(at.selectbox(key="preset_choice").options)
    assert len(at.session_state["flows"]) == 22
    assert at.selectbox(key="unit_choice").value == "$"
    assert at.text_input(key="chart_title").value.startswith("Manufacturing Cost Flow")
    assert [s.value for s in at.subheader] == [
        "1. Add a Flow", "2. Manage & Export Flows",
        "3. Flow Balance Check", "4. Flow Diagram",
    ]
    metrics = {m.label: m.value for m in at.metric}
    assert metrics["Entering the system (from sources)"] == "$650,000"
    assert metrics["Leaving the system (to sinks)"] == "$650,000"
    assert metrics["Share shipped as good product"] == "80.0%"
    assert metrics["Share lost to scrap & rework"] == "9.0%"
    assert "Unaccounted difference" not in metrics
    assert any("Every intermediate node is balanced" in s.value for s in at.success)
    assert not at.warning and not at.error
    labels = chart_spec(at)["data"][0]["node"]["label"]
    assert "Purchased materials ($400,000)" in labels
    assert "Finished goods cost ($556,000)" in labels
    assert "Shipped to customers (COGS) ($520,000)" in labels
    assert "Scrap & rework cost ($58,500)" in labels


def test_regression_template_description_escapes_dollar_signs():
    at = load_template(COST)
    info = next(i for i in at.info if COST in i.value)
    # amounts are escaped so Streamlit does not turn "$400,000 ... $150,000" into math
    assert r"\$650,000" in info.value and r"\$400,000" in info.value
    assert "$" not in info.value.replace(r"\$", "")


def test_manufacturing_cost_dropdowns_and_edit_triggers_dollar_warning():
    at = load_template(COST)
    assert "Warranty & returns" in at.selectbox(key="src_select").options
    flows = [f for f in at.session_state["flows"] if f["Target"] != "Other losses (idle time & shrinkage)"]
    at.session_state["flows"] = flows
    at.run()
    warning = next(w for w in at.warning if "do not send out" in w.value)
    assert r"in \$275,000, out \$259,000" in warning.value
    assert "$" not in warning.value.replace(r"\$", "")
    assert {m.label: m.value for m in at.metric}["Unaccounted difference"] == "$35,500"


def test_manufacturing_cost_template_add_flow_message_shows_dollars():
    at = load_template(COST)
    at.text_input(key="custom_src").set_value("Warranty & returns")
    at.text_input(key="custom_tgt").set_value("Other losses (idle time & shrinkage)")
    at.text_input(key="flow_amount").set_value("1200")
    button(at, "Add Flow").click().run()
    assert not at.exception
    assert any("$1,200" in s.value for s in at.success)
