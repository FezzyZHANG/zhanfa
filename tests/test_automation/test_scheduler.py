"""Scheduler tests."""

from unittest.mock import MagicMock, patch

from zhanfa.automation.scheduler import Scheduler


class TestSchedulerInit:
    def test_init_defaults(self):
        s = Scheduler()
        assert s.list_jobs() == []

    def test_init_with_state_file(self, tmp_path):
        state_file = tmp_path / "schedule.json"
        s = Scheduler(state_file=str(state_file))
        assert s._state_file == str(state_file)


class TestSchedulerJobs:
    def test_daily_decorator(self):
        s = Scheduler()

        @s.daily("17:00")
        def update_data():
            pass

        jobs = s.list_jobs()
        assert len(jobs) == 1
        assert jobs[0]["func"] == "update_data"
        assert jobs[0]["time"] == "17:00"
        assert jobs[0]["type"] == "daily"

    def test_hourly_decorator(self):
        s = Scheduler()

        @s.hourly()
        def refresh():
            pass

        jobs = s.list_jobs()
        assert len(jobs) == 1
        assert jobs[0]["func"] == "refresh"
        assert jobs[0]["time"] == "hourly"

    def test_multiple_jobs(self):
        s = Scheduler()

        @s.daily("09:00")
        def morning():
            pass

        @s.daily("17:00")
        def evening():
            pass

        @s.hourly()
        def heartbeat():
            pass

        jobs = s.list_jobs()
        assert len(jobs) == 3
        names = {j["func"] for j in jobs}
        assert names == {"morning", "evening", "heartbeat"}


class TestSchedulerRun:
    def test_run_pending(self):
        s = Scheduler()
        with patch("zhanfa.automation.scheduler.schedule") as mock_schedule:
            s.run_pending()
            mock_schedule.run_pending.assert_called_once()

    def test_run_loop_starts_and_stops(self):
        s = Scheduler()
        # Run loop in a way that exits immediately
        s._running = True

        def stop_after_one():
            s.stop()

        mock_func = MagicMock(side_effect=stop_after_one)

        with patch("zhanfa.automation.scheduler.schedule") as mock_schedule:
            mock_schedule.run_pending = mock_func
            s.run_loop(interval=0)
            assert not s._running


class TestSchedulerPersistence:
    def test_save_and_load_state(self, tmp_path):
        state_file = tmp_path / "schedule.json"

        s1 = Scheduler(state_file=str(state_file))

        @s1.daily("17:00")
        def task_a():
            pass

        @s1.hourly()
        def task_b():
            pass

        assert state_file.exists()

        s2 = Scheduler(state_file=str(state_file))
        jobs = s2.list_jobs()
        assert len(jobs) == 2
        names = {j["func"] for j in jobs}
        assert names == {"task_a", "task_b"}

    def test_no_state_file_no_persistence(self, tmp_path):
        s = Scheduler()  # No state_file

        @s.daily("17:00")
        def task():
            pass

        # Should not raise
        s._save_state()


class TestSchedulerErrorNotification:
    def test_on_error_callback_called(self):
        mock_callback = MagicMock()
        s = Scheduler(on_error=mock_callback)

        s._notify_error("test_job", "Traceback...")
        mock_callback.assert_called_once_with("test_job", mock_callback.call_args[0][1])

    def test_on_error_callback_handles_exception(self):
        def bad_callback(job, exc):
            raise RuntimeError("callback fail")

        s = Scheduler(on_error=bad_callback)
        # Should not raise even if callback fails
        s._notify_error("test_job", "Traceback...")

    def test_wrap_catches_and_notifies(self):
        mock_callback = MagicMock()

        def failing_func():
            raise ValueError("boom")

        s = Scheduler(on_error=mock_callback)
        wrapped = s._wrap(failing_func, "test_job")
        wrapped()  # Should not raise

        mock_callback.assert_called_once()
        assert mock_callback.call_args[0][0] == "test_job"


class TestSchedulerRunPending:
    def test_list_jobs_includes_registered_funcs(self):
        s = Scheduler()

        @s.daily("17:00")
        def task():
            pass

        jobs = s.list_jobs()
        assert len(jobs) == 1
        assert jobs[0]["func"] == "task"
