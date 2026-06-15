import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "vendor"))

import app


class PortableSelfTestTests(unittest.TestCase):
    def test_self_test_cleans_job_cache_and_writes_report(self):
        original_job_root = app.JOB_ROOT
        original_shutdown = app.SHUTDOWN_EVENT.is_set()
        with tempfile.TemporaryDirectory(dir=ROOT) as temp_dir:
            base = Path(temp_dir)
            report_path = base / "self-test.json"
            app.JOB_ROOT = base / "jobs"
            app.JOB_ROOT.mkdir()
            try:
                result = app.run_self_test(report_path)
                self.assertEqual(result["status"], "ok")
                self.assertTrue(result["jobs_removed"])
                self.assertFalse(app.JOB_ROOT.exists())
                self.assertTrue(report_path.exists())
            finally:
                app.JOB_ROOT = original_job_root
                if not original_shutdown:
                    app.SHUTDOWN_EVENT.clear()


if __name__ == "__main__":
    unittest.main()
