import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ProjectNamingTests(unittest.TestCase):
    def test_user_facing_start_script_uses_english_name(self):
        self.assertTrue((ROOT / "start-browser.bat").exists())
        self.assertFalse((ROOT / "启动网页.bat").exists())
        self.assertIn("start-browser.bat", (ROOT / "README.md").read_text(encoding="utf-8"))
        self.assertIn("start-browser.bat", (ROOT / "README.zh-CN.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
