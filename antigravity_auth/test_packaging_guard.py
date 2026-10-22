"""Tests for package build release-safety checks."""

import tempfile
import unittest
from pathlib import Path

from antigravity_auth.packaging_guard import assert_no_local_credentials_module


class TestPackagingGuard(unittest.TestCase):
    def test_allows_tree_without_local_credentials_module(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            package_dir = tmp_path / "antigravity_auth"
            package_dir.mkdir()
            assert_no_local_credentials_module(tmp_path)

    def test_rejects_tree_with_local_credentials_module(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            package_dir = tmp_path / "antigravity_auth"
            package_dir.mkdir()
            (package_dir / "_credentials.py").write_text("DUMMY = 'not-a-secret'\n")

            with self.assertRaises(RuntimeError) as ctx:
                assert_no_local_credentials_module(tmp_path)
            self.assertIn("Refusing to build", str(ctx.exception))

    def test_rejects_tree_with_local_credentials_bytecode(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            package_dir = tmp_path / "antigravity_auth"
            pycache_dir = package_dir / "__pycache__"
            pycache_dir.mkdir(parents=True)
            (pycache_dir / "_credentials.cpython-311.pyc").write_bytes(b"dummy-bytecode")

            with self.assertRaises(RuntimeError) as ctx:
                assert_no_local_credentials_module(tmp_path)
            self.assertIn("_credentials*.pyc", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
