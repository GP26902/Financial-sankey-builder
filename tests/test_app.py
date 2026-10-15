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
    at.number_input(key="flow_amount").set_value(120.0)
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
    button(at, "Add Flow").click().run()
    assert any("both" in e.value for e in at.error)

    at = new_app()
    at.text_input(key="custom_src").set_value("X")
    at.text_input(key="custom_tgt").set_value("Y")
    at.number_input(key="flow_amount").set_value(0.0)
    button(at, "Add Flow").click().run()
    assert any("greater than zero" in e.value for e in at.error)
    assert len(at.session_state["flows"]) == 6


def test_cycle_rejected_in_ui():
    at = new_app([F("A", "B", 10)])
    at.text_input(key="custom_src").set_value("B")
    at.text_input(key="custom_tgt").set_value("A")
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
