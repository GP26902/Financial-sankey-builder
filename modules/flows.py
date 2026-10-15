"""Pure flow logic: validation, balance checks and formatting.

No Streamlit or Plotly imports here, so everything in this file can be
unit-tested on its own (see tests/test_flows.py).

A *flow* is a dict: {"Source": str, "Target": str, "Value": float}.
The column names match the CSV export, so the download round-trips.
"""

from __future__ import annotations

import math
from collections import defaultdict, deque

# Relative / absolute tolerance used when deciding whether a node's inflow
# equals its outflow. Tight on purpose: 1000 in and 999.99 out is flagged.
BALANCE_REL_TOL = 1e-9
BALANCE_ABS_TOL = 1e-9

# Unit presets shown in the UI. "prefix" units print as "$1,200",
# everything else prints as "1,200 kWh".
PREFIX_UNITS = {"$", "€", "£", "₹"}
UNIT_CHOICES = [
    "$", "kWh", "MWh", "kg", "tonnes", "units", "m³", "hours", "Custom…",
]


class FlowError(ValueError):
    """Raised when a flow (or a set of flows) is not valid."""


# --------------------------------------------------------------------------
# Names
# --------------------------------------------------------------------------
def clean_name(name) -> str:
    """Trim and collapse internal whitespace. None becomes ''."""
    if name is None:
        return ""
    return " ".join(str(name).split())


def resolve_node_name(name, existing_nodes) -> str:
    """Return the spelling to use for `name`.

    Matching is case-insensitive, so typing "housing" when "Housing" is
    already a node reuses "Housing" instead of creating a second node.
    """
    cleaned = clean_name(name)
    for node in existing_nodes:
        if node.casefold() == cleaned.casefold():
            return node
    return cleaned


def list_nodes(flows) -> list[str]:
    """Unique node names in order of first appearance."""
    seen: dict[str, None] = {}
    for f in flows:
        seen.setdefault(f["Source"], None)
        seen.setdefault(f["Target"], None)
    return list(seen)


# --------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------
def _adjacency(flows) -> dict[str, set[str]]:
    adj: dict[str, set[str]] = defaultdict(set)
    for f in flows:
        adj[f["Source"]].add(f["Target"])
    return adj


def would_create_cycle(flows, source: str, target: str) -> bool:
    """True if adding source -> target closes a loop (incl. a self-loop)."""
    if source == target:
        return True
    adj = _adjacency(flows)
    queue, seen = deque([target]), {target}
    while queue:
        node = queue.popleft()
        if node == source:
            return True
        for nxt in adj.get(node, ()):
            if nxt not in seen:
                seen.add(nxt)
                queue.append(nxt)
    return False


def find_cycle(flows):
    """Return one cycle as a node list like ['A', 'B', 'A'], or None."""
    adj = _adjacency(flows)
    WHITE, GREY, BLACK = 0, 1, 2
    colour: dict[str, int] = defaultdict(int)

    for start in list(adj):
        if colour[start] != WHITE:
            continue
        stack = [(start, iter(sorted(adj.get(start, ()))))]
        path = [start]
        colour[start] = GREY
        while stack:
            node, it = stack[-1]
            advanced = False
            for nxt in it:
                if colour[nxt] == GREY:
                    return path[path.index(nxt):] + [nxt]
                if colour[nxt] == WHITE:
                    colour[nxt] = GREY
                    path.append(nxt)
                    stack.append((nxt, iter(sorted(adj.get(nxt, ())))))
                    advanced = True
                    break
            if not advanced:
                colour[node] = BLACK
                stack.pop()
                path.pop()
    return None


def validate_value(value) -> float:
    """Return value as float, or raise FlowError if it is not > 0 and finite."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        raise FlowError("Amount must be a number.")
    if not math.isfinite(v):
        raise FlowError("Amount must be a finite number.")
    if v <= 0:
        raise FlowError("Amount must be greater than zero.")
    return v


def validate_flows(flows) -> list[str]:
    """Return a list of problems with a whole flow set (empty list = OK)."""
    problems: list[str] = []
    for i, f in enumerate(flows, start=1):
        label = f"Row {i}"
        if not clean_name(f.get("Source")) or not clean_name(f.get("Target")):
            problems.append(f"{label}: source and target must not be blank.")
            continue
        if f["Source"] == f["Target"]:
            problems.append(f"{label}: '{f['Source']}' flows into itself.")
        try:
            validate_value(f.get("Value"))
        except FlowError as exc:
            problems.append(f"{label}: {exc}")
    if not problems:
        cycle = find_cycle(flows)
        if cycle:
            problems.append("Loop detected: " + " → ".join(cycle) + ".")
    return problems


# --------------------------------------------------------------------------
# Editing (all functions return a new list; the input is never mutated)
# --------------------------------------------------------------------------
def add_flow(flows, source, target, value) -> list[dict]:
    """Validate and append a flow. Raises FlowError with a readable message."""
    existing = list_nodes(flows)
    src = resolve_node_name(source, existing)
    if not src:
        raise FlowError("Choose or type a source.")
    tgt = resolve_node_name(target, existing + [src])
    if not tgt:
        raise FlowError("Choose or type a target.")
    amount = validate_value(value)
    if src == tgt:
        raise FlowError(f"Source and target are both '{src}'.")
    if would_create_cycle(flows, src, tgt):
        raise FlowError(
            f"{src} → {tgt} would create a loop (there is already a path "
            f"from {tgt} back to {src}). Sankey diagrams need one-way flow."
        )
    return list(flows) + [{"Source": src, "Target": tgt, "Value": amount}]


def delete_flows(flows, indices) -> list[dict]:
    """Remove flows by 0-based row index (safe when rows look identical)."""
    drop = set(indices)
    bad = [i for i in drop if not isinstance(i, int) or i < 0 or i >= len(flows)]
    if bad:
        raise FlowError(f"Unknown row index: {sorted(bad, key=str)}")
    return [f for i, f in enumerate(flows) if i not in drop]


# --------------------------------------------------------------------------
# Balance (flow conservation)
# --------------------------------------------------------------------------
def node_balance(flows) -> list[dict]:
    """Inflow, outflow and balance status for every node.

    Status:
      Source          only sends (no inflow)
      Sink            only receives (no outflow)
      Balanced        inflow equals outflow
      Unallocated     receives more than it sends
      Over-allocated  sends more than it receives
    """
    inflow: dict[str, list[float]] = defaultdict(list)
    outflow: dict[str, list[float]] = defaultdict(list)
    for f in flows:
        outflow[f["Source"]].append(float(f["Value"]))
        inflow[f["Target"]].append(float(f["Value"]))

    rows = []
    for node in list_nodes(flows):
        i, o = math.fsum(inflow[node]), math.fsum(outflow[node])
        if i == 0:
            status = "Source"
        elif o == 0:
            status = "Sink"
        elif math.isclose(i, o, rel_tol=BALANCE_REL_TOL, abs_tol=BALANCE_ABS_TOL):
            status = "Balanced"
        elif i > o:
            status = "Unallocated"
        else:
            status = "Over-allocated"
        rows.append(
            {
                "Node": node,
                "Inflow": i,
                "Outflow": o,
                "Difference (in − out)": 0.0 if status in ("Balanced", "Source", "Sink") else i - o,
                "Status": status,
            }
        )
    return rows


def unbalanced_nodes(flows) -> list[dict]:
    return [r for r in node_balance(flows) if r["Status"] in ("Unallocated", "Over-allocated")]


def system_totals(flows) -> dict:
    """Total entering the system (from sources) vs leaving it (to sinks)."""
    rows = node_balance(flows)
    total_in = math.fsum(r["Outflow"] for r in rows if r["Status"] == "Source")
    total_out = math.fsum(r["Inflow"] for r in rows if r["Status"] == "Sink")
    diff = total_in - total_out
    if math.isclose(total_in, total_out, rel_tol=BALANCE_REL_TOL, abs_tol=BALANCE_ABS_TOL):
        diff = 0.0
    return {"entering": total_in, "leaving": total_out, "difference": diff}


# --------------------------------------------------------------------------
# Formatting
# --------------------------------------------------------------------------
def resolve_unit(choice: str, custom: str = "") -> str:
    """Turn the unit dropdown + custom box into the unit string to display."""
    if choice == "Custom…":
        return clean_name(custom)
    return choice


def format_value(value: float, unit: str = "") -> str:
    """1200 -> '$1,200' or '1,200 kWh'. Shows 2 decimals only if needed."""
    number = f"{value:,.0f}" if abs(value - round(value)) < 1e-9 else f"{value:,.2f}"
    if not unit:
        return number
    if unit in PREFIX_UNITS:
        return f"{unit}{number}"
    return f"{number} {unit}"
