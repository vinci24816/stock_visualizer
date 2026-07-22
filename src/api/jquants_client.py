"""J-Quants API v2 client."""

from collections.abc import Mapping
from datetime import date, datetime
from typing import Any, Self

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

DateLike = str | date | datetime


class JQuantsAPIError(RuntimeError):
    """J-Quants APIへのリクエストまたはレスポンスが不正な場合の例外。"""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code


class JQuantsClient:
    """J-Quants API v2とのHTTP通信を担当するクライアント。"""

    DEFAULT_BASE_URL = "https://api.jquants.com/v2"
    RETRY_STATUS_CODES = (429, 500, 502, 503, 504)

    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        *,
        timeout: float = 30.0,
        session: requests.Session | None = None,
    ) -> None:
        normalized_api_key = api_key.strip()
        if not normalized_api_key:
            raise ValueError("api_key must not be empty")
        if timeout <= 0:
            raise ValueError("timeout must be greater than zero")

        self._api_key = normalized_api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._owns_session = session is None
        self._session = session or self._create_session()

    @staticmethod
    def _create_session() -> requests.Session:
        """一時障害とレート制限を再試行するHTTP Sessionを作成する。"""

        retry = Retry(
            total=3,
            connect=3,
            read=3,
            status=3,
            backoff_factor=0.5,
            status_forcelist=JQuantsClient.RETRY_STATUS_CODES,
            allowed_methods=frozenset({"GET"}),
            respect_retry_after_header=True,
        )
        adapter = HTTPAdapter(max_retries=retry)
        session = requests.Session()
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    @property
    def headers(self) -> dict[str, str]:
        """APIリクエストで共通利用する認証ヘッダーを返す。"""

        return {
            "x-api-key": self._api_key,
            "Accept": "application/json",
            "User-Agent": "stock-visualizer/0.1",
        }

    def authenticate(self) -> bool:
        """軽量な銘柄照会を行い、APIキーが利用可能か確認する。

        v2にはログインやトークン発行処理がないため、このメソッドは
        APIキーを送信して正常レスポンスを受け取れるかだけを検証する。
        """

        self.get_listed_info(code="86970")
        return True

    def get_listed_info(
        self,
        code: str | None = None,
        target_date: DateLike | None = None,
    ) -> list[dict[str, Any]]:
        """上場銘柄情報を取得する。"""

        params: dict[str, str] = {}
        if code:
            params["code"] = code.strip()
        if target_date is not None:
            params["date"] = self._format_date(target_date)
        return self._get_paginated("/equities/master", params)

    def get_daily_quotes(
        self,
        code: str,
        from_date: DateLike | None = None,
        to_date: DateLike | None = None,
        *,
        target_date: DateLike | None = None,
    ) -> list[dict[str, Any]]:
        """指定銘柄の日次株価を日付または期間で取得する。"""

        normalized_code = code.strip()
        if not normalized_code:
            raise ValueError("code must not be empty")
        if target_date is not None and (from_date is not None or to_date is not None):
            raise ValueError("target_date and date range cannot be specified together")

        params = {"code": normalized_code}
        if target_date is not None:
            params["date"] = self._format_date(target_date)
        else:
            if from_date is not None:
                params["from"] = self._format_date(from_date)
            if to_date is not None:
                params["to"] = self._format_date(to_date)

        return self._get_paginated("/equities/bars/daily", params)

    def get_statements(
        self,
        code: str,
        disclosure_date: DateLike | None = None,
    ) -> list[dict[str, Any]]:
        """指定銘柄の財務情報サマリーを取得する。"""

        normalized_code = code.strip()
        if not normalized_code:
            raise ValueError("code must not be empty")

        params = {"code": normalized_code}
        if disclosure_date is not None:
            params["date"] = self._format_date(disclosure_date)
        return self._get_paginated("/fins/summary", params)

    def get_financial_summary(
        self,
        code: str,
        disclosure_date: DateLike | None = None,
    ) -> list[dict[str, Any]]:
        """get_statements()の意味を明確にした別名。"""

        return self.get_statements(code, disclosure_date)

    def _get_paginated(
        self,
        path: str,
        params: Mapping[str, str] | None = None,
    ) -> list[dict[str, Any]]:
        """pagination_keyを追跡し、全ページのdataを結合して返す。"""

        query = dict(params or {})
        records: list[dict[str, Any]] = []

        while True:
            payload = self._get(path, query)
            page_data = payload.get("data", [])
            if not isinstance(page_data, list) or not all(
                isinstance(item, dict) for item in page_data
            ):
                raise JQuantsAPIError("API response field 'data' must be a list")
            records.extend(page_data)

            pagination_key = payload.get("pagination_key")
            if not pagination_key:
                return records
            query["pagination_key"] = str(pagination_key)

    def _get(self, path: str, params: Mapping[str, str]) -> dict[str, Any]:
        """GETリクエストを実行し、検証済みJSONオブジェクトを返す。"""

        url = f"{self.base_url}/{path.lstrip('/')}"
        try:
            response = self._session.get(
                url,
                params=dict(params),
                headers=self.headers,
                timeout=self.timeout,
            )
        except requests.RequestException as error:
            raise JQuantsAPIError(f"J-Quants API request failed: {error}") from error

        if not response.ok:
            message = self._extract_error_message(response)
            raise JQuantsAPIError(
                f"J-Quants API returned HTTP {response.status_code}: {message}",
                status_code=response.status_code,
            )

        try:
            payload = response.json()
        except requests.exceptions.JSONDecodeError as error:
            raise JQuantsAPIError("J-Quants API returned invalid JSON") from error
        if not isinstance(payload, dict):
            raise JQuantsAPIError("J-Quants API response must be a JSON object")
        return payload

    @staticmethod
    def _extract_error_message(response: requests.Response) -> str:
        """エラーレスポンスから利用者向けメッセージを取り出す。"""

        try:
            payload = response.json()
            if isinstance(payload, dict) and payload.get("message"):
                return str(payload["message"])
        except requests.exceptions.JSONDecodeError:
            pass
        return response.text or response.reason

    @staticmethod
    def _format_date(value: DateLike) -> str:
        """APIが受け付けるYYYYMMDD形式へ日付を正規化する。"""

        if isinstance(value, datetime):
            return value.strftime("%Y%m%d")
        if isinstance(value, date):
            return value.strftime("%Y%m%d")

        normalized = value.strip()
        for date_format in ("%Y%m%d", "%Y-%m-%d"):
            try:
                return datetime.strptime(normalized, date_format).strftime("%Y%m%d")
            except ValueError:
                continue
        raise ValueError("date must be YYYYMMDD or YYYY-MM-DD")

    def close(self) -> None:
        """このクライアントが作成したHTTP Sessionを閉じる。"""

        if self._owns_session:
            self._session.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        self.close()
