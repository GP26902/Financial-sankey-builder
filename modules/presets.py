"""Sample datasets. Every preset is illustrative, not real data."""

from __future__ import annotations

PRESETS = {
    "Personal budget (illustrative)": {
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
        "flows": [dict(f) for f in p["flows"]],
        "suggestions": list(p["suggestions"]),
    }
