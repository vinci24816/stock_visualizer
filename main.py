"""Streamlit application entry point."""

import streamlit as st

from src.config.setting import Settings
from src.db.database import Database
from src.db.repositories import CompanyRepository
from src.ui.app import DashboardApp


@st.cache_resource
def create_dashboard_app() -> DashboardApp:
    """アプリ全体で再利用するDB接続と画面オブジェクトを初期化する。"""

    settings = Settings.load()
    settings.ensure_directories()

    database = Database(settings.database_url)
    database.check_connection()
    database.create_tables()

    return DashboardApp(CompanyRepository(database))


create_dashboard_app().run()
