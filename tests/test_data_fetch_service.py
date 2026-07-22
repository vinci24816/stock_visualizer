from datetime import date
from pathlib import Path
from typing import Any

import pytest

from src.db.database import Database
from src.db.repositories import (
    CompanyRepository,
    FinancialStatementRepository,
    PriceRepository,
)
from src.services.data_fetch_service import DataFetchService, DataNormalizationError
from src.storage.raw_data_storage import RawDataStorage


class FakeJQuantsClient:
    def __init__(self) -> None:
        self.company_records: list[dict[str, Any]] = []
        self.price_records: list[dict[str, Any]] = []
        self.statement_records: list[dict[str, Any]] = []

    def get_listed_info(self, **kwargs: Any) -> list[dict[str, Any]]:
        return self.company_records

    def get_daily_quotes(self, *args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        return self.price_records

    def get_statements(self, *args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        return self.statement_records


@pytest.fixture
def service_parts(tmp_path: Path):
    database = Database("sqlite:///:memory:")
    database.create_tables()
    client = FakeJQuantsClient()
    company_repository = CompanyRepository(database)
    price_repository = PriceRepository(database)
    financial_statement_repository = FinancialStatementRepository(database)
    service = DataFetchService(
        client,  # type: ignore[arg-type]
        RawDataStorage(tmp_path / "raw"),
        company_repository,
        price_repository,
        financial_statement_repository,
    )
    yield (
        service,
        client,
        company_repository,
        price_repository,
        financial_statement_repository,
    )
    database.dispose()


def test_sync_companies_saves_raw_and_database(service_parts) -> None:
    service, client, company_repository, _, _ = service_parts
    client.company_records = [
        {
            "Code": "72030",
            "CoName": "トヨタ自動車",
            "S33Nm": "輸送用機器",
            "MktNm": "プライム",
        }
    ]

    result = service.sync_companies(nikkei225_codes={"72030"})

    company = company_repository.find_by_code("72030")
    assert result.record_count == 1
    assert result.raw_path.is_file()
    assert company is not None
    assert company.company_name == "トヨタ自動車"
    assert company.is_nikkei225 is True


def test_sync_companies_preserves_existing_nikkei_flag(service_parts) -> None:
    service, client, company_repository, _, _ = service_parts
    client.company_records = [{"Code": "72030", "CoName": "旧名称"}]
    service.sync_companies(nikkei225_codes={"72030"})
    client.company_records = [{"Code": "72030", "CoName": "新名称"}]

    service.sync_companies()

    company = company_repository.find_by_code("72030")
    assert company is not None
    assert company.company_name == "新名称"
    assert company.is_nikkei225 is True


def test_sync_daily_prices_saves_raw_and_database(service_parts) -> None:
    service, client, company_repository, price_repository, _ = service_parts
    client.company_records = [{"Code": "72030", "CoName": "トヨタ自動車"}]
    service.sync_companies()
    client.price_records = [
        {
            "Code": "72030",
            "Date": "2025-01-06",
            "O": 3000.5,
            "H": 3050,
            "L": 2980,
            "C": 3030,
            "Vo": 1000000,
            "Va": 3020000000,
            "AdjFactor": 1.0,
            "AdjC": 3030,
        }
    ]

    result = service.sync_daily_prices("72030", target_date=date(2025, 1, 6))

    prices = price_repository.find_by_code("72030")
    assert result.record_count == 1
    assert result.raw_path.is_file()
    assert len(prices) == 1
    assert prices[0].date == date(2025, 1, 6)
    assert str(prices[0].close) == "3030.000000"


def test_sync_daily_prices_requires_registered_company(service_parts) -> None:
    service, _, _, _, _ = service_parts

    with pytest.raises(ValueError, match="sync companies first"):
        service.sync_daily_prices("99990", target_date="20250106")


def test_sync_companies_rejects_missing_required_fields(service_parts) -> None:
    service, client, _, _, _ = service_parts
    client.company_records = [{"Code": "72030"}]

    with pytest.raises(DataNormalizationError, match="CoName"):
        service.sync_companies()


def test_sync_financial_statements_saves_raw_and_database(service_parts) -> None:
    service, client, _, _, financial_repository = service_parts
    client.company_records = [{"Code": "72030", "CoName": "トヨタ自動車"}]
    service.sync_companies()
    client.statement_records = [
        {
            "Code": "72030",
            "DiscDate": "2025-05-08",
            "DocType": "FYFinancialStatements_Consolidated_JP",
            "CurPerType": "FY",
            "CurFYSt": "2024-04-01",
            "CurFYEn": "2025-03-31",
            "Sales": "48036704000000",
            "OP": "4795586000000",
            "OdP": "5651447000000",
            "NP": "4765864000000",
            "TA": "90114296000000",
            "Eq": "35875909000000",
            "EPS": "955.28",
            "BPS": "6785.00",
            "DivAnn": "90.00",
        }
    ]

    result = service.sync_financial_statements(
        "72030", disclosure_date=date(2025, 5, 8)
    )

    statements = financial_repository.find_by_code("72030")
    assert result.category == "financial_statements"
    assert result.record_count == 1
    assert result.raw_path.is_file()
    assert len(statements) == 1
    assert str(statements[0].net_sales) == "48036704000000.00"
    assert str(statements[0].liabilities) == "54238387000000.00"


def test_sync_financial_statements_requires_registered_company(
    service_parts,
) -> None:
    service, _, _, _, _ = service_parts

    with pytest.raises(ValueError, match="sync companies first"):
        service.sync_financial_statements("99990")


def test_sync_financial_statements_rejects_missing_key_fields(
    service_parts,
) -> None:
    service, client, _, _, _ = service_parts
    client.company_records = [{"Code": "72030", "CoName": "トヨタ自動車"}]
    service.sync_companies()
    client.statement_records = [{"Code": "72030", "DiscDate": "2025-05-08"}]

    with pytest.raises(DataNormalizationError, match="CurPerType"):
        service.sync_financial_statements("72030")
