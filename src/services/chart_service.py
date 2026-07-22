"""株価・財務指標を可視化するPlotlyグラフ生成サービス。"""

from collections.abc import Iterable, Sequence

import pandas as pd
import plotly.graph_objects as go

from src.db.schema import DailyPrice


class ChartService:
    """DB取得結果から画面表示用のPlotly Figureを生成する。"""

    PERCENTAGE_METRICS = {
        "equity_ratio",
        "roe",
        "roa",
        "roi",
        "operating_margin",
        "dividend_yield",
    }
    METRIC_LABELS = {
        "equity_ratio": "自己資本比率",
        "roe": "ROE",
        "roa": "ROA",
        "roi": "ROI",
        "operating_margin": "営業利益率",
        "per": "PER",
        "pbr": "PBR",
        "dividend_yield": "配当利回り",
    }

    def create_price_line_chart(
        self,
        prices: Iterable[DailyPrice] | pd.DataFrame,
    ) -> go.Figure:
        """日次株価の終値を時系列折れ線グラフとして生成する。"""

        dataframe = self._price_dataframe(prices)
        if dataframe.empty:
            return self._empty_figure("株価データがありません")
        self._require_columns(dataframe, {"date", "close"})

        dataframe = dataframe.sort_values("date").copy()
        price_column = "close"
        price_label = "終値"
        if (
            "adjusted_close" in dataframe.columns
            and dataframe["adjusted_close"].notna().any()
        ):
            price_column = "adjusted_close"
            price_label = "調整後終値"

        code = self._single_value(dataframe, "code")
        title = f"{code} 株価推移" if code else "株価推移"
        figure = go.Figure(
            go.Scatter(
                x=dataframe["date"],
                y=dataframe[price_column],
                mode="lines",
                name=price_label,
                line={"width": 2},
                hovertemplate=(
                    "%{x|%Y-%m-%d}<br>"
                    + f"{price_label}: "
                    + "%{y:,.2f}<extra></extra>"
                ),
            )
        )
        self._apply_common_layout(
            figure,
            title=title,
            x_title="日付",
            y_title="株価（円）",
        )
        return figure

    def create_metric_line_chart(
        self,
        metrics: pd.DataFrame,
        metric_name: str,
    ) -> go.Figure:
        """1企業の財務指標を決算期ごとの折れ線グラフとして生成する。"""

        normalized_metric = self._normalize_metric_name(metric_name)
        if metrics.empty:
            return self._empty_figure("財務指標データがありません")
        self._require_columns(metrics, {"fiscal_period", normalized_metric})

        dataframe = metrics.sort_values("fiscal_period").copy()
        label = self.METRIC_LABELS.get(normalized_metric, normalized_metric)
        code = self._single_value(dataframe, "code")
        title = f"{code} {label}推移" if code else f"{label}推移"
        figure = go.Figure(
            go.Scatter(
                x=dataframe["fiscal_period"],
                y=dataframe[normalized_metric],
                mode="lines+markers",
                name=label,
                line={"width": 2},
                hovertemplate=self._metric_hover_template(
                    normalized_metric,
                    label,
                ),
            )
        )
        self._apply_common_layout(
            figure,
            title=title,
            x_title="決算期",
            y_title=label,
        )
        self._apply_metric_axis_format(figure, normalized_metric)
        return figure

    def create_comparison_chart(
        self,
        metrics: pd.DataFrame,
        codes: Sequence[str],
        metric_name: str,
    ) -> go.Figure:
        """複数企業の財務指標を同一グラフ上で比較する。"""

        normalized_metric = self._normalize_metric_name(metric_name)
        if metrics.empty or not codes:
            return self._empty_figure("比較できる財務指標データがありません")
        self._require_columns(
            metrics,
            {"code", "fiscal_period", normalized_metric},
        )

        normalized_codes = [code.strip() for code in codes if code.strip()]
        dataframe = metrics[metrics["code"].astype(str).isin(normalized_codes)].copy()
        if dataframe.empty:
            return self._empty_figure("選択した企業のデータがありません")

        label = self.METRIC_LABELS.get(normalized_metric, normalized_metric)
        figure = go.Figure()
        for code in normalized_codes:
            company_metrics = dataframe[
                dataframe["code"].astype(str) == code
            ].sort_values("fiscal_period")
            if company_metrics.empty:
                continue
            figure.add_trace(
                go.Scatter(
                    x=company_metrics["fiscal_period"],
                    y=company_metrics[normalized_metric],
                    mode="lines+markers",
                    name=code,
                    hovertemplate=self._metric_hover_template(
                        normalized_metric,
                        label,
                        include_code=True,
                    ),
                )
            )

        self._apply_common_layout(
            figure,
            title=f"企業別 {label}比較",
            x_title="決算期",
            y_title=label,
        )
        self._apply_metric_axis_format(figure, normalized_metric)
        return figure

    @staticmethod
    def _price_dataframe(
        prices: Iterable[DailyPrice] | pd.DataFrame,
    ) -> pd.DataFrame:
        if isinstance(prices, pd.DataFrame):
            return prices.copy()
        return pd.DataFrame(
            [
                {
                    "code": price.code,
                    "date": price.date,
                    "close": price.close,
                    "adjusted_close": price.adjusted_close,
                }
                for price in prices
            ]
        )

    @staticmethod
    def _require_columns(dataframe: pd.DataFrame, columns: set[str]) -> None:
        missing = columns.difference(dataframe.columns)
        if missing:
            names = ", ".join(sorted(missing))
            raise ValueError(f"required dataframe columns are missing: {names}")

    @staticmethod
    def _normalize_metric_name(metric_name: str) -> str:
        normalized = metric_name.strip().lower()
        if not normalized:
            raise ValueError("metric_name must not be empty")
        return normalized

    @staticmethod
    def _single_value(dataframe: pd.DataFrame, column: str) -> str | None:
        if column not in dataframe.columns:
            return None
        values = dataframe[column].dropna().astype(str).unique()
        return values[0] if len(values) == 1 else None

    @classmethod
    def _metric_hover_template(
        cls,
        metric_name: str,
        label: str,
        *,
        include_code: bool = False,
    ) -> str:
        value_format = ".2%" if metric_name in cls.PERCENTAGE_METRICS else ",.2f"
        prefix = "%{fullData.name}<br>" if include_code else ""
        return (
            prefix
            + "決算期: %{x}<br>"
            + f"{label}: %{{y:{value_format}}}<extra></extra>"
        )

    @classmethod
    def _apply_metric_axis_format(
        cls,
        figure: go.Figure,
        metric_name: str,
    ) -> None:
        if metric_name in cls.PERCENTAGE_METRICS:
            figure.update_yaxes(tickformat=".1%")

    @staticmethod
    def _apply_common_layout(
        figure: go.Figure,
        *,
        title: str,
        x_title: str,
        y_title: str,
    ) -> None:
        figure.update_layout(
            title=title,
            template="plotly_white",
            hovermode="x unified",
            xaxis_title=x_title,
            yaxis_title=y_title,
            margin={"l": 40, "r": 20, "t": 60, "b": 40},
            legend={
                "orientation": "h",
                "yanchor": "bottom",
                "y": 1.02,
                "xanchor": "right",
                "x": 1,
            },
        )

    @staticmethod
    def _empty_figure(message: str) -> go.Figure:
        figure = go.Figure()
        figure.add_annotation(
            text=message,
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            showarrow=False,
        )
        figure.update_layout(
            template="plotly_white",
            xaxis={"visible": False},
            yaxis={"visible": False},
        )
        return figure
