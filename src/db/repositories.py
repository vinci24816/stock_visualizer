"""Database repositories for imported market data."""

from collections.abc import Iterable
from datetime import date

from sqlalchemy import func, or_, select

from src.db.database import Database
from src.db.schema import Company, DailyPrice, FinancialStatement


class CompanyRepository:
    """上場企業・銘柄情報の保存と検索を担当するリポジトリ。"""

    def __init__(self, database: Database) -> None:
        self._database = database

    def upsert_companies(self, companies: Iterable[Company]) -> None:
        """企業を新規登録し、同じ証券コードが存在する場合は更新する。"""

        with self._database.get_session() as session:
            for company in companies:
                session.merge(company)

    def find_all(self) -> list[Company]:
        """登録されている全企業を証券コード順で取得する。"""

        statement = select(Company).order_by(Company.code)
        with self._database.get_session() as session:
            return list(session.scalars(statement))

    def find_nikkei225(self) -> list[Company]:
        """日経225採用企業を証券コード順で取得する。"""

        statement = (
            select(Company)
            .where(Company.is_nikkei225.is_(True))
            .order_by(Company.code)
        )
        with self._database.get_session() as session:
            return list(session.scalars(statement))

    def find_by_code(self, code: str) -> Company | None:
        """主キーである証券コードから企業を1件取得する。"""

        normalized_code = code.strip()
        if not normalized_code:
            return None

        with self._database.get_session() as session:
            return session.get(Company, normalized_code)

    def search(self, keyword: str) -> list[Company]:
        """会社名または証券コードの部分一致で企業を検索する。"""

        normalized_keyword = keyword.strip()
        if not normalized_keyword:
            return self.find_all()

        pattern = f"%{normalized_keyword}%"
        statement = (
            select(Company)
            .where(
                or_(
                    Company.code.ilike(pattern),
                    Company.company_name.ilike(pattern),
                )
            )
            .order_by(Company.code)
        )
        with self._database.get_session() as session:
            return list(session.scalars(statement))


class PriceRepository:
    """日次株価データの保存と検索を担当するリポジトリ。"""

    def __init__(self, database: Database) -> None:
        self._database = database

    def upsert_daily_prices(self, prices: Iterable[DailyPrice]) -> None:
        """日次株価を新規登録し、同一銘柄・日付が存在する場合は更新する。"""

        with self._database.get_session() as session:
            for price in prices:
                session.merge(price)

    def find_by_code(
        self,
        code: str,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> list[DailyPrice]:
        """指定銘柄の日次株価を期間で絞り込み、日付順で取得する。"""

        normalized_code = code.strip()
        if not normalized_code:
            return []
        if from_date is not None and to_date is not None and from_date > to_date:
            raise ValueError("from_date must be on or before to_date")

        statement = select(DailyPrice).where(DailyPrice.code == normalized_code)
        if from_date is not None:
            statement = statement.where(DailyPrice.date >= from_date)
        if to_date is not None:
            statement = statement.where(DailyPrice.date <= to_date)
        statement = statement.order_by(DailyPrice.date)

        with self._database.get_session() as session:
            return list(session.scalars(statement))

    def find_latest_date(self, code: str) -> date | None:
        """指定銘柄についてDBに保存されている最新の株価日付を取得する。"""

        normalized_code = code.strip()
        if not normalized_code:
            return None

        statement = select(func.max(DailyPrice.date)).where(
            DailyPrice.code == normalized_code
        )
        with self._database.get_session() as session:
            return session.scalar(statement)


class FinancialStatementRepository:
    """財務諸表データの保存と検索を担当するリポジトリ。"""

    def __init__(self, database: Database) -> None:
        self._database = database

    def upsert_statements(
        self,
        statements: Iterable[FinancialStatement],
    ) -> None:
        """財務情報を登録し、同じ複合主キーが存在する場合は更新する。"""

        with self._database.get_session() as session:
            for financial_statement in statements:
                session.merge(financial_statement)

    def find_by_code(
        self,
        code: str,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> list[FinancialStatement]:
        """指定銘柄の財務情報を開示日の期間で絞り込んで取得する。"""

        normalized_code = code.strip()
        if not normalized_code:
            return []
        if from_date is not None and to_date is not None and from_date > to_date:
            raise ValueError("from_date must be on or before to_date")

        query = select(FinancialStatement).where(
            FinancialStatement.code == normalized_code
        )
        if from_date is not None:
            query = query.where(FinancialStatement.disclosed_date >= from_date)
        if to_date is not None:
            query = query.where(FinancialStatement.disclosed_date <= to_date)
        query = query.order_by(
            FinancialStatement.fiscal_year_end,
            FinancialStatement.disclosed_date,
            FinancialStatement.fiscal_period,
        )

        with self._database.get_session() as session:
            return list(session.scalars(query))

    def find_latest_disclosed_date(self, code: str) -> date | None:
        """指定銘柄について保存済みの最新開示日を取得する。"""

        normalized_code = code.strip()
        if not normalized_code:
            return None

        query = select(func.max(FinancialStatement.disclosed_date)).where(
            FinancialStatement.code == normalized_code
        )
        with self._database.get_session() as session:
            return session.scalar(query)
