"""TICKET-065 日线 Provider、缓存水位和容错契约测试。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pandas as pd
import pytest
import requests

from zhanfa.data.daily_providers import (
    DAILY_COLUMNS,
    DailyProviderError,
    DailyProviderResponseError,
    DailyProviderUnavailable,
    ProviderResult,
    TencentDailyProvider,
    build_daily_provider,
    tencent_symbol,
)
from zhanfa.data.fetcher import Fetcher
from zhanfa.data.store import Store


class FakeResponse:
    def __init__(self, payload=None, status_code: int = 200, json_error: bool = False):
        self.payload = payload
        self.status_code = status_code
        self.json_error = json_error

    def json(self):
        if self.json_error:
            raise ValueError("not json")
        return self.payload


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self.trust_env = True

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def tencent_payload(
    symbol: str = "sh600519",
    key: str = "qfqday",
    rows: list[list[object]] | None = None,
):
    if rows is None:
        rows = [
            [
                "2024-01-02",
                "10.00",
                "10.50",
                "11.00",
                "9.50",
                "1234.00",
                {},
                "1.25",
                "567.89",
                "",
            ]
        ]
    return {"code": 0, "msg": "", "data": {symbol: {key: rows}}}


@pytest.mark.parametrize(
    ("code", "is_index", "expected"),
    [
        ("600519", False, "sh600519"),
        ("688001", False, "sh688001"),
        ("000001", False, "sz000001"),
        ("300750", False, "sz300750"),
        ("920002", False, "bj920002"),
        ("000300", True, "sh000300"),
        ("399001", True, "sz399001"),
    ],
)
def test_tencent_symbol_mapping(code, is_index, expected):
    assert tencent_symbol(code, is_index=is_index) == expected


@pytest.mark.parametrize(
    ("adjust", "key"), [("", "day"), ("qfq", "qfqday"), ("hfq", "hfqday")]
)
def test_tencent_provider_accepts_adjusted_response_keys(adjust, key, monkeypatch):
    monkeypatch.setenv("ZHANFA_DAILY_MAX_RETRIES", "0")
    session = FakeSession([FakeResponse(tencent_payload(key=key))])
    provider = TencentDailyProvider(session=session)

    result = provider.fetch("600519", "20240101", "20240105", adjust)

    assert list(result.frame.columns) == DAILY_COLUMNS
    assert result.frame.iloc[0].to_dict() == {
        "open": 10.0,
        "high": 11.0,
        "low": 9.5,
        "close": 10.5,
        "volume": 1234.0,
        "amount": 567.89,
        "turnover": 1.25,
    }
    assert result.request_count == 1
    assert session.calls[0][1]["timeout"] == (3.05, 10.0)


def test_tencent_provider_uses_beijing_security_key(monkeypatch):
    monkeypatch.setenv("ZHANFA_DAILY_MAX_RETRIES", "0")
    session = FakeSession(
        [FakeResponse(tencent_payload(symbol="bj920002", key="day"))]
    )
    provider = TencentDailyProvider(session=session)

    result = provider.fetch("920002", "20240101", "20240105", "")

    assert len(result.frame) == 1
    assert "bj920002" in session.calls[0][1]["params"]["param"]


@pytest.mark.parametrize(
    "payload",
    [
        {"code": 1, "msg": "bad", "data": {}},
        {"code": 0, "msg": "", "data": {}},
        tencent_payload(rows=[]),
        tencent_payload(rows=[["2024-01-02", "10"]]),
        tencent_payload(
            rows=[
                ["2024-01-02", "bad", "10", "11", "9", "1", {}, "1", "2"]
            ]
        ),
    ],
)
def test_tencent_provider_rejects_invalid_business_payload(payload, monkeypatch):
    monkeypatch.setenv("ZHANFA_DAILY_MAX_RETRIES", "0")
    provider = TencentDailyProvider(session=FakeSession([FakeResponse(payload)]))
    with pytest.raises(DailyProviderResponseError):
        provider.fetch("600519", "20240101", "20240105", "qfq")


@pytest.mark.parametrize("status_code", [400, 429, 500, 503])
def test_tencent_provider_rejects_http_errors(status_code, monkeypatch):
    monkeypatch.setenv("ZHANFA_DAILY_MAX_RETRIES", "0")
    provider = TencentDailyProvider(
        session=FakeSession([FakeResponse(status_code=status_code)])
    )
    with pytest.raises(DailyProviderError):
        provider.fetch("600519", "20240101", "20240105", "qfq")


def test_tencent_provider_retries_timeout_with_backoff(monkeypatch):
    monkeypatch.setenv("ZHANFA_DAILY_MAX_RETRIES", "1")
    monkeypatch.setenv("ZHANFA_DAILY_BACKOFF_BASE", "0.5")
    delays = []
    session = FakeSession(
        [requests.Timeout("slow"), FakeResponse(tencent_payload())]
    )
    provider = TencentDailyProvider(
        session=session, sleep=delays.append, jitter=lambda: 0.0
    )

    result = provider.fetch("600519", "20240101", "20240105", "qfq")

    assert result.request_count == 2
    assert result.retry_count == 1
    assert delays == [0.5]


def test_tencent_provider_retries_non_json(monkeypatch):
    monkeypatch.setenv("ZHANFA_DAILY_MAX_RETRIES", "1")
    session = FakeSession(
        [FakeResponse(json_error=True), FakeResponse(tencent_payload())]
    )
    provider = TencentDailyProvider(session=session, sleep=lambda _: None)
    assert provider.fetch("600519", "20240101", "20240105", "qfq").retry_count == 1


def test_tencent_provider_opens_circuit(monkeypatch):
    monkeypatch.setenv("ZHANFA_DAILY_MAX_RETRIES", "0")
    monkeypatch.setenv("ZHANFA_DAILY_CIRCUIT_FAILURES", "1")
    provider = TencentDailyProvider(
        session=FakeSession([requests.Timeout("slow")])
    )
    with pytest.raises(DailyProviderError):
        provider.fetch("600519", "20240101", "20240105", "qfq")
    with pytest.raises(DailyProviderUnavailable):
        provider.fetch("600519", "20240101", "20240105", "qfq")


def test_tencent_provider_requires_risk_acceptance_outside_research(monkeypatch):
    monkeypatch.setenv("ZHANFA_USAGE_MODE", "production")
    monkeypatch.delenv("ZHANFA_TENCENT_RISK_ACCEPTED", raising=False)
    with pytest.raises(DailyProviderUnavailable, match="authorization review"):
        build_daily_provider("tencent")


def test_akshare_primary_disables_unapproved_tencent_fallback(monkeypatch):
    monkeypatch.setenv("ZHANFA_USAGE_MODE", "commercial")
    monkeypatch.delenv("ZHANFA_TENCENT_RISK_ACCEPTED", raising=False)
    fetcher = Fetcher(store=mock_store(), daily_provider="akshare")
    assert fetcher.daily_fallback is None


def test_tencent_provider_slices_network_rows(monkeypatch):
    monkeypatch.setenv("ZHANFA_DAILY_MAX_RETRIES", "0")
    rows = [
        ["2023-12-29", "9", "9", "9", "9", "1", {}, "1", "1"],
        ["2024-01-02", "10", "10", "10", "10", "1", {}, "1", "1"],
        ["2024-01-08", "11", "11", "11", "11", "1", {}, "1", "1"],
    ]
    provider = TencentDailyProvider(
        session=FakeSession([FakeResponse(tencent_payload(rows=rows))])
    )
    frame = provider.fetch("600519", "20240101", "20240105", "qfq").frame
    assert frame.index.tolist() == [pd.Timestamp("2024-01-02")]


class StubProvider:
    def __init__(self, frame: pd.DataFrame, name: str = "tencent"):
        self.name = name
        self.frame = frame
        self.calls = []
        self.fail_codes: set[str] = set()

    def fetch(self, code, start, end, adjust, *, is_index=False):
        self.calls.append((code, start, end, adjust, is_index))
        if code in self.fail_codes:
            raise DailyProviderError(f"failed {code}")
        return ProviderResult(self.frame.copy(), self.name, 1, 0, 0.01)


def daily_frame(dates=("2024-01-02", "2024-01-03")):
    return pd.DataFrame(
        {
            "open": [10.0] * len(dates),
            "high": [11.0] * len(dates),
            "low": [9.0] * len(dates),
            "close": [10.5] * len(dates),
            "volume": [1000.0] * len(dates),
            "amount": [100.0] * len(dates),
            "turnover": [1.0] * len(dates),
        },
        index=pd.to_datetime(list(dates)),
    )


def mock_store() -> MagicMock:
    store = MagicMock(spec=Store)
    store.load.return_value = None
    store.load_metadata.return_value = None
    store.mtime.return_value = datetime.now(timezone.utc)
    return store


def test_fetcher_slices_old_cache_to_default_research_window():
    store = mock_store()
    cached = daily_frame(("2017-12-29", "2018-01-02"))
    store.load.return_value = cached
    fetcher = Fetcher(store=store, daily_provider=StubProvider(daily_frame()))

    result = fetcher.daily("600519")

    assert result.index.tolist() == [pd.Timestamp("2018-01-02")]
    assert fetcher.daily_status("600519").cache_hit is True


def test_fetcher_stale_cache_uses_waterline_increment():
    store = mock_store()
    stale = daily_frame(("2024-01-02", "2024-01-10"))
    store.load.side_effect = [None, stale]
    store.load_metadata.return_value = {
        "provider": "tencent",
        "adjust": "qfq",
        "full_refresh_at": datetime.now(timezone.utc).isoformat(),
    }
    provider = StubProvider(daily_frame(("2024-01-10", "2024-01-11")))
    fetcher = Fetcher(store=store, daily_provider=provider)
    fetcher.daily_fallback = None

    result = fetcher.daily("600519", start="20240102", end="20240131")

    assert provider.calls[0][1] == "20240103"
    assert result.index[-1] == pd.Timestamp("2024-01-11")
    store.save.assert_called_once()
    store.save_metadata.assert_called_once()


def test_fetcher_adjust_change_forces_same_source_full_refresh():
    store = mock_store()
    store.load.return_value = daily_frame(("2024-01-02", "2024-01-10"))
    store.load_metadata.return_value = {
        "provider": "tencent",
        "adjust": "qfq",
        "coverage_start": "20240101",
        "full_refresh_at": datetime.now(timezone.utc).isoformat(),
    }
    provider = StubProvider(daily_frame())
    fetcher = Fetcher(store=store, daily_provider=provider)
    fetcher.daily_fallback = None

    fetcher.daily("600519", start="20240101", end="20240131", adjust="")

    assert provider.calls[0][1] == "20240101"


def test_fetcher_qfq_calibration_period_forces_full_refresh():
    store = mock_store()
    stale = daily_frame(("2024-01-02", "2024-01-10"))
    store.load.side_effect = [None, stale]
    store.load_metadata.return_value = {
        "provider": "tencent",
        "adjust": "qfq",
        "coverage_start": "20240101",
        "full_refresh_at": (
            datetime.now(timezone.utc) - timedelta(days=31)
        ).isoformat(),
    }
    provider = StubProvider(daily_frame())
    fetcher = Fetcher(store=store, daily_provider=provider)
    fetcher.daily_fallback = None

    fetcher.daily("600519", start="20240101", end="20240131")

    assert provider.calls[0][1] == "20240101"


def test_fetcher_does_not_write_empty_provider_result():
    store = mock_store()
    provider = StubProvider(daily_frame().iloc[0:0])
    fetcher = Fetcher(store=store, daily_provider=provider)
    fetcher.daily_fallback = None

    with pytest.raises(DailyProviderError, match="Refusing to write empty"):
        fetcher.daily("600519", start="20240101", end="20240131")
    store.save.assert_not_called()


def test_fetcher_batch_continues_after_single_security_failure(monkeypatch):
    monkeypatch.setenv("ZHANFA_DAILY_MAX_CONCURRENCY", "2")
    store = mock_store()
    provider = StubProvider(daily_frame())
    provider.fail_codes.add("000002")
    fetcher = Fetcher(store=store, daily_provider=provider)
    fetcher.daily_fallback = None

    result = fetcher.daily_batch(
        ["000001", "000002"], start="20240101", end="20240131"
    )

    assert set(result) == {"000001"}
    assert "000002" in fetcher.last_batch_errors


def test_fetcher_batch_has_hard_code_limit(monkeypatch):
    monkeypatch.setenv("ZHANFA_DAILY_BATCH_MAX_CODES", "1")
    fetcher = Fetcher(store=mock_store(), daily_provider=StubProvider(daily_frame()))
    with pytest.raises(ValueError, match="hard limit"):
        fetcher.daily_batch(["000001", "000002"])
