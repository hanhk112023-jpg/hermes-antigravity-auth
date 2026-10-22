"""Unit tests for AntigravityProfile context length and dynamic discovery."""
import os
import unittest
from unittest.mock import patch

from antigravity_auth.hermes_provider_plugin import antigravity


class TestAntigravityContextAndDiscovery(unittest.TestCase):
    def test_default_family_context_lengths(self):
        # Gemini 3.8 / 4 Argon / 3.7 / 3.5 -> 1M tokens
        self.assertEqual(antigravity.get_model_context_length("gemini-4-argon"), 1_048_576)
        self.assertEqual(antigravity.get_model_context_length("gemini-3.8-flash"), 1_048_576)
        self.assertEqual(antigravity.get_model_context_length("gemini-3.5-flash"), 1_048_576)

        # Gemini Image -> 32k
        self.assertEqual(antigravity.get_model_context_length("gemini-3.1-flash-image"), 32_768)

        # Claude 4.6 / 3.5 -> 200k tokens
        self.assertEqual(antigravity.get_model_context_length("claude-sonnet-4-6"), 200_000)
        self.assertEqual(antigravity.get_model_context_length("claude-opus-4-6-thinking"), 200_000)

        # GPT-OSS -> 128k
        self.assertEqual(antigravity.get_model_context_length("gpt-oss-120b-medium"), 131_072)

    def test_fixed_context_pin_via_env(self):
        with patch.dict(os.environ, {"ANTIGRAVITY_CONTEXT_LENGTH": "524288"}):
            self.assertEqual(antigravity.get_model_context_length("gemini-3.8-flash"), 524_288)
            self.assertEqual(antigravity.get_model_context_length("claude-sonnet-4-6"), 524_288)

    def test_dynamic_catalog_context_length(self):
        mock_catalog = {
            "models": {
                "gemini-experimental-2026": {"maxTokens": 2_097_152},
            }
        }
        with patch("antigravity_auth.discovery.load_cached_catalog", return_value=mock_catalog):
            self.assertEqual(
                antigravity.get_model_context_length("gemini-experimental-2026"),
                2_097_152,
            )

    def test_max_output_tokens(self):
        self.assertEqual(antigravity.get_max_tokens("gemini-3.8-flash"), 65_536)
        self.assertEqual(antigravity.get_max_tokens("claude-sonnet-4-6"), 64_000)
        self.assertEqual(antigravity.get_max_tokens("gemini-3.1-flash-image"), 4_096)


if __name__ == "__main__":
    unittest.main()
