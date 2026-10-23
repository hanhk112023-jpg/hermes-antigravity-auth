"""DeepSeek CLI file plugin wrapper."""

import sys
from pathlib import Path

try:
    from deepseek_auth.plugin_contract import load_cli_register
except Exception as exc:
    raise RuntimeError(
        "Hermes DeepSeek CLI file-plugin wrapper failed to load.\n"
        f"Wrapper: {Path(__file__).expanduser()}\n"
        f"Python: {Path(sys.executable).expanduser()}\n"
        "Target: deepseek_auth.plugin_contract\n"
        f"Cause: {type(exc).__name__}: {exc}\n"
    ) from exc

register = load_cli_register(__file__)
