"""Tests for modules/chart.py and modules/presets.py."""

import pytest

from modules.chart import build_sankey, hex_to_rgba, node_colour, node_label, PALETTE
from modules.flows import node_balance, validate_flows
from modules.presets import PRESETS, get_preset


def F(s, t, v):
    return {"Source": s, "Target": t, "Value": float(v)}


def test_labels_for_balanced_and_unbalanced_nodes():
    flows = [F("Salary", "Jan", 5000), F("Jan", "Rent", 2800)]
    fig = build_sankey(flows, unit="$")
    labels = list(fig.data[0].node.label)
    assert labels[0] == "Salary ($5,000)"
    assert labels[1] == "Jan (in $5,000 / out $2,800)"   # gap visible on the chart
    assert labels[2] == "Rent ($2,800)"


def test_balanced_pass_through_shows_single_number():
    flows = [F("Supplier", "Plant", 100), F("Plant", "DC", 100)]
    labels = list(build_sankey(flows, unit="kg").data[0].node.label)
    assert labels[1] == "Plant (100 kg)"


def test_link_indices_and_values_match_flows():
    flows = [F("A", "B", 3), F("A", "C", 4), F("B", "C", 3)]
    link = build_sankey(flows).data[0].link
    nodes = ["A", "B", "C"]
    assert [nodes[i] for i in link.source] == ["A", "A", "B"]
    assert [nodes[i] for i in link.target] == ["B", "C", "C"]
    assert list(link.value) == [3, 4, 3]
    assert sum(link.value) == sum(f["Value"] for f in flows)


def test_chart_title_and_units_applied():
    fig = build_sankey([F("A", "B", 1500)], unit="kWh", title="Energy flow")
    assert fig.layout.title.text == "Energy flow"
    assert list(fig.data[0].node.label)[0] == "A (1,500 kWh)"
    assert list(fig.data[0].link.customdata) == ["1,500 kWh"]


def test_regression_colour_is_stable_when_other_flows_change():
    """The old app coloured by list position, so colours shifted on delete."""
    a = build_sankey([F("Salary", "Rent", 1), F("Salary", "Food", 1)])
    b = build_sankey([F("Salary", "Food", 1)])
    colour_a = dict(zip(["Salary", "Rent", "Food"], a.data[0].node.color))
    colour_b = dict(zip(["Salary", "Food"], b.data[0].node.color))
    assert colour_a["Salary"] == colour_b["Salary"]
    assert colour_a["Food"] == colour_b["Food"]


def test_node_colour_deterministic_and_case_insensitive():
    assert node_colour("Housing") == node_colour("Housing")
    assert node_colour("Housing") == node_colour("housing")
    assert node_colour("anything") in PALETTE


def test_hex_to_rgba():
    assert hex_to_rgba("#1f77b4", 0.5) == "rgba(31, 119, 180, 0.5)"
    assert hex_to_rgba("#fff", 1) == "rgba(255, 255, 255, 1)"
    with pytest.raises(ValueError):
        hex_to_rgba("#12345")


def test_node_label_helper():
    row = {"Node": "X", "Inflow": 10.0, "Outflow": 0.0, "Status": "Sink"}
    assert node_label(row, "$") == "X ($10)"


# ---- presets -----------------------------------------------------------------
@pytest.mark.parametrize("name", list(PRESETS))
def test_every_preset_is_valid_and_charts(name):
    p = get_preset(name)
    assert validate_flows(p["flows"]) == []
    if p["flows"]:
        build_sankey(p["flows"], unit=p["unit"], title=p["title"])


def test_budget_preset_totals_match_original_sample():
    flows = get_preset("Personal budget (illustrative)")["flows"]
    assert len(flows) == 6
    assert sum(f["Value"] for f in flows) == 5650
    assert all(r["Status"] in ("Source", "Sink") for r in node_balance(flows))


def test_presets_are_labelled_illustrative_and_not_shared():
    for name in PRESETS:
        if PRESETS[name]["flows"]:
            assert "illustrative" in name.lower()
    p = get_preset("Personal budget (illustrative)")
    p["flows"].append({"Source": "x", "Target": "y", "Value": 1.0})
    assert len(PRESETS["Personal budget (illustrative)"]["flows"]) == 6
