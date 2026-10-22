"""Unit tests for thinking budget calculation based on pi-antigravity spec."""
import unittest

from antigravity_auth.transform.envelope import get_thinking_config


class TestThinkingBudget(unittest.TestCase):
    def test_gemini_4_argon(self):
        # Argon rejects thinkingBudget 0 / under 1000, returns None when off
        self.assertIsNone(get_thinking_config("gemini-4-argon", "off"))
        self.assertIsNone(get_thinking_config("gemini-4-argon", ""))
        self.assertIsNone(get_thinking_config("gemini-4-argon", None))

        high = get_thinking_config("gemini-4-argon", "high")
        self.assertIsNotNone(high)
        assert high is not None
        self.assertTrue(high["includeThoughts"])
        self.assertEqual(high["thinkingBudget"], -1)

        xhigh = get_thinking_config("gemini-4-argon", "xhigh")
        self.assertIsNotNone(xhigh)
        assert xhigh is not None
        self.assertEqual(xhigh["thinkingBudget"], -1)

        med = get_thinking_config("gemini-4-argon", "medium")
        self.assertIsNotNone(med)
        assert med is not None
        self.assertEqual(med["thinkingBudget"], 4000)

        low = get_thinking_config("gemini-4-argon", "low")
        self.assertIsNotNone(low)
        assert low is not None
        self.assertEqual(low["thinkingBudget"], 1000)

    def test_gemini_38_flash(self):
        off = get_thinking_config("gemini-3.8-flash", "off")
        self.assertIsNotNone(off)
        assert off is not None
        self.assertFalse(off["includeThoughts"])
        self.assertEqual(off["thinkingBudget"], 0)

        high = get_thinking_config("gemini-3.8-flash", "high")
        self.assertIsNotNone(high)
        assert high is not None
        self.assertTrue(high["includeThoughts"])
        self.assertEqual(high["thinkingBudget"], -1)

        med = get_thinking_config("gemini-3.8-flash", "medium")
        self.assertIsNotNone(med)
        assert med is not None
        self.assertEqual(med["thinkingBudget"], 4000)

        low = get_thinking_config("gemini-3.8-flash", "low")
        self.assertIsNotNone(low)
        assert low is not None
        self.assertEqual(low["thinkingBudget"], 1000)

    def test_gemini_35_flash(self):
        off = get_thinking_config("gemini-3.5-flash", "off")
        self.assertIsNotNone(off)
        assert off is not None
        self.assertFalse(off["includeThoughts"])
        self.assertEqual(off["thinkingBudget"], 0)

        high = get_thinking_config("gemini-3.5-flash", "high")
        self.assertIsNotNone(high)
        assert high is not None
        self.assertTrue(high["includeThoughts"])
        self.assertEqual(high["thinkingBudget"], 10000)

        med = get_thinking_config("gemini-3.5-flash", "medium")
        self.assertIsNotNone(med)
        assert med is not None
        self.assertEqual(med["thinkingBudget"], 4000)

        low = get_thinking_config("gemini-3.5-flash", "low")
        self.assertIsNotNone(low)
        assert low is not None
        self.assertEqual(low["thinkingBudget"], 1000)

    def test_gemini_31_pro(self):
        off = get_thinking_config("gemini-3.1-pro", "off")
        self.assertIsNotNone(off)
        assert off is not None
        self.assertFalse(off["includeThoughts"])
        self.assertEqual(off["thinkingBudget"], 0)

        high = get_thinking_config("gemini-3.1-pro", "high")
        self.assertIsNotNone(high)
        assert high is not None
        self.assertTrue(high["includeThoughts"])
        self.assertEqual(high["thinkingBudget"], 10001)

        low = get_thinking_config("gemini-3.1-pro", "low")
        self.assertIsNotNone(low)
        assert low is not None
        self.assertEqual(low["thinkingBudget"], 1001)

    def test_claude_models(self):
        off = get_thinking_config("claude-sonnet-4-6", "off")
        self.assertIsNotNone(off)
        assert off is not None
        self.assertFalse(off["includeThoughts"])
        self.assertEqual(off["thinkingBudget"], 0)

        on = get_thinking_config("claude-sonnet-4-6", "high")
        self.assertIsNotNone(on)
        assert on is not None
        self.assertTrue(on["includeThoughts"])
        self.assertEqual(on["thinkingBudget"], 1024)

    def test_gpt_oss_models(self):
        off = get_thinking_config("gpt-oss-120b", "off")
        self.assertIsNotNone(off)
        assert off is not None
        self.assertFalse(off["includeThoughts"])
        self.assertEqual(off["thinkingBudget"], 0)

        on = get_thinking_config("gpt-oss-120b", "medium")
        self.assertIsNotNone(on)
        assert on is not None
        self.assertTrue(on["includeThoughts"])
        self.assertEqual(on["thinkingBudget"], 8192)


if __name__ == "__main__":
    unittest.main()
