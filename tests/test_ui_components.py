from datetime import date

import pytest

from src.db.schema import DailyPrice
from src.services.chart_service import ChartService

pytest.importorskip("streamlit")

from src.ui import components


def test_render_price_section_displays_price_chart(monkeypatch) -> None:
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        components.st,
        "subheader",
        lambda title: captured.update(title=title),
    )
    monkeypatch.setattr(
        components.st,
        "info",
        lambda message: captured.update(info=message),
    )
    monkeypatch.setattr(
        components.st,
        "plotly_chart",
        lambda figure, **kwargs: captured.update(figure=figure, kwargs=kwargs),
    )

    prices = [
        DailyPrice(
            code="72030",
            trade_date=date(2024, 1, 4),
            open=2600.0,
            high=2650.0,
            low=2580.0,
            close=2630.0,
            volume=1_000_000,
        )
    ]

    components.render_price_section(" 72030 ", prices, ChartService())

    assert captured["title"] == "72030 株価推移"
    assert "info" not in captured
    assert len(captured["figure"].data) == 1
    assert captured["kwargs"] == {
        "width": "stretch",
        "key": "price-chart-72030",
    }


def test_render_price_section_displays_message_when_prices_are_empty(
    monkeypatch,
) -> None:
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        components.st,
        "subheader",
        lambda title: captured.update(title=title),
    )
    monkeypatch.setattr(
        components.st,
        "info",
        lambda message: captured.update(info=message),
    )
    monkeypatch.setattr(
        components.st,
        "plotly_chart",
        lambda *args, **kwargs: captured.update(chart_rendered=True),
    )

    components.render_price_section("72030", [], ChartService())

    assert captured["title"] == "72030 株価推移"
    assert "株価データがありません" in captured["info"]
    assert "chart_rendered" not in captured
