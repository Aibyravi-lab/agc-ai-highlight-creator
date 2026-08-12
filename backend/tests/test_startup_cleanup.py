"""VED-P1-010: startup crash-recovery orphan cleanup.

app.main runs its startup sequence as module-level import-time code (not a
FastAPI lifespan hook), so exercising it means reimporting app.main with
every real side-effecting dependency mocked: DB init, FFmpeg validation,
file logging, and the health-monitoring thread all touch disk / require
binaries that a unit test must not depend on. Each test pops "app.main"
from sys.modules, patches those dependencies, then reimports fresh.
"""

import importlib
import sys
import unittest
from unittest.mock import MagicMock, patch


class StartupCleanupOrderingTests(unittest.TestCase):

    def setUp(self):
        # Keyed explicitly rather than by patcher.attribute — several
        # targets below (DatabaseService, JobStorageService, LoggerService)
        # share the attribute name "initialize", which would collide as a
        # dict/mock-manager key if derived from the target string alone.
        patch_specs = [
            (
                "db_initialize",
                "app.services.database_service.DatabaseService.initialize",
                {},
            ),
            (
                "reconcile_interrupted_jobs",
                "app.services.job_service.JobService.reconcile_interrupted_jobs",
                {"return_value": 0},
            ),
            (
                "job_storage_initialize",
                "app.services.job_storage_service.JobStorageService.initialize",
                {},
            ),
            (
                "ffmpeg_validate",
                "app.services.ffmpeg_service.FFmpegService.validate",
                {},
            ),
            (
                "logger_initialize",
                "app.services.logger_service.LoggerService.initialize",
                {},
            ),
            (
                "logger_info",
                "app.services.logger_service.LoggerService.info",
                {},
            ),
            (
                "cleanup",
                "app.services.cleanup_service.CleanupService.cleanup",
                {},
            ),
            (
                "health_scheduler_start",
                "app.services.health_scheduler_service.HealthSchedulerService.start",
                {},
            ),
        ]

        self.manager = MagicMock()
        self.mocks = {}

        for name, target, kwargs in patch_specs:
            patcher = patch(target, **kwargs)
            mock = patcher.start()
            self.addCleanup(patcher.stop)
            self.mocks[name] = mock
            self.manager.attach_mock(mock, name)

        self.addCleanup(sys.modules.pop, "app.main", None)

    def _import_fresh_main(self):
        sys.modules.pop("app.main", None)
        return importlib.import_module("app.main")

    def test_startup_calls_reconciliation(self):
        self._import_fresh_main()

        self.mocks["reconcile_interrupted_jobs"].assert_called_once()

    def test_startup_calls_cleanup(self):
        self._import_fresh_main()

        self.mocks["cleanup"].assert_called_once()

    def test_cleanup_runs_after_reconciliation(self):
        self._import_fresh_main()

        call_order = [c[0] for c in self.manager.mock_calls]

        self.assertIn("reconcile_interrupted_jobs", call_order)
        self.assertIn("cleanup", call_order)
        self.assertLess(
            call_order.index("reconcile_interrupted_jobs"),
            call_order.index("cleanup"),
        )

    def test_cleanup_called_exactly_once(self):
        self._import_fresh_main()

        self.assertEqual(
            self.mocks["cleanup"].call_count,
            1,
        )

    def test_startup_succeeds_when_cleanup_has_nothing_to_delete(self):
        # CleanupService.cleanup is mocked to a no-op returning None, i.e.
        # the "nothing to delete" case — startup must still complete and
        # produce a usable app.
        main_module = self._import_fresh_main()

        self.assertTrue(hasattr(main_module, "app"))

    def test_existing_startup_steps_still_run_unchanged(self):
        main_module = self._import_fresh_main()

        self.mocks["db_initialize"].assert_called_once()
        self.mocks["job_storage_initialize"].assert_called_once()
        self.mocks["logger_initialize"].assert_called_once()
        self.mocks["ffmpeg_validate"].assert_called_once()
        self.mocks["health_scheduler_start"].assert_called_once()

        route_paths = {
            route.path
            for route in main_module.app.routes
            if hasattr(route, "path")
        }
        self.assertIn("/", route_paths)
        self.assertIn("/version", route_paths)


if __name__ == "__main__":
    unittest.main()
