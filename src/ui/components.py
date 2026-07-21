"""Streamlit画面で再利用する表示コンポーネント。"""

import pandas as pd
import streamlit as st

from src.db.schema import Company


def render_company_table(companies: list[Company]) -> None:
    """日経225銘柄を含む企業一覧をインタラクティブな表で表示する。

    Args:
        companies: 表示対象の企業ORMインスタンス。呼び出し側で検索や
            日経225絞り込みを行った結果を渡す。
    """

    st.subheader("日経225銘柄一覧")
    if not companies:
        st.warning(
            "表示できる企業データがありません。"
            "先にJ-QuantsまたはCSVから企業情報を取り込んでください。"
        )
        return

    dataframe = pd.DataFrame(
        [
            {
                "証券コード": company.code,
                "会社名": company.company_name,
                "業種": company.sector or "",
                "市場": company.market or "",
                "日経225": company.is_nikkei225,
            }
            for company in companies
        ]
    )
    st.dataframe(
        dataframe,
        width="stretch",
        hide_index=True,
        column_config={
            "日経225": st.column_config.CheckboxColumn(
                "日経225",
                disabled=True,
            )
        },
    )
