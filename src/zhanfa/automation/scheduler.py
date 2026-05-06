"""定时任务调度 — 基于 schedule 库，含持久化与错误通知"""

from __future__ import annotations

import json
import logging
import os
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import schedule

logger = logging.getLogger(__name__)


class Scheduler:
    """轻量定时调度器，支持状态持久化与错误通知回调。"""

    def __init__(
        self,
        state_file: str | None = None,
        on_error: Callable[[str, Exception], None] | None = None,
    ):
        self._jobs: list[dict] = []
        self._state_file = state_file
        self._on_error = on_error
        self._running = False
        self._last_errors: list[dict] = []  # recent error records
        self._execution_log: dict[str, str | None] = {}  # job_label → last_run_at or error

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        )

        if state_file:
            self._load_state()

    # ── 装饰器 ──────────────────────────────

    def daily(self, time_str: str) -> Callable:
        """每日定时执行装饰器。

        Usage:
            @scheduler.daily("17:00")
            def update_data():
                ...
        """
        def decorator(func: Callable):
            wrapped = self._wrap(func, f"{func.__name__}@daily:{time_str}")
            schedule.every().day.at(time_str).do(wrapped)
            self._register(func.__name__, time_str, "daily")
            return func
        return decorator

    def hourly(self) -> Callable:
        """每小时执行装饰器"""
        def decorator(func: Callable):
            wrapped = self._wrap(func, f"{func.__name__}@hourly")
            schedule.every().hour.do(wrapped)
            self._register(func.__name__, "hourly", "hourly")
            return func
        return decorator

    # ── 任务注册 / 查询 ────────────────────

    def _register(self, name: str, time_str: str, job_type: str) -> None:
        entry = {"func": name, "time": time_str, "type": job_type}
        self._jobs.append(entry)
        self._save_state()

    def list_jobs(self) -> list[dict]:
        return self._jobs

    # ── 周期执行 ────────────────────────────

    def run_pending(self) -> None:
        schedule.run_pending()

    def run_loop(self, interval: int = 60) -> None:
        self._running = True
        logger.info("调度器启动，检查间隔 %ss", interval)
        while self._running:
            try:
                schedule.run_pending()
            except Exception:
                logger.exception("调度循环异常")
            time.sleep(interval)

    def stop(self) -> None:
        self._running = False
        logger.info("调度器已停止")

    # ── 持久化 ──────────────────────────────

    def _save_state(self) -> None:
        if not self._state_file:
            return
        try:
            Path(self._state_file).parent.mkdir(parents=True, exist_ok=True)
            with open(self._state_file, "w", encoding="utf-8") as f:
                json.dump({
                    "jobs": self._jobs,
                    "saved_at": datetime.now(timezone.utc).isoformat(),
                }, f, ensure_ascii=False, indent=2)
        except Exception:
            logger.exception("持久化失败: %s", self._state_file)

    def _load_state(self) -> None:
        if not self._state_file or not os.path.exists(self._state_file):
            return
        try:
            with open(self._state_file, encoding="utf-8") as f:
                data = json.load(f)
            self._jobs = data.get("jobs", [])
            logger.info("已加载调度状态: %d 个任务", len(self._jobs))
        except Exception:
            logger.exception("加载调度状态失败: %s", self._state_file)

    # ── 编程式注册 ──────────────────────────

    def register_func(self, name: str, time_str: str, job_type: str, func: Callable) -> None:
        """直接注册函数为定时任务（非装饰器方式）。"""
        wrapped = self._wrap(func, f"{name}@{job_type}:{time_str}")
        if job_type == "daily":
            schedule.every().day.at(time_str).do(wrapped)
        elif job_type == "hourly":
            schedule.every().hour.do(wrapped)
        else:
            raise ValueError(f"unsupported job_type: {job_type}")
        self._register(name, time_str, job_type)

    # ── 错误通知 ────────────────────────────

    def _wrap(self, func: Callable, job_label: str) -> Callable:
        """包装任务以统一错误处理和通知。"""
        def wrapper():
            try:
                logger.info("执行任务: %s", job_label)
                self._execution_log[job_label] = datetime.now(timezone.utc).isoformat()
                func()
                logger.info("任务完成: %s", job_label)
            except Exception as e:
                msg = f"任务 [{job_label}] 执行失败"
                logger.exception(msg)
                tb = traceback.format_exc()
                self._execution_log[job_label] = f"error: {str(e)[:200]}"
                self._last_errors.append({
                    "job": job_label,
                    "error": str(e)[:200],
                    "time": datetime.now(timezone.utc).isoformat(),
                })
                if len(self._last_errors) > 20:
                    self._last_errors = self._last_errors[-20:]
                self._notify_error(job_label, tb)
        return wrapper

    def get_status(self) -> dict:
        return {
            "jobs": self._jobs,
            "running": self._running,
            "last_errors": self._last_errors[-5:],
            "next_run": self._next_run_times(),
            "execution_log": self._execution_log,
        }

    def _next_run_times(self) -> dict[str, str | None]:
        """Get next scheduled run time for each job."""
        result: dict[str, str | None] = {}
        for job in schedule.jobs:
            next_run = job.next_run
            label = job.job_func.keyword.get("label", "") if hasattr(job.job_func, "keyword") else ""
            if label:
                result[label] = next_run.isoformat() if next_run else None
        return result

    def _notify_error(self, job_label: str, traceback_str: str) -> None:
        """错误通知：回调 + 日志"""
        if self._on_error:
            try:
                self._on_error(job_label, Exception(traceback_str))
            except Exception:
                logger.exception("on_error 回调失败")


scheduler = Scheduler()
