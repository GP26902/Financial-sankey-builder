"""Sample datasets and engineering templates.

Every preset is illustrative, not real data. Each one carries:
  unit         unit shown on the chart (must be in flows.UNIT_CHOICES)
  title        default chart title
  flows        starting Source -> Target -> Value rows
  suggestions  extra names offered in the Source / Target dropdowns
  category     "Engineering", "Finance" or "Blank" (used for ordering/labels)
  description  one or two sentences shown above the chart: what the diagram
               represents and how to read it

To add a template: append an entry to PRESETS (name must contain
"illustrative"), then run `pytest`. tests/test_chart.py checks that every
engineering template is a valid, loop-free, balanced flow set.
"""

from __future__ import annotations

PRESETS = {
    "Plant material flow & scrap (illustrative)": {
        "category": "Engineering",
        "unit": "kg",
        "title": "Plant Material Flow & Scrap, Steel Fabrication Line (illustrative)",
        "description": (
            "Follows 50,000 kg of purchased steel through a fabrication line "
            "(receiving, blanking, stamping, welding, finishing, final inspection). "
            "Material that is not shipped leaves as rejected stock, recycled scrap "
            "or disposal. Wide scrap links show where yield is lost; every stage "
            "should balance: kg in = kg good out + kg scrapped."
        ),
        "flows": [
            {"Source": "Purchased steel", "Target": "Receiving & inspection", "Value": 50000.0},
            {"Source": "Receiving & inspection", "Target": "Returned to supplier", "Value": 500.0},
            {"Source": "Receiving & inspection", "Target": "Blanking", "Value": 49500.0},
            {"Source": "Blanking", "Target": "Scrap collected", "Value": 4950.0},
            {"Source": "Blanking", "Target": "Stamping", "Value": 44550.0},
            {"Source": "Stamping", "Target": "Scrap collected", "Value": 1550.0},
            {"Source": "Stamping", "Target": "Welding", "Value": 43000.0},
            {"Source": "Welding", "Target": "Scrap collected", "Value": 1000.0},
            {"Source": "Welding", "Target": "Finishing", "Value": 42000.0},
            {"Source": "Finishing", "Target": "Scrap collected", "Value": 700.0},
            {"Source": "Finishing", "Target": "Final inspection", "Value": 41300.0},
            {"Source": "Final inspection", "Target": "Scrap collected", "Value": 800.0},
            {"Source": "Final inspection", "Target": "Finished goods shipped", "Value": 40500.0},
            {"Source": "Scrap collected", "Target": "Sold to recycler", "Value": 7650.0},
            {"Source": "Scrap collected", "Target": "Disposal (landfill)", "Value": 1350.0},
        ],
        "suggestions": [
            "Purchased steel", "Purchased aluminium", "Receiving & inspection",
            "Returned to supplier", "Cutting", "Blanking", "Stamping", "Machining",
            "Welding", "Heat treatment", "Finishing", "Painting", "Assembly",
            "Final inspection", "Rework", "Scrap collected", "Sold to recycler",
            "Disposal (landfill)", "Finished goods shipped", "Work in progress",
        ],
    },
    "Personal budget (illustrative)": {
        "category": "Finance",
        "description": (
            "Monthly spending by category. Months are the sources and spending "
            "categories are the sinks, so there is nothing to balance between them."
        ),
        "unit": "$",
        "title": "Monthly Budget Flow (illustrative)",
        "flows": [
            {"Source": "January", "Target": "Housing", "Value": 2000.0},
            {"Source": "January", "Target": "Groceries", "Value": 500.0},
            {"Source": "January", "Target": "Utilities", "Value": 300.0},
            {"Source": "February", "Target": "Housing", "Value": 2000.0},
            {"Source": "February", "Target": "Groceries", "Value": 600.0},
            {"Source": "February", "Target": "Utilities", "Value": 250.0},
        ],
        # Extra names offered in the Source/Target dropdowns.
        "suggestions": [
            "Salary", "Business Income", "Side Hustle", "Taxes", "Housing",
            "Utilities", "Groceries", "Dining & Coffee", "Transportation",
            "Savings & Investments", "Miscellaneous",
        ],
    },
    "Blank canvas": {
        "category": "Blank",
        "description": "",
        "unit": "$",
        "title": "Flow breakdown",
        "flows": [],
        "suggestions": [],
    },
}

DEFAULT_PRESET = "Personal budget (illustrative)"


def get_preset(name: str) -> dict:
    """Return a deep-enough copy so callers can't mutate the master data."""
    p = PRESETS[name]
    return {
        "unit": p["unit"],
        "title": p["title"],
        "category": p.get("category", ""),
        "description": p.get("description", ""),
        "flows": [dict(f) for f in p["flows"]],
        "suggestions": list(p["suggestions"]),
    }
