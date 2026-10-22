"""Regression tests for Hermes 0.21 model-picker overlay registration."""

from dataclasses import dataclass
import sys
import types
import unittest
from unittest.mock import patch

from antigravity_auth import hermes_provider_plugin as provider_plugin


def _providers_stub(*, table: bool = True, overlay_cls: bool = True):
  package = types.ModuleType("hermes_cli")
  package.__path__ = []
  module = types.ModuleType("hermes_cli.providers")
  if table:
    module.HERMES_OVERLAYS = {}
  if overlay_cls:
    @dataclass(frozen=True)
    class HermesOverlay:
      transport: str = "openai_chat"
      is_aggregator: bool = False
      auth_type: str = "api_key"
      extra_env_vars: tuple = ()
      base_url_override: str = ""
      base_url_env_var: str = ""

    module.HermesOverlay = HermesOverlay
  return {"hermes_cli": package, "hermes_cli.providers": module}, module


class TestPickerOverlay(unittest.TestCase):
  def test_registers_overlay_when_table_present(self) -> None:
    modules, providers = _providers_stub()
    with patch.dict(sys.modules, modules):
      self.assertTrue(provider_plugin._register_picker_overlay())
      entry = providers.HERMES_OVERLAYS.get("google-gemini-cli")
      self.assertIsNotNone(entry)
      self.assertEqual(entry.auth_type, "oauth_external")
      self.assertEqual(entry.base_url_override, "cloudcode-pa://google")

  def test_registration_is_idempotent(self) -> None:
    modules, providers = _providers_stub()
    with patch.dict(sys.modules, modules):
      self.assertTrue(provider_plugin._register_picker_overlay())
      first = providers.HERMES_OVERLAYS["google-gemini-cli"]
      self.assertTrue(provider_plugin._register_picker_overlay())
      self.assertIs(providers.HERMES_OVERLAYS["google-gemini-cli"], first)

  def test_old_hermes_without_table_or_class_does_not_crash(self) -> None:
    for kwargs in ({"table": False}, {"overlay_cls": False}):
      with self.subTest(**kwargs):
        modules, _ = _providers_stub(**kwargs)
        with patch.dict(sys.modules, modules):
          self.assertFalse(provider_plugin._register_picker_overlay())

  def test_no_hermes_at_all_does_not_crash(self) -> None:
    with patch.dict(sys.modules, {}):
      sys.modules.pop("hermes_cli", None)
      sys.modules.pop("hermes_cli.providers", None)
      self.assertFalse(provider_plugin._register_picker_overlay())


if __name__ == "__main__":
  unittest.main()
