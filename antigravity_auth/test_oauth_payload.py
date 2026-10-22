"""Regression tests for cross-platform loadCodeAssist project discovery."""

import json
import sys
import unittest
from unittest.mock import patch

from antigravity_auth.oauth import fetch_project_id, load_code_assist_payload


class TestLoadCodeAssistPayload(unittest.TestCase):
  def test_platform_is_unspecified(self) -> None:
    payload = load_code_assist_payload()
    self.assertEqual(payload["metadata"]["platform"], "PLATFORM_UNSPECIFIED")
    self.assertEqual(payload["metadata"]["ideType"], "ANTIGRAVITY")
    self.assertEqual(payload["metadata"]["pluginType"], "GEMINI")

  def test_payload_identical_on_all_platforms(self) -> None:
    expected = load_code_assist_payload()
    for platform in ("linux", "darwin", "win32"):
      with self.subTest(platform=platform), patch.object(sys, "platform", platform):
        self.assertEqual(load_code_assist_payload(), expected)

  def test_fetch_uses_compatible_payload(self) -> None:
    seen = []
    import antigravity_auth.oauth as oauth

    def fake_post(url, headers, data, timeout=10):
      seen.append((url, json.loads(data.decode("utf-8"))))
      return 200, b'{"cloudaicompanionProject": "test-project-123"}'

    with patch.object(oauth, "make_post_request", side_effect=fake_post):
      self.assertEqual(fetch_project_id("dummy-token"), "test-project-123")
    self.assertTrue(seen)
    for _, payload in seen:
      self.assertEqual(payload["metadata"]["platform"], "PLATFORM_UNSPECIFIED")


if __name__ == "__main__":
  unittest.main()
