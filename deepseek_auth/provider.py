"""Hermes Provider Plugin for DeepSeek Web."""

from __future__ import annotations

import logging
from typing import Any

from .client import DeepSeekWebClient

logger = logging.getLogger(__name__)


def create_deepseek_client(**kwargs: Any) -> DeepSeekWebClient:
    """Factory hook called by Hermes Agent to create the OpenAI client."""
    logger.debug("Creating DeepSeekWebClient for Hermes Agent")
    return DeepSeekWebClient(**kwargs)
