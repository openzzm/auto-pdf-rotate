import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "vendor"))

import fitz

import app


def sample_pdf():
    candidates = list((ROOT / "jobs").glob("*/source.pdf"))
    candidates.extend((ROOT / ".analysis").glob("desktop-path-sample.pdf"))
    if not candidates:
        raise unittest.SkipTest("Regression sample PDF is not available")
    return candidates[0]


class RotationRegressionTests(unittest.TestCase):
    def assert_sample_page_rotation(self, page_index, expected_rotation):
        source_doc = fitz.open(sample_pdf())
        single_page = fitz.open()
        single_page.insert_pdf(source_doc, from_page=page_index, to_page=page_index)

        with tempfile.TemporaryDirectory(dir=ROOT) as temp_dir:
            source = Path(temp_dir) / f"page{page_index + 1}.pdf"
            output = Path(temp_dir) / f"page{page_index + 1}-output.pdf"
            single_page.save(source)
            single_page.close()
            source_doc.close()

            app.process_pdf(f"page{page_index + 1}-regression", str(source), str(output))

            result = fitz.open(output)
            try:
                self.assertEqual(result[0].rotation, expected_rotation)
            finally:
                result.close()

    def test_sparse_upside_down_page_gets_high_resolution_retry(self):
        self.assert_sample_page_rotation(16, 180)

    def test_three_strong_upside_down_votes_outweigh_upright_watermark(self):
        self.assert_sample_page_rotation(24, 180)


class OutputFilenameTests(unittest.TestCase):
    def test_preserves_chinese_source_name(self):
        self.assertEqual(
            app.output_filename_for("单位工程竣工文件(2).pdf"),
            "单位工程竣工文件(2)_已修正方向版.pdf",
        )

    def test_removes_path_and_windows_invalid_characters(self):
        self.assertEqual(
            app.output_filename_for(r"C:\fakepath\工程<>报告.pdf"),
            "工程__报告_已修正方向版.pdf",
        )


if __name__ == "__main__":
    unittest.main()
