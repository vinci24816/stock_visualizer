import pytest
from sqlalchemy import ForeignKey, Integer, String, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, mapped_column

from src.db.database import Database
from src.db.schema import Base


class DatabaseTestItem(Base):
    __tablename__ = "database_test_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)


class DatabaseTestChild(Base):
    __tablename__ = "database_test_children"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    item_id: Mapped[int] = mapped_column(
        ForeignKey("database_test_items.id"), nullable=False
    )


@pytest.fixture
def database() -> Database:
    value = Database("sqlite:///:memory:")
    value.create_tables()
    yield value
    value.dispose()


def test_check_connection(database: Database) -> None:
    database.check_connection()


def test_get_session_commits_on_success(database: Database) -> None:
    with database.get_session() as session:
        session.add(DatabaseTestItem(name="committed"))

    with database.get_session() as session:
        names = session.scalars(select(DatabaseTestItem.name)).all()

    assert names == ["committed"]


def test_get_session_rolls_back_on_failure(database: Database) -> None:
    with pytest.raises(RuntimeError):
        with database.get_session() as session:
            session.add(DatabaseTestItem(name="rolled-back"))
            session.flush()
            raise RuntimeError("force rollback")

    with database.get_session() as session:
        names = session.scalars(select(DatabaseTestItem.name)).all()

    assert names == []


def test_connect_commits_on_success(database: Database) -> None:
    with database.connect() as connection:
        connection.execute(
            text("INSERT INTO database_test_items (name) VALUES (:name)"),
            {"name": "connection-commit"},
        )

    with database.connect() as connection:
        count = connection.scalar(text("SELECT COUNT(*) FROM database_test_items"))

    assert count == 1


def test_sqlite_foreign_keys_are_enabled(database: Database) -> None:
    with pytest.raises(IntegrityError):
        with database.get_session() as session:
            session.add(DatabaseTestChild(item_id=999))
