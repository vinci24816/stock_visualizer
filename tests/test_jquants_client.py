from datetime import date

import pytest
import requests
import responses

from src.api.jquants_client import JQuantsAPIError, JQuantsClient


@responses.activate
def test_get_listed_info_sends_api_key_and_parameters() -> None:
    responses.get(
        "https://api.jquants.com/v2/equities/master",
        json={"data": [{"Code": "86970", "CoName": "JPX"}]},
        status=200,
    )
    client = JQuantsClient("secret-key")

    records = client.get_listed_info(code="86970", target_date="2025-01-06")

    request = responses.calls[0].request
    assert request.headers["x-api-key"] == "secret-key"
    assert "code=86970" in request.url
    assert "date=20250106" in request.url
    assert records == [{"Code": "86970", "CoName": "JPX"}]


@responses.activate
def test_get_daily_quotes_follows_pagination() -> None:
    url = "https://api.jquants.com/v2/equities/bars/daily"
    responses.get(
        url,
        json={"data": [{"Code": "86970", "Date": "2025-01-06"}], "pagination_key": "next"},
        status=200,
    )
    responses.get(
        url,
        json={"data": [{"Code": "86970", "Date": "2025-01-07"}]},
        status=200,
    )
    client = JQuantsClient("secret-key")

    records = client.get_daily_quotes(
        "86970",
        from_date=date(2025, 1, 6),
        to_date="2025-01-07",
    )

    assert len(records) == 2
    assert "pagination_key=next" in responses.calls[1].request.url


@responses.activate
def test_get_statements_uses_financial_summary_endpoint() -> None:
    responses.get(
        "https://api.jquants.com/v2/fins/summary",
        json={"data": [{"Code": "86970", "DiscDate": "2025-01-30"}]},
        status=200,
    )

    records = JQuantsClient("secret-key").get_statements("86970")

    assert records[0]["Code"] == "86970"


@responses.activate
def test_api_error_contains_status_and_message() -> None:
    responses.get(
        "https://api.jquants.com/v2/equities/master",
        json={"message": "invalid parameter"},
        status=400,
    )

    with pytest.raises(JQuantsAPIError, match="invalid parameter") as error:
        JQuantsClient("secret-key").get_listed_info()

    assert error.value.status_code == 400


def test_rejects_conflicting_daily_quote_dates() -> None:
    client = JQuantsClient("secret-key", session=requests.Session())

    with pytest.raises(ValueError, match="cannot be specified together"):
        client.get_daily_quotes(
            "86970",
            from_date="20250101",
            target_date="20250106",
        )


def test_rejects_invalid_date() -> None:
    client = JQuantsClient("secret-key", session=requests.Session())

    with pytest.raises(ValueError, match="YYYYMMDD"):
        client.get_listed_info(target_date="2025/01/06")
