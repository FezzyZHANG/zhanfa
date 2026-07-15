"""Fixture-only FastAPI runtime used by the Playwright launcher."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from zhanfa.data.daily_providers import (
    DAILY_COLUMNS,
    ProviderResult,
    slice_daily_frame,
)


class FixtureDailyProvider:
    """Deterministic in-process replacement for every external daily provider."""

    name = "fixture"

    def fetch(
        self,
        code: str,
        start: str,
        end: str,
        adjust: str,
        *,
        is_index: bool = False,
    ) -> ProviderResult:
        del code, adjust, is_index
        index = pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"])
        frame = pd.DataFrame(
            {
                "open": [10.0, 10.5, 10.8],
                "high": [10.8, 11.0, 11.2],
                "low": [9.8, 10.2, 10.6],
                "close": [10.5, 10.8, 11.0],
                "volume": [1000.0, 1100.0, 1200.0],
                "amount": [10_500.0, 11_880.0, 13_200.0],
                "turnover": [1.0, 1.1, 1.2],
            },
            index=index,
        )[DAILY_COLUMNS]
        frame.index.name = "date"
        frame = slice_daily_frame(frame, start, end)
        return ProviderResult(
            frame=frame,
            provider=self.name,
            request_count=0,
            retry_count=0,
            elapsed_seconds=0.0,
        )


def create_e2e_app(data_dir: Path, *, use_fixture_provider: bool = True):
    """Create an empty isolated app, installing fixtures unless live mode is used."""
    provider = FixtureDailyProvider()
    if use_fixture_provider:
        from zhanfa.data import fetcher as fetcher_module

        fetcher_module.build_daily_provider = lambda _name: provider

        def fixture_stock_list(fetcher):
            if fetcher.store.base.resolve() != data_dir.resolve():
                raise RuntimeError(
                    f"Fixture Fetcher store escaped E2E data dir: {fetcher.store.base}"
                )
            frame = pd.DataFrame(
                {
                    "code": ["600519"],
                    "name": ["贵州茅台"],
                    "industry": ["白酒"],
                }
            )
            fetcher.store.save("stock_list", frame, "meta")
            return frame.copy()

        fetcher_module.Fetcher.stock_list = fixture_stock_list

    from zhanfa.api import create_app
    from zhanfa.db.base import init_db
    from zhanfa.db.register_strategies import register_strategies

    init_db()
    register_strategies()
    return create_app(init_database=False, start_scheduler=False)
