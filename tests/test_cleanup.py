import sys
import tempfile
import threading
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "vendor"))

import app


class ShutdownCleanupTests(unittest.TestCase):
    def test_shutdown_clears_jobs_workers_and_temporary_files(self):
        original_job_root = app.JOB_ROOT
        original_jobs = app.JOBS.copy()
        original_workers = list(app.WORKERS)
        original_shutdown = app.SHUTDOWN_EVENT.is_set()

        with tempfile.TemporaryDirectory(dir=ROOT) as temp_dir:
            job_root = Path(temp_dir) / "jobs"
            job_dir = job_root / "job-id"
            job_dir.mkdir(parents=True)
            (job_dir / "source.pdf").write_bytes(b"temporary")

            app.SHUTDOWN_EVENT.clear()
            worker = threading.Thread(target=lambda: app.SHUTDOWN_EVENT.wait())
            worker.start()

            app.JOB_ROOT = job_root
            app.JOBS.clear()
            app.JOBS["job-id"] = {"status": "done"}
            app.WORKERS.clear()
            app.WORKERS.append(worker)

            try:
                app.shutdown_cleanup()

                self.assertFalse(job_root.exists())
                self.assertEqual(app.JOBS, {})
                self.assertEqual(app.WORKERS, [])
                self.assertTrue(app.SHUTDOWN_EVENT.is_set())
                self.assertFalse(worker.is_alive())
            finally:
                app.JOB_ROOT = original_job_root
                app.JOBS.clear()
                app.JOBS.update(original_jobs)
                app.WORKERS.clear()
                app.WORKERS.extend(original_workers)
                if not original_shutdown:
                    app.SHUTDOWN_EVENT.clear()


if __name__ == "__main__":
    unittest.main()
