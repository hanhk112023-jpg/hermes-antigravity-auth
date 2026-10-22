"""Unit tests for Antigravity dynamic discovery and usage parsing."""
import time
import unittest

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


if __name__ == "__main__":
    unittest.main()
