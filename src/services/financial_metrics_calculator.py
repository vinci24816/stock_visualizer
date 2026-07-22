"""財務諸表と株価から財務指標を計算するサービス。"""

from decimal import Decimal

from src.db.schema import DailyPrice, FinancialStatement


class FinancialMetricsCalculator:
    """FinancialStatementとDailyPriceから主要な財務指標を計算する。"""

    def calculate_equity_ratio(
        self,
        statement: FinancialStatement,
    ) -> Decimal | None:
        """自己資本比率（自己資本 ÷ 総資産）を比率で返す。"""

        return self._safe_divide(statement.equity, statement.total_assets)

    def calculate_roe(
        self,
        statement: FinancialStatement,
    ) -> Decimal | None:
        """ROE（当期純利益 ÷ 自己資本）を比率で返す。"""

        return self._safe_divide(statement.profit, statement.equity)

    def calculate_roa(
        self,
        statement: FinancialStatement,
    ) -> Decimal | None:
        """ROA（当期純利益 ÷ 総資産）を比率で返す。"""

        return self._safe_divide(statement.profit, statement.total_assets)

    def calculate_roi(
        self,
        statement: FinancialStatement,
    ) -> Decimal | None:
        """ROI（営業利益 ÷（自己資本＋負債））を比率で返す。"""

        if statement.equity is None or statement.liabilities is None:
            return None
        invested_capital = statement.equity + statement.liabilities
        return self._safe_divide(statement.operating_profit, invested_capital)

    def calculate_operating_margin(
        self,
        statement: FinancialStatement,
    ) -> Decimal | None:
        """営業利益率（営業利益 ÷ 売上高）を比率で返す。"""

        return self._safe_divide(statement.operating_profit, statement.net_sales)

    def calculate_price_metrics(
        self,
        statement: FinancialStatement,
        price: DailyPrice,
    ) -> dict[str, Decimal | None]:
        """PER、PBR、配当利回りを計算して指標名ごとに返す。

        株価には調整後終値を優先し、存在しない場合は終値を使用する。
        PERとPBRは倍率、配当利回りは比率として返す。
        """

        market_price = (
            price.adjusted_close
            if price.adjusted_close is not None
            else price.close
        )
        return {
            "per": self._safe_divide(market_price, statement.eps),
            "pbr": self._safe_divide(market_price, statement.bps),
            "dividend_yield": self._safe_divide(
                statement.dividend,
                market_price,
            ),
        }

    @staticmethod
    def _safe_divide(
        numerator: Decimal | None,
        denominator: Decimal | None,
    ) -> Decimal | None:
        """欠損値または0除算を避けてDecimal同士を除算する。"""

        if numerator is None or denominator is None or denominator == 0:
            return None
        return numerator / denominator
