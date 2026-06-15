import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class FrontendBridgeTests(unittest.TestCase):
    def test_waits_for_pywebview_api_method_before_calling_it(self):
        script = (ROOT / "static" / "app.js").read_text(encoding="utf-8")

        self.assertIn("pywebviewready", script)
        self.assertIn('typeof window.pywebview?.api?.select_pdf === "function"', script)

    def test_desktop_page_shows_loading_state_until_bridge_is_ready(self):
        script = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        page = (ROOT / "templates" / "index.html").read_text(encoding="utf-8")
        application = (ROOT / "app.py").read_text(encoding="utf-8")

        self.assertIn('id="startupLoading"', page)
        self.assertIn('id="selectFile" class="dropzone" type="button" disabled', page)
        self.assertIn('searchParams.get("desktop") === "1"', script)
        self.assertIn("setInterfaceReady", script)
        self.assertIn("http://127.0.0.1:8765/?desktop=1", application)


if __name__ == "__main__":
    unittest.main()
