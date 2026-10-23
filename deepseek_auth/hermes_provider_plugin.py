"""Hermes provider profile registration for DeepSeek Web."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from .interceptor import install as install_interceptor

logger = logging.getLogger(__name__)

# Ensure runtime interceptor hook is installed
install_interceptor()

try:
    from providers import register_provider as _hermes_register_provider  # type: ignore
    from providers.base import ProviderProfile as _HermesProviderProfile  # type: ignore
    BaseProviderProfile = _HermesProviderProfile
    def register_provider(profile: Any) -> None:
        _hermes_register_provider(profile)
except Exception:
    @dataclass
    class _FallbackProviderProfile:
        name: str
        api_mode: str = "chat_completions"
        aliases: tuple = ()
        display_name: str = ""
        description: str = ""
        signup_url: str = ""
        env_vars: tuple = ()
        base_url: str = ""
        models_url: str = ""
        auth_type: str = "api_key"
        supports_health_check: bool = True
        fallback_models: tuple = ()
        hostname: str = ""
        default_headers: dict[str, str] = field(default_factory=dict)
        fixed_temperature: Any = None
        default_max_tokens: int | None = None
        default_aux_model: str = ""

        def get_model_context_length(self, model: str) -> int | None:
            return 131_072

        def get_max_tokens(self, model: str | None) -> int | None:
            return 8_192

    BaseProviderProfile = _FallbackProviderProfile  # type: ignore

    def register_provider(profile: Any) -> None:
        pass


class DeepSeekWebProfile(BaseProviderProfile):  # type: ignore
    def get_model_context_length(self, model: str) -> int | None:
        return 131_072

    def get_max_tokens(self, model: str | None) -> int | None:
        return 8_192


DEEPSEEK_PROFILE = DeepSeekWebProfile(
    name="deepseek-web",
    display_name="DeepSeek Web to API",
    description="DeepSeek Web backend with automated PoW and session manager",
    aliases=("deepseek", "deepseek2api", "ds"),
    base_url="https://chat.deepseek.com",
    fallback_models=("deepseek-chat", "deepseek-reasoner"),
    default_aux_model="deepseek-chat",
    default_max_tokens=8192,
)

register_provider(DEEPSEEK_PROFILE)

__all__ = ["DeepSeekWebProfile", "DEEPSEEK_PROFILE"]
