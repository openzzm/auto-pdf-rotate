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

    def test_dropzone_supports_drag_and_drop_path_selection(self):
        script = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        styles = (ROOT / "static" / "style.css").read_text(encoding="utf-8")
        application = (ROOT / "app.py").read_text(encoding="utf-8")

        self.assertIn('selectFile.addEventListener("dragover"', script)
        self.assertIn('selectFile.addEventListener("drop"', script)
        self.assertIn("pdf-path-selected", script)
        self.assertIn("start_pdf_path", script)
        self.assertIn(".drag-over", styles)
        self.assertIn("DOMEventHandler", application)
        self.assertIn("pywebviewFullPath", application)

    def test_ui_internationalization_defaults_to_english(self):
        script = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        page = (ROOT / "templates" / "index.html").read_text(encoding="utf-8")
        english = (ROOT / "static" / "locales" / "en.json").read_text(encoding="utf-8")
        chinese = (ROOT / "static" / "locales" / "zh-CN.json").read_text(encoding="utf-8")

        self.assertIn('<html lang="en">', page)
        self.assertIn('id="languageSelect"', page)
        self.assertIn('data-i18n="app.title"', page)
        self.assertIn('const DEFAULT_LANGUAGE = "en"', script)
        self.assertIn("static/locales", script)
        self.assertIn("localStorage.setItem", script)
        self.assertIn('"app.title": "Auto PDF Rotate"', english)
        self.assertIn('"app.title": "PDF 页面方向自动修正"', chinese)


if __name__ == "__main__":
    unittest.main()
