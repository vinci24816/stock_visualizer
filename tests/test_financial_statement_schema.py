from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session

from src.db.schema import Base, Company, FinancialStatement


def test_financial_statements_table_definition() -> None:
    table = FinancialStatement.__table__

    assert table.name == "financial_statements"
    assert set(table.primary_key.columns.keys()) == {
        "code",
        "fiscal_period",
        "disclosed_date",
    }
    assert {foreign_key.target_fullname for foreign_key in table.foreign_keys} == {
        "companies.code"
    }


def test_financial_statement_can_be_persisted() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        session.add(Company(code="86970", company_name="JPX"))
        session.add(
            FinancialStatement(
                code="86970",
                fiscal_period="FY",
                disclosed_date=date(2025, 1, 30),
                fiscal_year_start=date(2024, 4, 1),
                fiscal_year_end=date(2025, 3, 31),
                net_sales=Decimal("150000000000.00"),
                operating_profit=Decimal("80000000000.00"),
                eps=Decimal("120.500000"),
            )
        )
        session.commit()

        saved = session.get(
            FinancialStatement,
            ("86970", "FY", date(2025, 1, 30)),
        )

        assert saved is not None
        assert saved.net_sales == Decimal("150000000000.00")
        assert saved.eps == Decimal("120.500000")

    assert inspect(engine).has_table("financial_statements")
