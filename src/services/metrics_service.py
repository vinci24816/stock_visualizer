"""財務指標の計算とDB保存を制御するサービス。"""

from bisect import bisect_right
from collections.abc import Iterable

from src.db.repositories import (
    FinancialMetricRepository,
    FinancialStatementRepository,
    PriceRepository,
)
from src.db.schema import DailyPrice, FinancialMetric, FinancialStatement
from src.services.financial_metrics_calculator import FinancialMetricsCalculator


class MetricsService:
    """保存済み財務情報と株価から指標を計算し、計算結果を保存する。"""

    def __init__(
        self,
        statement_repository: FinancialStatementRepository,
        price_repository: PriceRepository,
        metric_repository: FinancialMetricRepository,
        calculator: FinancialMetricsCalculator,
    ) -> None:
        self._statement_repository = statement_repository
        self._price_repository = price_repository
        self._metric_repository = metric_repository
        self._calculator = calculator

    def calculate_for_code(self, code: str) -> list[FinancialMetric]:
        """1銘柄の全財務情報から指標を計算し、保存して返す。"""

        normalized_code = code.strip()
        if not normalized_code:
            raise ValueError("code must not be empty")

        statements = self._statement_repository.find_by_code(normalized_code)
        metrics = self._calculate_statements(normalized_code, statements)
        self._metric_repository.upsert_metrics(metrics)
        return metrics

    def calculate_for_codes(self, codes: Iterable[str]) -> list[FinancialMetric]:
        """複数銘柄の指標を計算し、まとめて返す。"""

        all_metrics: list[FinancialMetric] = []
        processed_codes: set[str] = set()
        for code in codes:
            normalized_code = code.strip()
            if not normalized_code:
                raise ValueError("code must not be empty")
            if normalized_code in processed_codes:
                continue
            processed_codes.add(normalized_code)
            all_metrics.extend(self.calculate_for_code(normalized_code))
        return all_metrics

    def recalculate_all(self) -> list[FinancialMetric]:
        """保存済み財務情報がある全銘柄について指標を再計算する。"""

        statements = self._statement_repository.find_all()
        codes = dict.fromkeys(statement.code for statement in statements)
        return self.calculate_for_codes(codes)

    def _calculate_statements(
        self,
        code: str,
        statements: list[FinancialStatement],
    ) -> list[FinancialMetric]:
        if not statements:
            return []

        prices = self._price_repository.find_by_code(
            code,
            to_date=max(statement.disclosed_date for statement in statements),
        )
        price_dates = [price.date for price in prices]

        metrics: list[FinancialMetric] = []
        for statement in statements:
            price = self._latest_price_on_or_before(
                statement,
                prices,
                price_dates,
            )
            metrics.append(self._calculate_metric(statement, price))
        return metrics

    def _calculate_metric(
        self,
        statement: FinancialStatement,
        price: DailyPrice | None,
    ) -> FinancialMetric:
        price_metrics = (
            self._calculator.calculate_price_metrics(statement, price)
            if price is not None
            else {"per": None, "pbr": None, "dividend_yield": None}
        )
        return FinancialMetric(
            code=statement.code,
            fiscal_period=statement.fiscal_period,
            disclosed_date=statement.disclosed_date,
            fiscal_year_end=statement.fiscal_year_end,
            price_date=price.date if price is not None else None,
            equity_ratio=self._calculator.calculate_equity_ratio(statement),
            roe=self._calculator.calculate_roe(statement),
            roa=self._calculator.calculate_roa(statement),
            roi=self._calculator.calculate_roi(statement),
            operating_margin=self._calculator.calculate_operating_margin(statement),
            per=price_metrics["per"],
            pbr=price_metrics["pbr"],
            dividend_yield=price_metrics["dividend_yield"],
        )

    @staticmethod
    def _latest_price_on_or_before(
        statement: FinancialStatement,
        prices: list[DailyPrice],
        price_dates: list,
    ) -> DailyPrice | None:
        price_index = bisect_right(price_dates, statement.disclosed_date) - 1
        if price_index < 0:
            return None
        return prices[price_index]
