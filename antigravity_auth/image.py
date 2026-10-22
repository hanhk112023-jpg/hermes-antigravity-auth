"""Native image generation using Antigravity gemini-3.1-flash-image API.
Ported from Rahularya01/pi-antigravity for Hermes Agent.
"""
from __future__ import annotations

import base64
import json
import os
import time
import urllib.error
import urllib.request
import uuid
from typing import Any, Dict, List, Optional, Tuple

from .constants import (
    ANTIGRAVITY_ENDPOINT_PROD,
    ANTIGRAVITY_DEFAULT_PROJECT_ID,
    get_antigravity_headers,
)
from .redaction import redact_secret_text

DEFAULT_IMAGE_MODEL = "gemini-3.1-flash-image"

IMAGE_ASPECT_RATIOS = (
    "1:1",
    "2:3",
    "3:2",
    "3:4",
    "4:3",
    "4:5",
    "5:4",
    "9:16",
    "16:9",
    "21:9",
)

DEFAULT_IMAGE_DIR = os.path.expanduser("~/.hermes/generated-images")


def assert_safe_aspect_ratio(ratio: str) -> str:
    cleaned = ratio.strip()
    if cleaned in IMAGE_ASPECT_RATIOS:
        return cleaned
    raise ValueError(
        f"Unsupported aspect ratio: '{ratio}'. Allowed ratios: {', '.join(IMAGE_ASPECT_RATIOS)}"
    )


def build_image_generate_request(
    prompt: str,
    project_id: str,
    aspect_ratio: str = "1:1",
    model: str = DEFAULT_IMAGE_MODEL,
) -> Dict[str, Any]:
    safe_ratio = assert_safe_aspect_ratio(aspect_ratio)
    return {
        "project": project_id,
        "model": model,
        "request": {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}],
                }
            ],
            "generationConfig": {
                "imageConfig": {"aspectRatio": safe_ratio},
                "candidateCount": 1,
            },
        },
        "requestType": "image_gen",
        "userAgent": "antigravity",
        "requestId": f"image_gen/{int(time.time() * 1000)}/{uuid.uuid4()}/1",
    }


def parse_image_response_payload(raw_text: str) -> Tuple[List[Dict[str, str]], List[str]]:
    """Extract inlineData images and text parts from either SSE lines or a JSON response."""
    images: List[Dict[str, str]] = []
    text_chunks: List[str] = []

    def inspect_parts(parts: Any) -> None:
        if not isinstance(parts, list):
            return
        for part in parts:
            if not isinstance(part, dict):
                continue
            if part.get("text"):
                text_chunks.append(part["text"])
            inline_data = part.get("inlineData")
            if isinstance(inline_data, dict) and inline_data.get("data"):
                images.append({
                    "mimeType": inline_data.get("mimeType", "image/png"),
                    "data": inline_data["data"],
                })

    def process_chunk(chunk: Any) -> None:
        if not isinstance(chunk, dict):
            return
        candidates = chunk.get("candidates")
        if not candidates and isinstance(chunk.get("response"), dict):
            candidates = chunk["response"].get("candidates")
        if isinstance(candidates, list):
            for candidate in candidates:
                if isinstance(candidate, dict):
                    content = candidate.get("content")
                    if isinstance(content, dict):
                        inspect_parts(content.get("parts"))

    # Try as SSE
    lines = raw_text.splitlines()
    has_sse = any(line.strip().startswith("data:") for line in lines)
    if has_sse:
        for line in lines:
            trimmed = line.strip()
            if not trimmed.startswith("data:"):
                continue
            payload = trimmed[5:].strip()
            if not payload or payload == "[DONE]":
                continue
            try:
                parsed = json.loads(payload)
                process_chunk(parsed)
            except Exception:
                continue
    else:
        # Try raw JSON
        try:
            parsed = json.loads(raw_text)
            process_chunk(parsed)
        except Exception:
            pass

    return images, text_chunks


def generate_image(
    prompt: str,
    access_token: str,
    project_id: str,
    aspect_ratio: str = "1:1",
    model: str = DEFAULT_IMAGE_MODEL,
    output_path: Optional[str] = None,
    timeout: float = 60.0,
) -> Dict[str, Any]:
    """Call Antigravity API to generate an image and save it to disk."""
    req_payload = build_image_generate_request(
        prompt=prompt,
        project_id=project_id,
        aspect_ratio=aspect_ratio,
        model=model,
    )

    url = f"{ANTIGRAVITY_ENDPOINT_PROD}/v1internal:streamGenerateContent?alt=sse"
    headers = get_antigravity_headers()
    headers["Authorization"] = f"Bearer {access_token}"
    headers["Content-Type"] = "application/json"
    headers["Accept"] = "text/event-stream, application/json"

    body_bytes = json.dumps(req_payload).encode("utf-8")
    req = urllib.request.Request(url, data=body_bytes, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw_text = resp.read().decode("utf-8", errors="ignore")
    except urllib.error.HTTPError as exc:
        err_msg = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"Image generation failed with HTTP {exc.code}: {redact_secret_text(err_msg)}")

    images, text_chunks = parse_image_response_payload(raw_text)
    if not images:
        fallback_note = " ".join(text_chunks) if text_chunks else "No image returned by model."
        raise RuntimeError(f"Antigravity returned no image data. Notes: {fallback_note}")

    img_info = images[0]
    mime_type = img_info["mimeType"]
    ext = "jpg" if "jpeg" in mime_type or "jpg" in mime_type else ("webp" if "webp" in mime_type else "png")

    if not output_path:
        os.makedirs(DEFAULT_IMAGE_DIR, exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(DEFAULT_IMAGE_DIR, f"antigravity_{timestamp}_{uuid.uuid4().hex[:6]}.{ext}")
    else:
        output_path = os.path.expanduser(output_path)
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    img_bytes = base64.b64decode(img_info["data"])
    with open(output_path, "wb") as f:
        f.write(img_bytes)

    return {
        "saved_path": output_path,
        "mime_type": mime_type,
        "aspect_ratio": aspect_ratio,
        "model": model,
        "prompt": prompt,
        "text": text_chunks,
        "size_bytes": len(img_bytes),
    }
