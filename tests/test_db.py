"""Tests for core.db"""
import sys
import os
import tempfile
import unittest
from pathlib import Path

# Patch DATA_DIR before importing
_tmpdir = tempfile.mkdtemp()
sys.path.insert(0, str(Path(__file__).parent.parent))
import core
core.DATA_DIR = Path(_tmpdir)
core.PROJECT_ROOT = Path(__file__).parent.parent

from core.db import upsert_jobs, get_all_jobs, update_job_status, get_stats, get_expiring_jobs, update_job_deadline


class TestDB(unittest.TestCase):

    def setUp(self):
        import core.db
        db = Path(core.db.DB_PATH)
        if db.exists():
            db.unlink()

    def test_upsert_and_dedup(self):
        jobs = [
            {"company": "TestCo", "title": "算法工程师", "url": "http://test.com"},
            {"company": "TestCo", "title": "后端工程师", "url": ""},
        ]
        r1 = upsert_jobs(jobs)
        self.assertEqual(r1["new"], 2)
        self.assertEqual(r1["total"], 2)

        # Insert same jobs again - should dedup
        r2 = upsert_jobs(jobs)
        self.assertEqual(r2["new"], 0)

        all_j = get_all_jobs()
        self.assertEqual(len(all_j), 2)

    def test_status_update(self):
        jobs = [{"company": "StatusCo", "title": "测试岗位"}]
        upsert_jobs(jobs)
        all_j = get_all_jobs(company="StatusCo")
        self.assertTrue(len(all_j) > 0)
        job_id = all_j[0]["id"]
        self.assertEqual(all_j[0]["status"], "待关注")

        update_job_status(job_id, "待投递")
        all_j = get_all_jobs(company="StatusCo")
        self.assertEqual(all_j[0]["status"], "待投递")

    def test_deadline(self):
        jobs = [{"company": "DeadlineCo", "title": "紧急岗位"}]
        upsert_jobs(jobs)
        all_j = get_all_jobs(company="DeadlineCo")
        job_id = all_j[0]["id"]

        from datetime import datetime, timedelta
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        update_job_deadline(job_id, tomorrow)

        expiring = get_expiring_jobs(3)
        self.assertTrue(any(j["company"] == "DeadlineCo" for j in expiring))

    def test_stats(self):
        stats = get_stats()
        self.assertIn("total", stats)
        self.assertIn("by_status", stats)
        self.assertIn("expiring", stats)

    def test_filter(self):
        jobs = [
            {"company": "FilterCo", "title": "岗位A"},
            {"company": "FilterCo", "title": "岗位B"},
            {"company": "OtherCo", "title": "岗位C"},
        ]
        upsert_jobs(jobs)
        filtered = get_all_jobs(company="FilterCo")
        self.assertEqual(len(filtered), 2)

    def test_empty_input(self):
        r = upsert_jobs([{"company": "", "title": ""}])
        self.assertEqual(r["new"], 0)


if __name__ == "__main__":
    unittest.main()
