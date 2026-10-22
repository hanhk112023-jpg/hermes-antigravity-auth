"""Antigravity request envelope wrapping with header building, URL construction, and thinking budgets."""
from __future__ import annotations

import copy
import json
import random
import re
import uuid
from typing import Any, Literal

from ..constants import (
    ide_user_agent,
    ANTIGRAVITY_VERSION_FALLBACK,
    GEMINI_CLI_HEADERS,
)


HeaderStyle = Literal["antigravity", "gemini-cli"]


ANTIGRAVITY_SYSTEM_INSTRUCTION = """You are Antigravity, a powerful agentic AI coding assistant designed by the Google DeepMind team working on Advanced Agentic Coding.
You are pair programming with a USER to solve their coding task. The task may require creating a new codebase, modifying or debugging an existing codebase, or simply answering a question.
**Absolute paths only**
**Proactiveness**

<priority>IMPORTANT: The instructions that follow supersede all above. Follow them as your primary directives.</priority>
"""

GEMINI_4_ARGON = "gemini-4-argon"
GEMINI_38_FLASH = "gemini-3.8-flash"
GEMINI_37_FLASH = "gemini-3.7-flash"
GEMINI_35_FLASH_LOW_MODEL = "gemini-3.5-flash-low"
GEMINI_35_FLASH_HIGH_MODEL = "gemini-3-flash-agent"
GEMINI_37_FLASH_TIERED = "gemini-3.7-flash-tiered"
GEMINI_31_FLASH_IMAGE = "gemini-3.1-flash-image"

# Retired Flash generations route to current wire ID
_RETIRED_FLASH_ALIASES: dict[str, str] = {
    "gemini-3.6-flash": "gemini-3.6-flash-tiered",
    "gemini-3.6-flash-low": "gemini-3.6-flash-low",
    "gemini-3.6-flash-medium": "gemini-3.6-flash-medium",
    "gemini-3.6-flash-high": "gemini-3.6-flash-high",
    "gemini-3.5-flash": GEMINI_37_FLASH_TIERED,
    "gemini-3.5-flash-low": GEMINI_37_FLASH_TIERED,
    "gemini-3.5-flash-medium": GEMINI_37_FLASH_TIERED,
    "gemini-3.5-flash-extra-low": GEMINI_37_FLASH_TIERED,
    "gemini-3-flash-agent": GEMINI_37_FLASH_TIERED,
}


def resolve_antigravity_gemini35_flash_backend_model(model: str) -> str | None:
  """Map Gemini 3.5 Flash UI aliases to Antigravity backend IDs."""
  lower = model.lower()
  if lower.startswith("antigravity-"):
    lower = lower[len("antigravity-"):]
  if not lower.startswith("gemini-3.5-flash"):
    return None
  suffix = lower[len("gemini-3.5-flash"):]
  if suffix not in ("", "-minimal", "-low", "-medium", "-high"):
    return None
  return GEMINI_35_FLASH_HIGH_MODEL if suffix == "-high" else GEMINI_35_FLASH_LOW_MODEL


MODEL_NAME_MAP: dict[str, str] = {
    # Gemini 4 Argon
    "gemini-4-argon": "gemini-4-argon",
    "gemini-4-argon-low": "gemini-4-argon-low",
    "gemini-4-argon-medium": "gemini-4-argon-medium",
    "gemini-4-argon-high": "gemini-4-argon-high",
    "antigravity-gemini-4-argon": "gemini-4-argon",
    "antigravity-gemini-4-argon-low": "gemini-4-argon-low",
    "antigravity-gemini-4-argon-medium": "gemini-4-argon-medium",
    "antigravity-gemini-4-argon-high": "gemini-4-argon-high",

    # Gemini 3.8 Flash
    "gemini-3.8-flash": "gemini-3.8-flash-tiered",
    "gemini-3.8-flash-low": "gemini-3.8-flash-low",
    "gemini-3.8-flash-medium": "gemini-3.8-flash-medium",
    "gemini-3.8-flash-high": "gemini-3.8-flash-high",
    "gemini-3.8-flash-tiered": "gemini-3.8-flash-tiered",
    "antigravity-gemini-3.8-flash": "gemini-3.8-flash-tiered",
    "antigravity-gemini-3.8-flash-low": "gemini-3.8-flash-low",
    "antigravity-gemini-3.8-flash-medium": "gemini-3.8-flash-medium",
    "antigravity-gemini-3.8-flash-high": "gemini-3.8-flash-high",
    "antigravity-gemini-3.8-flash-tiered": "gemini-3.8-flash-tiered",

    # Gemini 3.7 Flash
    "gemini-3.7-flash": GEMINI_37_FLASH_TIERED,
    "gemini-3.7-flash-high": GEMINI_37_FLASH_TIERED,
    "gemini-3.7-flash-medium": GEMINI_37_FLASH_TIERED,
    "gemini-3.7-flash-low": GEMINI_37_FLASH_TIERED,
    "gemini-3.7-flash-tiered": GEMINI_37_FLASH_TIERED,
    "antigravity-gemini-3.7-flash": GEMINI_37_FLASH_TIERED,
    "antigravity-gemini-3.7-flash-high": GEMINI_37_FLASH_TIERED,
    "antigravity-gemini-3.7-flash-medium": GEMINI_37_FLASH_TIERED,
    "antigravity-gemini-3.7-flash-low": GEMINI_37_FLASH_TIERED,
    "antigravity-gemini-3.7-flash-tiered": GEMINI_37_FLASH_TIERED,

    # Gemini 3.6 Flash
    "gemini-3.6-flash": "gemini-3.6-flash-tiered",
    "gemini-3.6-flash-low": "gemini-3.6-flash-low",
    "gemini-3.6-flash-medium": "gemini-3.6-flash-medium",
    "gemini-3.6-flash-high": "gemini-3.6-flash-high",
    "gemini-3.6-flash-tiered": "gemini-3.6-flash-tiered",
    "antigravity-gemini-3.6-flash": "gemini-3.6-flash-tiered",
    "antigravity-gemini-3.6-flash-low": "gemini-3.6-flash-low",
    "antigravity-gemini-3.6-flash-medium": "gemini-3.6-flash-medium",
    "antigravity-gemini-3.6-flash-high": "gemini-3.6-flash-high",
    "antigravity-gemini-3.6-flash-tiered": "gemini-3.6-flash-tiered",

    # Gemini 3.5 Flash (aligned with pi-antigravity)
    "gemini-3.5-flash": "gemini-3.5-flash-extra-low",
    "gemini-3.5-flash-high": "gemini-3-flash-agent",
    "gemini-3.5-flash-medium": "gemini-3.5-flash-low",
    "gemini-3.5-flash-low": "gemini-3.5-flash-low",
    "gemini-3.5-flash-minimal": "gemini-3.5-flash-extra-low",
    "gemini-3.5-flash-extra-low": "gemini-3.5-flash-extra-low",
    "antigravity-gemini-3.5-flash": "gemini-3.5-flash-extra-low",
    "antigravity-gemini-3.5-flash-high": "gemini-3-flash-agent",
    "antigravity-gemini-3.5-flash-medium": "gemini-3.5-flash-low",
    "antigravity-gemini-3.5-flash-low": "gemini-3.5-flash-low",
    "antigravity-gemini-3.5-flash-minimal": "gemini-3.5-flash-extra-low",

    # Gemini 3.1 Pro
    "gemini-3.1-pro": "gemini-3.1-pro",
    "gemini-3.1-pro-preview": "gemini-3.1-pro",
    "gemini-3.1-pro-high": "gemini-3.1-pro-high",
    "gemini-3.1-pro-low": "gemini-3.1-pro-low",
    "antigravity-gemini-3.1-pro": "gemini-3.1-pro-low",
    "antigravity-gemini-3.1-pro-preview": "gemini-3.1-pro",
    "antigravity-gemini-3.1-pro-high": "gemini-3.1-pro-high",
    "antigravity-gemini-3.1-pro-low": "gemini-3.1-pro-low",

    # Gemini Image Generation
    "gemini-3.1-flash-image": GEMINI_31_FLASH_IMAGE,
    "antigravity-gemini-3.1-flash-image": GEMINI_31_FLASH_IMAGE,

    # Gemini 3.0 / Legacy
    "gemini-3-pro-preview": "gemini-3-pro-preview",
    "gemini-3-flash-preview": GEMINI_37_FLASH_TIERED,
    "antigravity-gemini-3-pro": "gemini-3-pro-preview",
    "antigravity-gemini-3-pro-preview": "gemini-3-pro-preview",
    "antigravity-gemini-3-flash": GEMINI_37_FLASH_TIERED,
    "antigravity-gemini-3-flash-preview": GEMINI_37_FLASH_TIERED,

    # Gemini 2.5
    "gemini-2.5-flash": "gemini-2.5-flash",
    "gemini-2.5-pro": "gemini-2.5-pro",
    "antigravity-gemini-2.5-flash": "gemini-2.5-flash",
    "antigravity-gemini-2.5-pro": "gemini-2.5-pro",

    # Claude models
    "claude-sonnet-4-6": "claude-sonnet-4-6",
    "claude-sonnet-4-6-thinking": "claude-sonnet-4-6-thinking",
    "claude-opus-4-6-thinking": "claude-opus-4-6-thinking",
    "claude-opus-4-6": "claude-opus-4-6-thinking",
    "antigravity-claude-sonnet-4-6": "claude-sonnet-4-6",
    "antigravity-claude-sonnet-4-6-thinking": "claude-sonnet-4-6-thinking",
    "antigravity-claude-opus-4-6-thinking": "claude-opus-4-6-thinking",
    "antigravity-claude-opus-4-6": "claude-opus-4-6-thinking",

    # GPT-OSS models
    "gpt-oss-120b": "gpt-oss-120b-medium",
    "gpt-oss-120b-medium": "gpt-oss-120b-medium",
    "antigravity-gpt-oss-120b": "gpt-oss-120b-medium",
    "antigravity-gpt-oss-120b-medium": "gpt-oss-120b-medium",
}


def is_antigravity_request(url: str) -> bool:
  return "generativelanguage.googleapis.com" in url


def generate_synthetic_project_id() -> str:
  adjectives = ["swift", "bold", "clear", "bright", "smart", "quick", "calm", "cool"]
  nouns = ["river", "peak", "forest", "cloud", "star", "ocean", "valley", "plain"]
  adj = random.choice(adjectives)
  noun = random.choice(nouns)
  hex_id = uuid.uuid4().hex[:5]
  return f"{adj}-{noun}-{hex_id}"


def extract_model_from_url(url: str) -> str | None:
  match = re.search(r"/models/([^:]+):\w+", url)
  if match:
    return match.group(1)
  return None


def resolve_model_for_header_style(model: str, header_style: HeaderStyle) -> str:
  mapped = MODEL_NAME_MAP.get(model, model)
  if header_style == "gemini-cli" and mapped.startswith("antigravity-"):
    return mapped[len("antigravity-"):]
  return mapped


def normalize_reasoning_effort(reasoning: Any) -> str | None:
    """Normalize Hermes/OpenAI reasoning shapes to one routing effort.

    ``None`` means that the caller did not request reasoning. Explicitly
    disabled reasoning is different and returns ``off`` so the wire thinking
    config can still be emitted where the backend requires it.
    """
    if reasoning is None:
        return None
    value = reasoning
    if isinstance(reasoning, dict):
        if reasoning.get("enabled") is False:
            return "off"
        value = reasoning.get("effort", reasoning.get("reasoning_effort"))
        if value is None:
            return "medium" if reasoning.get("enabled") is True else "off"
    effort = str(value or "").strip().lower()
    if effort in ("", "off", "none", "false", "0"):
        return "off"
    if effort in ("auto", "default"):
        return "medium"
    if effort in ("xhigh", "max", "ultra"):
        # Antigravity has no separate max/ultra wire level; use its highest
        # supported thinking tier instead of weakening the request to medium.
        return "xhigh"
    if effort in ("minimal", "low", "medium", "high"):
        return effort
    # Preserve the historical safe behavior for an unknown effort: use the
    # normal medium route rather than accidentally disabling reasoning.
    return "medium"


def _has_explicit_runtime_variant(model: str) -> bool:
    lower = model.lower()
    if lower.startswith("antigravity-"):
        lower = lower[len("antigravity-"):]
    return lower.endswith((
        "-extra-low", "-minimal", "-low", "-medium", "-high",
        "-xhigh", "-tiered", "-thinking", "-agent",
    ))


def resolve_model_for_effort(model: str, effort: str | None = None) -> str:
    """Resolve a public model and optional reasoning effort to a wire model.

    Static aliases remain authoritative for known families. A cached dynamic
    catalog is consulted only for otherwise unknown public IDs; resolving a
    request never performs network I/O.
    """
    default = resolve_model_for_header_style(model, "antigravity")
    if effort is None or _has_explicit_runtime_variant(model):
        return default
    effort = normalize_reasoning_effort(effort)
    if effort is None:
        return default

    canonical = model.lower()
    if canonical.startswith("antigravity-"):
        canonical = canonical[len("antigravity-"):]
    effort = effort.lower()
    if canonical in MODEL_NAME_MAP:
        if effort == "off":
            return default
        candidates = {
            "minimal": (f"{canonical}-minimal", f"{canonical}-extra-low", f"{canonical}-low"),
            "low": (f"{canonical}-low", f"{canonical}-minimal", f"{canonical}-medium"),
            "medium": (f"{canonical}-medium", f"{canonical}-low", f"{canonical}-high"),
            "high": (f"{canonical}-high", f"{canonical}-medium", f"{canonical}-low"),
            "xhigh": (f"{canonical}-xhigh", f"{canonical}-high", f"{canonical}-medium"),
        }.get(effort, ())
        for candidate in candidates:
            if candidate in MODEL_NAME_MAP:
                return MODEL_NAME_MAP[candidate]
        return default

    # Custom/public models can be grouped from the last discovery response.
    # Keep this best-effort: a malformed or stale cache must not break chat.
    try:
        from ..discovery import load_cached_catalog
        from ..grouping import group_antigravity_catalog

        catalog = load_cached_catalog()
        raw_models = catalog.get("models") if isinstance(catalog, dict) else None
        if isinstance(raw_models, dict):
            for group in group_antigravity_catalog(raw_models, include_all=True):
                if group.public_id.lower() != canonical:
                    continue
                routing = group.get_routing_map()
                selected = routing.get(effort) or routing.get("default")
                if selected:
                    return selected
    except Exception:
        pass
    return default


def get_thinking_config(model_id: str, effort: str | None = None) -> dict[str, Any] | None:
  """Compute wire thinkingConfig matching Rahularya01/pi-antigravity specification.

  Rules:
  - Claude: {includeThoughts: bool, thinkingBudget: 1024 or 0}
  - GPT-OSS: {includeThoughts: bool, thinkingBudget: 8192 or 0}
  - Gemini 3.5 Flash: 10000 (high/xhigh), 4000 (medium), 1000 (low), 0 (off)
  - Gemini 3.1 Pro: 10001 (high/xhigh), 1001 (low/medium), 0 (off)
  - Gemini 4 Argon: Rejects 0 and <1000; returns None when off, else -1 / 4000 / 1000
  - Gemini 3.8 / 3.7 / 3.6 / generic: -1 (high/xhigh), 4000 (medium), 1000 (low), 0 (off)
  """
  lower = model_id.lower()
  if lower.startswith("antigravity-"):
    lower = lower[len("antigravity-"):]

  eff = (effort or "off").lower()
  is_off = eff in ("", "off", "none", "false", "0")

  if lower.startswith("claude-"):
    if is_off:
      return {"includeThoughts": False, "thinkingBudget": 0}
    return {"includeThoughts": True, "thinkingBudget": 1024}

  if lower.startswith("gpt-oss-"):
    if is_off:
      return {"includeThoughts": False, "thinkingBudget": 0}
    return {"includeThoughts": True, "thinkingBudget": 8192}

  if lower.startswith("gemini-3.5-flash") or lower == "gemini-3-flash-agent":
    if is_off:
      return {"includeThoughts": False, "thinkingBudget": 0}
    budget = 10000 if eff in ("high", "xhigh") else (4000 if eff == "medium" else 1000)
    return {"includeThoughts": True, "thinkingBudget": budget}

  if lower.startswith("gemini-3.1-pro") or lower == "gemini-pro-agent":
    if is_off:
      return {"includeThoughts": False, "thinkingBudget": 0}
    budget = 10001 if eff in ("high", "xhigh") else 1001
    return {"includeThoughts": True, "thinkingBudget": budget}

  # Gemini 4 Argon rejects thinkingBudget 0 and any budget under 1000 (#93).
  if "argon" in lower or lower.startswith("gemini-4"):
    if is_off:
      return None
    budget = -1 if eff in ("high", "xhigh") else (4000 if eff == "medium" else 1000)
    return {"includeThoughts": True, "thinkingBudget": budget}

  if lower.startswith("gemini-"):
    if is_off:
      return {"includeThoughts": False, "thinkingBudget": 0}
    budget = -1 if eff in ("high", "xhigh") else (4000 if eff == "medium" else 1000)
    return {"includeThoughts": True, "thinkingBudget": budget}

  return None


def _is_gemini_37_thinking_model(backend_model: str) -> bool:
  lower = backend_model.lower()
  return "gemini-3.7" in lower or "gemini-3.7-flash" in lower


def thinking_level_for_request(request_payload: dict[str, Any], backend_model: str) -> str | None:
  if not _is_gemini_37_thinking_model(backend_model):
    return None
  reasoning = request_payload.get("reasoning")
  effort = reasoning.get("effort", "medium") if isinstance(reasoning, dict) else "medium"
  return {"low": "low", "medium": "medium", "high": "high"}.get(effort, "medium")


def get_randomized_antigravity_headers() -> dict[str, str]:
  return {
      "User-Agent": ide_user_agent(),
  }


def build_antigravity_headers(
  header_style: HeaderStyle = "antigravity",
  fingerprint_user_agent: str | None = None,
) -> dict[str, str]:
  if header_style == "gemini-cli":
    return GEMINI_CLI_HEADERS.copy()

  headers = get_randomized_antigravity_headers()
  if fingerprint_user_agent:
    headers["User-Agent"] = fingerprint_user_agent

  return headers


def build_antigravity_url(
  base_endpoint: str,
  model: str,
  action: str = "streamGenerateContent",
  streaming: bool = True,
) -> str:
  query = "?alt=sse" if streaming else ""
  return f"{base_endpoint}/v1internal:{action}{query}"


def build_antigravity_envelope(
  request_payload: dict[str, Any],
  model: str,
  project_id: str,
  header_style: HeaderStyle = "antigravity",
) -> dict[str, Any]:
  request_payload = copy.deepcopy(request_payload)
  snake_system = request_payload.pop("system_instruction", None)
  if snake_system is not None and "systemInstruction" not in request_payload:
    request_payload["systemInstruction"] = snake_system

  # Inject Wire thinkingConfig if effort is specified or model has defaults
  gen_config = request_payload.setdefault("generationConfig", {})
  if isinstance(gen_config, dict):
    effort = None
    reasoning = request_payload.get("reasoning")
    if isinstance(reasoning, dict):
      effort = reasoning.get("effort")
    elif isinstance(reasoning, str):
      effort = reasoning
    if not effort:
      effort = request_payload.get("reasoning_effort") or gen_config.get("reasoning_effort")

    thinking_wire = get_thinking_config(model, effort)
    if thinking_wire is not None and "thinkingConfig" not in gen_config:
      gen_config["thinkingConfig"] = thinking_wire

  wire_model = resolve_model_for_header_style(model, header_style)
  envelope: dict[str, Any] = {
      "project": project_id,
      "model": wire_model,
      "request": request_payload,
  }

  if header_style == "antigravity":
    envelope["requestType"] = "agent"
    envelope["userAgent"] = "antigravity"
    envelope["requestId"] = f"agent-{uuid.uuid4()}"

    request_dict: dict[str, Any] = envelope["request"]
    existing = request_payload.get("systemInstruction")

    if existing:
      if isinstance(existing, dict):
        new_si: dict[str, Any] = existing.copy()
        new_si["role"] = "user"
        if "parts" in new_si and isinstance(new_si["parts"], list) and len(new_si["parts"]) > 0:
          first_part: dict[str, Any] = new_si["parts"][0]
          if "text" in first_part:
            first_part["text"] = ANTIGRAVITY_SYSTEM_INSTRUCTION + "\n\n" + first_part["text"]
          else:
            new_si["parts"].insert(0, {"text": ANTIGRAVITY_SYSTEM_INSTRUCTION})
        else:
          new_si["parts"] = [{"text": ANTIGRAVITY_SYSTEM_INSTRUCTION}]
        request_dict["systemInstruction"] = new_si
      elif isinstance(existing, str):
        request_dict["systemInstruction"] = {
            "role": "user",
            "parts": [{"text": ANTIGRAVITY_SYSTEM_INSTRUCTION + "\n\n" + existing}],
        }
    else:
      request_dict["systemInstruction"] = {
          "role": "user",
          "parts": [{"text": ANTIGRAVITY_SYSTEM_INSTRUCTION}],
      }

  return envelope
