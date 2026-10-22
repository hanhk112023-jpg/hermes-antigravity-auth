import asyncio
import json
import os
import sys
import types
import unittest
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import httpx

import antigravity_auth.cloudcode_client as cloudcode_client


class TestAntigravityCloudCodeClient(unittest.TestCase):
  def test_close_failure_preserves_state_and_can_retry(self):
    with patch("antigravity_auth.cloudcode_client._wrap_antigravity_http_client", side_effect=lambda client: client):
      backend = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200)), trust_env=False)
      client = cloudcode_client.AntigravityCloudCodeClient(http_client=backend)
      with patch.object(backend, "close", side_effect=OSError("backend close denied")):
        with self.assertRaisesRegex(OSError, "backend close denied"):
          client.close()
      self.assertFalse(client.is_closed)
      client.close()
      client.close()
      self.assertTrue(client.is_closed)

  def test_sync_context_chains_body_error_when_close_fails(self):
    body_error = ValueError("body failed")
    with patch("antigravity_auth.cloudcode_client._wrap_antigravity_http_client", side_effect=lambda client: client):
      backend = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200)), trust_env=False)
      client = cloudcode_client.AntigravityCloudCodeClient(http_client=backend)
      with patch.object(backend, "close", side_effect=OSError("backend close denied")):
        with self.assertRaisesRegex(OSError, "backend close denied") as caught:
          with client:
            raise body_error
      self.assertIs(caught.exception.__context__, body_error)
      self.assertFalse(client.is_closed)
      client.close()

  def test_async_close_failure_and_context_error_chaining(self):
    with patch("antigravity_auth.cloudcode_client._wrap_antigravity_http_client", side_effect=lambda client: client):
      backend = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200)), trust_env=False)
      sync = cloudcode_client.AntigravityCloudCodeClient(http_client=backend)
      client = cloudcode_client.AsyncAntigravityCloudCodeClient(sync)

      async def check():
        body_error = ValueError("async body failed")
        with patch.object(backend, "close", side_effect=OSError("backend close denied")):
          with self.assertRaisesRegex(OSError, "backend close denied"):
            await client.close()
          self.assertFalse(client.is_closed)
          with self.assertRaisesRegex(OSError, "backend close denied") as caught:
            async with client:
              raise body_error
          self.assertIs(caught.exception.__context__, body_error)
          self.assertFalse(client.is_closed)
        await client.close()
        await client.close()
        self.assertTrue(client.is_closed)

      asyncio.run(check())

  def test_wrap_antigravity_http_client_warns_when_interceptor_wrap_fails(self):
    client = httpx.Client()
    try:
      with patch(
        "antigravity_auth.interceptor._wrap_http_client",
        side_effect=RuntimeError("wrap exploded"),
      ), self.assertLogs("antigravity_auth.cloudcode_client", level="WARNING") as logs:
        wrapped = cloudcode_client._wrap_antigravity_http_client(client)

      self.assertIs(wrapped, client)
      self.assertIn("Could not wrap Antigravity HTTP client", "\n".join(logs.output))
    finally:
      client.close()

  def test_non_stream_request_uses_cloudcode_envelope_and_openai_response_shape(self):
    captured: list[httpx.Request] = []

    def build_gemini_request(**kwargs):
      messages = kwargs.get("messages") or []
      return {
        "contents": [{
          "role": "user",
          "parts": [{"text": messages[0]["content"]}],
        }],
        "generationConfig": {"maxOutputTokens": kwargs.get("max_tokens")},
      }

    def translate_gemini_response(payload, model):
      text = payload["candidates"][0]["content"]["parts"][0]["text"]
      return SimpleNamespace(
        choices=[SimpleNamespace(
          message=SimpleNamespace(content=text, tool_calls=None),
          finish_reason="stop",
        )],
        model=model,
      )

    def transport(request: httpx.Request) -> httpx.Response:
      captured.append(request)
      request.read()
      return httpx.Response(
        200,
        request=request,
        json={
          "response": {
            "candidates": [{
              "content": {"parts": [{"text": "hello from antigravity"}]},
              "finishReason": "STOP",
            }],
            "usageMetadata": {"totalTokenCount": 3},
          },
        },
      )

    native = types.ModuleType("agent.gemini_native_adapter")
    native.build_gemini_request = build_gemini_request
    native.translate_gemini_response = translate_gemini_response
    native.gemini_http_error = lambda response, body_text="": RuntimeError(body_text or response.text)
    native._iter_sse_events = lambda response: iter(())
    native.translate_stream_event = lambda event, model, tool_call_indices: []
    agent = types.ModuleType("agent")

    with patch.dict(sys.modules, {
      "agent": agent,
      "agent.gemini_native_adapter": native,
    }), patch.dict(os.environ, {
      "HERMES_GEMINI_PROJECT_ID": "project-1",
    }), patch(
      "antigravity_auth.cloudcode_client._wrap_antigravity_http_client",
      side_effect=lambda client: client,
    ):
      client = cloudcode_client.AntigravityCloudCodeClient(
        api_key="placeholder",
        base_url="cloudcode-pa://google",
        http_client=httpx.Client(transport=httpx.MockTransport(transport)),
      )
      response = client.chat.completions.create(
        model="gemini-2.5-flash",
        messages=[{"role": "user", "content": "hello"}],
        max_tokens=12,
      )

    self.assertEqual(response.choices[0].message.content, "hello from antigravity")
    self.assertEqual(len(captured), 1)
    request = captured[0]
    self.assertEqual(
      str(request.url),
        "https://daily-cloudcode-pa.googleapis.com/v1internal:generateContent",
    )
    body = json.loads(request.content)
    self.assertEqual(body["project"], "project-1")
    self.assertEqual(body["model"], "gemini-2.5-flash")
    self.assertEqual(body["request"]["contents"][0]["parts"][0]["text"], "hello")

  def test_virtual_cloudcode_endpoint_is_reselected_per_request(self):
    captured_urls: list[str] = []

    def build_gemini_request(**kwargs):
      return {"contents": kwargs.get("messages") or []}

    def translate_gemini_response(payload, model):
      return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="ok", tool_calls=None), finish_reason="stop")],
        model=model,
      )

    def transport(request: httpx.Request) -> httpx.Response:
      captured_urls.append(str(request.url))
      request.read()
      return httpx.Response(
        200,
        request=request,
        json={"response": {"candidates": [{"content": {"parts": [{"text": "ok"}]}}]}},
      )

    native = types.ModuleType("agent.gemini_native_adapter")
    native.build_gemini_request = build_gemini_request
    native.translate_gemini_response = translate_gemini_response
    native.gemini_http_error = lambda response, body_text="": RuntimeError(body_text or response.text)
    native._iter_sse_events = lambda response: iter(())
    native.translate_stream_event = lambda event, model, tool_call_indices: []
    agent = types.ModuleType("agent")

    with patch.dict(sys.modules, {
      "agent": agent,
      "agent.gemini_native_adapter": native,
    }), patch.dict(os.environ, {
      "HERMES_GEMINI_PROJECT_ID": "project-1",
    }), patch(
      "antigravity_auth.cloudcode_client._wrap_antigravity_http_client",
      side_effect=lambda client: client,
    ), patch(
      "antigravity_auth.cloudcode_client.select_endpoint",
      side_effect=[
        "https://init.example.test",
        "https://first.example.test",
        "https://second.example.test",
      ],
    ):
      client = cloudcode_client.AntigravityCloudCodeClient(
        api_key="placeholder",
        base_url="cloudcode-pa://google",
        http_client=httpx.Client(transport=httpx.MockTransport(transport)),
      )
      client.chat.completions.create(model="gemini-2.5-flash", messages=[])
      client.chat.completions.create(model="gemini-2.5-flash", messages=[])
      client.close()

    self.assertEqual(captured_urls, [
      "https://first.example.test/v1internal:generateContent",
      "https://second.example.test/v1internal:generateContent",
    ])

  def test_async_stream_and_close_match_hermes_facade(self):
    def build_gemini_request(**kwargs):
      return {"contents": kwargs.get("messages") or []}

    def translate_stream_event(event, model, tool_call_indices):
      return [SimpleNamespace(delta=event["delta"], model=model)]

    def transport(request: httpx.Request) -> httpx.Response:
      return httpx.Response(200, request=request, content=b"data: ok\n\n")

    native = types.ModuleType("agent.gemini_native_adapter")
    native.build_gemini_request = build_gemini_request
    native.translate_gemini_response = lambda payload, model: SimpleNamespace(model=model)
    native.gemini_http_error = lambda response, body_text="": RuntimeError(body_text or response.text)
    native._iter_sse_events = lambda response: iter([{"delta": "one"}, {"delta": "two"}])
    native.translate_stream_event = translate_stream_event
    agent = types.ModuleType("agent")

    with patch.dict(sys.modules, {
      "agent": agent,
      "agent.gemini_native_adapter": native,
    }), patch.dict(os.environ, {
      "HERMES_GEMINI_PROJECT_ID": "project-1",
    }), patch(
      "antigravity_auth.cloudcode_client._wrap_antigravity_http_client",
      side_effect=lambda client: client,
    ):
      sync_client = cloudcode_client.AntigravityCloudCodeClient(
        api_key="placeholder",
        base_url="cloudcode-pa://google",
        http_client=httpx.Client(transport=httpx.MockTransport(transport)),
      )
      async_client = cloudcode_client.AsyncAntigravityCloudCodeClient(sync_client)

      async def collect_stream():
        stream = await async_client.chat.completions.create(
          model="gemini-2.5-flash",
          messages=[{"role": "user", "content": "hello"}],
          stream=True,
        )
        chunks = []
        async for chunk in stream:
          chunks.append(chunk.delta)
        await async_client.close()
        return chunks

      chunks = asyncio.run(collect_stream())

    self.assertEqual(chunks, ["one", "two"])
    self.assertTrue(sync_client.is_closed)

  def test_async_stream_aclose_closes_sync_iterator(self):
    class ClosableIterator:
      def __init__(self):
        self.closed = False
        self._items = iter(["one", "two"])

      def __iter__(self):
        return self

      def __next__(self):
        return next(self._items)

      def close(self):
        self.closed = True

    result = ClosableIterator()

    class FakeSyncClient:
      def __init__(self):
        self.api_key = "placeholder"
        self.base_url = "cloudcode-pa://google"
        self.is_closed = False
        self.chat = SimpleNamespace(
          completions=SimpleNamespace(create=lambda **kwargs: result),
        )

      def _advance_stream_iterator(self, iterator):
        try:
          return False, next(iterator)
        except StopIteration:
          return True, None

      def close(self):
        self.is_closed = True

    async def read_one_and_close():
      sync_client = FakeSyncClient()
      async_client = cloudcode_client.AsyncAntigravityCloudCodeClient(sync_client)
      stream = await async_client.chat.completions.create(stream=True)
      first = await stream.__anext__()
      await stream.aclose()
      self.assertFalse(async_client.is_closed)
      async with async_client:
        pass
      self.assertTrue(async_client.is_closed)
      return first

    first = asyncio.run(read_one_and_close())

    self.assertEqual(first, "one")
    self.assertTrue(result.closed)

  def test_reasoning_routes_wire_model_and_preserves_antigravity_envelope(self):
    captured: dict[str, Any] = {}
    native_kwargs: dict[str, Any] = {}

    def build_gemini_request(**kwargs):
      native_kwargs.update(kwargs)
      return {
        "contents": [],
        "generationConfig": {
          "maxOutputTokens": kwargs.get("max_tokens"),
          "thinkingConfig": kwargs.get("thinking_config"),
        },
      }

    def transport(request: httpx.Request) -> httpx.Response:
      request.read()
      captured["body"] = json.loads(request.content)
      return httpx.Response(200, request=request, json={"response": {"candidates": []}})

    native = types.ModuleType("agent.gemini_native_adapter")
    native.build_gemini_request = build_gemini_request
    native.translate_gemini_response = lambda payload, model: SimpleNamespace(model=model)
    native.gemini_http_error = lambda response, body_text="": RuntimeError(body_text or response.text)
    agent = types.ModuleType("agent")
    response_format = {"type": "json_object"}

    with patch.dict(sys.modules, {
      "agent": agent,
      "agent.gemini_native_adapter": native,
    }), patch.dict(os.environ, {"HERMES_GEMINI_PROJECT_ID": "project-1"}), patch(
      "antigravity_auth.cloudcode_client._wrap_antigravity_http_client",
      side_effect=lambda client: client,
    ):
      client = cloudcode_client.AntigravityCloudCodeClient(
        base_url="https://cloudcode-pa.googleapis.com",
        http_client=httpx.Client(transport=httpx.MockTransport(transport)),
      )
      result = client.chat.completions.create(
        model="gemini-3.8-flash",
        messages=[],
        max_tokens=200_000,
        response_format=response_format,
        extra_body={"reasoning": {"enabled": True, "effort": "high"}},
      )
      client.close()

    body = captured["body"]
    self.assertEqual(result.model, "gemini-3.8-flash")
    self.assertEqual(body["model"], "gemini-3.8-flash-high")
    self.assertEqual(body["requestType"], "agent")
    self.assertEqual(body["userAgent"], "antigravity")
    self.assertTrue(body["requestId"].startswith("agent-"))
    self.assertIn("systemInstruction", body["request"])
    self.assertEqual(body["request"]["generationConfig"]["thinkingConfig"], {
      "includeThoughts": True,
      "thinkingBudget": -1,
    })
    self.assertEqual(body["request"]["generationConfig"]["maxOutputTokens"], 65_536)
    self.assertEqual(native_kwargs["model"], "gemini-3.8-flash-high")
    self.assertEqual(native_kwargs["response_format"], response_format)

  def test_stream_uses_effort_routing_but_returns_public_model(self):
    captured: dict[str, Any] = {}
    translated_models: list[str] = []

    def build_gemini_request(**kwargs):
      return {
        "contents": [],
        "generationConfig": {"thinkingConfig": kwargs.get("thinking_config")},
      }

    def translate_stream_event(event, model, tool_call_indices):
      translated_models.append(model)
      return [SimpleNamespace(model=model)]

    def transport(request: httpx.Request) -> httpx.Response:
      request.read()
      captured["body"] = json.loads(request.content)
      return httpx.Response(200, request=request, content=b"data: {}\n\n")

    native = types.ModuleType("agent.gemini_native_adapter")
    native.build_gemini_request = build_gemini_request
    native.translate_gemini_response = lambda payload, model: SimpleNamespace(model=model)
    native.gemini_http_error = lambda response, body_text="": RuntimeError(body_text or response.text)
    native._iter_sse_events = lambda response: iter([{"candidates": []}])
    native.translate_stream_event = translate_stream_event
    agent = types.ModuleType("agent")

    with patch.dict(sys.modules, {
      "agent": agent,
      "agent.gemini_native_adapter": native,
    }), patch.dict(os.environ, {"HERMES_GEMINI_PROJECT_ID": "project-1"}), patch(
      "antigravity_auth.cloudcode_client._wrap_antigravity_http_client",
      side_effect=lambda client: client,
    ):
      client = cloudcode_client.AntigravityCloudCodeClient(
        base_url="https://cloudcode-pa.googleapis.com",
        http_client=httpx.Client(transport=httpx.MockTransport(transport)),
      )
      stream = client.chat.completions.create(
        model="gemini-3.5-flash",
        messages=[],
        stream=True,
        extra_body={"reasoning": {"effort": "high"}},
      )
      chunks = list(stream)
      client.close()

    self.assertEqual([chunk.model for chunk in chunks], ["gemini-3.5-flash"])
    self.assertEqual(translated_models, ["gemini-3.5-flash"])
    self.assertEqual(captured["body"]["model"], "gemini-3-flash-agent")
    self.assertEqual(captured["body"]["requestType"], "agent")
    self.assertEqual(captured["body"]["request"]["generationConfig"]["thinkingConfig"]["thinkingBudget"], 10_000)

  def test_legacy_native_signature_still_builds_request(self):
    captured: dict[str, Any] = {}

    def build_gemini_request(*, messages, tools, tool_choice, temperature, max_tokens, top_p, stop, thinking_config):
      return {
        "contents": messages,
        "generationConfig": {
          # Simulate Hermes' generic thinking-headroom adjustment.
          "maxOutputTokens": max(max_tokens or 0, 65_535),
          "thinkingConfig": thinking_config,
        },
      }

    def transport(request: httpx.Request) -> httpx.Response:
      request.read()
      captured["body"] = json.loads(request.content)
      return httpx.Response(200, request=request, json={"response": {"candidates": []}})

    native = types.ModuleType("agent.gemini_native_adapter")
    native.build_gemini_request = build_gemini_request
    native.translate_gemini_response = lambda payload, model: SimpleNamespace(model=model)
    native.gemini_http_error = lambda response, body_text="": RuntimeError(body_text or response.text)
    agent = types.ModuleType("agent")

    with patch.dict(sys.modules, {
      "agent": agent,
      "agent.gemini_native_adapter": native,
    }), patch(
      "antigravity_auth.cloudcode_client._wrap_antigravity_http_client",
      side_effect=lambda client: client,
    ):
      client = cloudcode_client.AntigravityCloudCodeClient(
        base_url="https://cloudcode-pa.googleapis.com",
        http_client=httpx.Client(transport=httpx.MockTransport(transport)),
      )
      client.chat.completions.create(
        model="gpt-oss-120b",
        messages=[],
        response_format={"type": "json_object"},
        extra_body={"reasoning": {"effort": "high"}},
      )
      client.close()

    self.assertEqual(captured["body"]["model"], "gpt-oss-120b-medium")
    self.assertEqual(captured["body"]["request"]["generationConfig"]["maxOutputTokens"], 32_768)


if __name__ == "__main__":
  unittest.main()
