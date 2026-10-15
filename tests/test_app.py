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


def test_regression_delete_one_of_two_identical_rows():
    at = new_app([F("S", "R", 1000), F("S", "R", 1000), F("S", "F", 300)])
    at.multiselect(key="delete_rows").set_value([0]).run()
    button(at, "Delete Selected").click().run()
    assert at.session_state["flows"] == [F("S", "R", 1000), F("S", "F", 300)]


def test_delete_with_nothing_selected_warns():
    at = new_app()
    button(at, "Delete Selected").click().run()
    assert any("Select at least one" in w.value for w in at.warning)
    assert len(at.session_state["flows"]) == 6


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
