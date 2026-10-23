"""Modern Terminal UI styling for DeepSeek Web."""

from __future__ import annotations
import os

class UI:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    CYAN = "\033[36m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_CYAN = "\033[96m"

    @classmethod
    def banner(cls) -> str:
        art = r"""
  ____                  ____            _    ____  ____ ___ 
 |  _ \  ___  ___ _ __ / ___|  ___  ___| | _|___ \|  _ \_ _|
 | | | |/ _ \/ _ \ '_ \\___ \ / _ \/ _ \ |/ / __) | |_) | | 
 | |_| |  __/  __/ |_) |___) |  __/  __/   < / __/|  __/| | 
 |____/ \___|\___| .__/|____/ \___|\___|_|\_\_____|_|  |___|
                 |_|                                         
"""
        return f"{cls.BOLD}{cls.BRIGHT_BLUE}{art}{cls.RESET}{cls.DIM}   DeepSeek Web to OpenAI API Gateway • High-Performance Web Reverse Proxy{cls.RESET}\n"
