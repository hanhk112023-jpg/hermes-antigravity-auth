"""Terminal UI styling helpers for Google Antigravity CLI."""

import sys
import os

# Check if colors are supported
_NO_COLOR = bool(os.getenv("NO_COLOR") or os.getenv("TERM") == "dumb" or not sys.stdout.isatty())

class UI:
    RESET = "" if _NO_COLOR else "\033[0m"
    BOLD = "" if _NO_COLOR else "\033[1m"
    DIM = "" if _NO_COLOR else "\033[2m"
    ITALIC = "" if _NO_COLOR else "\033[3m"
    UNDERLINE = "" if _NO_COLOR else "\033[4m"

    # Foreground colors
    BLACK = "" if _NO_COLOR else "\033[30m"
    RED = "" if _NO_COLOR else "\033[31m"
    GREEN = "" if _NO_COLOR else "\033[32m"
    YELLOW = "" if _NO_COLOR else "\033[33m"
    BLUE = "" if _NO_COLOR else "\033[34m"
    MAGENTA = "" if _NO_COLOR else "\033[35m"
    CYAN = "" if _NO_COLOR else "\033[36m"
    WHITE = "" if _NO_COLOR else "\033[37m"

    # Bright colors
    BRIGHT_CYAN = "" if _NO_COLOR else "\033[96m"
    BRIGHT_GREEN = "" if _NO_COLOR else "\033[92m"
    BRIGHT_YELLOW = "" if _NO_COLOR else "\033[93m"
    BRIGHT_MAGENTA = "" if _NO_COLOR else "\033[95m"

    @classmethod
    def banner(cls) -> str:
        raw_art = r"""
   ___       _   _                    _ _         
  / _ \___  | |_(_)__ _ _ _ __ ___ __(_) |_ _  _ 
 / /_\/ _ \ |  _| / _` | '_/ _` \ V / |  _| || |
/_/ \_\___/  \__|_\__, |_| \__,_|\_/|_|\__|\_, |
                  |___/                    |__/ 
"""
        return f"{cls.BOLD}{cls.BRIGHT_CYAN}{raw_art}{cls.RESET}{cls.DIM}   Google Antigravity for Hermes Agent • High-Performance AI Transport{cls.RESET}\n"

    @classmethod
    def badge(cls, text: str, color: str = "") -> str:
        c = color or cls.CYAN
        return f"{c}[{text}]{cls.RESET}"

    @classmethod
    def success(cls, text: str) -> str:
        return f"{cls.BOLD}{cls.BRIGHT_GREEN}✓ {text}{cls.RESET}"

    @classmethod
    def warning(cls, text: str) -> str:
        return f"{cls.BOLD}{cls.BRIGHT_YELLOW}⚠ {text}{cls.RESET}"

    @classmethod
    def error(cls, text: str) -> str:
        return f"{cls.BOLD}{cls.RED}✗ {text}{cls.RESET}"

    @classmethod
    def progress_bar(cls, fraction: float | None, width: int = 20) -> str:
        if fraction is None:
            return f"{cls.DIM}[{'?' * width}]   n/a{cls.RESET}"
        frac = max(0.0, min(1.0, float(fraction)))
        pct = frac * 100
        filled = int(round(frac * width))
        empty = width - filled

        if frac > 0.4:
            color = cls.BRIGHT_GREEN
        elif frac > 0.15:
            color = cls.BRIGHT_YELLOW
        else:
            color = cls.RED

        bar = f"{color}{'━' * filled}{cls.DIM}{'─' * empty}{cls.RESET}"
        return f"[{bar}] {color}{pct:>5.1f}%{cls.RESET}"
