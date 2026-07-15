"""Fixture-only FastAPI runtime used by the Playwright launcher."""

from __future__ import annotations

from datetime import date
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
    """Create and seed an isolated app, installing fixtures unless live mode is used."""
    provider = FixtureDailyProvider()
    if use_fixture_provider:
        from zhanfa.data import fetcher as fetcher_module

        fetcher_module.build_daily_provider = lambda _name: provider

    from zhanfa.api import create_app
    from zhanfa.data.store import Store
    from zhanfa.db.base import SessionLocal, init_db
    from zhanfa.db.models import Stock
    from zhanfa.db.register_strategies import register_strategies

    init_db()
    register_strategies()
    with SessionLocal() as session:
        session.merge(
            Stock(
                code="600519",
                name="贵州茅台",
                exchange="SH",
                listed_date=date(2001, 8, 27),
            )
        )
        session.commit()

    fixture = provider.fetch("600519", "20240101", "20240131", "qfq")
    store = Store(str(data_dir))
    store.save("600519", fixture.frame, "daily")
    store.save_metadata(
        "600519",
        "daily",
        {
            "provider": provider.name,
            "adjust": "qfq",
            "request_count": fixture.request_count,
            "retry_count": fixture.retry_count,
        },
    )
    return create_app(init_database=False, start_scheduler=False)
