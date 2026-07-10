"""本地数据缓存 - 基于 parquet 格式"""

import logging
import os
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

logger = logging.getLogger(__name__)

_SAFE_PATH_SEGMENT = re.compile(r"^[A-Za-z0-9_.-]+$")


class Store:
    """本地 parquet 缓存，按 {base_dir}/{freq}/{code}.parquet 组织"""

    def __init__(self, base_dir: str = "data"):
        self.base = Path(base_dir)

    def _path(self, code: str, freq: str = "daily") -> Path:
        self._validate_path_segment(code, "code")
        self._validate_path_segment(freq, "freq")
        return self.base / freq / f"{code}.parquet"

    @staticmethod
    def _validate_path_segment(value: str, field: str) -> None:
        text = str(value)
        if (
            not text
            or ".." in text
            or "/" in text
            or "\\" in text
            or ":" in text
            or not _SAFE_PATH_SEGMENT.fullmatch(text)
        ):
            raise ValueError(f"Invalid cache {field}: {value!r}")

    def save(self, code: str, df: pd.DataFrame, freq: str = "daily") -> None:
        path = self._path(code, freq)
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(path, index=True)

    def load(self, code: str, freq: str = "daily", max_age: timedelta | None = None) -> pd.DataFrame | None:
        path = self._path(code, freq)
        if not path.exists():
            return None
        if max_age is not None:
            mtime = datetime.fromtimestamp(os.path.getmtime(path), tz=timezone.utc)
            if datetime.now(timezone.utc) - mtime > max_age:
                return None
        try:
            return pd.read_parquet(path)
        except Exception:
            logger.warning("Failed to read parquet file (possibly corrupted): %s", path, exc_info=True)
            return None

    def exists(self, code: str, freq: str = "daily") -> bool:
        return self._path(code, freq).exists()

    def mtime(self, code: str, freq: str = "daily") -> datetime | None:
        """Return the last-modified time of a cached parquet file, or None."""
        path = self._path(code, freq)
        try:
            return datetime.fromtimestamp(os.path.getmtime(path), tz=timezone.utc)
        except OSError:
            return None

    def codes(self, freq: str = "daily") -> list[str]:
        p = self.base / freq
        if not p.exists():
            return []
        return [f.stem for f in p.glob("*.parquet")]

    def delete(self, code: str, freq: str = "daily") -> None:
        path = self._path(code, freq)
        if path.exists():
            path.unlink()

    def last_row(self, code: str, freq: str = "daily") -> dict | None:
        """Read only the last row of a parquet file via pyarrow (avoids full DataFrame load)."""
        path = self._path(code, freq)
        if not path.exists():
            return None
        pf = pq.ParquetFile(path)
        last_rg = pf.read_row_group(pf.num_row_groups - 1)
        row = {}
        for col_name in last_rg.schema.names:
            col_data = last_rg.column(col_name).to_pylist()
            row[col_name] = col_data[-1] if col_data else None
        return row

    def last_close(self, code: str, freq: str = "daily") -> dict | None:
        """Read only the last 2 'close' values for a quick price + change_pct calc."""
        path = self._path(code, freq)
        if not path.exists():
            return None
        pf = pq.ParquetFile(path)
        last_rg = pf.read_row_group(pf.num_row_groups - 1)
        close_data = last_rg.column("close").to_pylist()
        if not close_data:
            return None
        result = {"close": close_data[-1]}
        if len(close_data) >= 2:
            result["prev_close"] = close_data[-2]
        # If only 1 row in the last group, try the previous group
        elif pf.num_row_groups >= 2 and len(close_data) == 1:
            prev_rg = pf.read_row_group(pf.num_row_groups - 2)
            prev_close_data = prev_rg.column("close").to_pylist()
            if prev_close_data:
                result["prev_close"] = prev_close_data[-1]
        return result

    def date_range(self, code: str, freq: str = "daily") -> dict | None:
        """Get date range and row count from parquet metadata + first/last row groups."""
        path = self._path(code, freq)
        if not path.exists():
            return None
        pf = pq.ParquetFile(path)
        idx_col = None
        try:
            import json
            meta = pf.schema_arrow.metadata
            if meta is not None:
                pandas_meta = json.loads(meta.get(b"pandas", b"{}"))
                idx_cols = pandas_meta.get("index_columns", [])
                if idx_cols:
                    idx_col = idx_cols[0]
        except Exception:
            pass

        import pandas as pd
        first_tbl = pf.read_row_group(0, columns=[idx_col] if idx_col else None)
        last_tbl = pf.read_row_group(pf.num_row_groups - 1, columns=[idx_col] if idx_col else None)
        if idx_col:
            first_series = first_tbl.column(idx_col).to_pandas()
            last_series = last_tbl.column(idx_col).to_pandas()
            values = pd.to_datetime(pd.concat([first_series, last_series]))
            return {
                "start": values.min().date(),
                "end": values.max().date(),
                "rows": pf.metadata.num_rows,
            }
        return {"start": None, "end": None, "rows": pf.metadata.num_rows}

    def last_closes(self, codes: list[str], freq: str = "daily") -> dict[str, dict | None]:
        """Batch read last close for multiple codes.

        Returns a dict mapping code → last_close result (or None if cache miss).
        Reads are tried per-file; a single corrupted file won't fail the batch.
        """
        result: dict[str, dict | None] = {}
        for code in codes:
            try:
                result[code] = self.last_close(code, freq)
            except Exception:
                logger.warning("Failed to read last_close (code=%s, freq=%s)", code, freq, exc_info=True)
                result[code] = None
        return result

    def date_ranges(self, codes: list[str], freq: str = "daily") -> dict[str, dict | None]:
        """Batch read date range for multiple codes.

        Returns a dict mapping code → date_range result (or None if cache miss).
        """
        result: dict[str, dict | None] = {}
        for code in codes:
            try:
                result[code] = self.date_range(code, freq)
            except Exception:
                logger.warning("Failed to read date_range (code=%s, freq=%s)", code, freq, exc_info=True)
                result[code] = None
        return result

    def save_batch(self, data: dict[str, pd.DataFrame], freq: str = "daily") -> None:
        """批量保存 {code: DataFrame}"""
        for code, df in data.items():
            self.save(code, df, freq)

    # ── 统计 ──────────────────────────────────

    def stats(self) -> dict:
        """扫描缓存目录返回统计信息。

        Returns:
            {"stock_count": int, "total_rows": int, "storage_bytes": int,
             "date_range": {"start": date|None, "end": date|None},
             "freq_stats": {"daily": int, "financial": int, ...},
             "last_refreshed_at": datetime|None}
        """
        if not self.base.exists():
            return {
                "stock_count": 0, "total_rows": 0, "storage_bytes": 0,
                "date_range": {"start": None, "end": None},
                "freq_stats": {},
                "last_refreshed_at": None,
            }

        freq_stats: dict[str, int] = {}
        total_rows = 0
        total_bytes = 0
        global_min_date: date | None = None
        global_max_date: date | None = None
        latest_mtime: datetime | None = None

        for freq_dir in sorted(self.base.iterdir()):
            if not freq_dir.is_dir():
                continue
            freq = freq_dir.name
            files = list(freq_dir.glob("*.parquet"))
            freq_stats[freq] = len(files)

            for f in files:
                total_bytes += f.stat().st_size
                try:
                    total_rows += pq.read_metadata(f).num_rows

                    f_mtime = datetime.fromtimestamp(os.path.getmtime(f), tz=timezone.utc)
                    if latest_mtime is None or f_mtime > latest_mtime:
                        latest_mtime = f_mtime

                    if freq in ("daily", "index_daily"):
                        _min, _max = self._file_date_range(f)
                        if _min is not None:
                            if global_min_date is None or _min < global_min_date:
                                global_min_date = _min
                        if _max is not None:
                            if global_max_date is None or _max > global_max_date:
                                global_max_date = _max
                except Exception:
                    logger.warning("Failed to scan parquet stats: %s", f, exc_info=True)

        daily_count = sum(v for k, v in freq_stats.items() if k not in ("meta", "index_daily"))
        return {
            "stock_count": daily_count,
            "total_rows": total_rows,
            "storage_bytes": total_bytes,
            "date_range": {"start": global_min_date, "end": global_max_date},
            "freq_stats": freq_stats,
            "last_refreshed_at": latest_mtime.isoformat() if latest_mtime else None,
        }

    def _file_date_range(self, path: Path) -> tuple[date | None, date | None]:
        """抽样读取 parquet 文件头尾行获取日期范围（避免全量扫描）。"""
        import json

        pf = pq.ParquetFile(path)
        idx_col = "__index_level_0__"
        meta = pf.schema_arrow.metadata
        if meta is not None:
            try:
                pandas_meta = json.loads(meta.get(b"pandas", b"{}"))
                idx_cols = pandas_meta.get("index_columns", [])
                if idx_cols:
                    idx_col = idx_cols[0]
            except (json.JSONDecodeError, KeyError, IndexError):
                pass

        # Read only the index column directly (avoids pandas metadata mangling)
        first_tbl = pf.read_row_group(0, columns=[idx_col])
        last_tbl = pf.read_row_group(pf.num_row_groups - 1, columns=[idx_col])
        first_series = first_tbl.column(idx_col).to_pandas()
        last_series = last_tbl.column(idx_col).to_pandas()
        values = pd.to_datetime(pd.concat([first_series, last_series]))
        return values.min().date(), values.max().date()
