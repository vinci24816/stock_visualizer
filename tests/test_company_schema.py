import pytest
from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError

from src.db.database import Database
from src.db.schema import Company


@pytest.fixture
def database() -> Database:
    value = Database("sqlite:///:memory:")
    value.create_tables()
    yield value
    value.dispose()


def test_create_tables_creates_companies_table(database: Database) -> None:
    inspector = inspect(database.engine)

    assert "companies" in inspector.get_table_names()
    assert {column["name"] for column in inspector.get_columns("companies")} == {
        "code",
        "company_name",
        "sector",
        "market",
        "is_nikkei225",
    }


def test_company_can_be_saved_and_loaded(database: Database) -> None:
    with database.get_session() as session:
        session.add(
            Company(
                code="72030",
                company_name="トヨタ自動車",
                sector="輸送用機器",
                market="プライム",
                is_nikkei225=True,
            )
        )

    with database.get_session() as session:
        company = session.get(Company, "72030")

        assert company is not None
        assert company.company_name == "トヨタ自動車"
        assert company.sector == "輸送用機器"
        assert company.market == "プライム"
        assert company.is_nikkei225 is True


def test_is_nikkei225_defaults_to_false(database: Database) -> None:
    with database.get_session() as session:
        session.add(Company(code="99990", company_name="テスト会社"))

    with database.get_session() as session:
        company = session.get(Company, "99990")

        assert company is not None
        assert company.is_nikkei225 is False


def test_company_code_must_be_unique(database: Database) -> None:
    with database.get_session() as session:
        session.add(Company(code="72030", company_name="会社A"))

    with pytest.raises(IntegrityError):
        with database.get_session() as session:
            session.add(Company(code="72030", company_name="会社B"))


def test_companies_can_be_filtered_by_nikkei225(database: Database) -> None:
    with database.get_session() as session:
        session.add_all(
            [
                Company(code="72030", company_name="会社A", is_nikkei225=True),
                Company(code="99990", company_name="会社B", is_nikkei225=False),
            ]
        )

    with database.get_session() as session:
        companies = session.scalars(
            select(Company).where(Company.is_nikkei225.is_(True))
        ).all()

        assert [company.code for company in companies] == ["72030"]
