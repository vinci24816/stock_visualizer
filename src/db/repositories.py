"""Database repositories for imported market data."""

from collections.abc import Iterable

from sqlalchemy import or_, select

from src.db.database import Database
from src.db.schema import Company


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
