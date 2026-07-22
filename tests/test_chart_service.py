from datetime import date
from decimal import Decimal

import pandas as pd
import pytest

from src.db.schema import DailyPrice
from src.services.chart_service import ChartService


def test_create_price_line_chart_uses_adjusted_close() -> None:
    prices = [
        DailyPrice(
            code="72030",
            date=date(2025, 1, 7),
            close=Decimal("200"),
            adjusted_close=Decimal("100"),
        ),
        DailyPrice(
            code="72030",
            date=date(2025, 1, 6),
            close=Decimal("180"),
            adjusted_close=Decimal("90"),
        ),
    ]

    figure = ChartService().create_price_line_chart(prices)

    assert list(figure.data[0].x) == [date(2025, 1, 6), date(2025, 1, 7)]
    assert list(figure.data[0].y) == [Decimal("90"), Decimal("100")]
    assert figure.data[0].name == "調整後終値"


def test_create_metric_line_chart_formats_percentage() -> None:
    metrics = pd.DataFrame(
        [
            {"code": "72030", "fiscal_period": "2024", "roe": 0.10},
            {"code": "72030", "fiscal_period": "2025", "roe": 0.12},
        ]
    )

    figure = ChartService().create_metric_line_chart(metrics, "ROE")

    assert list(figure.data[0].y) == [0.10, 0.12]
    assert figure.layout.yaxis.tickformat == ".1%"
    assert "72030" in figure.layout.title.text


def test_create_comparison_chart_filters_and_orders_codes() -> None:
    metrics = pd.DataFrame(
        [
            {"code": "72030", "fiscal_period": "2025", "pbr": 1.2},
            {"code": "67580", "fiscal_period": "2025", "pbr": 2.1},
            {"code": "99990", "fiscal_period": "2025", "pbr": 0.8},
        ]
    )

    figure = ChartService().create_comparison_chart(
        metrics,
        ["67580", "72030"],
        "pbr",
    )

    assert [trace.name for trace in figure.data] == ["67580", "72030"]
    assert [list(trace.y) for trace in figure.data] == [[2.1], [1.2]]


def test_empty_data_returns_annotated_figure() -> None:
    figure = ChartService().create_metric_line_chart(pd.DataFrame(), "roe")

    assert len(figure.data) == 0
    assert figure.layout.annotations[0].text == "財務指標データがありません"


def test_missing_metric_column_raises_error() -> None:
    metrics = pd.DataFrame([{"code": "72030", "fiscal_period": "2025"}])

    with pytest.raises(ValueError, match="roe"):
        ChartService().create_metric_line_chart(metrics, "roe")
