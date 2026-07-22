from datetime import date
from decimal import Decimal

import pytest

from src.db.database import Database
from src.db.repositories import PriceRepository
from src.db.schema import Company, DailyPrice


@pytest.fixture
def repository() -> PriceRepository:
    database = Database("sqlite:///:memory:")
    database.create_tables()
    with database.get_session() as session:
        session.add(Company(code="72030", company_name="トヨタ自動車"))

    value = PriceRepository(database)
    yield value
    database.dispose()


def test_upsert_daily_prices_inserts_and_updates(
    repository: PriceRepository,
) -> None:
    repository.upsert_daily_prices(
        [
            DailyPrice(
                code="72030",
                date=date(2025, 1, 6),
                close=Decimal("3000"),
            )
        ]
    )
    repository.upsert_daily_prices(
        [
            DailyPrice(
                code="72030",
                date=date(2025, 1, 6),
                close=Decimal("3030"),
                volume=1_000_000,
            )
        ]
    )

    prices = repository.find_by_code("72030")

    assert len(prices) == 1
    assert prices[0].close == Decimal("3030.000000")
    assert prices[0].volume == 1_000_000


def test_find_by_code_filters_period_and_orders_by_date(
    repository: PriceRepository,
) -> None:
    repository.upsert_daily_prices(
        [
            DailyPrice(code="72030", date=date(2025, 1, 8), close=Decimal("3")),
            DailyPrice(code="72030", date=date(2025, 1, 6), close=Decimal("1")),
            DailyPrice(code="72030", date=date(2025, 1, 7), close=Decimal("2")),
        ]
    )

    prices = repository.find_by_code(
        "72030",
        from_date=date(2025, 1, 7),
        to_date=date(2025, 1, 8),
    )

    assert [price.date for price in prices] == [date(2025, 1, 7), date(2025, 1, 8)]


def test_find_latest_date_returns_latest_or_none(
    repository: PriceRepository,
) -> None:
    repository.upsert_daily_prices(
        [
            DailyPrice(code="72030", date=date(2025, 1, 6)),
            DailyPrice(code="72030", date=date(2025, 1, 8)),
        ]
    )

    assert repository.find_latest_date("72030") == date(2025, 1, 8)
    assert repository.find_latest_date("99990") is None
    assert repository.find_latest_date(" ") is None


def test_find_by_code_rejects_reversed_period(
    repository: PriceRepository,
) -> None:
    with pytest.raises(ValueError, match="from_date"):
        repository.find_by_code(
            "72030",
            from_date=date(2025, 1, 8),
            to_date=date(2025, 1, 6),
        )
