"""Tests for modules/export.py."""

import pytest

from modules.export import export_filename


@pytest.mark.parametrize(
    "title,ext,expected",
    [
        ("Monthly Budget Flow (illustrative)", "png", "monthly-budget-flow-illustrative.png"),
        ("  Plant / Energy  ", ".svg", "plant-energy.svg"),
        ("", "png", "flow-diagram.png"),
        ("***", "png", "flow-diagram.png"),
        ("Ünïcode ñame", "png", "n-code-ame.png"),
    ],
)
def test_export_filename(title, ext, expected):
    assert export_filename(title, ext) == expected
