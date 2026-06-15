import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "vendor"))

import app
import fitz


class FakeWindow:
    def __init__(self, selection):
        self.selection = selection

    def create_file_dialog(self, **kwargs):
        return self.selection


class DesktopPathJobTests(unittest.TestCase):
    def test_output_path_is_created_beside_source(self):
        source = Path(r"C:\documents\单位工程竣工文件(2).pdf")
        self.assertEqual(
            app.output_path_for(source),
            source.with_name("单位工程竣工文件(2)_已修正方向版.pdf"),
        )

    def test_create_path_job_records_sibling_output_and_starts_worker(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as temp_dir:
            source = Path(temp_dir) / "sample.pdf"
            source.write_bytes(b"pdf")

            with patch.object(app.threading.Thread, "start") as start:
                job_id = app.create_path_job(source)

            job = app.JOBS[job_id]
            self.assertEqual(Path(job["source"]), source)
            self.assertEqual(Path(job["output"]), app.output_path_for(source))
            self.assertEqual(job["saved_path"], str(app.output_path_for(source)))
            start.assert_called_once()

            with app.JOBS_LOCK:
                app.JOBS.pop(job_id, None)
            with app.WORKERS_LOCK:
                app.WORKERS.clear()

    def test_desktop_api_returns_cancelled_when_picker_is_closed(self):
        desktop_api = app.DesktopApi()
        desktop_api.window = FakeWindow(None)
        self.assertEqual(desktop_api.select_pdf(), {"ok": False, "cancelled": True})

    def test_browser_selection_endpoint_creates_path_job(self):
        source = Path(__file__).resolve()
        with patch.object(app, "select_pdf_path", return_value=source):
            with patch.object(app, "create_path_job", return_value="job-id") as create:
                response = app.app.test_client().post("/api/select-pdf")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["job_id"], "job-id")
        create.assert_called_once_with(source)

    def test_browser_selection_endpoint_returns_cancelled(self):
        with patch.object(app, "select_pdf_path", return_value=None):
            response = app.app.test_client().post("/api/select-pdf")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"ok": False, "cancelled": True})

    def test_shutdown_cleanup_keeps_auto_saved_output(self):
        original_job_root = app.JOB_ROOT
        original_shutdown = app.SHUTDOWN_EVENT.is_set()
        with tempfile.TemporaryDirectory(dir=ROOT) as temp_dir:
            base = Path(temp_dir)
            app.JOB_ROOT = base / "jobs"
            app.JOB_ROOT.mkdir()
            output = base / "sample_已修正方向版.pdf"
            output.write_bytes(b"result")
            try:
                app.shutdown_cleanup()
                self.assertTrue(output.exists())
            finally:
                app.JOB_ROOT = original_job_root
                if not original_shutdown:
                    app.SHUTDOWN_EVENT.clear()

    def test_processing_keeps_analysis_report_out_of_source_directory(self):
        original_job_root = app.JOB_ROOT
        with tempfile.TemporaryDirectory(dir=ROOT) as temp_dir:
            base = Path(temp_dir)
            source = base / "sample.pdf"
            output = app.output_path_for(source)
            app.JOB_ROOT = base / "jobs"
            app.JOB_ROOT.mkdir()
            document = fitz.open()
            document.new_page()
            document.save(source)
            document.close()
            try:
                app.process_pdf("report-location", str(source), str(output))
                self.assertFalse(output.with_suffix(".json").exists())
                self.assertTrue((app.JOB_ROOT / "report-location.json").exists())
            finally:
                app.JOB_ROOT = original_job_root


if __name__ == "__main__":
    unittest.main()
