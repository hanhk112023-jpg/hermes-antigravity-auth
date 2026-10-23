"""Plugin contract helper for Hermes file-based plugins."""

from __future__ import annotations

import importlib
from typing import Any


def load_cli_register(wrapper_path: str) -> Any:
    mod = importlib.import_module("deepseek_auth.hermes_plugin")
    return getattr(mod, "register")


def load_provider_namespace(wrapper_path: str) -> dict[str, Any]:
    mod = importlib.import_module("deepseek_auth.hermes_provider_plugin")
    names = getattr(mod, "__all__", [n for n in vars(mod) if not n.startswith("__")])
    return {n: getattr(mod, n) for n in names}
