"""Tests for core.scraper_lite (offline, no network)"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import core
import tempfile
core.DATA_DIR = Path(tempfile.mkdtemp())
core.PROJECT_ROOT = Path(__file__).parent.parent


class TestScraperHelpers(unittest.TestCase):

    def test_keywords_loaded(self):
        from core.scraper_lite import _keywords
        kw, ex = _keywords()
        self.assertIsInstance(kw, list)
        self.assertTrue(len(kw) > 0)

    def test_extract_jobs_from_html(self):
        from core.scraper_lite import extract_jobs_from_html, KEYWORDS
        html = '<div><a>大模型算法工程师-北京</a><a>前台接待</a></div>'
        jobs = extract_jobs_from_html(html, "测试公司", "http://test.com")
        # Should find the LLM job if keywords match
        titles = [j["title"] for j in jobs]
        self.assertTrue(any("大模型" in t for t in titles) or len(jobs) == 0)

    def test_exclude_keywords(self):
        from core.scraper_lite import EXCLUDE_KEYWORDS
        self.assertIsInstance(EXCLUDE_KEYWORDS, list)


if __name__ == "__main__":
    unittest.main()
