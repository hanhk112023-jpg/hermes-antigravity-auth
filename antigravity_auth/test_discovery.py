"""Unit tests for Antigravity dynamic discovery and usage parsing."""
import json
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

import antigravity_auth.discovery as discovery

from antigravity_auth.discovery import (
    format_reset_time,
    get_endpoint_candidates,
    load_cached_catalog,
    save_cached_catalog,
)


class TestAntigravityDiscovery(unittest.TestCase):
    def test_endpoint_candidates(self):
        eps = get_endpoint_candidates()
        self.assertGreater(len(eps), 1)
        self.assertIn("https://daily-cloudcode-pa.googleapis.com", eps)

    def test_format_reset_time(self):
        self.assertEqual(format_reset_time(None), "n/a")
        self.assertEqual(format_reset_time(""), "n/a")

        # Future time test
        import datetime
        future_dt = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=2, minutes=30)
        future_iso = future_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        res = format_reset_time(future_iso)
        self.assertIn("h", res)
        self.assertIn("m", res)

        # Past time test
        past_dt = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=5)
        past_iso = past_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        self.assertEqual(format_reset_time(past_iso), "ready")

    def test_catalog_cache_roundtrip(self):
        data = {
            "models": {
                "gemini-4-argon": {"displayName": "Gemini 4 Argon"},
                "gemini-3.8-flash": {"displayName": "Gemini 3.8 Flash"},
            },
            "fetched_at": time.time(),
        }
        save_cached_catalog(data)
        loaded = load_cached_catalog()
        self.assertIsNotNone(loaded)
        assert loaded is not None
        self.assertIn("gemini-4-argon", loaded["models"])
        self.assertIn("gemini-3.8-flash", loaded["models"])


class TestCatalogCacheIsolation(unittest.TestCase):
    def setUp(self):
        self._old_cache = discovery._MEM_CATALOG_CACHE
        self._old_cache_time = discovery._MEM_CATALOG_CACHE_TIME
        self._old_cache_path = getattr(discovery, "_MEM_CATALOG_CACHE_PATH", None)
        discovery._MEM_CATALOG_CACHE = {}
        discovery._MEM_CATALOG_CACHE_TIME = 0.0
        if hasattr(discovery, "_MEM_CATALOG_CACHE_PATH"):
            discovery._MEM_CATALOG_CACHE_PATH = None

    def tearDown(self):
        discovery._MEM_CATALOG_CACHE = self._old_cache
        discovery._MEM_CATALOG_CACHE_TIME = self._old_cache_time
        if hasattr(discovery, "_MEM_CATALOG_CACHE_PATH"):
            discovery._MEM_CATALOG_CACHE_PATH = self._old_cache_path

    def test_cache_follows_hermes_home_relocation(self):
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            with patch.dict(os.environ, {"HERMES_HOME": first}):
                discovery.save_cached_catalog({"models": {"first": {}}, "fetched_at": time.time()})
                self.assertTrue((Path(first) / "antigravity-catalog.json").is_file())
                os.environ["HERMES_HOME"] = second
                self.assertIsNone(discovery.load_cached_catalog())
                discovery.save_cached_catalog({"models": {"second": {}}, "fetched_at": time.time()})
                self.assertTrue((Path(second) / "antigravity-catalog.json").is_file())
                with open(Path(first) / "antigravity-catalog.json", encoding="utf-8") as handle:
                    self.assertIn("first", json.load(handle)["models"])

    def test_concurrent_saves_leave_one_valid_catalog(self):
        with tempfile.TemporaryDirectory() as home, patch.dict(os.environ, {"HERMES_HOME": home}):
            def save(index):
                discovery.save_cached_catalog({
                    "models": {f"model-{index}": {"displayName": str(index)}},
                    "fetched_at": time.time(),
                })

            with ThreadPoolExecutor(max_workers=8) as pool:
                list(pool.map(save, range(24)))
            discovery._MEM_CATALOG_CACHE = {}
            discovery._MEM_CATALOG_CACHE_TIME = 0.0
            loaded = discovery.load_cached_catalog()
            self.assertIsNotNone(loaded)
            self.assertEqual(len(loaded["models"]), 1)
            self.assertTrue(next(iter(loaded["models"])).startswith("model-"))
            self.assertEqual(list(Path(home).glob("*.tmp")), [])

    def test_interrupted_atomic_save_preserves_previous_catalog(self):
        with tempfile.TemporaryDirectory() as home, patch.dict(os.environ, {"HERMES_HOME": home}):
            path = Path(home) / "antigravity-catalog.json"
            discovery.save_cached_catalog({"models": {"old": {}}, "fetched_at": time.time()})
            with patch.object(discovery.os, "replace", side_effect=OSError("interrupted replace")):
                discovery.save_cached_catalog({"models": {"new": {}}, "fetched_at": time.time()})
            discovery._MEM_CATALOG_CACHE = {}
            discovery._MEM_CATALOG_CACHE_TIME = 0.0
            loaded = discovery.load_cached_catalog()
            self.assertIsNotNone(loaded)
            self.assertIn("old", loaded["models"])
            self.assertNotIn("new", loaded["models"])
            self.assertEqual(list(Path(home).glob("*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
