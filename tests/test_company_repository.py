import pytest

from src.db.database import Database
from src.db.repositories import CompanyRepository
from src.db.schema import Company


@pytest.fixture
def repository() -> CompanyRepository:
    database = Database("sqlite:///:memory:")
    database.create_tables()
    value = CompanyRepository(database)
    yield value
    database.dispose()


def test_upsert_companies_inserts_and_updates(repository: CompanyRepository) -> None:
    repository.upsert_companies(
        [Company(code="72030", company_name="旧名称", is_nikkei225=False)]
    )
    repository.upsert_companies(
        [
            Company(
                code="72030",
                company_name="トヨタ自動車",
                sector="輸送用機器",
                market="プライム",
                is_nikkei225=True,
            )
        ]
    )

    companies = repository.find_all()

    assert len(companies) == 1
    assert companies[0].company_name == "トヨタ自動車"
    assert companies[0].is_nikkei225 is True


def test_find_all_returns_code_order(repository: CompanyRepository) -> None:
    repository.upsert_companies(
        [
            Company(code="99990", company_name="会社B"),
            Company(code="72030", company_name="会社A"),
        ]
    )

    assert [company.code for company in repository.find_all()] == ["72030", "99990"]


def test_find_nikkei225_filters_companies(repository: CompanyRepository) -> None:
    repository.upsert_companies(
        [
            Company(code="72030", company_name="会社A", is_nikkei225=True),
            Company(code="99990", company_name="会社B", is_nikkei225=False),
        ]
    )

    assert [company.code for company in repository.find_nikkei225()] == ["72030"]


def test_find_by_code_returns_company_or_none(repository: CompanyRepository) -> None:
    repository.upsert_companies([Company(code="72030", company_name="会社A")])

    assert repository.find_by_code(" 72030 ") is not None
    assert repository.find_by_code("99990") is None
    assert repository.find_by_code(" ") is None


def test_search_matches_code_or_company_name(repository: CompanyRepository) -> None:
    repository.upsert_companies(
        [
            Company(code="72030", company_name="トヨタ自動車"),
            Company(code="67580", company_name="ソニーグループ"),
        ]
    )

    assert [company.code for company in repository.search("720")] == ["72030"]
    assert [company.code for company in repository.search("ソニー")] == ["67580"]
    assert len(repository.search(" ")) == 2
