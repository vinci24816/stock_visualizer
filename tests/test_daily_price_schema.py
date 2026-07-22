from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from src.db.database import Database
from src.db.schema import Company, DailyPrice


@pytest.fixture
def database() -> Database:
    value = Database("sqlite:///:memory:")
    value.create_tables()
    yield value
    value.dispose()


def test_create_tables_creates_daily_prices_table(database: Database) -> None:
    inspector = inspect(database.engine)

    assert "daily_prices" in inspector.get_table_names()
    assert {column["name"] for column in inspector.get_columns("daily_prices")} == {
        "code",
        "date",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "turnover_value",
        "adjustment_factor",
        "adjusted_open",
        "adjusted_high",
        "adjusted_low",
        "adjusted_close",
        "adjusted_volume",
    }


def test_daily_price_can_be_saved_and_loaded(database: Database) -> None:
    with database.get_session() as session:
        session.add(Company(code="72030", company_name="トヨタ自動車"))
        session.add(
            DailyPrice(
                code="72030",
                date=date(2025, 1, 6),
                open=Decimal("3000.5"),
                high=Decimal("3050"),
                low=Decimal("2980"),
                close=Decimal("3030"),
                volume=1_000_000,
                turnover_value=Decimal("3020000000"),
                adjustment_factor=Decimal("1"),
                adjusted_close=Decimal("3030"),
            )
        )

    with database.get_session() as session:
        price = session.get(DailyPrice, ("72030", date(2025, 1, 6)))

        assert price is not None
        assert price.close == Decimal("3030.000000")
        assert price.volume == 1_000_000
        assert price.adjusted_close == Decimal("3030.000000")


def test_code_and_date_form_composite_primary_key(database: Database) -> None:
    with database.get_session() as session:
        session.add(Company(code="72030", company_name="トヨタ自動車"))
        session.add(DailyPrice(code="72030", date=date(2025, 1, 6)))

    with pytest.raises(IntegrityError):
        with database.get_session() as session:
            session.add(DailyPrice(code="72030", date=date(2025, 1, 6)))


def test_daily_price_requires_existing_company(database: Database) -> None:
    with pytest.raises(IntegrityError):
        with database.get_session() as session:
            session.add(DailyPrice(code="99990", date=date(2025, 1, 6)))
