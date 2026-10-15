"""Tests for modules/export.py."""

import pytest

from modules import export
from modules.chart import build_sankey
from modules.export import (
    ExportError,
    export_filename,
    figure_signature,
    figure_to_html,
    figure_to_image,
)


def F(s, t, v):
    return {"Source": s, "Target": t, "Value": float(v)}


FLOWS = [F("Supplier", "Plant", 100), F("Plant", "DC", 60), F("Plant", "Scrap", 40)]


def engine_works():
    try:
        figure_to_image(build_sankey(FLOWS), "png")
        return True
    except ExportError:
        return False


needs_engine = pytest.mark.skipif(not engine_works(), reason="kaleido not usable here")


@pytest.mark.parametrize(
    "title,ext,expected",
    [
        ("Monthly Budget Flow (illustrative)", "png", "monthly-budget-flow-illustrative.png"),
        ("  Plant / Energy  ", ".svg", "plant-energy.svg"),
        ("", "png", "flow-diagram.png"),
        ("***", "html", "flow-diagram.html"),
        ("Ünïcode ñame", "png", "n-code-ame.png"),
    ],
)
def test_export_filename(title, ext, expected):
    assert export_filename(title, ext) == expected


def test_signature_changes_with_flows_unit_and_title_only():
    base = figure_signature(FLOWS, "kg", "T")
    assert base == figure_signature([dict(f) for f in FLOWS], "kg", "T")
    assert base != figure_signature(FLOWS[:2], "kg", "T")
    assert base != figure_signature(FLOWS, "$", "T")
    assert base != figure_signature(FLOWS, "kg", "T2")
    assert base != figure_signature([F("Supplier", "Plant", 101)] + FLOWS[1:], "kg", "T")


def test_html_export_is_standalone_and_white_background():
    html = figure_to_html(build_sankey(FLOWS, "kg", "My title")).decode("utf-8")
    assert html.lstrip().lower().startswith("<html")
    assert "My title" in html and "sankey" in html
    assert "white" in html


def test_export_does_not_modify_the_on_screen_figure():
    fig = build_sankey(FLOWS)
    before = fig.to_json()
    figure_to_html(fig)
    assert fig.to_json() == before


def test_unsupported_format_raises_export_error():
    with pytest.raises(ExportError):
        figure_to_image(build_sankey(FLOWS), "gif")


def test_engine_failure_is_wrapped(monkeypatch):
    import plotly.graph_objects as go

    def boom(self, *a, **k):
        raise RuntimeError("chrome not found")

    monkeypatch.setattr(go.Figure, "to_image", boom)
    with pytest.raises(ExportError, match="chrome not found"):
        figure_to_image(build_sankey(FLOWS), "png")


@needs_engine
def test_png_export_is_a_real_png_at_expected_size():
    data = figure_to_image(build_sankey(FLOWS, "kg"), "png")
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    width = int.from_bytes(data[16:20], "big")
    height = int.from_bytes(data[20:24], "big")
    assert (width, height) == (export.EXPORT_WIDTH * export.EXPORT_SCALE,
                               export.EXPORT_HEIGHT * export.EXPORT_SCALE)


@needs_engine
def test_svg_export_is_svg_and_contains_labels():
    data = figure_to_image(build_sankey(FLOWS, "kg", "Plant flow"), "svg").decode("utf-8")
    assert "<svg" in data
    assert "Supplier" in data
