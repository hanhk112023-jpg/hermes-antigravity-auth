"""DeepSeek Web provider file plugin wrapper."""

import sys
from pathlib import Path

try:
    from deepseek_auth.plugin_contract import load_provider_namespace
except Exception as exc:
    raise RuntimeError(
        "Hermes DeepSeek Web provider file-plugin wrapper failed to load.\n"
        f"Wrapper: {Path(__file__).expanduser()}\n"
        f"Python: {Path(sys.executable).expanduser()}\n"
        "Target: deepseek_auth.plugin_contract\n"
        f"Cause: {type(exc).__name__}: {exc}\n"
    ) from exc

globals().update(load_provider_namespace(__file__))
