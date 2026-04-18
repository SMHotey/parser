import pytest
import sys
import os
import tempfile
import json
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import advanced_features


class TestProfileManager:
    def setup_method(self):
        # Use temporary directory for tests
        self.temp_dir = tempfile.mkdtemp()
        self.pm = advanced_features.ProfileManager(profiles_dir=self.temp_dir)

    def teardown_method(self):
        # Clean up
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_save_and_load_profile(self):
        settings = {"url": "https://example.com", "method": "static"}
        name = "test_profile"

        result = self.pm.save_profile(name, settings)
        assert result is True

        loaded = self.pm.load_profile(name)
        assert loaded is not None
        assert loaded["url"] == "https://example.com"

    def test_load_nonexistent_profile(self):
        result = self.pm.load_profile("nonexistent")
        assert result is None

    def test_get_profiles_list(self):
        self.pm.save_profile("profile1", {"url": "http://example1.com"})
        self.pm.save_profile("profile2", {"url": "http://example2.com"})

        profiles = self.pm.get_profiles_list()
        assert "profile1" in profiles
        assert "profile2" in profiles

    def test_delete_profile(self):
        self.pm.save_profile("to_delete", {"url": "http://example.com"})

        result = self.pm.delete_profile("to_delete")
        assert result is True

        loaded = self.pm.load_profile("to_delete")
        assert loaded is None

    def test_delete_nonexistent_profile(self):
        result = self.pm.delete_profile("nonexistent")
        assert result is False


class TestProxyManager:
    def setup_method(self):
        self.proxy_mgr = advanced_features.ProxyManager()

    def test_add_proxy(self):
        result = self.proxy_mgr.add_proxy("192.168.1.1:8080")
        assert result is True

    def test_add_duplicate_proxy(self):
        self.proxy_mgr.add_proxy("192.168.1.1:8080")
        result = self.proxy_mgr.add_proxy("192.168.1.1:8080")
        assert result is False

    def test_get_next_proxy_disabled(self):
        self.proxy_mgr.add_proxy("192.168.1.1:8080")
        self.proxy_mgr.enabled = False

        result = self.proxy_mgr.get_next_proxy()
        assert result is None

    def test_get_next_proxy_enabled(self):
        self.proxy_mgr.add_proxy("192.168.1.1:8080")
        self.proxy_mgr.enabled = True

        result = self.proxy_mgr.get_next_proxy()
        assert result is not None

    def test_get_next_proxy_round_robin(self):
        self.proxy_mgr.add_proxy("192.168.1.1:8080")
        self.proxy_mgr.add_proxy("192.168.1.2:8080")
        self.proxy_mgr.enabled = True

        first = self.proxy_mgr.get_next_proxy()
        second = self.proxy_mgr.get_next_proxy()

        assert first != second

    def test_clear_proxies(self):
        self.proxy_mgr.add_proxy("192.168.1.1:8080")
        self.proxy_mgr.clear_proxies()

        result = self.proxy_mgr.get_next_proxy()
        assert result is None

    def test_load_proxies_from_file(self):
        # Create temporary proxy file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("192.168.1.1:8080\n")
            f.write("192.168.1.2:8080\n")
            f.write("192.168.1.3:8080")
            proxy_file = f.name

        try:
            count = self.proxy_mgr.load_proxies(proxy_file)
            assert count == 3
        finally:
            os.unlink(proxy_file)


class TestTaskSchedulerCalculateNextRun:
    def test_interval(self):
        scheduler = advanced_features.TaskScheduler()

        # Interval of 30 minutes
        next_run = scheduler.calculate_next_run('interval', 30)
        assert isinstance(next_run, datetime)
        assert next_run > datetime.now()

    def test_daily_future_time(self):
        scheduler = advanced_features.TaskScheduler()

        # Set to 23:59 (definitely in future for any time of day)
        next_run = scheduler.calculate_next_run('daily', '23:59')
        assert isinstance(next_run, datetime)
        assert next_run.date() >= datetime.now().date()

    def test_weekly(self):
        scheduler = advanced_features.TaskScheduler()

        # Monday at 09:00
        next_run = scheduler.calculate_next_run('weekly', 'mon 09:00')
        assert isinstance(next_run, datetime)

    def test_add_task(self):
        scheduler = advanced_features.TaskScheduler()

        task_id = scheduler.add_task(
            name="Test Task",
            url="https://example.com",
            methods=["static"],
            schedule_type="interval",
            schedule_value=30,
            export_format="csv"
        )

        assert task_id == 0
        assert len(scheduler.tasks) == 1
        assert scheduler.tasks[0]["name"] == "Test Task"