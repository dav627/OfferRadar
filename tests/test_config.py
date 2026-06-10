"""Tests for core.config"""
import sys
import os
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import core
_tmpdir = tempfile.mkdtemp()
core.PROJECT_ROOT = Path(_tmpdir)
core.DATA_DIR = Path(_tmpdir) / "data"

# Create a test config.yaml
import yaml
test_config = {
    "llm": {"api_key": "sk-test123", "base_url": "https://test.com/v1", "model": "test-model"},
    "push": {"serverchan": {"enabled": True, "sendkey": "SCTtest"}},
    "proxy": {"http": "http://127.0.0.1:1234", "https": ""},
    "profile": {
        "target_role": "测试工程师",
        "graduation": "2027",
        "keywords": ["测试", "QA"],
        "exclude_keywords": ["前端"],
        "bio": "测试简介",
    },
    "schedule": {"enabled": True, "time": "08:00"},
}
config_path = Path(_tmpdir) / "config.yaml"
with open(config_path, "w", encoding="utf-8") as f:
    yaml.dump(test_config, f, allow_unicode=True)

# Reset config cache
import core.config as cfg
cfg.CONFIG_PATH = config_path
cfg._config = None


class TestConfig(unittest.TestCase):

    def test_llm_config(self):
        c = cfg.get_llm_config()
        self.assertEqual(c["api_key"], "sk-test123")
        self.assertEqual(c["model"], "test-model")

    def test_proxy(self):
        p = cfg.get_proxy()
        self.assertEqual(p["http"], "http://127.0.0.1:1234")

    def test_profile(self):
        p = cfg.get_profile()
        self.assertEqual(p["target_role"], "测试工程师")
        self.assertIn("测试", p["keywords"])
        self.assertIn("前端", p["exclude_keywords"])

    def test_push_config(self):
        push = cfg.get_push_config()
        self.assertTrue(push["serverchan"]["enabled"])

    def test_schedule(self):
        s = cfg.get_schedule_config()
        self.assertTrue(s["enabled"])
        self.assertEqual(s["time"], "08:00")

    def test_get(self):
        v = cfg.get("llm", "model")
        self.assertEqual(v, "test-model")

    def test_default(self):
        v = cfg.get("nonexistent", "key", "default_val")
        self.assertEqual(v, "default_val")


if __name__ == "__main__":
    unittest.main()
