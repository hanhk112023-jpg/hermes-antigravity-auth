"""Hermes Plugin registration for DeepSeek CLI."""

from __future__ import annotations

import argparse
import logging
from typing import Any

from deepseek_auth.cli import cmd_list, cmd_login, cmd_test

logger = logging.getLogger(__name__)


def setup_cli_parser(parser: argparse.ArgumentParser) -> None:
    subparsers = parser.add_subparsers(dest="deepseek_command", help="DeepSeek CLI subcommands")

    p_login = subparsers.add_parser("login", help="Log into DeepSeek with email/mobile")
    p_login.add_argument("--identifier", "-u", help="Email or mobile phone")
    p_login.add_argument("--password", "-p", help="Account password")
    p_login.set_defaults(func=cmd_login)

    p_list = subparsers.add_parser("list", help="List configured accounts")
    p_list.set_defaults(func=cmd_list)

    p_test = subparsers.add_parser("test", help="Test chat completion")
    p_test.add_argument("--prompt", help="Prompt text")
    p_test.add_argument("--model", default="deepseek-chat", help="Model name (deepseek-chat or deepseek-reasoner)")
    p_test.set_defaults(func=cmd_test)


def handle_cli_command(args: argparse.Namespace) -> int:
    if hasattr(args, "func"):
        args.func(args)
    else:
        cmd_list(args)
    return 0


def register(ctx: Any) -> None:
    """Entry point invoked by Hermes PluginManager."""
    if hasattr(ctx, "register_cli_command"):
        ctx.register_cli_command(
            name="deepseek",
            help="DeepSeek Web to API account management, login, and diagnostics",
            setup_fn=setup_cli_parser,
            handler_fn=handle_cli_command,
            description="Manage DeepSeek Web accounts, PoW solver and test chat completions.",
        )
