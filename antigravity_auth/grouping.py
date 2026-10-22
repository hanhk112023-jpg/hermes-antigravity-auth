"""Grouping and catalog synthesis engine for Antigravity models.

Mirrors TypeScript implementation from Rahularya01/pi-antigravity:
  - Collapses runtime thinking variants into clean Public Model IDs.
  - Resolves request routing (low/medium/high/off -> runtime IDs).
  - Calculates context windows and max output tokens.
  - Formats public display names and models.
"""
from __future__ import annotations

import re
from typing import Any

from .discovery import format_reset_time


THINKING_SUFFIXES = [
    ("extra-low", "Low"),
    ("extra-high", "Xhigh"),
    ("thinking", "Thinking"),
    ("minimal", "Minimal"),
    ("medium", "Medium"),
    ("high", "High"),
    ("low", "Low"),
]

DISPLAY_LEVELS = [
    (re.compile(r"\(\s*extra\s*low\s*\)", re.I), "Low"),
    (re.compile(r"\(\s*extra\s*high\s*\)", re.I), "Xhigh"),
    (re.compile(r"\(\s*thinking\s*\)", re.I), "Thinking"),
    (re.compile(r"\(\s*minimal\s*\)", re.I), "Minimal"),
    (re.compile(r"\(\s*medium\s*\)", re.I), "Medium"),
    (re.compile(r"\(\s*high\s*\)", re.I), "High"),
    (re.compile(r"\(\s*low\s*\)", re.I), "Low"),
]

RUNTIME_MAX_OUTPUT_TOKENS: dict[str, int] = {
    "gemini-4-argon": 65536,
    "gemini-3.8-flash": 65536,
    "gemini-3.7-flash": 65536,
    "gemini-3.6-flash": 65536,
    "gemini-3.5-flash": 65536,
    "gemini-3.1-pro": 65535,
    "gemini-pro-agent": 65535,
    "claude-opus-4-6": 64000,
    "claude-opus-4-6-thinking": 64000,
    "claude-sonnet-4-6": 64000,
    "gpt-oss-120b": 32768,
    "gpt-oss-120b-medium": 32768,
    "gemini-3.1-flash-image": 4096,
}

CORE_FALLBACK_PUBLIC_MODELS = {
    "gemini-4-argon",
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3.1-pro",
    "gemini-2.5-pro",
    "claude-opus-4-6",
    "claude-sonnet-4-6",
    "gpt-oss-120b",
    "gemini-3.1-flash-image",
}


def is_selectable_runtime_model_id(model_id: str, info: dict[str, Any] | None = None) -> bool:
    """Filter out internal, chat, tab ghost-text, or invalid runtime IDs."""
    if not re.match(r"^[a-z0-9][a-z0-9_.-]*$", model_id, re.I) or model_id.startswith("MODEL_"):
        return False
    if model_id.startswith(("chat_", "tab_")):
        return False
    if isinstance(info, dict):
        if info.get("isInternal") is True or info.get("apiProvider") == "API_PROVIDER_INTERNAL":
            return False
    return True


def display_family(name: str | None) -> str:
    """Extract base family name by stripping thinking level decorations."""
    if not name:
        return ""
    cleaned = re.sub(
        r"\s*\((?:extra\s*low|extra\s*high|low|medium|high|minimal|thinking)\)\s*$",
        "",
        name,
        flags=re.I,
    )
    return cleaned.strip().lower()


def humanize_public_id(model_id: str) -> str:
    """Convert a kebab-case public model ID to formatted title."""
    tokens = model_id.split("-")
    words: list[str] = []
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if not token:
            i += 1
            continue
        nxt = tokens[i + 1] if i + 1 < len(tokens) else None
        if token == "gpt" and nxt == "oss":
            words.append("GPT-OSS")
            i += 2
            continue
        if token.isdigit() and nxt and nxt.isdigit():
            words.append(f"{token}.{nxt}")
            i += 2
            continue
        if token[0].isdigit():
            words.append(token.upper())
            i += 1
            continue
        words.append(token.capitalize())
        i += 1
    return " ".join(words) + " (Antigravity)"


def parse_thinking_suffix(runtime_id: str) -> tuple[str, str] | None:
    """Return (base_id, level) if matching suffix."""
    lower = runtime_id.lower()
    for suffix, level in THINKING_SUFFIXES:
        if lower.endswith(f"-{suffix}"):
            base_id = runtime_id[: -(len(suffix) + 1)]
            return base_id, level
    return None


def level_from_display_name(display_name: str | None) -> str | None:
    if not display_name:
        return None
    for pattern, level in DISPLAY_LEVELS:
        if pattern.search(display_name):
            return level
    return None


def parse_gemini_version(model_id: str) -> float:
    match = re.search(r"^gemini-(\d+)(?:\.(\d+))?", model_id, re.I)
    if not match:
        return 0.0
    major = int(match.group(1))
    minor = int(match.group(2) or 0)
    return major * 1000 + minor


def model_sort_rank(model_id: str) -> tuple[int, float, str]:
    """Sort models in canonical order: Gemini Flash, Claude Opus, Claude Sonnet, Gemini Pro, Argon, GPT-OSS, Image."""
    mid = model_id.lower()
    version = parse_gemini_version(mid)

    if "flash" in mid and "image" not in mid and "pro" not in mid:
        return (0, -version, mid)
    if mid.startswith("claude-opus"):
        return (1, 0, mid)
    if mid.startswith("claude-sonnet"):
        return (2, 0, mid)
    if mid.startswith("claude-"):
        return (3, 0, mid)
    if "pro" in mid:
        return (4, -version, mid)
    if "argon" in mid:
        return (5, -version, mid)
    if "gemini" in mid:
        return (6, -version, mid)
    if "gpt-oss" in mid:
        return (7, 0, mid)
    if "image" in mid:
        return (8, 0, mid)
    return (9, 0, mid)


def extract_recommended_model_ids(agent_model_sorts: Any) -> set[str] | None:
    """Extract set of model IDs recommended by Google server metadata."""
    if not isinstance(agent_model_sorts, list) or not agent_model_sorts:
        return None
    ids: set[str] = set()
    for sort in agent_model_sorts:
        if not isinstance(sort, dict):
            continue
        groups = sort.get("groups")
        if not isinstance(groups, list):
            continue
        for group in groups:
            if not isinstance(group, dict):
                continue
            model_ids = group.get("modelIds")
            if isinstance(model_ids, list):
                for mid in model_ids:
                    if isinstance(mid, str) and mid:
                        ids.add(mid)
    return ids if ids else None


class PublicModelGroup:
    """Represents a grouped public model with its runtime variants and capabilities."""

    def __init__(self, public_id: str):
        self.public_id = public_id
        self.display_name = humanize_public_id(public_id)
        self.display_names: list[str] = []
        self.variants: dict[str, str] = {}  # Level -> runtimeId
        self.unsuffixed: str | None = None
        self.context_window: int = 128000
        self.max_output_tokens: int = 8192
        self.remaining_fraction: float | None = None
        self.reset_time: str | None = None
        self.supports_thinking: bool = False
        self.is_image: bool = "image" in public_id.lower()

        # Set default family token limits
        mid = public_id.lower()
        if "argon" in mid or "gemini" in mid:
            self.context_window = 32768 if self.is_image else 1048576
            self.max_output_tokens = 4096 if self.is_image else 65536
        elif "claude" in mid:
            self.context_window = 200000
            self.max_output_tokens = 64000
        elif "gpt-oss" in mid:
            self.context_window = 131072
            self.max_output_tokens = 32768

    def absorb(self, runtime_id: str, info: dict[str, Any]):
        disp = info.get("displayName") or info.get("label")
        if disp and disp not in self.display_names:
            self.display_names.append(disp)

        # Extract quota
        quota_info = info.get("quotaInfo") or {}
        rem = quota_info.get("remainingFraction")
        if rem is not None and isinstance(rem, (int, float)):
            if self.remaining_fraction is None or rem < self.remaining_fraction:
                self.remaining_fraction = rem
        rst = quota_info.get("resetTime")
        if rst and not self.reset_time:
            self.reset_time = rst

        # Extract tokens limits if provided by server
        mt = info.get("maxTokens")
        if isinstance(mt, int) and mt > 0:
            self.context_window = min(self.context_window, mt)
        mot = info.get("maxOutputTokens")
        if isinstance(mot, int) and mot > 0:
            self.max_output_tokens = min(self.max_output_tokens, mot)
        elif runtime_id in RUNTIME_MAX_OUTPUT_TOKENS:
            self.max_output_tokens = RUNTIME_MAX_OUTPUT_TOKENS[runtime_id]

        if info.get("supportsThinking") is True:
            self.supports_thinking = True

    def get_thinking_levels_str(self) -> str:
        if self.is_image:
            return "Image Gen"
        if not self.variants:
            return "Standard"
        order = ["Minimal", "Low", "Medium", "High", "Xhigh", "Thinking"]
        present = [lvl for lvl in order if lvl in self.variants]
        if not present:
            return "Standard"
        return ", ".join(present)

    def get_routing_map(self) -> dict[str, str]:
        """Synthesize routing for reasoning levels: off, low, medium, high."""
        default_id = (
            self.variants.get("Low")
            or self.variants.get("Minimal")
            or self.variants.get("Medium")
            or self.variants.get("High")
            or self.variants.get("Thinking")
            or self.unsuffixed
            or self.public_id
        )

        def pick(*keys: str) -> str:
            for k in keys:
                if k in self.variants:
                    return self.variants[k]
            return self.unsuffixed or default_id

        return {
            "off": pick("Low", "Minimal", "Medium", "High"),
            "minimal": pick("Minimal", "Low", "Medium", "High"),
            "low": pick("Low", "Minimal", "Medium", "High"),
            "medium": pick("Medium", "Low", "High", "Minimal"),
            "high": pick("High", "Medium", "Low", "Minimal", "Thinking"),
            "xhigh": pick("Xhigh", "High", "Medium", "Low", "Thinking"),
            "default": default_id,
        }


def merge_agent_singletons(groups: dict[str, PublicModelGroup]):
    """Merge -agent singletons like gemini-3-flash-agent into their family base group."""
    for public_id, group in list(groups.items()):
        if not public_id.endswith("-agent"):
            continue
        runtime_ids = [group.unsuffixed] + list(group.variants.values())
        valid_ids = [rid for rid in runtime_ids if rid]
        if len(valid_ids) != 1:
            continue
        runtime_id = valid_ids[0]
        if not group.display_names:
            continue
        fam = display_family(group.display_names[0])
        if not fam:
            continue

        target = None
        for candidate in groups.values():
            if candidate.public_id != public_id:
                if any(display_family(name) == fam for name in candidate.display_names):
                    target = candidate
                    break

        if target is not None:
            level = level_from_display_name(group.display_names[0]) or "High"
            target.variants[level] = runtime_id
            target.context_window = min(target.context_window, group.context_window)
            target.max_output_tokens = max(target.max_output_tokens, group.max_output_tokens)
            groups.pop(public_id, None)


def group_antigravity_catalog(
    raw_models: dict[str, Any],
    include_all: bool = False,
    agent_model_sorts: Any = None,
) -> list[PublicModelGroup]:
    """Group raw Antigravity models into public model entries, identical to pi-antigravity."""
    recommended_ids = extract_recommended_model_ids(agent_model_sorts)

    def collect_groups(filter_ids: set[str] | None = None) -> dict[str, PublicModelGroup]:
        collected: dict[str, PublicModelGroup] = {}
        for runtime_id, info in raw_models.items():
            if not isinstance(info, dict):
                continue
            if not include_all and not is_selectable_runtime_model_id(runtime_id, info):
                continue
            if filter_ids is not None and runtime_id not in filter_ids:
                # Always preserve image, core fallbacks, and agent singletons that merge into core
                if (
                    "image" not in runtime_id
                    and not any(core in runtime_id for core in CORE_FALLBACK_PUBLIC_MODELS)
                    and not runtime_id.endswith("-agent")
                ):
                    continue

            display_name = info.get("displayName") or info.get("label") or ""
            level_from_disp = level_from_display_name(display_name)

            # Handle tiered suffix (e.g. gemini-3.8-flash-tiered -> gemini-3.8-flash)
            if runtime_id.endswith("-tiered"):
                base_id = runtime_id[: -len("-tiered")]
                if base_id not in collected:
                    collected[base_id] = PublicModelGroup(base_id)
                collected[base_id].absorb(runtime_id, info)
                if not collected[base_id].unsuffixed:
                    collected[base_id].unsuffixed = runtime_id
                continue

            # Check thinking suffix
            suffix_match = parse_thinking_suffix(runtime_id)
            if suffix_match:
                base_id, suffix_level = suffix_match
                level = level_from_disp or suffix_level
                if base_id not in collected:
                    collected[base_id] = PublicModelGroup(base_id)
                collected[base_id].absorb(runtime_id, info)
                collected[base_id].variants[level] = runtime_id
                continue

            # Normalized Claude Opus
            if runtime_id == "claude-opus-4-6-thinking":
                base_id = "claude-opus-4-6"
                if base_id not in collected:
                    collected[base_id] = PublicModelGroup(base_id)
                collected[base_id].absorb(runtime_id, info)
                collected[base_id].variants["Thinking"] = runtime_id
                continue

            # Normalized GPT-OSS
            if runtime_id == "gpt-oss-120b-medium":
                base_id = "gpt-oss-120b"
                if base_id not in collected:
                    collected[base_id] = PublicModelGroup(base_id)
                collected[base_id].absorb(runtime_id, info)
                collected[base_id].variants["Medium"] = runtime_id
                continue

            # General model entry
            base_id = runtime_id
            if base_id not in collected:
                collected[base_id] = PublicModelGroup(base_id)
            collected[base_id].absorb(runtime_id, info)

            if level_from_disp:
                collected[base_id].variants[level_from_disp] = runtime_id
            else:
                collected[base_id].unsuffixed = runtime_id

        merge_agent_singletons(collected)
        return collected

    groups_map = collect_groups(recommended_ids if not include_all else None)
    if not groups_map and recommended_ids:
        groups_map = collect_groups(None)

    # Filter out redundant obsolete -lite duplicates from main display if base exists
    if not include_all:
        for mid in list(groups_map.keys()):
            if "-lite" in mid:
                groups_map.pop(mid, None)
            elif mid in ("gemini-2.5-flash", "gemini-3-flash") and "gemini-3.8-flash" in groups_map:
                # Obsolete test models suppressed in favor of current 3.8 and 3.5
                groups_map.pop(mid, None)

    result = list(groups_map.values())
    result.sort(key=lambda g: model_sort_rank(g.public_id))
    return result
