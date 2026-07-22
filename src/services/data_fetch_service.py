"""J-Quants API取得、raw保存、DB保存のオーケストレーション。"""

from collections.abc import Collection, Mapping
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from src.api.jquants_client import DateLike, JQuantsClient
from src.db.repositories import (
    CompanyRepository,
    FinancialStatementRepository,
    PriceRepository,
)
from src.db.schema import Company, DailyPrice, FinancialStatement
from src.storage.raw_data_storage import RawDataStorage


class DataNormalizationError(ValueError):
    """APIレコードをDBモデルへ変換できない場合の例外。"""


@dataclass(frozen=True)
class SyncResult:
    """1回の同期処理の結果。"""

    category: str
    record_count: int
    raw_path: Path


class DataFetchService:
    """API取得からraw保存、正規化、DB保存までを一括して制御する。"""

    def __init__(
        self,
        client: JQuantsClient,
        raw_storage: RawDataStorage,
        company_repository: CompanyRepository,
        price_repository: PriceRepository,
        financial_statement_repository: FinancialStatementRepository,
    ) -> None:
        self._client = client
        self._raw_storage = raw_storage
        self._company_repository = company_repository
        self._price_repository = price_repository
        self._financial_statement_repository = financial_statement_repository

    def sync_companies(
        self,
        target_date: DateLike | None = None,
        *,
        nikkei225_codes: Collection[str] | None = None,
    ) -> SyncResult:
        """上場銘柄を取得し、raw JSONとcompaniesテーブルへ保存する。"""

        records = self._client.get_listed_info(target_date=target_date)
        raw_path = self._raw_storage.save_json(
            source="api",
            category="listed_info",
            data=records,
            file_name=self._timestamped_file_name("companies"),
        )

        existing_flags = {
            company.code: company.is_nikkei225
            for company in self._company_repository.find_all()
        }
        specified_codes = (
            {code.strip() for code in nikkei225_codes}
            if nikkei225_codes is not None
            else None
        )
        companies = [
            self._normalize_company(record, existing_flags, specified_codes)
            for record in records
        ]
        self._company_repository.upsert_companies(companies)
        return SyncResult("listed_info", len(companies), raw_path)

    def sync_daily_prices(
        self,
        code: str,
        from_date: DateLike | None = None,
        to_date: DateLike | None = None,
        *,
        target_date: DateLike | None = None,
    ) -> SyncResult:
        """1銘柄の日次株価を取得し、raw JSONとdaily_pricesへ保存する。"""

        normalized_code = code.strip()
        if not normalized_code:
            raise ValueError("code must not be empty")
        if self._company_repository.find_by_code(normalized_code) is None:
            raise ValueError(
                f"company {normalized_code!r} is not registered; sync companies first"
            )

        records = self._client.get_daily_quotes(
            normalized_code,
            from_date,
            to_date,
            target_date=target_date,
        )
        raw_path = self._raw_storage.save_json(
            source="api",
            category="daily_quotes",
            data=records,
            file_name=self._timestamped_file_name(f"prices_{normalized_code}"),
        )
        prices = [self._normalize_daily_price(record) for record in records]
        self._price_repository.upsert_daily_prices(prices)
        return SyncResult("daily_quotes", len(prices), raw_path)

    def sync_financial_statements(
        self,
        code: str,
        disclosure_date: DateLike | None = None,
    ) -> SyncResult:
        """1銘柄の財務情報を取得し、raw JSONとDBへ保存する。"""

        normalized_code = code.strip()
        if not normalized_code:
            raise ValueError("code must not be empty")
        if self._company_repository.find_by_code(normalized_code) is None:
            raise ValueError(
                f"company {normalized_code!r} is not registered; sync companies first"
            )

        records = self._client.get_statements(normalized_code, disclosure_date)
        raw_path = self._raw_storage.save_json(
            source="api",
            category="financial_statements",
            data=records,
            file_name=self._timestamped_file_name(
                f"financial_statements_{normalized_code}"
            ),
        )
        statements = [
            self._normalize_financial_statement(record) for record in records
        ]
        self._financial_statement_repository.upsert_statements(statements)
        return SyncResult("financial_statements", len(statements), raw_path)

    @staticmethod
    def _normalize_company(
        record: Mapping[str, Any],
        existing_flags: Mapping[str, bool],
        specified_codes: set[str] | None,
    ) -> Company:
        """J-Quantsの銘柄レコードをCompanyへ変換する。"""

        code = DataFetchService._required_text(record, "Code")
        company_name = DataFetchService._required_text(record, "CoName")
        if specified_codes is None:
            is_nikkei225 = existing_flags.get(code, False)
        else:
            is_nikkei225 = code in specified_codes

        return Company(
            code=code,
            company_name=company_name,
            sector=DataFetchService._optional_text(record.get("S33Nm")),
            market=DataFetchService._optional_text(record.get("MktNm")),
            is_nikkei225=is_nikkei225,
        )

    @staticmethod
    def _normalize_daily_price(record: Mapping[str, Any]) -> DailyPrice:
        """J-Quantsの日足レコードをDailyPriceへ変換する。"""

        return DailyPrice(
            code=DataFetchService._required_text(record, "Code"),
            date=DataFetchService._required_date(record, "Date"),
            open=DataFetchService._optional_decimal(record.get("O"), "O"),
            high=DataFetchService._optional_decimal(record.get("H"), "H"),
            low=DataFetchService._optional_decimal(record.get("L"), "L"),
            close=DataFetchService._optional_decimal(record.get("C"), "C"),
            volume=DataFetchService._optional_integer(record.get("Vo"), "Vo"),
            turnover_value=DataFetchService._optional_decimal(record.get("Va"), "Va"),
            adjustment_factor=DataFetchService._optional_decimal(
                record.get("AdjFactor"), "AdjFactor"
            ),
            adjusted_open=DataFetchService._optional_decimal(
                record.get("AdjO"), "AdjO"
            ),
            adjusted_high=DataFetchService._optional_decimal(
                record.get("AdjH"), "AdjH"
            ),
            adjusted_low=DataFetchService._optional_decimal(
                record.get("AdjL"), "AdjL"
            ),
            adjusted_close=DataFetchService._optional_decimal(
                record.get("AdjC"), "AdjC"
            ),
            adjusted_volume=DataFetchService._optional_decimal(
                record.get("AdjVo"), "AdjVo"
            ),
        )

    @staticmethod
    def _normalize_financial_statement(
        record: Mapping[str, Any],
    ) -> FinancialStatement:
        """J-Quantsの財務サマリーをFinancialStatementへ変換する。"""

        total_assets = DataFetchService._optional_decimal(record.get("TA"), "TA")
        equity = DataFetchService._optional_decimal(record.get("Eq"), "Eq")
        liabilities = DataFetchService._optional_decimal(
            record.get("Liab"), "Liab"
        )
        if liabilities is None and total_assets is not None and equity is not None:
            liabilities = total_assets - equity

        return FinancialStatement(
            code=DataFetchService._required_text(record, "Code"),
            fiscal_period=DataFetchService._required_text(record, "CurPerType"),
            disclosed_date=DataFetchService._required_date(record, "DiscDate"),
            document_type=DataFetchService._optional_text(record.get("DocType")),
            fiscal_year_start=DataFetchService._optional_date(
                record.get("CurFYSt"), "CurFYSt"
            ),
            fiscal_year_end=DataFetchService._optional_date(
                record.get("CurFYEn"), "CurFYEn"
            ),
            net_sales=DataFetchService._optional_decimal(
                record.get("Sales"), "Sales"
            ),
            operating_profit=DataFetchService._optional_decimal(
                record.get("OP"), "OP"
            ),
            ordinary_profit=DataFetchService._optional_decimal(
                record.get("OdP"), "OdP"
            ),
            profit=DataFetchService._optional_decimal(record.get("NP"), "NP"),
            total_assets=total_assets,
            equity=equity,
            liabilities=liabilities,
            eps=DataFetchService._optional_decimal(record.get("EPS"), "EPS"),
            bps=DataFetchService._optional_decimal(record.get("BPS"), "BPS"),
            dividend=DataFetchService._optional_decimal(
                record.get("DivAnn"), "DivAnn"
            ),
        )

    @staticmethod
    def _required_text(record: Mapping[str, Any], field: str) -> str:
        value = DataFetchService._optional_text(record.get(field))
        if value is None:
            raise DataNormalizationError(f"required API field {field!r} is missing")
        return value

    @staticmethod
    def _optional_text(value: Any) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None

    @staticmethod
    def _required_date(record: Mapping[str, Any], field: str) -> date:
        value = DataFetchService._required_text(record, field)
        for date_format in ("%Y-%m-%d", "%Y%m%d"):
            try:
                return datetime.strptime(value, date_format).date()
            except ValueError:
                continue
        raise DataNormalizationError(f"API field {field!r} is not a valid date")

    @staticmethod
    def _optional_date(value: Any, field: str) -> date | None:
        normalized = DataFetchService._optional_text(value)
        if normalized is None:
            return None
        return DataFetchService._required_date({field: normalized}, field)

    @staticmethod
    def _optional_decimal(value: Any, field: str) -> Decimal | None:
        if value is None or value == "":
            return None
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError) as error:
            raise DataNormalizationError(
                f"API field {field!r} is not a valid decimal"
            ) from error

    @staticmethod
    def _optional_integer(value: Any, field: str) -> int | None:
        decimal_value = DataFetchService._optional_decimal(value, field)
        if decimal_value is None:
            return None
        if decimal_value != decimal_value.to_integral_value():
            raise DataNormalizationError(f"API field {field!r} is not an integer")
        return int(decimal_value)

    @staticmethod
    def _timestamped_file_name(prefix: str) -> str:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        return f"{prefix}_{timestamp}"
