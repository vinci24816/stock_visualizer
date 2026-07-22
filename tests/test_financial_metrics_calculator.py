from datetime import date
from decimal import Decimal

from src.db.schema import DailyPrice, FinancialStatement
from src.services.financial_metrics_calculator import FinancialMetricsCalculator


def make_statement(**overrides) -> FinancialStatement:
    values = {
        "code": "72030",
        "fiscal_period": "FY",
        "disclosed_date": date(2025, 5, 8),
        "net_sales": Decimal("1000"),
        "operating_profit": Decimal("100"),
        "profit": Decimal("60"),
        "total_assets": Decimal("800"),
        "equity": Decimal("300"),
        "liabilities": Decimal("500"),
        "eps": Decimal("200"),
        "bps": Decimal("1000"),
        "dividend": Decimal("50"),
    }
    values.update(overrides)
    return FinancialStatement(**values)


def test_statement_metrics_are_returned_as_ratios() -> None:
    calculator = FinancialMetricsCalculator()
    statement = make_statement()

    assert calculator.calculate_equity_ratio(statement) == Decimal("0.375")
    assert calculator.calculate_roe(statement) == Decimal("0.2")
    assert calculator.calculate_roa(statement) == Decimal("0.075")
    assert calculator.calculate_roi(statement) == Decimal("0.125")
    assert calculator.calculate_operating_margin(statement) == Decimal("0.1")


def test_price_metrics_use_adjusted_close_first() -> None:
    calculator = FinancialMetricsCalculator()
    price = DailyPrice(
        code="72030",
        date=date(2025, 5, 8),
        close=Decimal("2100"),
        adjusted_close=Decimal("2000"),
    )

    metrics = calculator.calculate_price_metrics(make_statement(), price)

    assert metrics == {
        "per": Decimal("10"),
        "pbr": Decimal("2"),
        "dividend_yield": Decimal("0.025"),
    }


def test_price_metrics_fall_back_to_close() -> None:
    calculator = FinancialMetricsCalculator()
    price = DailyPrice(
        code="72030",
        date=date(2025, 5, 8),
        close=Decimal("2000"),
    )

    assert calculator.calculate_price_metrics(make_statement(), price)["per"] == 10


def test_metrics_return_none_for_missing_or_zero_denominator() -> None:
    calculator = FinancialMetricsCalculator()
    statement = make_statement(
        total_assets=Decimal("0"),
        equity=None,
        liabilities=None,
        net_sales=None,
        eps=Decimal("0"),
        bps=None,
        dividend=None,
    )
    price = DailyPrice(
        code="72030",
        date=date(2025, 5, 8),
        close=None,
    )

    assert calculator.calculate_equity_ratio(statement) is None
    assert calculator.calculate_roe(statement) is None
    assert calculator.calculate_roa(statement) is None
    assert calculator.calculate_roi(statement) is None
    assert calculator.calculate_operating_margin(statement) is None
    assert calculator.calculate_price_metrics(statement, price) == {
        "per": None,
        "pbr": None,
        "dividend_yield": None,
    }
