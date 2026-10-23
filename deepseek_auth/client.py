"""DeepSeek Web Reverse-Engineering API Client.
Handles login, session creation, PoW challenge solving, and streaming completions.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Iterator
import httpx

from .pow import solve_pow_challenge
from .storage import add_or_update_account, get_active_account, load_accounts, save_accounts

logger = logging.getLogger(__name__)

DEEPSEEK_HOST = "chat.deepseek.com"
DEEPSEEK_BASE_URL = f"https://{DEEPSEEK_HOST}"
DEEPSEEK_LOGIN_URL = f"{DEEPSEEK_BASE_URL}/api/v0/users/login"
DEEPSEEK_CREATE_SESSION_URL = f"{DEEPSEEK_BASE_URL}/api/v0/chat_session/create"
DEEPSEEK_CREATE_POW_URL = f"{DEEPSEEK_BASE_URL}/api/v0/chat/create_pow_challenge"
DEEPSEEK_COMPLETION_URL = f"{DEEPSEEK_BASE_URL}/api/v0/chat/completion"
DEEPSEEK_DELETE_SESSION_URL = f"{DEEPSEEK_BASE_URL}/api/v0/chat_session/delete"

BASE_HEADERS = {
    "Host": DEEPSEEK_HOST,
    "User-Agent": "DeepSeek/2.1.1 Android/35",
    "Accept": "application/json",
    "Accept-Encoding": "gzip",
    "Content-Type": "application/json",
    "x-client-platform": "android",
    "x-client-version": "2.1.1",
    "x-client-locale": "zh_CN",
    "accept-charset": "UTF-8",
}


def login_deepseek(account_data: dict[str, Any]) -> str:
    """Login using email/mobile and password, return the user token."""
    email = account_data.get("email", "").strip()
    mobile = account_data.get("mobile", "").strip()
    password = account_data.get("password", "").strip()

    if not password or (not email and not mobile):
        raise ValueError("Missing login credentials: password and either email or mobile required")

    payload = {
        "device_id": "deepseek_to_api",
        "os": "android",
        "password": password,
    }
    if email:
        payload["email"] = email
    else:
        payload["mobile"] = mobile
        payload["area_code"] = None

    with httpx.Client(timeout=15.0) as client:
        resp = client.post(DEEPSEEK_LOGIN_URL, headers=BASE_HEADERS, json=payload)
        resp.raise_for_status()
        data = resp.json()

    if data.get("code") != 0 or not data.get("data"):
        biz_msg = (data.get("data") or {}).get("biz_msg") or data.get("msg") or "Login failed"
        raise RuntimeError(f"DeepSeek login failed: {biz_msg}")

    biz_data = data["data"].get("biz_data") or {}
    user_info = biz_data.get("user") or {}
    token = user_info.get("token")
    if not token:
        raise RuntimeError("DeepSeek login response missing token")

    identifier = email or mobile
    add_or_update_account(identifier, token, password=password, email=email, mobile=mobile)
    logger.info("Successfully logged in DeepSeek account: %s", identifier)
    return token


class DeepSeekWebClient:
    """OpenAI-compatible client facade routing completions through DeepSeek Web."""

    def __init__(self, api_key: str = "", **kwargs: Any) -> None:
        self.api_key = api_key
        self.base_url = "https://chat.deepseek.com"
        self._http = httpx.Client(timeout=httpx.Timeout(connect=15.0, read=300.0, write=30.0, pool=30.0))
        self.chat = _DeepSeekChatNamespace(self)

    def _get_auth_headers(self, token: str) -> dict[str, str]:
        headers = dict(BASE_HEADERS)
        headers["authorization"] = f"Bearer {token}"
        return headers

    def _ensure_token(self) -> tuple[str, dict[str, Any]]:
        acc = get_active_account()
        if not acc:
            raise RuntimeError("No active DeepSeek account configured. Run 'hermes deepseek login' first.")
        token = acc.get("token", "").strip()
        if not token:
            token = login_deepseek(acc)
        return token, acc

    def _create_session(self, token: str) -> str:
        headers = self._get_auth_headers(token)
        resp = self._http.post(
            DEEPSEEK_CREATE_SESSION_URL,
            headers=headers,
            json={"agent": "chat"},
            timeout=15.0,
        )
        data = resp.json()
        if resp.status_code == 200 and data.get("code") == 0:
            biz_data = data.get("data", {}).get("biz_data", {})
            if "chat_session" in biz_data and "id" in biz_data["chat_session"]:
                return str(biz_data["chat_session"]["id"])
            if "id" in biz_data:
                return str(biz_data["id"])
        msg = data.get("msg") or str(resp.status_code)
        raise RuntimeError(f"Failed to create DeepSeek chat session: {msg}")

    def _get_pow_challenge(self, token: str) -> str:
        headers = self._get_auth_headers(token)
        resp = self._http.post(
            DEEPSEEK_CREATE_POW_URL,
            headers=headers,
            json={"target_path": "/api/v0/chat/completion"},
            timeout=15.0,
        )
        data = resp.json()
        if resp.status_code == 200 and data.get("code") == 0:
            biz_data = data.get("data", {}).get("biz_data", {})
            challenge = biz_data.get("challenge") or biz_data
            return solve_pow_challenge(challenge)
        msg = data.get("msg") or str(resp.status_code)
        raise RuntimeError(f"Failed to obtain DeepSeek PoW challenge: {msg}")

    def _delete_session(self, token: str, session_id: str) -> None:
        try:
            headers = self._get_auth_headers(token)
            self._http.post(
                DEEPSEEK_DELETE_SESSION_URL,
                headers=headers,
                json={"chat_session_id": session_id},
                timeout=5.0,
            )
        except Exception as exc:
            logger.debug("Failed to delete DeepSeek session %s: %s", session_id, exc)

    def _create_chat_completion(self, **kwargs: Any) -> Any:
        messages = kwargs.get("messages", [])
        stream = bool(kwargs.get("stream", False))
        model = str(kwargs.get("model", "deepseek-chat"))

        # Convert OpenAI messages to simple prompt text
        prompt_parts: list[str] = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if isinstance(content, list):
                # Flatten multimodal or parts
                content = " ".join(p.get("text", "") for p in content if isinstance(p, dict))
            prompt_parts.append(f"{role.capitalize()}: {content}")
        final_prompt = "\n\n".join(prompt_parts)

        m = model.lower()
        thinking_enabled = "r1" in m or "reasoner" in m or "think" in m or "deepthink" in m
        search_enabled = bool(kwargs.get("search_enabled", False)) or "search" in m

        token, _ = self._ensure_token()
        session_id = self._create_session(token)
        pow_resp = self._get_pow_challenge(token)

        headers = self._get_auth_headers(token)
        headers["x-ds-pow-response"] = pow_resp

        payload = {
            "chat_session_id": session_id,
            "parent_message_id": None,
            "prompt": final_prompt,
            "ref_file_ids": [],
            "thinking_enabled": thinking_enabled,
            "search_enabled": search_enabled,
        }

        if stream:
            return self._stream_completion(token, session_id, payload, headers, model)

        # Non-streaming
        try:
            with self._http.stream(
                "POST",
                DEEPSEEK_COMPLETION_URL,
                headers=headers,
                json=payload,
                timeout=180.0,
            ) as response:
                response.raise_for_status()
                text_result = ""
                reasoning_result = ""
                current_fragment_type = "RESPONSE"

                for line in response.iter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data_str = line[5:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk_obj = json.loads(data_str)
                        if chunk_obj.get("p") == "response/status" and chunk_obj.get("v") == "FINISHED":
                            break
                        if chunk_obj.get("p") in ("response/search_status", "response/status"):
                            continue

                        val = chunk_obj.get("v")
                        # 1. New fragment appended: [{"id": 3, "type": "RESPONSE", "content": "..."}]
                        if chunk_obj.get("p") == "response/fragments" and isinstance(val, list):
                            for frag in val:
                                if isinstance(frag, dict) and "type" in frag:
                                    current_fragment_type = frag.get("type", "RESPONSE")
                                    content = frag.get("content", "")
                                    if content:
                                        if current_fragment_type == "THINK":
                                            reasoning_result += content
                                        elif current_fragment_type == "RESPONSE":
                                            text_result += content
                            continue

                        # 2. Initial message envelope with fragments
                        if isinstance(val, dict):
                            resp_meta = val.get("response", {})
                            for frag in resp_meta.get("fragments", []):
                                if isinstance(frag, dict) and "type" in frag:
                                    current_fragment_type = frag.get("type", "RESPONSE")
                                    content = frag.get("content", "")
                                    if content:
                                        if current_fragment_type == "THINK":
                                            reasoning_result += content
                                        elif current_fragment_type == "RESPONSE":
                                            text_result += content
                            continue

                        # 3. Text delta (string val)
                        if isinstance(val, str):
                            if current_fragment_type == "THINK":
                                reasoning_result += val
                            elif current_fragment_type == "RESPONSE":
                                text_result += val
                    except Exception:
                        pass
        finally:
            self._delete_session(token, session_id)

        from types import SimpleNamespace
        msg_ns = SimpleNamespace(role="assistant", content=text_result)
        if reasoning_result:
            msg_ns.reasoning_content = reasoning_result
            msg_ns.reasoning = reasoning_result

        return SimpleNamespace(
            id=f"chatcmpl-{session_id}",
            object="chat.completion",
            created=int(time.time()),
            model=model,
            choices=[
                SimpleNamespace(
                    index=0,
                    message=msg_ns,
                    finish_reason="stop",
                )
            ],
            usage=SimpleNamespace(prompt_tokens=len(final_prompt)//4, completion_tokens=len(text_result)//4, total_tokens=(len(final_prompt)+len(text_result))//4),
        )

    def _stream_completion(
        self,
        token: str,
        session_id: str,
        payload: dict[str, Any],
        headers: dict[str, str],
        model: str,
    ) -> Iterator[Any]:
        from types import SimpleNamespace

        def _generator() -> Iterator[Any]:
            try:
                with self._http.stream(
                    "POST",
                    DEEPSEEK_COMPLETION_URL,
                    headers=headers,
                    json=payload,
                    timeout=300.0,
                ) as resp:
                    resp.raise_for_status()
                    current_fragment_type = "RESPONSE"

                    for line in resp.iter_lines():
                        if not line or not line.startswith("data:"):
                            continue
                        raw = line[5:].strip()
                        if raw == "[DONE]":
                            break
                        try:
                            parsed = json.loads(raw)
                            if parsed.get("p") == "response/status" and parsed.get("v") == "FINISHED":
                                break
                            if parsed.get("p") in ("response/search_status", "response/status"):
                                continue

                            # 1. New fragment appended
                            if parsed.get("p") == "response/fragments" and isinstance(parsed.get("v"), list):
                                for frag in parsed["v"]:
                                    if isinstance(frag, dict) and "type" in frag:
                                        current_fragment_type = frag.get("type", "RESPONSE")
                                        content = frag.get("content", "")
                                        if content:
                                            delta_kwargs = {"role": "assistant"}
                                            if current_fragment_type == "THINK":
                                                delta_kwargs["reasoning_content"] = content
                                                delta_kwargs["content"] = ""
                                            else:
                                                delta_kwargs["content"] = content
                                            yield SimpleNamespace(
                                                id=f"chatcmpl-{session_id}",
                                                object="chat.completion.chunk",
                                                created=int(time.time()),
                                                model=model,
                                                choices=[
                                                    SimpleNamespace(
                                                        index=0,
                                                        delta=SimpleNamespace(**delta_kwargs),
                                                        finish_reason=None,
                                                    )
                                                ],
                                            )
                                continue

                            # 2. Initial envelope
                            val = parsed.get("v")
                            if isinstance(val, dict):
                                resp_meta = val.get("response", {})
                                for frag in resp_meta.get("fragments", []):
                                    if isinstance(frag, dict) and "type" in frag:
                                        current_fragment_type = frag.get("type", "RESPONSE")
                                        content = frag.get("content", "")
                                        if content:
                                            delta_kwargs = {"role": "assistant"}
                                            if current_fragment_type == "THINK":
                                                delta_kwargs["reasoning_content"] = content
                                                delta_kwargs["content"] = ""
                                            else:
                                                delta_kwargs["content"] = content
                                            yield SimpleNamespace(
                                                id=f"chatcmpl-{session_id}",
                                                object="chat.completion.chunk",
                                                created=int(time.time()),
                                                model=model,
                                                choices=[
                                                    SimpleNamespace(
                                                        index=0,
                                                        delta=SimpleNamespace(**delta_kwargs),
                                                        finish_reason=None,
                                                    )
                                                ],
                                            )
                                continue

                            # 3. String delta
                            if isinstance(val, str) and val:
                                delta_kwargs = {"role": "assistant"}
                                if current_fragment_type == "THINK":
                                    delta_kwargs["reasoning_content"] = val
                                    delta_kwargs["content"] = ""
                                else:
                                    delta_kwargs["content"] = val
                                yield SimpleNamespace(
                                    id=f"chatcmpl-{session_id}",
                                    object="chat.completion.chunk",
                                    created=int(time.time()),
                                    model=model,
                                    choices=[
                                        SimpleNamespace(
                                            index=0,
                                            delta=SimpleNamespace(**delta_kwargs),
                                            finish_reason=None,
                                        )
                                    ],
                                )
                        except Exception:
                            continue

                # Emit final chunk with finish_reason="stop" so Hermes knows stream ended cleanly
                yield SimpleNamespace(
                    id=f"chatcmpl-{session_id}",
                    object="chat.completion.chunk",
                    created=int(time.time()),
                    model=model,
                    choices=[
                        SimpleNamespace(
                            index=0,
                            delta=SimpleNamespace(content="", role="assistant"),
                            finish_reason="stop",
                        )
                    ],
                )
            finally:
                self._delete_session(token, session_id)

        return _generator()

    def close(self) -> None:
        self._http.close()


class _DeepSeekChatCompletions:
    def __init__(self, client: DeepSeekWebClient) -> None:
        self._client = client

    def create(self, **kwargs: Any) -> Any:
        return self._client._create_chat_completion(**kwargs)


class _DeepSeekChatNamespace:
    def __init__(self, client: DeepSeekWebClient) -> None:
        self.completions = _DeepSeekChatCompletions(client)
