"""DeepSeek Web to API Gateway."""

__version__ = "2.0.0"

from .client import DeepSeekWebClient
from .provider import create_deepseek_client

__all__ = ["DeepSeekWebClient", "create_deepseek_client", "__version__"]
