"""Hermes CLI Plugin for DeepSeek Web."""

from __future__ import annotations

import logging
from typing import Any

from .cli import main as cli_main

logger = logging.getLogger(__name__)


def register(cli_group: Any) -> None:
    """Register 'deepseek' command with Hermes CLI."""
    try:
        import click

        @cli_group.command(
            "deepseek",
            context_settings=dict(ignore_unknown_options=True, allow_extra_args=True),
            help="DeepSeek Web to API account management, login, and diagnostics",
        )
        @click.pass_context
        def deepseek_cmd(ctx: Any) -> None:
            cli_main(ctx.args)

    except Exception as exc:
        logger.warning("Could not register deepseek command with Hermes CLI: %s", exc)
