"""Database connection and transaction management."""

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.db.schema import Base


class Database:
    """Own the SQLAlchemy engine and transactional session lifecycle."""

    def __init__(self, database_url: str, *, echo: bool = False) -> None:
        if not database_url.strip():
            raise ValueError("database_url must not be empty")

        self.database_url = database_url
        engine_options: dict[str, object] = {
            "echo": echo,
            "pool_pre_ping": True,
        }
        
        # データベースの種類によって接続オプションを設定
        if database_url.startswith("sqlite"):
            engine_options["connect_args"] = {"check_same_thread": False}
            if database_url in {"sqlite://", "sqlite:///:memory:"}:
                engine_options["poolclass"] = StaticPool

        # 接続およびSQL実行のためのオブジェクトを作成
        self.engine: Engine = create_engine(database_url, **engine_options)
        self._session_factory = sessionmaker(
            bind=self.engine,
            class_=Session,
            expire_on_commit=False,
        )

        if self.engine.dialect.name == "sqlite":
            event.listen(self.engine, "connect", self._enable_sqlite_foreign_keys)

    @staticmethod
    def _enable_sqlite_foreign_keys(
        dbapi_connection: object, connection_record: object
    ) -> None:
        del connection_record
        cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
        try:
            cursor.execute("PRAGMA foreign_keys=ON")
        finally:
            cursor.close()

    @contextmanager
    def connect(self) -> Iterator[Connection]:
        """Yield a connection inside an automatically managed transaction."""

        with self.engine.begin() as connection:
            yield connection

    def check_connection(self) -> None:
        """Raise a SQLAlchemy exception when the database is unreachable."""

        with self.engine.connect() as connection:
            connection.execute(text("SELECT 1"))

    def create_tables(self) -> None:
        """Create every table registered on the shared declarative base."""

        Base.metadata.create_all(self.engine)

    @contextmanager
    def get_session(self) -> Iterator[Session]:
        """Commit successful work, roll back failures, and always close."""

        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def dispose(self) -> None:
        """Release pooled database connections."""

        self.engine.dispose()
