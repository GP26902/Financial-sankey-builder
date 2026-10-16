"""Sample datasets and engineering templates.

Every preset is illustrative, not real data. Each one carries:
  unit         unit shown on the chart (must be in flows.UNIT_CHOICES)
  title        default chart title
  flows        starting Source -> Target -> Value rows
  suggestions  extra names offered in the Source / Target dropdowns
  category     "Engineering", "Finance" or "Blank" (used for ordering/labels)
  kpis         optional list of KPI specs (see modules/kpis.py), shown as
               metrics under the balance check
  description  one or two sentences shown above the chart: what the diagram
               represents and how to read it

To add a template: append an entry to PRESETS (name must contain
"illustrative"), then run `pytest`. tests/test_chart.py checks that every
engineering template is a valid, loop-free, balanced flow set.
"""

from __future__ import annotations

from .kpis import ENTERING

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
        "kpis": [
            {
                "label": "Overall yield",
                "numerator": "Finished goods shipped",
                "denominator": ENTERING,
                "help": "Finished goods shipped ÷ material purchased.",
            },
            {
                "label": "Scrap recovery",
                "numerator": "Sold to recycler",
                "denominator": "Scrap collected",
                "help": "Scrap sold to a recycler ÷ all scrap collected.",
            },
        ],
        "suggestions": [
            "Purchased steel", "Purchased aluminium", "Receiving & inspection",
            "Returned to supplier", "Cutting", "Blanking", "Stamping", "Machining",
            "Welding", "Heat treatment", "Finishing", "Painting", "Assembly",
            "Final inspection", "Rework", "Scrap collected", "Sold to recycler",
            "Disposal (landfill)", "Finished goods shipped", "Work in progress",
        ],
    },
    "Supply chain network (illustrative)": {
        "category": "Engineering",
        "unit": "units",
        "title": "Supply Chain Network, One Plant and Two Distribution Centres (illustrative)",
        "description": (
            "Follows 100,000 units (finished-unit equivalents, one month) from three "
            "suppliers through inbound freight, receiving and the assembly plant. "
            "Plant output goes either direct to customers or through an East or West "
            "distribution centre (DC). Losses leave as returns to suppliers and "
            "production scrap; stock built up in the DCs is shown as its own link. "
            "Every node should balance: units in = units out."
        ),
        "flows": [
            {"Source": "Supplier A (domestic)", "Target": "Inbound truck freight", "Value": 50000.0},
            {"Source": "Supplier B (regional)", "Target": "Inbound truck freight", "Value": 30000.0},
            {"Source": "Supplier C (overseas)", "Target": "Inbound ocean freight", "Value": 20000.0},
            {"Source": "Inbound truck freight", "Target": "Receiving & inspection", "Value": 80000.0},
            {"Source": "Inbound ocean freight", "Target": "Receiving & inspection", "Value": 20000.0},
            {"Source": "Receiving & inspection", "Target": "Returned to supplier", "Value": 1500.0},
            {"Source": "Receiving & inspection", "Target": "Assembly plant", "Value": 98500.0},
            {"Source": "Assembly plant", "Target": "Production scrap", "Value": 2500.0},
            {"Source": "Assembly plant", "Target": "Plant shipments", "Value": 96000.0},
            {"Source": "Plant shipments", "Target": "Direct to customers", "Value": 24000.0},
            {"Source": "Plant shipments", "Target": "East distribution centre", "Value": 40000.0},
            {"Source": "Plant shipments", "Target": "West distribution centre", "Value": 32000.0},
            {"Source": "Direct to customers", "Target": "Industrial customers", "Value": 18000.0},
            {"Source": "Direct to customers", "Target": "Retail customers", "Value": 6000.0},
            {"Source": "East distribution centre", "Target": "Retail customers", "Value": 18000.0},
            {"Source": "East distribution centre", "Target": "E-commerce customers", "Value": 10000.0},
            {"Source": "East distribution centre", "Target": "Industrial customers", "Value": 9000.0},
            {"Source": "East distribution centre", "Target": "Added to DC stock", "Value": 3000.0},
            {"Source": "West distribution centre", "Target": "Retail customers", "Value": 12000.0},
            {"Source": "West distribution centre", "Target": "E-commerce customers", "Value": 11000.0},
            {"Source": "West distribution centre", "Target": "Industrial customers", "Value": 7000.0},
            {"Source": "West distribution centre", "Target": "Added to DC stock", "Value": 2000.0},
        ],
        "kpis": [
            {
                "label": "Share shipped direct",
                "numerator": "Direct to customers",
                "denominator": "Plant shipments",
                "help": "Units shipped from the plant straight to customers ÷ all units shipped from the plant.",
            },
            {
                "label": "Inbound acceptance",
                "numerator": "Assembly plant",
                "denominator": "Receiving & inspection",
                "help": "Units accepted into the plant ÷ units received from suppliers (the rest is returned).",
            },
        ],
        "suggestions": [
            "Supplier A (domestic)", "Supplier B (regional)", "Supplier C (overseas)",
            "Inbound truck freight", "Inbound ocean freight", "Inbound air freight",
            "Receiving & inspection", "Returned to supplier", "Assembly plant",
            "Production scrap", "Plant shipments", "Direct to customers",
            "East distribution centre", "West distribution centre",
            "Added to DC stock", "Retail customers", "Industrial customers",
            "E-commerce customers",
        ],
    },
    "Plant energy flow (illustrative)": {
        "category": "Engineering",
        "unit": "MWh",
        "title": "Plant Energy Flow, Metal Parts Plant, One Month (illustrative)",
        "description": (
            "Follows 4,000 MWh of energy bought in one month (2,400 MWh grid "
            "electricity and 1,600 MWh natural gas, counted as thermal energy). "
            "Energy passes through electrical distribution and the utilities "
            "(boiler and steam, compressed air, chilled water) to three production "
            "areas and building services. What is not used leaves as distribution "
            "and leak losses, idle and standby losses, or waste heat. Wide loss "
            "links show where energy is wasted; every node should balance: "
            "MWh in = MWh out."
        ),
        "flows": [
            {"Source": "Grid electricity", "Target": "Electrical distribution", "Value": 2400.0},
            {"Source": "Electrical distribution", "Target": "Distribution & leak losses", "Value": 70.0},
            {"Source": "Electrical distribution", "Target": "Compressed air", "Value": 600.0},
            {"Source": "Electrical distribution", "Target": "Chilled water", "Value": 300.0},
            {"Source": "Electrical distribution", "Target": "Machining", "Value": 700.0},
            {"Source": "Electrical distribution", "Target": "Heat treatment & paint ovens", "Value": 250.0},
            {"Source": "Electrical distribution", "Target": "Assembly & packaging", "Value": 250.0},
            {"Source": "Electrical distribution", "Target": "Building services (lighting & HVAC)", "Value": 230.0},
            {"Source": "Natural gas", "Target": "Boiler / steam plant", "Value": 1200.0},
            {"Source": "Natural gas", "Target": "Heat treatment & paint ovens", "Value": 400.0},
            {"Source": "Boiler / steam plant", "Target": "Waste heat", "Value": 180.0},
            {"Source": "Boiler / steam plant", "Target": "Process steam", "Value": 1020.0},
            {"Source": "Process steam", "Target": "Distribution & leak losses", "Value": 70.0},
            {"Source": "Process steam", "Target": "Machining", "Value": 150.0},
            {"Source": "Process steam", "Target": "Heat treatment & paint ovens", "Value": 600.0},
            {"Source": "Process steam", "Target": "Building services (lighting & HVAC)", "Value": 200.0},
            {"Source": "Compressed air", "Target": "Waste heat", "Value": 300.0},
            {"Source": "Compressed air", "Target": "Distribution & leak losses", "Value": 90.0},
            {"Source": "Compressed air", "Target": "Machining", "Value": 120.0},
            {"Source": "Compressed air", "Target": "Assembly & packaging", "Value": 90.0},
            {"Source": "Chilled water", "Target": "Waste heat", "Value": 100.0},
            {"Source": "Chilled water", "Target": "Distribution & leak losses", "Value": 20.0},
            {"Source": "Chilled water", "Target": "Machining", "Value": 80.0},
            {"Source": "Chilled water", "Target": "Building services (lighting & HVAC)", "Value": 100.0},
            {"Source": "Machining", "Target": "Useful process energy", "Value": 650.0},
            {"Source": "Machining", "Target": "Idle & standby losses", "Value": 250.0},
            {"Source": "Machining", "Target": "Waste heat", "Value": 150.0},
            {"Source": "Heat treatment & paint ovens", "Target": "Useful process energy", "Value": 730.0},
            {"Source": "Heat treatment & paint ovens", "Target": "Idle & standby losses", "Value": 150.0},
            {"Source": "Heat treatment & paint ovens", "Target": "Waste heat", "Value": 370.0},
            {"Source": "Assembly & packaging", "Target": "Useful process energy", "Value": 220.0},
            {"Source": "Assembly & packaging", "Target": "Idle & standby losses", "Value": 80.0},
            {"Source": "Assembly & packaging", "Target": "Waste heat", "Value": 40.0},
        ],
        "kpis": [
            {
                "label": "Share used in production",
                "numerator": "Useful process energy",
                "denominator": ENTERING,
                "help": "Energy that ends up as useful process energy in the production areas ÷ all energy purchased.",
            },
            {
                "label": "Boiler efficiency",
                "numerator": "Process steam",
                "denominator": "Boiler / steam plant",
                "help": "Steam sent to the plant ÷ natural gas burned in the boiler (the rest leaves as waste heat).",
            },
        ],
        "suggestions": [
            "Grid electricity", "Natural gas", "Solar PV (on-site)",
            "Electrical distribution", "Boiler / steam plant", "Process steam",
            "Compressed air", "Chilled water", "Machining", "Welding",
            "Heat treatment & paint ovens", "Assembly & packaging",
            "Building services (lighting & HVAC)", "Useful process energy",
            "Distribution & leak losses", "Idle & standby losses", "Waste heat",
        ],
    },
    "Machine / process energy balance (illustrative)": {
        "category": "Engineering",
        "unit": "kWh",
        "title": "Machine Energy Balance, CNC Machining Centre, One 8-Hour Shift (illustrative)",
        "description": (
            "Follows 200 kWh of electricity into ONE machine, a CNC machining "
            "centre, over one 8-hour shift (an average draw of 25 kW). The energy "
            "is split between the subsystems (spindle and axis drives, hydraulic "
            "unit, coolant pump, chiller, controls and auxiliaries) and ends as "
            "useful cutting and clamping work or as one of three losses: heat to "
            "chips and coolant, friction, drive and conversion losses, and idle "
            "and standby consumption. Wide loss links show where to save energy; "
            "every node should balance: kWh in = kWh out. For a furnace, rename "
            "the subsystems and add a gas source."
        ),
        "flows": [
            {"Source": "Electrical input", "Target": "Spindle & axis drives", "Value": 100.0},
            {"Source": "Electrical input", "Target": "Hydraulic unit", "Value": 25.0},
            {"Source": "Electrical input", "Target": "Coolant pump", "Value": 20.0},
            {"Source": "Electrical input", "Target": "Chiller", "Value": 30.0},
            {"Source": "Electrical input", "Target": "Controls & auxiliaries", "Value": 25.0},
            {"Source": "Spindle & axis drives", "Target": "Useful cutting & clamping work", "Value": 30.0},
            {"Source": "Spindle & axis drives", "Target": "Friction, drive & conversion losses", "Value": 22.0},
            {"Source": "Spindle & axis drives", "Target": "Idle & standby losses", "Value": 28.0},
            {"Source": "Spindle & axis drives", "Target": "Heat to chips & coolant", "Value": 20.0},
            {"Source": "Hydraulic unit", "Target": "Useful cutting & clamping work", "Value": 5.0},
            {"Source": "Hydraulic unit", "Target": "Friction, drive & conversion losses", "Value": 8.0},
            {"Source": "Hydraulic unit", "Target": "Idle & standby losses", "Value": 12.0},
            {"Source": "Coolant pump", "Target": "Useful cutting & clamping work", "Value": 6.0},
            {"Source": "Coolant pump", "Target": "Friction, drive & conversion losses", "Value": 4.0},
            {"Source": "Coolant pump", "Target": "Idle & standby losses", "Value": 6.0},
            {"Source": "Coolant pump", "Target": "Heat to chips & coolant", "Value": 4.0},
            {"Source": "Chiller", "Target": "Heat to chips & coolant", "Value": 20.0},
            {"Source": "Chiller", "Target": "Friction, drive & conversion losses", "Value": 4.0},
            {"Source": "Chiller", "Target": "Idle & standby losses", "Value": 6.0},
            {"Source": "Controls & auxiliaries", "Target": "Useful cutting & clamping work", "Value": 5.0},
            {"Source": "Controls & auxiliaries", "Target": "Friction, drive & conversion losses", "Value": 6.0},
            {"Source": "Controls & auxiliaries", "Target": "Idle & standby losses", "Value": 14.0},
        ],
        "kpis": [
            {
                "label": "Share doing useful work",
                "numerator": "Useful cutting & clamping work",
                "denominator": ENTERING,
                "help": "Energy that ends up as useful cutting and clamping work ÷ all electricity entering the machine.",
            },
            {
                "label": "Share lost to idle & standby",
                "numerator": "Idle & standby losses",
                "denominator": ENTERING,
                "help": "Energy used while the machine is not cutting (spindle spinning, pumps running, controls on) ÷ all electricity entering the machine.",
            },
        ],
        "suggestions": [
            "Electrical input", "Natural gas", "Compressed air",
            "Spindle & axis drives", "Hydraulic unit", "Coolant pump", "Chiller",
            "Controls & auxiliaries", "Chip conveyor", "Furnace burners",
            "Circulation fans", "Quench system",
            "Useful cutting & clamping work", "Heat to chips & coolant", "Friction, drive & conversion losses", "Idle & standby losses",
        ],
    },
    "Manufacturing cost flow (illustrative)": {
        "category": "Engineering",
        "unit": "$",
        "title": "Manufacturing Cost Flow, Metal Parts Plant, One Month (illustrative)",
        "description": (
            "Follows $650,000 of manufacturing cost in one month: $400,000 of "
            "purchased materials, $150,000 of direct labour and $100,000 of "
            "overhead. The cost is charged to three production work centres "
            "(treated as parallel cost centres to keep the diagram simple). "
            "Each work centre's cost ends as finished goods cost, as scrap and "
            "rework cost, or as other losses (idle time and shrinkage). Finished "
            "goods cost is either shipped (cost of goods sold) or added to "
            "inventory. Wide loss links show where money is wasted; every node "
            "should balance: $ in = $ out."
        ),
        "flows": [
            {"Source": "Purchased materials", "Target": "Machining", "Value": 180000.0},
            {"Source": "Purchased materials", "Target": "Welding & fabrication", "Value": 120000.0},
            {"Source": "Purchased materials", "Target": "Assembly & test", "Value": 100000.0},
            {"Source": "Direct labour", "Target": "Machining", "Value": 50000.0},
            {"Source": "Direct labour", "Target": "Welding & fabrication", "Value": 45000.0},
            {"Source": "Direct labour", "Target": "Assembly & test", "Value": 55000.0},
            {"Source": "Manufacturing overhead", "Target": "Machining", "Value": 45000.0},
            {"Source": "Manufacturing overhead", "Target": "Welding & fabrication", "Value": 25000.0},
            {"Source": "Manufacturing overhead", "Target": "Assembly & test", "Value": 30000.0},
            {"Source": "Machining", "Target": "Finished goods cost", "Value": 233000.0},
            {"Source": "Machining", "Target": "Scrap & rework cost", "Value": 26000.0},
            {"Source": "Machining", "Target": "Other losses (idle time & shrinkage)", "Value": 16000.0},
            {"Source": "Welding & fabrication", "Target": "Finished goods cost", "Value": 160000.0},
            {"Source": "Welding & fabrication", "Target": "Scrap & rework cost", "Value": 18500.0},
            {"Source": "Welding & fabrication", "Target": "Other losses (idle time & shrinkage)", "Value": 11500.0},
            {"Source": "Assembly & test", "Target": "Finished goods cost", "Value": 163000.0},
            {"Source": "Assembly & test", "Target": "Scrap & rework cost", "Value": 14000.0},
            {"Source": "Assembly & test", "Target": "Other losses (idle time & shrinkage)", "Value": 8000.0},
            {"Source": "Finished goods cost", "Target": "Shipped to customers (COGS)", "Value": 520000.0},
            {"Source": "Finished goods cost", "Target": "Added to finished goods inventory", "Value": 36000.0},
            {"Source": "Scrap & rework cost", "Target": "Scrap written off", "Value": 36000.0},
            {"Source": "Scrap & rework cost", "Target": "Rework cost (extra labour & materials)", "Value": 22500.0},
        ],
        "kpis": [
            {
                "label": "Share shipped as good product",
                "numerator": "Shipped to customers (COGS)",
                "denominator": ENTERING,
                "help": "Cost of good product shipped to customers ÷ total manufacturing cost for the month.",
            },
            {
                "label": "Share lost to scrap & rework",
                "numerator": "Scrap & rework cost",
                "denominator": ENTERING,
                "help": "Cost of scrapped and reworked product ÷ total manufacturing cost for the month.",
            },
        ],
        "suggestions": [
            "Purchased materials", "Direct labour", "Manufacturing overhead",
            "Purchased components", "Indirect labour", "Utilities & maintenance",
            "Machining", "Welding & fabrication", "Heat treatment", "Painting & finishing",
            "Assembly & test", "Finished goods cost", "Shipped to customers (COGS)",
            "Added to finished goods inventory", "Scrap & rework cost", "Scrap written off",
            "Rework cost (extra labour & materials)", "Other losses (idle time & shrinkage)",
            "Warranty & returns",
        ],
    },
    "Machine time / OEE losses (illustrative)": {
        "category": "Engineering",
        "unit": "hours",
        "title": "Machine Time & OEE Losses, CNC Machining Line, One Week (illustrative)",
        "description": (
            "Follows 120 hours of scheduled time on ONE machine line (three 8-hour "
            "shifts, five days) down to fully productive time. Planned stops "
            "(breaks, meetings, planned maintenance) come out first, which leaves "
            "planned production time. The OEE losses are then taken in order: "
            "availability losses (breakdowns, changeovers, waiting), performance "
            "losses (slow cycles, minor stops) and quality losses (scrap, rework). "
            "What is left is the time the machine spent making good parts at full "
            "speed. OEE is measured against planned production time, so planned "
            "stops do not count against it; every node should balance: hours in "
            "= hours out."
        ),
        "flows": [
            {"Source": "Scheduled time", "Target": "Planned stops", "Value": 12.0},
            {"Source": "Scheduled time", "Target": "Planned production time", "Value": 108.0},
            {"Source": "Planned stops", "Target": "Breaks & meetings", "Value": 7.0},
            {"Source": "Planned stops", "Target": "Planned maintenance", "Value": 5.0},
            {"Source": "Planned production time", "Target": "Availability losses", "Value": 16.0},
            {"Source": "Planned production time", "Target": "Operating time", "Value": 92.0},
            {"Source": "Availability losses", "Target": "Breakdowns", "Value": 6.0},
            {"Source": "Availability losses", "Target": "Changeovers & setup", "Value": 8.0},
            {"Source": "Availability losses", "Target": "Waiting for material or operator", "Value": 2.0},
            {"Source": "Operating time", "Target": "Performance losses", "Value": 12.0},
            {"Source": "Operating time", "Target": "Net operating time", "Value": 80.0},
            {"Source": "Performance losses", "Target": "Slow cycles (reduced speed)", "Value": 7.0},
            {"Source": "Performance losses", "Target": "Minor stops & idling", "Value": 5.0},
            {"Source": "Net operating time", "Target": "Quality losses", "Value": 4.0},
            {"Source": "Net operating time", "Target": "Fully productive time", "Value": 76.0},
            {"Source": "Quality losses", "Target": "Scrap (time making rejects)", "Value": 2.5},
            {"Source": "Quality losses", "Target": "Rework (time re-making parts)", "Value": 1.5},
        ],
        "kpis": [
            {
                "label": "OEE",
                "numerator": "Fully productive time",
                "denominator": "Planned production time",
                "help": "Fully productive time ÷ planned production time (planned stops are excluded, the usual OEE definition).",
            },
            {
                "label": "Availability",
                "numerator": "Operating time",
                "denominator": "Planned production time",
                "help": "Time the machine was actually running ÷ planned production time (breakdowns, changeovers and waiting are the losses).",
            },
        ],
        "suggestions": [
            "Scheduled time", "Calendar time", "Planned stops", "Breaks & meetings",
            "Planned maintenance", "Planned production time", "Availability losses",
            "Breakdowns", "Changeovers & setup", "Waiting for material or operator",
            "Operating time", "Performance losses", "Slow cycles (reduced speed)",
            "Minor stops & idling", "Net operating time", "Quality losses",
            "Scrap (time making rejects)", "Rework (time re-making parts)",
            "Fully productive time",
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
        "kpis": [dict(k) for k in p.get("kpis", [])],
        "flows": [dict(f) for f in p["flows"]],
        "suggestions": list(p["suggestions"]),
    }
