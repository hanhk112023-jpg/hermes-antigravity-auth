"""Dynamic model catalog discovery and user quota summary via Antigravity API.
Ported from Rahularya01/pi-antigravity for Hermes Agent.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from .constants import (
    ANTIGRAVITY_ENDPOINT_PROD,
    ANTIGRAVITY_ENDPOINT_DAILY,
    ANTIGRAVITY_ENDPOINT_AUTOPUSH,
    get_antigravity_headers,
)
from .redaction import redact_secret_text

# Default cache TTL: 4 hours
DEFAULT_CATALOG_REFRESH_INTERVAL_SECONDS = 4 * 3600
CATALOG_CACHE_FILE = os.path.expanduser("~/.hermes/antigravity-catalog.json")

_MEM_CATALOG_CACHE: Dict[str, Any] = {}
_MEM_CATALOG_CACHE_TIME: float = 0.0


def get_endpoint_candidates() -> List[str]:
    """Return available Antigravity endpoints in fallback order."""
    return [
        ANTIGRAVITY_ENDPOINT_PROD,
        ANTIGRAVITY_ENDPOINT_DAILY,
        "https://cloudcode-pa.googleapis.com",
    ]


def fetch_available_models(
    access_token: str,
    project_id: str,
    endpoint: Optional[str] = None,
    timeout: float = 15.0,
) -> Dict[str, Any]:
    """Query /v1internal:fetchAvailableModels across candidate endpoints.

    Returns dict with keys:
      - 'models': raw model dict from Antigravity API
      - 'agentModelSorts': optional group recommendations
      - 'endpoint': successful endpoint
      - 'fetched_at': unix timestamp
    """
    endpoints = [endpoint] if endpoint else get_endpoint_candidates()
    last_err: Optional[Exception] = None

    for ep in endpoints:
        url = f"{ep}/v1internal:fetchAvailableModels"
        headers = get_antigravity_headers()
        headers["Authorization"] = f"Bearer {access_token}"
        headers["Content-Type"] = "application/json"
        body = json.dumps({"project": project_id}).encode("utf-8")

        try:
            req = urllib.request.Request(url, data=body, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8", errors="ignore"))
                models = data.get("models") or {}
                return {
                    "models": models,
                    "agentModelSorts": data.get("agentModelSorts"),
                    "endpoint": ep,
                    "fetched_at": time.time(),
                }
        except urllib.error.HTTPError as exc:
            last_err = exc
            if exc.code not in (403, 404, 429, 500, 502, 503, 504):
                raise
            continue
        except Exception as exc:
            last_err = exc
            continue

    if last_err:
        raise RuntimeError(f"fetchAvailableModels failed on all endpoints: {last_err}")
    return {"models": {}, "fetched_at": time.time()}


def fetch_user_quota_summary(
    access_token: str,
    project_id: str,
    endpoint: Optional[str] = None,
    timeout: float = 15.0,
) -> Dict[str, Any]:
    """Query /v1internal:retrieveUserQuotaSummary to get detailed quota groups and reset times."""
    endpoints = [endpoint] if endpoint else get_endpoint_candidates()
    last_err: Optional[Exception] = None

    for ep in endpoints:
        url = f"{ep}/v1internal:retrieveUserQuotaSummary"
        headers = get_antigravity_headers()
        headers["Authorization"] = f"Bearer {access_token}"
        headers["Content-Type"] = "application/json"
        body = json.dumps({"project": project_id}).encode("utf-8")

        try:
            req = urllib.request.Request(url, data=body, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8", errors="ignore"))
                return {
                    "groups": data.get("groups") or [],
                    "description": data.get("description"),
                    "endpoint": ep,
                    "fetched_at": time.time(),
                }
        except urllib.error.HTTPError as exc:
            last_err = exc
            if exc.code not in (403, 404, 429, 500, 502, 503, 504):
                raise
            continue
        except Exception as exc:
            last_err = exc
            continue

    if last_err:
        raise RuntimeError(f"retrieveUserQuotaSummary failed on all endpoints: {last_err}")
    return {"groups": [], "fetched_at": time.time()}


def load_cached_catalog() -> Optional[Dict[str, Any]]:
    """Load cached model catalog from disk or memory."""
    global _MEM_CATALOG_CACHE, _MEM_CATALOG_CACHE_TIME
    now = time.time()
    if _MEM_CATALOG_CACHE and (now - _MEM_CATALOG_CACHE_TIME < DEFAULT_CATALOG_REFRESH_INTERVAL_SECONDS):
        return _MEM_CATALOG_CACHE

    if os.path.isfile(CATALOG_CACHE_FILE):
        try:
            with open(CATALOG_CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                cached_at = data.get("fetched_at", 0)
                if now - cached_at < DEFAULT_CATALOG_REFRESH_INTERVAL_SECONDS:
                    _MEM_CATALOG_CACHE = data
                    _MEM_CATALOG_CACHE_TIME = cached_at
                    return data
        except Exception:
            pass
    return None


def save_cached_catalog(catalog_data: Dict[str, Any]) -> None:
    """Save model catalog to disk and memory."""
    global _MEM_CATALOG_CACHE, _MEM_CATALOG_CACHE_TIME
    _MEM_CATALOG_CACHE = catalog_data
    _MEM_CATALOG_CACHE_TIME = time.time()

    os.makedirs(os.path.dirname(CATALOG_CACHE_FILE), exist_ok=True)
    try:
        with open(CATALOG_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(catalog_data, f, indent=2)
    except Exception:
        pass


def format_reset_time(iso_str: Optional[str]) -> str:
    """Format ISO 8601 reset time to a human readable delta (e.g. '3h 15m')."""
    if not iso_str:
        return "n/a"
    try:
        import datetime
        norm = iso_str.replace("Z", "+00:00")
        dt = datetime.datetime.fromisoformat(norm)
        delta_seconds = dt.timestamp() - time.time()
        if delta_seconds <= 0:
            return "ready"
        total_min = int(round(delta_seconds / 60))
        days = total_min // (60 * 24)
        hours = (total_min % (60 * 24)) // 60
        mins = total_min % 60
        if days > 0:
            return f"{days}d {hours}h"
        if hours > 0:
            return f"{hours}h {mins}m"
        return f"{mins}m"
    except Exception:
        return iso_str
