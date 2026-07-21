"""Streamlit dashboard composition."""

from dataclasses import dataclass

import streamlit as st

from src.db.repositories import CompanyRepository
from src.db.schema import Company
from src.ui.components import render_company_table as render_company_table_component


@dataclass(frozen=True)
class DashboardFilters:
    """サイドバーで選択された企業一覧の絞り込み条件。"""

    keyword: str = ""
    nikkei225_only: bool = True


class DashboardApp:
    """株価・財務指標ダッシュボードのStreamlit画面を構成する。"""

    def __init__(self, company_repository: CompanyRepository) -> None:
        self._company_repository = company_repository

    def run(self) -> None:
        """ページ全体を構築し、現在のデータを表示する。"""

        st.set_page_config(
            page_title="日経225 財務指標可視化",
            page_icon="📈",
            layout="wide",
        )
        st.title("日経225 財務指標可視化")
        st.caption("J-Quantsの株価・財務データを確認するためのダッシュボード")

        filters = self.render_sidebar()
        companies = self._load_companies(filters)
        self.render_data_status(companies)
        self.render_company_table(companies)

        st.divider()
        st.info("株価・財務指標グラフは、データ取得機能の実装後に追加します。")

    def render_sidebar(self) -> DashboardFilters:
        """企業検索と日経225絞り込み条件をサイドバーに表示する。"""

        with st.sidebar:
            st.header("表示条件")
            keyword = st.text_input(
                "企業を検索",
                placeholder="会社名または証券コード",
            )
            nikkei225_only = st.checkbox(
                "日経225採用企業のみ",
                value=True,
            )

        return DashboardFilters(
            keyword=keyword,
            nikkei225_only=nikkei225_only,
        )

    def render_company_table(self, companies: list[Company]) -> None:
        """企業一覧コンポーネントへ表示処理を委譲する。"""

        render_company_table_component(companies)

    def render_data_status(self, companies: list[Company]) -> None:
        """現在の検索条件に一致する企業数を表示する。"""

        st.metric("表示銘柄数", len(companies))

    def _load_companies(self, filters: DashboardFilters) -> list[Company]:
        """Repositoryから企業を取得し、画面条件で絞り込む。"""

        if filters.keyword:
            companies = self._company_repository.search(filters.keyword)
            if filters.nikkei225_only:
                return [company for company in companies if company.is_nikkei225]
            return companies

        if filters.nikkei225_only:
            return self._company_repository.find_nikkei225()
        return self._company_repository.find_all()
