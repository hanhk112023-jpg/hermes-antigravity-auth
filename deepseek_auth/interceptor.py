"""Modern Hermes runtime interceptor for DeepSeek Web."""

from __future__ import annotations

import logging
from typing import Any

from .client import DeepSeekWebClient

logger = logging.getLogger(__name__)

_PATCHED = False
_ORIGINAL_CREATE_OPENAI_CLIENT: Any = None
_ORIGINAL_RESOLVE_RUNTIME_PROVIDER: Any = None
_ORIGINAL_RESOLVE_PROVIDER_CLIENT: Any = None


def _is_deepseek_provider_name(value: Any) -> bool:
    val = str(value or "").strip().lower()
    return val in {
        "deepseek",
        "deepseek-web",
        "deepseek2api",
        "deepseek-chat",
        "deepseek-reasoner",
        "ds",
    }


def _deepseek_runtime(requested: Any = None) -> dict[str, Any]:
    return {
        "provider": "deepseek-web",
        "api_mode": "chat_completions",
        "base_url": "https://chat.deepseek.com",
        "api_key": "deepseek-web-auth",
        "source": "deepseek-auth-store",
        "requested_provider": str(requested or "deepseek-web"),
    }


class AsyncDeepSeekWebClient:
    """Async wrapper around DeepSeekWebClient for Hermes aux calls."""

    def __init__(self, sync_client: DeepSeekWebClient) -> None:
        self._sync_client = sync_client
        self.chat = _AsyncDeepSeekChatNamespace(sync_client)

    async def close(self) -> None:
        self._sync_client.close()


class _AsyncDeepSeekChatNamespace:
    def __init__(self, sync_client: DeepSeekWebClient) -> None:
        self.completions = _AsyncDeepSeekChatCompletions(sync_client)


class _AsyncDeepSeekChatCompletions:
    def __init__(self, sync_client: DeepSeekWebClient) -> None:
        self._sync_client = sync_client

    async def create(self, **kwargs: Any) -> Any:
        return self._sync_client.chat.completions.create(**kwargs)


def install() -> bool:
    global _PATCHED, _ORIGINAL_CREATE_OPENAI_CLIENT
    global _ORIGINAL_RESOLVE_RUNTIME_PROVIDER, _ORIGINAL_RESOLVE_PROVIDER_CLIENT

    if _PATCHED:
        return True

    try:
        from agent import agent_runtime_helpers as runtime_helpers
        from agent import auxiliary_client
        from hermes_cli import runtime_provider
    except Exception as exc:
        logger.debug("Hermes runtime modules not present: %s", exc)
        return False

    _ORIGINAL_CREATE_OPENAI_CLIENT = runtime_helpers.create_openai_client
    _ORIGINAL_RESOLVE_RUNTIME_PROVIDER = runtime_provider.resolve_runtime_provider
    _ORIGINAL_RESOLVE_PROVIDER_CLIENT = auxiliary_client.resolve_provider_client

    def _patched_create_openai_client(*args: Any, **kwargs: Any) -> Any:
        agent = args[0] if args else kwargs.get("agent")
        client_kwargs = args[1] if len(args) >= 2 else kwargs.get("client_kwargs") or {}
        provider = getattr(agent, "provider", "")
        base_url = ""
        try:
            base_url = str((client_kwargs or {}).get("base_url") or "")
        except Exception:
            base_url = ""

        if _is_deepseek_provider_name(provider) or "chat.deepseek.com" in base_url:
            return DeepSeekWebClient(**(client_kwargs or {}))
        return _ORIGINAL_CREATE_OPENAI_CLIENT(*args, **kwargs)

    def _patched_resolve_runtime_provider(*args: Any, **kwargs: Any) -> dict[str, Any]:
        requested = kwargs.get("requested")
        if requested is None and args:
            requested = args[0]
        if _is_deepseek_provider_name(requested):
            return _deepseek_runtime(requested)
        return _ORIGINAL_RESOLVE_RUNTIME_PROVIDER(*args, **kwargs)

    def _patched_resolve_provider_client(provider: str, *args: Any, **kwargs: Any):
        if _is_deepseek_provider_name(provider):
            model = kwargs.get("model")
            if model is None and args:
                model = args[0]
            async_mode = bool(kwargs.get("async_mode", False))
            if len(args) >= 2:
                async_mode = bool(args[1])
            final_model = str(model or "deepseek-chat")
            client = DeepSeekWebClient()
            if async_mode:
                client = AsyncDeepSeekWebClient(client)
            return client, final_model
        return _ORIGINAL_RESOLVE_PROVIDER_CLIENT(provider, *args, **kwargs)

    runtime_helpers.create_openai_client = _patched_create_openai_client
    runtime_provider.resolve_runtime_provider = _patched_resolve_runtime_provider
    auxiliary_client.resolve_provider_client = _patched_resolve_provider_client

    _PATCHED = True
    logger.info("DeepSeek Web Hermes runtime interceptor installed successfully")
    return True
