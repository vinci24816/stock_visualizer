from datetime import date
from decimal import Decimal

import pytest

from src.db.database import Database
from src.db.repositories import (
    FinancialMetricRepository,
    FinancialStatementRepository,
    PriceRepository,
)
from src.db.schema import Company, DailyPrice, FinancialStatement
from src.services.financial_metrics_calculator import FinancialMetricsCalculator
from src.services.metrics_service import MetricsService


@pytest.fixture
def service_parts():
    database = Database("sqlite:///:memory:")
    database.create_tables()
    statement_repository = FinancialStatementRepository(database)
    price_repository = PriceRepository(database)
    metric_repository = FinancialMetricRepository(database)
    service = MetricsService(
        statement_repository,
        price_repository,
        metric_repository,
        FinancialMetricsCalculator(),
    )
    with database.get_session() as session:
        session.add_all(
            [
                Company(code="67580", company_name="ソニーグループ"),
                Company(code="72030", company_name="トヨタ自動車"),
            ]
        )
    yield service, statement_repository, price_repository, metric_repository
    database.dispose()


def make_statement(code: str, disclosed_date: date) -> FinancialStatement:
    return FinancialStatement(
        code=code,
        fiscal_period="FY",
        disclosed_date=disclosed_date,
        fiscal_year_end=date(2025, 3, 31),
        net_sales=Decimal("1000"),
        operating_profit=Decimal("100"),
        profit=Decimal("60"),
        total_assets=Decimal("800"),
        equity=Decimal("300"),
        liabilities=Decimal("500"),
        eps=Decimal("200"),
        bps=Decimal("1000"),
        dividend=Decimal("50"),
    )


def test_calculate_for_code_calculates_and_saves_all_metrics(service_parts) -> None:
    service, statement_repository, price_repository, metric_repository = service_parts
    statement_repository.upsert_statements(
        [make_statement("72030", date(2025, 5, 8))]
    )
    price_repository.upsert_daily_prices(
        [
            DailyPrice(
                code="72030",
                date=date(2025, 5, 7),
                adjusted_close=Decimal("2000"),
            ),
            DailyPrice(
                code="72030",
                date=date(2025, 5, 9),
                adjusted_close=Decimal("3000"),
            ),
        ]
    )

    result = service.calculate_for_code(" 72030 ")
    saved = metric_repository.find_by_code("72030")

    assert len(result) == len(saved) == 1
    assert saved[0].price_date == date(2025, 5, 7)
    assert saved[0].roe == Decimal("0.2000000000")
    assert saved[0].roi == Decimal("0.1250000000")
    assert saved[0].per == Decimal("10.000000")
    assert saved[0].dividend_yield == Decimal("0.0250000000")


def test_calculate_for_code_saves_non_price_metrics_without_price(
    service_parts,
) -> None:
    service, statement_repository, _, metric_repository = service_parts
    statement_repository.upsert_statements(
        [make_statement("72030", date(2025, 5, 8))]
    )

    service.calculate_for_code("72030")
    saved = metric_repository.find_by_code("72030")[0]

    assert saved.roe == Decimal("0.2000000000")
    assert saved.price_date is None
    assert saved.per is None
    assert saved.pbr is None
    assert saved.dividend_yield is None


def test_calculate_for_codes_and_recalculate_all(service_parts) -> None:
    service, statement_repository, _, metric_repository = service_parts
    statement_repository.upsert_statements(
        [
            make_statement("67580", date(2025, 5, 8)),
            make_statement("72030", date(2025, 5, 8)),
        ]
    )

    calculated = service.calculate_for_codes(["72030", "67580", "72030"])
    recalculated = service.recalculate_all()

    assert len(calculated) == 2
    assert len(recalculated) == 2
    assert len(metric_repository.find_by_code("67580")) == 1
    assert len(metric_repository.find_by_code("72030")) == 1


def test_calculate_for_code_rejects_empty_code(service_parts) -> None:
    service, _, _, _ = service_parts

    with pytest.raises(ValueError, match="code"):
        service.calculate_for_code(" ")
