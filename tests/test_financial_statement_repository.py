from datetime import date
from decimal import Decimal

import pytest

from src.db.database import Database
from src.db.repositories import FinancialStatementRepository
from src.db.schema import Company, FinancialStatement


@pytest.fixture
def repository() -> FinancialStatementRepository:
    database = Database("sqlite:///:memory:")
    database.create_tables()
    with database.get_session() as session:
        session.add(Company(code="72030", company_name="トヨタ自動車"))

    value = FinancialStatementRepository(database)
    yield value
    database.dispose()


def make_statement(
    disclosed_date: date,
    *,
    fiscal_period: str = "FY",
    fiscal_year_end: date = date(2025, 3, 31),
    net_sales: str = "100",
) -> FinancialStatement:
    return FinancialStatement(
        code="72030",
        fiscal_period=fiscal_period,
        disclosed_date=disclosed_date,
        fiscal_year_end=fiscal_year_end,
        net_sales=Decimal(net_sales),
    )


def test_upsert_statements_inserts_and_updates(
    repository: FinancialStatementRepository,
) -> None:
    repository.upsert_statements(
        [make_statement(date(2025, 5, 8), net_sales="100")]
    )
    repository.upsert_statements(
        [make_statement(date(2025, 5, 8), net_sales="120")]
    )

    statements = repository.find_by_code("72030")

    assert len(statements) == 1
    assert statements[0].net_sales == Decimal("120.00")


def test_find_by_code_filters_and_orders_by_fiscal_year_and_disclosed_date(
    repository: FinancialStatementRepository,
) -> None:
    repository.upsert_statements(
        [
            make_statement(
                date(2025, 8, 7),
                fiscal_period="1Q",
                fiscal_year_end=date(2026, 3, 31),
            ),
            make_statement(date(2025, 5, 8)),
            make_statement(date(2025, 5, 15)),
        ]
    )

    statements = repository.find_by_code(
        " 72030 ",
        from_date=date(2025, 5, 10),
        to_date=date(2025, 8, 7),
    )

    assert [item.disclosed_date for item in statements] == [
        date(2025, 5, 15),
        date(2025, 8, 7),
    ]


def test_find_latest_disclosed_date_returns_latest_or_none(
    repository: FinancialStatementRepository,
) -> None:
    repository.upsert_statements(
        [
            make_statement(date(2025, 5, 8)),
            make_statement(date(2025, 5, 15)),
        ]
    )

    assert repository.find_latest_disclosed_date("72030") == date(2025, 5, 15)
    assert repository.find_latest_disclosed_date("99990") is None
    assert repository.find_latest_disclosed_date(" ") is None


def test_find_by_code_rejects_reversed_period(
    repository: FinancialStatementRepository,
) -> None:
    with pytest.raises(ValueError, match="from_date"):
        repository.find_by_code(
            "72030",
            from_date=date(2025, 8, 7),
            to_date=date(2025, 5, 8),
        )
