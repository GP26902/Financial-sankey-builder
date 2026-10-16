"""Tests for modules/chart.py and modules/presets.py."""

import pytest

from modules.chart import PALETTE, assign_colours, build_sankey, hex_to_rgba, node_label
from modules.flows import UNIT_CHOICES, node_balance, system_totals, validate_flows
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


def test_regression_colours_do_not_depend_on_flow_order():
    """The old app coloured by list position, so colours shifted whenever
    flows were added or deleted."""
    flows = [F("Salary", "Rent", 1), F("Salary", "Food", 1), F("Salary", "Fun", 1)]
    a = build_sankey(flows)
    b = build_sankey(list(reversed(flows)))
    colour_a = dict(zip(["Salary", "Rent", "Food", "Fun"], a.data[0].node.color))
    names_b = ["Salary", "Fun", "Food", "Rent"]
    colour_b = dict(zip(names_b, b.data[0].node.color))
    assert colour_a == colour_b


def test_regression_nodes_get_distinct_colours_up_to_palette_size():
    """Hash-only colouring made 3 of 4 nodes the same colour in a real example."""
    names = ["Supplier A", "Supplier B", "Plant", "Distribution Center", "Scrap"]
    colours = assign_colours(names)
    assert len(set(colours.values())) == len(names)
    for n in range(2, len(PALETTE) + 1):
        c = assign_colours([f"Node {i}" for i in range(n)])
        assert len(set(c.values())) == n


def test_more_nodes_than_colours_still_works():
    colours = assign_colours([f"N{i}" for i in range(len(PALETTE) + 5)])
    assert len(colours) == len(PALETTE) + 5
    assert set(colours.values()) <= set(PALETTE)


def test_colours_case_insensitive_and_deterministic():
    assert assign_colours(["Housing"]) == assign_colours(["Housing"])
    assert assign_colours(["Housing"])["Housing"] == assign_colours(["housing"])["housing"]


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


# ---- template system ---------------------------------------------------------
ENGINEERING = [n for n, p in PRESETS.items() if p.get("category") == "Engineering"]


def test_there_is_at_least_one_engineering_template():
    assert ENGINEERING


@pytest.mark.parametrize("name", ENGINEERING)
def test_engineering_template_is_complete_and_balanced(name):
    p = get_preset(name)
    assert p["unit"] in UNIT_CHOICES
    assert p["description"].strip()
    assert "illustrative" in name.lower() and "illustrative" in p["title"].lower()
    assert len(p["suggestions"]) >= 8
    flows = p["flows"]
    assert validate_flows(flows) == []
    # every intermediate node must send out exactly what it receives
    assert all(r["Status"] in ("Source", "Sink", "Balanced") for r in node_balance(flows))
    totals = system_totals(flows)
    assert totals["difference"] == 0
    assert totals["entering"] > 0


def test_plant_material_flow_template_values():
    flows = get_preset("Plant material flow & scrap (illustrative)")["flows"]
    assert len(flows) == 15
    by_pair = {(f["Source"], f["Target"]): f["Value"] for f in flows}
    totals = system_totals(flows)
    assert totals["entering"] == totals["leaving"] == 50000
    assert by_pair[("Final inspection", "Finished goods shipped")] == 40500
    scrap_in = sum(v for (s, t), v in by_pair.items() if t == "Scrap collected")
    assert scrap_in == 9000
    assert by_pair[("Scrap collected", "Sold to recycler")] + by_pair[
        ("Scrap collected", "Disposal (landfill)")
    ] == scrap_in
    # overall yield 81 %, scrap recovery 85 %
    assert 40500 / 50000 == 0.81
    assert by_pair[("Scrap collected", "Sold to recycler")] / scrap_in == 0.85


def test_get_preset_includes_category_and_description_and_is_a_copy():
    p = get_preset("Plant material flow & scrap (illustrative)")
    assert p["category"] == "Engineering"
    p["flows"][0]["Value"] = 1.0
    assert PRESETS["Plant material flow & scrap (illustrative)"]["flows"][0]["Value"] == 50000.0


# ---- KPIs --------------------------------------------------------------------
from modules.kpis import ENTERING, compute_kpis  # noqa: E402


def test_compute_kpis_basic_and_skips_missing_or_zero():
    flows = [F("In", "A", 100), F("A", "Good", 80), F("A", "Scrap", 20)]
    specs = [
        {"label": "Yield", "numerator": "Good", "denominator": ENTERING},
        {"label": "Scrap share", "numerator": "Scrap", "denominator": "A"},
        {"label": "Ghost", "numerator": "Nope", "denominator": ENTERING},
        {"label": "Ghost2", "numerator": "Good", "denominator": "Nope"},
    ]
    got = {k["label"]: k["text"] for k in compute_kpis(flows, specs)}
    assert got == {"Yield": "80.0%", "Scrap share": "20.0%"}
    assert compute_kpis([], specs) == []
    assert compute_kpis(flows, []) == []


@pytest.mark.parametrize("name", ENGINEERING)
def test_every_template_kpi_resolves_on_its_own_data(name):
    p = get_preset(name)
    got = compute_kpis(p["flows"], p["kpis"])
    assert len(got) == len(p["kpis"])
    assert all(0 <= k["value"] <= 1 for k in got)


def test_plant_template_kpis():
    p = get_preset("Plant material flow & scrap (illustrative)")
    got = {k["label"]: k["text"] for k in compute_kpis(p["flows"], p["kpis"])}
    assert got == {"Overall yield": "81.0%", "Scrap recovery": "85.0%"}


# ---- supply chain network template ------------------------------------------
SUPPLY = "Supply chain network (illustrative)"


def test_supply_chain_template_values():
    p = get_preset(SUPPLY)
    flows = p["flows"]
    assert p["unit"] == "units"
    assert len(flows) == 22
    totals = system_totals(flows)
    assert totals["entering"] == totals["leaving"] == 100000
    by_node = {r["Node"]: r for r in node_balance(flows)}
    assert by_node["Receiving & inspection"]["Inflow"] == 100000
    assert by_node["Assembly plant"]["Inflow"] == 98500
    assert by_node["Plant shipments"]["Inflow"] == 96000
    assert by_node["Added to DC stock"]["Inflow"] == 5000
    delivered = sum(by_node[n]["Inflow"] for n in (
        "Retail customers", "Industrial customers", "E-commerce customers"))
    assert delivered == 91000
    # everything that enters is delivered, held in DC stock, returned or scrapped
    assert delivered + 5000 + 1500 + 2500 == 100000


def test_supply_chain_template_kpis():
    p = get_preset(SUPPLY)
    got = {k["label"]: k["text"] for k in compute_kpis(p["flows"], p["kpis"])}
    assert got == {"Share shipped direct": "25.0%", "Inbound acceptance": "98.5%"}


# ---- plant energy flow template ----------------------------------------------
ENERGY = "Plant energy flow (illustrative)"


def test_plant_energy_template_values():
    p = get_preset(ENERGY)
    flows = p["flows"]
    assert p["unit"] == "MWh"
    assert len(flows) == 33
    totals = system_totals(flows)
    assert totals["entering"] == totals["leaving"] == 4000
    by_node = {r["Node"]: r for r in node_balance(flows)}
    assert by_node["Grid electricity"]["Outflow"] == 2400
    assert by_node["Natural gas"]["Outflow"] == 1600
    assert by_node["Boiler / steam plant"]["Inflow"] == 1200
    assert by_node["Process steam"]["Inflow"] == 1020
    assert by_node["Useful process energy"]["Inflow"] == 1600
    assert by_node["Building services (lighting & HVAC)"]["Inflow"] == 530
    losses = {n: by_node[n]["Inflow"] for n in (
        "Distribution & leak losses", "Idle & standby losses", "Waste heat")}
    assert losses == {
        "Distribution & leak losses": 250,
        "Idle & standby losses": 480,
        "Waste heat": 1140,
    }
    # everything bought is used in production, used by building services or lost
    assert 1600 + 530 + sum(losses.values()) == 4000


def test_plant_energy_template_kpis():
    p = get_preset(ENERGY)
    got = {k["label"]: k["text"] for k in compute_kpis(p["flows"], p["kpis"])}
    assert got == {"Share used in production": "40.0%", "Boiler efficiency": "85.0%"}


# ---- machine / process energy balance template -------------------------------
MACHINE = "Machine / process energy balance (illustrative)"


def test_machine_energy_template_values():
    p = get_preset(MACHINE)
    flows = p["flows"]
    assert p["unit"] == "kWh"
    assert len(flows) == 22
    totals = system_totals(flows)
    assert totals["entering"] == totals["leaving"] == 200
    by_node = {r["Node"]: r for r in node_balance(flows)}
    assert by_node["Electrical input"]["Outflow"] == 200
    subsystems = {
        "Spindle & axis drives": 100, "Hydraulic unit": 25, "Coolant pump": 20,
        "Chiller": 30, "Controls & auxiliaries": 25,
    }
    for node, kwh in subsystems.items():
        assert by_node[node]["Inflow"] == by_node[node]["Outflow"] == kwh
    outcomes = {n: by_node[n]["Inflow"] for n in (
        "Useful cutting & clamping work", "Heat to chips & coolant",
        "Friction, drive & conversion losses", "Idle & standby losses")}
    assert outcomes == {
        "Useful cutting & clamping work": 46,
        "Heat to chips & coolant": 44,
        "Friction, drive & conversion losses": 44,
        "Idle & standby losses": 66,
    }
    # all electricity ends as useful work or as one of the three losses
    assert sum(outcomes.values()) == 200


def test_machine_energy_template_kpis():
    p = get_preset(MACHINE)
    got = {k["label"]: k["text"] for k in compute_kpis(p["flows"], p["kpis"])}
    assert got == {"Share doing useful work": "23.0%", "Share lost to idle & standby": "33.0%"}
