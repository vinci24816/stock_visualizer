from datetime import date
from decimal import Decimal

import pytest

from src.db.database import Database
from src.db.repositories import FinancialMetricRepository
from src.db.schema import Company, FinancialMetric, FinancialStatement


@pytest.fixture
def repository() -> FinancialMetricRepository:
    database = Database("sqlite:///:memory:")
    database.create_tables()
    with database.get_session() as session:
        session.add_all(
            [
                Company(code="67580", company_name="ソニーグループ"),
                Company(code="72030", company_name="トヨタ自動車"),
            ]
        )
        for code in ("67580", "72030"):
            for disclosed_date, fiscal_year_end in (
                (date(2025, 5, 8), date(2025, 3, 31)),
                (date(2025, 8, 7), date(2026, 3, 31)),
            ):
                session.add(
                    FinancialStatement(
                        code=code,
                        fiscal_period="FY",
                        disclosed_date=disclosed_date,
                        fiscal_year_end=fiscal_year_end,
                    )
                )

    value = FinancialMetricRepository(database)
    yield value
    database.dispose()


def make_metric(
    code: str,
    disclosed_date: date,
    *,
    fiscal_year_end: date,
    roe: Decimal | None = None,
    roa: Decimal | None = None,
) -> FinancialMetric:
    return FinancialMetric(
        code=code,
        fiscal_period="FY",
        disclosed_date=disclosed_date,
        fiscal_year_end=fiscal_year_end,
        roe=roe,
        roa=roa,
    )


def test_upsert_metrics_inserts_and_updates(
    repository: FinancialMetricRepository,
) -> None:
    repository.upsert_metrics(
        [
            make_metric(
                "72030",
                date(2025, 5, 8),
                fiscal_year_end=date(2025, 3, 31),
                roe=Decimal("0.10"),
            )
        ]
    )
    repository.upsert_metrics(
        [
            make_metric(
                "72030",
                date(2025, 5, 8),
                fiscal_year_end=date(2025, 3, 31),
                roe=Decimal("0.20"),
            )
        ]
    )

    metrics = repository.find_by_code("72030")

    assert len(metrics) == 1
    assert metrics[0].roe == Decimal("0.2000000000")


def test_find_by_code_filters_and_orders_metrics(
    repository: FinancialMetricRepository,
) -> None:
    repository.upsert_metrics(
        [
            make_metric(
                "72030",
                date(2025, 8, 7),
                fiscal_year_end=date(2026, 3, 31),
                roe=Decimal("0.20"),
            ),
            make_metric(
                "72030",
                date(2025, 5, 8),
                fiscal_year_end=date(2025, 3, 31),
                roe=Decimal("0.10"),
            ),
        ]
    )

    metrics = repository.find_by_code(
        " 72030 ",
        from_date=date(2025, 5, 1),
        to_date=date(2025, 8, 7),
    )

    assert [item.disclosed_date for item in metrics] == [
        date(2025, 5, 8),
        date(2025, 8, 7),
    ]


def test_find_by_metric_returns_only_non_null_values(
    repository: FinancialMetricRepository,
) -> None:
    repository.upsert_metrics(
        [
            make_metric(
                "72030",
                date(2025, 5, 8),
                fiscal_year_end=date(2025, 3, 31),
                roe=Decimal("0.20"),
            ),
            make_metric(
                "67580",
                date(2025, 5, 8),
                fiscal_year_end=date(2025, 3, 31),
                roa=Decimal("0.05"),
            ),
        ]
    )

    metrics = repository.find_by_metric(" ROE ")

    assert [item.code for item in metrics] == ["72030"]


def test_find_by_metric_rejects_unknown_metric(
    repository: FinancialMetricRepository,
) -> None:
    with pytest.raises(ValueError, match="metric_name"):
        repository.find_by_metric("unknown")


def test_repository_rejects_reversed_period(
    repository: FinancialMetricRepository,
) -> None:
    with pytest.raises(ValueError, match="from_date"):
        repository.find_by_code(
            "72030",
            from_date=date(2025, 8, 7),
            to_date=date(2025, 5, 8),
        )
