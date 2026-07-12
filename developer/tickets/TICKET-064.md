# TICKET-064: Default akshare requests must not inherit system proxy

> Source: 2026-07-12 runtime log | Priority: P1

## Symptom

Daily data refresh logged a per-symbol failure:

```text
zhanfa.automation.workflows: update 000049 failed: HTTPSConnectionPool(host='push2his.eastmoney.com', port=443) ... ProxyError('Unable to connect to proxy')
```

The workflow error handling kept the batch alive, but the failed symbol was counted as failed immediately.

## Root Cause

The Python process inherited `HTTP_PROXY` / `HTTPS_PROXY` values from the host environment. akshare uses HTTP clients that honor these proxy environment variables, so Eastmoney traffic was routed through the local proxy by default. When that proxy disconnected, the data refresh failed even though zhanfa had not explicitly configured a proxy.

## Scope

- [x] Make zhanfa's akshare calls ignore inherited proxy environment variables by default.
- [x] Keep an explicit opt-in for users who really need a proxy: `ZHANFA_AKSHARE_USE_PROXY=true`.
- [x] Apply the behavior to all `Fetcher` akshare calls, not only daily data.
- [x] Add regression tests for default no-proxy behavior and explicit proxy opt-in.
- [x] Document the environment variable and operational diagnosis.

## Verification

- `uv run pytest tests/test_data/test_fetcher.py -q` - passed
- `uv run ruff check src/zhanfa/data/fetcher.py tests/test_data/test_fetcher.py` - passed
- `uv run mypy src/` - passed
- `uv run pytest -q` - 348 passed, 233 warnings

## Residual Risk

This change prevents accidental proxy inheritance. It does not guarantee Eastmoney availability when the upstream service itself is down or rate limited; those failures will still be counted by the existing per-symbol workflow failure handling.

## Status

Completed
