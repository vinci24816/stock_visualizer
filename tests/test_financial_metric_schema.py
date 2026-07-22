from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.db.schema import Base, Company, FinancialMetric, FinancialStatement


def test_financial_metrics_table_definition() -> None:
    table = FinancialMetric.__table__

    assert table.name == "financial_metrics"
    assert set(table.primary_key.columns.keys()) == {
        "code",
        "fiscal_period",
        "disclosed_date",
    }
    assert {foreign_key.target_fullname for foreign_key in table.foreign_keys} == {
        "financial_statements.code",
        "financial_statements.fiscal_period",
        "financial_statements.disclosed_date",
    }


def test_financial_metric_can_be_persisted() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    disclosed_date = date(2025, 5, 8)

    with Session(engine) as session:
        session.add(Company(code="72030", company_name="トヨタ自動車"))
        session.add(
            FinancialStatement(
                code="72030",
                fiscal_period="FY",
                disclosed_date=disclosed_date,
            )
        )
        session.commit()
        session.add(
            FinancialMetric(
                code="72030",
                fiscal_period="FY",
                disclosed_date=disclosed_date,
                fiscal_year_end=date(2025, 3, 31),
                price_date=date(2025, 5, 8),
                equity_ratio=Decimal("0.375"),
                roe=Decimal("0.2"),
                per=Decimal("10"),
            )
        )
        session.commit()

        saved = session.get(
            FinancialMetric,
            ("72030", "FY", disclosed_date),
        )

        assert saved is not None
        assert saved.equity_ratio == Decimal("0.3750000000")
        assert saved.roe == Decimal("0.2000000000")
        assert saved.per == Decimal("10.000000")


def test_financial_metric_requires_source_statement() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, connection_record) -> None:
        del connection_record
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)

    with Session(engine) as session:
        session.add(
            FinancialMetric(
                code="72030",
                fiscal_period="FY",
                disclosed_date=date(2025, 5, 8),
                roe=Decimal("0.2"),
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()
