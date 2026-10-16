"""Unit tests for modules/flows.py (no Streamlit needed)."""

import math

import pytest

from modules.flows import (
    FlowError,
    add_flow,
    clean_name,
    find_cycle,
    format_value,
    list_nodes,
    node_balance,
    resolve_node_name,
    resolve_unit,
    rows_to_flows,
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


# ---- Table edits: rows_to_flows ---------------------------------------------------
def R(s, t, v):
    return {"Source": s, "Target": t, "Value": v}


def test_rows_to_flows_clean_table_round_trips():
    flows, errors, incomplete, renamed = rows_to_flows([R("A", "B", 10.0), R("B", "C", 4.5)])
    assert flows == [F("A", "B", 10), F("B", "C", 4.5)]
    assert (errors, incomplete, renamed) == ([], 0, False)


def test_regression_identical_rows_are_kept_when_only_one_is_removed():
    """The old dropdown delete matched on label text and removed both copies."""
    table = [R("Salary", "Rent", 1000.0), R("Salary", "Food", 300.0)]   # one copy already deleted
    flows, errors, *_ = rows_to_flows(table)
    assert errors == []
    assert flows == [F("Salary", "Rent", 1000), F("Salary", "Food", 300)]
    both, *_ = rows_to_flows([R("Salary", "Rent", 1000.0)] * 2)
    assert len(both) == 2          # duplicates are legitimate rows


def test_rows_to_flows_blank_rows_ignored_and_half_filled_rows_wait():
    nan = float("nan")
    rows = [R("A", "B", 10.0), R(None, None, nan), R("", "  ", None), R("X", None, nan), R(None, "Y", 5.0)]
    flows, errors, incomplete, _ = rows_to_flows(rows)
    assert flows == [F("A", "B", 10)]
    assert errors == []
    assert incomplete == 2


@pytest.mark.parametrize("bad", [0.0, -3.0, float("inf"), "abc"])
def test_rows_to_flows_rejects_bad_amounts_with_row_number(bad):
    _, errors, _, _ = rows_to_flows([R("A", "B", 10.0), R("B", "C", bad)])
    assert len(errors) == 1 and errors[0].startswith("Row 2:")


def test_rows_to_flows_rejects_self_loop_including_case_variant():
    _, errors, _, _ = rows_to_flows([R("A", "a", 5.0)])
    assert errors and "itself" in errors[0]


def test_rows_to_flows_rejects_cycle():
    _, errors, _, _ = rows_to_flows([R("A", "B", 1.0), R("B", "C", 1.0), R("C", "A", 1.0)])
    assert any("Loop detected" in e for e in errors)


def test_rows_to_flows_merges_case_variants_and_reports_rename():
    flows, errors, _, renamed = rows_to_flows([R("Salary", "Housing", 100.0), R("salary", "housing", 50.0)])
    assert errors == [] and renamed is True
    assert list_nodes(flows) == ["Salary", "Housing"]


def test_rows_to_flows_tidies_whitespace():
    flows, _, _, renamed = rows_to_flows([R("  Plant   A ", "DC", 5.0)])
    assert flows[0]["Source"] == "Plant A" and renamed is True


def test_rows_to_flows_accepts_numpy_and_pandas_missing_values():
    import numpy as np
    import pandas as pd
    flows, errors, incomplete, _ = rows_to_flows(
        [R(np.str_("A"), "B", np.float64(2.5)), R(pd.NA, pd.NA, pd.NA), R("C", pd.NA, 1.0)]
    )
    assert flows == [F("A", "B", 2.5)] and errors == [] and incomplete == 1
    assert isinstance(flows[0]["Value"], float)


# ---- CSV upload parser -------------------------------------------------------
from modules.flows import parse_flows_csv  # noqa: E402


def test_parse_csv_round_trips_the_download_format():
    csv_text = "Source,Target,Value\nJanuary,Housing,2000.0\nJanuary,Groceries,500.0\n"
    flows, errors, skipped = parse_flows_csv(csv_text.encode("utf-8"))
    assert errors == [] and skipped == 0
    assert flows == [
        {"Source": "January", "Target": "Housing", "Value": 2000.0},
        {"Source": "January", "Target": "Groceries", "Value": 500.0},
    ]


def test_parse_csv_is_tolerant_of_excel_quirks():
    text = '\ufeff source , TARGET,Value,Notes\nA,B,"1,200.50",x\nb,C,$300,y\n'
    flows, errors, _ = parse_flows_csv(text.encode("utf-8"))
    assert errors == []
    assert [f["Value"] for f in flows] == [1200.5, 300.0]
    assert flows[1]["Source"] == "B"        # 'b' merged with the existing node 'B'


@pytest.mark.parametrize("text, fragment", [
    ("", "empty"),
    ("Source,Target\nA,B\n", "Missing column"),
    ("Source,Target,Value\n", "no complete rows"),
    ("Source,Target,Value\nA,B,abc\n", "Data row 1"),
    ("Source,Target,Value\nA,B,-5\n", "greater than zero"),
    ("Source,Target,Value\nA,A,5\n", "flows into itself"),
    ("Source,Target,Value\nA,B,5\nB,A,5\n", "Loop detected"),
])
def test_parse_csv_rejects_bad_files_with_a_readable_message(text, fragment):
    flows, errors, _ = parse_flows_csv(text.encode("utf-8"))
    assert flows == []
    assert any(fragment in e for e in errors)


def test_parse_csv_skips_incomplete_rows_and_enforces_row_limit():
    flows, errors, skipped = parse_flows_csv("Source,Target,Value\nA,B,5\nC,,7\n")
    assert len(flows) == 1 and skipped == 1 and errors == []
    flows, errors, _ = parse_flows_csv("Source,Target,Value\nA,B,5\nC,D,7\n", max_rows=1)
    assert flows == [] and "limit" in errors[0]


def test_parse_csv_accepts_windows_1252_files():
    flows, errors, _ = parse_flows_csv("Source,Target,Value\nCafé,B,5\n".encode("cp1252"))
    assert errors == [] and flows[0]["Source"] == "Café"


# ---- $ escaping for Streamlit markdown ---------------------------------------
from modules.flows import escape_markdown_dollars  # noqa: E402


def test_escape_markdown_dollars_escapes_every_dollar_sign():
    assert escape_markdown_dollars("in $5,000, out $2,800") == r"in \$5,000, out \$2,800"
    assert escape_markdown_dollars("in 100 kWh, out 60 kWh") == "in 100 kWh, out 60 kWh"
    assert escape_markdown_dollars("") == ""
