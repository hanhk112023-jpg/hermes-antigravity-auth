"""Account and Session Storage for DeepSeek Web Accounts."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEEPSEEK_ACCOUNTS_FILE = Path.home() / ".hermes" / "deepseek-accounts.json"


def load_accounts() -> dict[str, Any]:
    if not DEEPSEEK_ACCOUNTS_FILE.exists():
        return {"accounts": [], "active_index": 0}
    try:
        with open(DEEPSEEK_ACCOUNTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                return {"accounts": [], "active_index": 0}
            data.setdefault("accounts", [])
            data.setdefault("active_index", 0)
            return data
    except Exception as exc:
        logger.warning("Failed to read %s: %s", DEEPSEEK_ACCOUNTS_FILE, exc)
        return {"accounts": [], "active_index": 0}


def save_accounts(data: dict[str, Any]) -> None:
    DEEPSEEK_ACCOUNTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        temp_file = DEEPSEEK_ACCOUNTS_FILE.with_suffix(".tmp")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(temp_file, DEEPSEEK_ACCOUNTS_FILE)
        try:
            os.chmod(DEEPSEEK_ACCOUNTS_FILE, 0o600)
        except OSError:
            pass
    except Exception as exc:
        logger.error("Failed to save accounts to %s: %s", DEEPSEEK_ACCOUNTS_FILE, exc)


def sync_token_to_hermes_auth(token: str) -> None:
    """Sync DeepSeek token to Hermes ~/.hermes/auth.json under deepseek and deepseek-web."""
    auth_file = Path.home() / ".hermes" / "auth.json"
    if not auth_file.exists():
        data = {"version": 1, "providers": {}}
    else:
        try:
            with open(auth_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                data = {"version": 1, "providers": {}}
        except Exception:
            data = {"version": 1, "providers": {}}
    try:
        from agent.credential_pool import load_pool, PooledCredential, AUTH_TYPE_API_KEY, SOURCE_MANUAL
        pool = load_pool("deepseek")
        if not pool.has_credentials():
            entry = PooledCredential(
                provider="deepseek",
                id="deepseek-web",
                label="DeepSeek Web Token",
                auth_type=AUTH_TYPE_API_KEY,
                priority=0,
                source=SOURCE_MANUAL,
                access_token=token,
            )
            pool.add_entry(entry)
    except Exception as exc:
        logger.debug("Failed to seed credential pool: %s", exc)

    try:
        from hermes_cli.auth import _load_auth_store, _save_auth_store
        auth_store = _load_auth_store()
        cp = auth_store.setdefault("credential_pool", {})
        cp["deepseek"] = [{
            "id": "deepseek-web",
            "provider": "deepseek",
            "auth_type": "api_key",
            "priority": 0,
            "source": "manual",
            "label": "DeepSeek Web Token",
            "access_token": token,
        }]
        providers = auth_store.setdefault("providers", {})
        providers["deepseek"] = {"token": token, "api_key": token}
        providers["deepseek-web"] = {"token": token, "api_key": token}
        _save_auth_store(auth_store)
    except Exception:
        pass


def add_or_update_account(
    identifier: str,
    token: str,
    *,
    password: str = "",
    mobile: str = "",
    email: str = "",
) -> None:
    # Auto-extract token if user pasted JSON: {"value": "..."} or full userToken object
    token = token.strip()
    if token.startswith("{") and "value" in token:
        try:
            parsed = json.loads(token)
            if isinstance(parsed, dict) and "value" in parsed:
                token = str(parsed["value"]).strip()
        except Exception:
            pass

    data = load_accounts()
    accounts = data["accounts"]
    found = False
    for acc in accounts:
        if acc.get("identifier") == identifier or (email and acc.get("email") == email) or (mobile and acc.get("mobile") == mobile):
            acc["token"] = token
            if password:
                acc["password"] = password
            if email:
                acc["email"] = email
            if mobile:
                acc["mobile"] = mobile
            found = True
            break
    if not found:
        accounts.append({
            "identifier": identifier,
            "email": email or (identifier if "@" in identifier else ""),
            "mobile": mobile or (identifier if "@" not in identifier else ""),
            "password": password,
            "token": token,
            "enabled": True,
        })
    save_accounts(data)
    sync_token_to_hermes_auth(token)


def get_active_account() -> dict[str, Any] | None:
    data = load_accounts()
    accounts = [a for a in data.get("accounts", []) if a.get("enabled", True)]
    if not accounts:
        return None
    idx = data.get("active_index", 0)
    if 0 <= idx < len(accounts):
        return accounts[idx]
    return accounts[0]
