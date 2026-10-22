"""Unit tests for Antigravity model grouping and synthesis (pi-antigravity parity)."""

import unittest

from antigravity_auth.grouping import (
    display_family,
    group_antigravity_catalog,
    humanize_public_id,
    level_from_display_name,
    model_sort_rank,
    parse_thinking_suffix,
)


class TestGrouping(unittest.TestCase):
    def test_humanize_public_id(self):
        self.assertEqual(humanize_public_id("gemini-3.8-flash"), "Gemini 3.8 Flash (Antigravity)")
        self.assertEqual(humanize_public_id("claude-sonnet-4-6"), "Claude Sonnet 4.6 (Antigravity)")
        self.assertEqual(humanize_public_id("claude-opus-4-6"), "Claude Opus 4.6 (Antigravity)")
        self.assertEqual(humanize_public_id("gpt-oss-120b"), "GPT-OSS 120B (Antigravity)")
        self.assertEqual(humanize_public_id("gemini-3.1-flash-image"), "Gemini 3.1 Flash Image (Antigravity)")

    def test_display_family(self):
        self.assertEqual(display_family("Gemini 3.5 Flash (Medium)"), "gemini 3.5 flash")
        self.assertEqual(display_family("Gemini 3.5 Flash (Low)"), "gemini 3.5 flash")
        self.assertEqual(display_family("Gemini 3.5 Flash (High)"), "gemini 3.5 flash")
        self.assertEqual(display_family("Claude Sonnet 4.6 (Thinking)"), "claude sonnet 4.6")
        self.assertEqual(display_family("GPT-OSS 120B (Medium)"), "gpt-oss 120b")

    def test_level_from_display_name(self):
        self.assertEqual(level_from_display_name("Gemini 3.5 Flash (Medium)"), "Medium")
        self.assertEqual(level_from_display_name("Gemini 3.5 Flash (Low)"), "Low")
        self.assertEqual(level_from_display_name("Claude Sonnet 4.6 (Thinking)"), "Thinking")
        self.assertEqual(level_from_display_name("Gemini 3.1 Flash Image"), None)

    def test_parse_thinking_suffix(self):
        self.assertEqual(parse_thinking_suffix("gemini-3.8-flash-low"), ("gemini-3.8-flash", "Low"))
        self.assertEqual(parse_thinking_suffix("gemini-3.8-flash-medium"), ("gemini-3.8-flash", "Medium"))
        self.assertEqual(parse_thinking_suffix("gemini-3.8-flash-high"), ("gemini-3.8-flash", "High"))
        self.assertEqual(parse_thinking_suffix("gemini-3.5-flash-extra-low"), ("gemini-3.5-flash", "Low"))

    def test_group_antigravity_catalog_synthetic(self):
        mock_raw = {
            "gemini-3.8-flash-low": {"displayName": "Gemini 3.8 Flash (Low)", "supportsThinking": True},
            "gemini-3.8-flash-medium": {"displayName": "Gemini 3.8 Flash (Medium)", "supportsThinking": True},
            "gemini-3.8-flash-high": {"displayName": "Gemini 3.8 Flash (High)", "supportsThinking": True},
            "gemini-3.8-flash-tiered": {"displayName": "gemini-3.8-flash-tiered"},
            "gemini-3.5-flash-extra-low": {"displayName": "Gemini 3.5 Flash (Low)", "supportsThinking": True},
            "gemini-3.5-flash-low": {"displayName": "Gemini 3.5 Flash (Medium)", "supportsThinking": True},
            "gemini-3-flash-agent": {"displayName": "Gemini 3.5 Flash (High)", "supportsThinking": True},
            "claude-opus-4-6-thinking": {"displayName": "Claude Opus 4.6 (Thinking)", "supportsThinking": True},
            "claude-sonnet-4-6": {"displayName": "Claude Sonnet 4.6 (Thinking)", "supportsThinking": True},
            "gemini-3.1-flash-image": {"displayName": "Gemini 3.1 Flash Image", "supportsThinking": False},
            "gpt-oss-120b-medium": {"displayName": "GPT-OSS 120B (Medium)", "supportsThinking": True},
            "chat_20706": {"displayName": "chat_20706"},
        }
        groups = group_antigravity_catalog(mock_raw, include_all=False)
        ids = [g.public_id for g in groups]
        self.assertIn("gemini-3.8-flash", ids)
        self.assertIn("gemini-3.5-flash", ids)
        self.assertIn("claude-opus-4-6", ids)
        self.assertIn("claude-sonnet-4-6", ids)
        self.assertIn("gemini-3.1-flash-image", ids)
        self.assertIn("gpt-oss-120b", ids)
        self.assertNotIn("chat_20706", ids)

        # Check Gemini 3.8 Flash variants
        g38 = next(g for g in groups if g.public_id == "gemini-3.8-flash")
        self.assertEqual(g38.get_thinking_levels_str(), "Low, Medium, High")
        self.assertEqual(g38.context_window, 1048576)
        routing38 = g38.get_routing_map()
        self.assertEqual(routing38["low"], "gemini-3.8-flash-low")
        self.assertEqual(routing38["medium"], "gemini-3.8-flash-medium")
        self.assertEqual(routing38["high"], "gemini-3.8-flash-high")

        # Check Gemini 3.5 Flash merged variants
        g35 = next(g for g in groups if g.public_id == "gemini-3.5-flash")
        self.assertEqual(g35.get_thinking_levels_str(), "Low, Medium, High")
        routing35 = g35.get_routing_map()
        self.assertEqual(routing35["low"], "gemini-3.5-flash-extra-low")
        self.assertEqual(routing35["medium"], "gemini-3.5-flash-low")
        self.assertEqual(routing35["high"], "gemini-3-flash-agent")

        # Check Claude Opus
        g_opus = next(g for g in groups if g.public_id == "claude-opus-4-6")
        self.assertEqual(g_opus.get_thinking_levels_str(), "Thinking")
        self.assertEqual(g_opus.context_window, 200000)

        # Check Image model
        g_img = next(g for g in groups if g.public_id == "gemini-3.1-flash-image")
        self.assertEqual(g_img.get_thinking_levels_str(), "Image Gen")
        self.assertEqual(g_img.context_window, 32768)


if __name__ == "__main__":
    unittest.main()
