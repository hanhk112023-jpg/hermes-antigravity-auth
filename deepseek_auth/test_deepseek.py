"""Unit tests for hermes-deepseek2api."""

import base64
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from deepseek_auth.pow import solve_pow_challenge
from deepseek_auth.storage import (
    add_or_update_account,
    get_active_account,
    load_accounts,
)


class TestDeepSeekWeb(unittest.TestCase):
    def test_pow_solver(self):
        challenge = {
            "algorithm": "DeepSeekHashV1",
            "challenge": "cebab4aa8e50955666f589816c66811144e056a8f41c43a43bd78cedc4b5f4a1",
            "salt": "8360f8c9205c96c32b7a",
            "expire_at": 1739764288699,
            "difficulty": 144000,
            "signature": "10b7849b1e6203b288dc4975a1e23753ed9d6fb656964b8e86daebab3628a40c",
            "target_path": "/api/v0/chat/completion",
        }
        encoded = solve_pow_challenge(challenge)
        self.assertIsInstance(encoded, str)
        decoded = json.loads(base64.b64decode(encoded).decode("utf-8"))
        self.assertEqual(decoded["algorithm"], "DeepSeekHashV1")
        self.assertEqual(decoded["answer"], 77906)
        self.assertEqual(decoded["salt"], "8360f8c9205c96c32b7a")

    def test_account_storage(self):
        test_file = Path("/tmp/test_deepseek_accounts.json")
        if test_file.exists():
            test_file.unlink()

        with patch("deepseek_auth.storage.DEEPSEEK_ACCOUNTS_FILE", test_file):
            self.assertIsNone(get_active_account())
            add_or_update_account("test@example.com", "fake_token_123", password="secret_password")
            active = get_active_account()
            self.assertIsNotNone(active)
            self.assertEqual(active["email"], "test@example.com")
            self.assertEqual(active["token"], "fake_token_123")
            self.assertEqual(active["password"], "secret_password")

        if test_file.exists():
            test_file.unlink()


if __name__ == "__main__":
    unittest.main()
