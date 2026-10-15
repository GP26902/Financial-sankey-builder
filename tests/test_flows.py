"""Unit tests for modules/flows.py (no Streamlit needed)."""

import math

import pytest

from modules.flows import (
    FlowError,
    add_flow,
    clean_name,
    delete_flows,
    find_cycle,
    format_value,
    list_nodes,
    node_balance,
    resolve_node_name,
    resolve_unit,
    system_totals,
    unbalanced_nodes,
    validate_flows,
    validate_value,
    would_create_cycle,
)


def F(s, t, v):
    return {"Source": s, "Target": t, "Value": float(v)}


# ---- Regression: flow conservation was never checked -----------------------
def test_regression_pass_through_gap_is_reported():
    """Salary -> Jan 5000, Jan -> Rent 2800: the old app labelled Jan $2,800
    and silently lost $2,200."""
    flows = [F("Salary", "Jan", 5000), F("Jan", "Rent", 2800)]
    rows = {r["Node"]: r for r in node_balance(flows)}
    assert rows["Jan"]["Status"] == "Unallocated"
    assert rows["Jan"]["Inflow"] == 5000
    assert rows["Jan"]["Outflow"] == 2800
    assert rows["Jan"]["Difference (in − out)"] == 2200
    assert [r["Node"] for r in unbalanced_nodes(flows)] == ["Jan"]
    totals = system_totals(flows)
    assert totals["entering"] == 5000
    assert totals["leaving"] == 2800
    assert totals["difference"] == 2200


def test_balanced_chain_has_no_gap():
    flows = [F("Supplier", "Plant", 100), F("Plant", "DC", 60), F("Plant", "Scrap", 40)]
    rows = {r["Node"]: r["Status"] for r in node_balance(flows)}
    assert rows == {"Supplier": "Source", "Plant": "Balanced", "DC": "Sink", "Scrap": "Sink"}
    assert unbalanced_nodes(flows) == []
    assert system_totals(flows)["difference"] == 0


def test_over_allocated_node():
    flows = [F("A", "B", 10), F("B", "C", 15)]
    assert node_balance(flows)[1]["Status"] == "Over-allocated"
    assert node_balance(flows)[1]["Difference (in − out)"] == -5


def test_float_noise_is_not_flagged():
    # 0.1 + 0.2 != 0.3 in binary floating point
    flows = [F("A", "B", 0.3), F("B", "C", 0.1), F("B", "D", 0.2)]
    assert unbalanced_nodes(flows) == []


def test_small_real_gap_is_flagged():
    flows = [F("A", "B", 1000), F("B", "C", 999.99)]
    assert len(unbalanced_nodes(flows)) == 1


def test_system_difference_equals_sum_of_node_gaps():
    flows = [F("S", "M1", 100), F("M1", "T", 70), F("S", "M2", 50), F("M2", "T", 60)]
    gap_sum = sum(r["Difference (in − out)"] for r in node_balance(flows))
    assert system_totals(flows)["difference"] == pytest.approx(gap_sum)


# ---- Regression: self-loops --------------------------------------------------
def test_regression_self_loop_rejected():
    with pytest.raises(FlowError):
        add_flow([], "April", "April", 500)


def test_self_loop_rejected_ignoring_case_and_spaces():
    with pytest.raises(FlowError):
        add_flow([], "  April ", "april", 500)


# ---- Regression: cycles ------------------------------------------------------
def test_regression_two_node_cycle_rejected():
    flows = [F("A", "B", 100)]
    assert would_create_cycle(flows, "B", "A")
    with pytest.raises(FlowError, match="loop"):
        add_flow(flows, "B", "A", 100)


def test_long_cycle_rejected():
    flows = [F("A", "B", 1), F("B", "C", 1)]
    with pytest.raises(FlowError):
        add_flow(flows, "C", "A", 1)


def test_diamond_is_not_a_cycle():
    flows = [F("A", "B", 1), F("A", "C", 1), F("B", "D", 1)]
    assert not would_create_cycle(flows, "C", "D")
    assert find_cycle(flows + [F("C", "D", 1)]) is None


def test_find_cycle_reports_path():
    cyc = find_cycle([F("A", "B", 1), F("B", "C", 1), F("C", "A", 1)])
    assert cyc[0] == cyc[-1]
    assert set(cyc) == {"A", "B", "C"}


def test_validate_flows_reports_cycle_in_loaded_data():
    problems = validate_flows([F("A", "B", 1), F("B", "A", 1)])
    assert any("Loop" in p for p in problems)


# ---- Regression: delete matched on label, removed duplicates -----------------
def test_regression_delete_by_index_keeps_identical_rows():
    flows = [F("Salary", "Rent", 1000), F("Salary", "Rent", 1000), F("Salary", "Food", 300)]
    result = delete_flows(flows, [0])
    assert len(result) == 2
    assert result[0] == F("Salary", "Rent", 1000)
    assert result[1] == F("Salary", "Food", 300)


def test_delete_does_not_mutate_input():
    flows = [F("A", "B", 1), F("B", "C", 1)]
    delete_flows(flows, [0])
    assert len(flows) == 2


def test_delete_bad_index():
    with pytest.raises(FlowError):
        delete_flows([F("A", "B", 1)], [5])
    with pytest.raises(FlowError):
        delete_flows([F("A", "B", 1)], [-1])


# ---- Regression: zero / invalid amounts --------------------------------------
@pytest.mark.parametrize("bad", [0, 0.0, -5, float("nan"), float("inf"), "abc", None])
def test_regression_bad_amounts_rejected(bad):
    with pytest.raises(FlowError):
        validate_value(bad)
    with pytest.raises(FlowError):
        add_flow([], "A", "B", bad)


def test_validate_flows_catches_bad_rows():
    problems = validate_flows([F("A", "A", 5), F("B", "C", 0), {"Source": "", "Target": "X", "Value": 1}])
    assert len(problems) == 3


# ---- Regression: case-sensitive duplicate nodes ------------------------------
def test_regression_case_variants_merge_into_one_node():
    flows = [F("Salary", "Housing", 100)]
    flows = add_flow(flows, "salary", "housing", 50)
    assert list_nodes(flows) == ["Salary", "Housing"]
    assert flows[-1]["Source"] == "Salary" and flows[-1]["Target"] == "Housing"


def test_resolve_node_name_new_name_is_cleaned():
    assert resolve_node_name("  New   Node ", ["Other"]) == "New Node"


# ---- add_flow behaviour -------------------------------------------------------
def test_add_flow_blank_names():
    with pytest.raises(FlowError):
        add_flow([], "", "B", 1)
    with pytest.raises(FlowError):
        add_flow([], "A", "   ", 1)
    with pytest.raises(FlowError):
        add_flow([], None, "B", 1)


def test_add_flow_does_not_mutate_input_and_appends():
    original = [F("A", "B", 1)]
    new = add_flow(original, "B", "C", 2)
    assert len(original) == 1
    assert new[-1] == F("B", "C", 2)


def test_duplicate_pairs_are_allowed_and_sum_in_balance():
    flows = [F("A", "B", 100), F("A", "B", 50)]
    rows = {r["Node"]: r for r in node_balance(flows)}
    assert rows["A"]["Outflow"] == 150
    assert rows["B"]["Inflow"] == 150


def test_clean_name():
    assert clean_name(None) == ""
    assert clean_name("  a   b ") == "a b"


# ---- Formatting ----------------------------------------------------------------
@pytest.mark.parametrize(
    "value,unit,expected",
    [
        (1200, "$", "$1,200"),
        (1200, "kWh", "1,200 kWh"),
        (1200.5, "kg", "1,200.50 kg"),
        (0.25, "$", "$0.25"),
        (1200, "", "1,200"),
        (5, "₹", "₹5"),
    ],
)
def test_format_value(value, unit, expected):
    assert format_value(value, unit) == expected


def test_resolve_unit():
    assert resolve_unit("kg") == "kg"
    assert resolve_unit("Custom…", "  pallets ") == "pallets"
    assert resolve_unit("Custom…", "") == ""
