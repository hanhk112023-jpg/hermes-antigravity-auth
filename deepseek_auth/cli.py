"""CLI for DeepSeek Web Accounts and Testing."""

from __future__ import annotations

import argparse
import getpass
import sys
from typing import Any

from .client import DeepSeekWebClient, login_deepseek
from .storage import (
    add_or_update_account,
    get_active_account,
    load_accounts,
    save_accounts,
)
from .ui import UI


def cmd_login(args: Any) -> None:
    print(UI.banner())
    identifier = args.identifier
    if not identifier:
        identifier = input(f"{UI.BOLD}Email or Mobile (+84...): {UI.RESET}").strip()
    if not identifier:
        print(f"{UI.RED}Error: Email or mobile is required.{UI.RESET}")
        return

    password = args.password
    if not password:
        password = getpass.getpass(f"{UI.BOLD}Password: {UI.RESET}").strip()
    if not password:
        print(f"{UI.RED}Error: Password is required.{UI.RESET}")
        return

    acc_data = {
        "password": password,
        "email": identifier if "@" in identifier else "",
        "mobile": identifier if "@" not in identifier else "",
    }
    print(f"\n{UI.CYAN}Connecting to DeepSeek Web API (Android v2.1.1)...{UI.RESET}")
    try:
        token = login_deepseek(acc_data)
        print(f"{UI.GREEN}✓ Successfully authenticated! Token saved.{UI.RESET}")
        print(f"{UI.DIM}Account: {identifier}{UI.RESET}\n")
    except Exception as exc:
        print(f"{UI.RED}✗ Login failed: {exc}{UI.RESET}")


def cmd_list(args: Any) -> None:
    print(UI.banner())
    data = load_accounts()
    accounts = data.get("accounts", [])
    if not accounts:
        print(f"{UI.YELLOW}No accounts configured yet. Run 'login' to add one.{UI.RESET}\n")
        return

    active_idx = data.get("active_index", 0)
    print(f"{UI.BOLD}Configured DeepSeek Web Accounts:{UI.RESET}")
    print(f"{'#':<4} {'Identifier':<35} {'Status':<12} {'Active':<8}")
    print("-" * 65)
    for idx, acc in enumerate(accounts):
        ident = acc.get("identifier") or acc.get("email") or acc.get("mobile")
        status = f"{UI.GREEN}Active{UI.RESET}" if acc.get("enabled", True) else f"{UI.DIM}Disabled{UI.RESET}"
        is_active = f"{UI.BRIGHT_CYAN}★ Current{UI.RESET}" if idx == active_idx else ""
        print(f"{idx + 1:<4} {ident:<35} {status:<12} {is_active:<8}")
    print()


def cmd_test(args: Any) -> None:
    print(UI.banner())
    acc = get_active_account()
    if not acc:
        print(f"{UI.RED}No active account found. Please run 'login' first.{UI.RESET}")
        return

    prompt = args.prompt or "Hello DeepSeek, explain quantum computing in 1 short sentence."
    model = args.model or "deepseek-chat"
    print(f"{UI.CYAN}Sending test prompt to {model} via DeepSeek Web PoW gateway...{UI.RESET}")
    print(f"{UI.DIM}Prompt: {prompt}{UI.RESET}\n")

    client = DeepSeekWebClient()
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            stream=False,
        )
        content = resp.choices[0].message.content
        print(f"{UI.GREEN}{UI.BOLD}Response:{UI.RESET}")
        print(content)
        print()
    except Exception as exc:
        print(f"{UI.RED}✗ Request failed: {exc}{UI.RESET}")
    finally:
        client.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="DeepSeek Web to API Manager")
    subparsers = parser.add_subparsers(dest="command", help="Subcommand to execute")

    # login
    p_login = subparsers.add_parser("login", help="Log into DeepSeek with email/mobile")
    p_login.add_argument("--identifier", "-u", help="Email or mobile phone")
    p_login.add_argument("--password", "-p", help="Account password")
    p_login.set_defaults(func=cmd_login)

    # list
    p_list = subparsers.add_parser("list", help="List configured accounts")
    p_list.set_defaults(func=cmd_list)

    # test
    p_test = subparsers.add_parser("test", help="Test chat completion")
    p_test.add_argument("--prompt", help="Prompt text")
    p_test.add_argument("--model", default="deepseek-chat", help="Model name (deepseek-chat or deepseek-reasoner)")
    p_test.set_defaults(func=cmd_test)

    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        cmd_list(args)
        return 0

    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
