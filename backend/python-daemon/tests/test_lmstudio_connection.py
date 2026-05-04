import json
import os
import unittest
from unittest import mock

import requests

from orchestrator.lmstudio_connection import (
    LMStudioConnectionConfig,
    LMStudioConnectionError,
    LMStudioConnectionManager,
)


class FakeResponse:
    def __init__(self, payload=None, *, raw=None, status=200):
        self.payload = payload if payload is not None else {}
        self.raw = raw
        self.status_code = status
        self.reason = "error" if status >= 400 else "OK"

    @property
    def content(self):
        data = self.raw if self.raw is not None else json.dumps(self.payload).encode("utf-8")
        return data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(response=self)


def config(**kwargs):
    values = {
        "native_base_url": "http://lm/api/v1",
        "compat_base_url": "http://lm/v1",
        "api_token": None,
        "request_timeout_seconds": 180.0,
        "max_response_bytes": 1000000,
        "chat_model": "chat-model",
        "embedding_model": "embed-model",
        "context_length": None,
        "max_output_tokens": None,
        "temperature": 0,
        "reasoning": None,
    }
    values.update(kwargs)
    return LMStudioConnectionConfig(**values)


class LMStudioConnectionTests(unittest.TestCase):
    def test_headers_include_authorization_only_when_token_configured(self):
        self.assertNotIn("Authorization", LMStudioConnectionManager(config()).headers())
        headers = LMStudioConnectionManager(config(api_token="secret")).headers()
        self.assertEqual(headers["Authorization"], "Bearer secret")
        self.assertEqual(LMStudioConnectionManager(config(api_token="secret"))._headers()["Authorization"], "Bearer secret")

    def test_lm_client_requires_model(self):
        with self.assertRaises(LMStudioConnectionError):
            LMStudioConnectionManager(config()).chat_native(model="", input="test")

    def test_list_models_find_model_and_loaded_instances(self):
        payload = {
            "models": [
                {
                    "key": "chat-model",
                    "type": "llm",
                    "loaded_instances": [{"id": "chat-model:1"}],
                }
            ]
        }
        with mock.patch("requests.get", lambda url, headers=None, timeout=None: FakeResponse(payload)):
            manager = LMStudioConnectionManager(config())
            self.assertEqual(manager.list_models(), payload)
            self.assertEqual(manager.find_model("chat-model")["key"], "chat-model")
            self.assertEqual(manager.find_model("chat-model:1")["key"], "chat-model")
            self.assertEqual(manager.get_loaded_instances("chat-model:1")[0]["id"], "chat-model:1")
            self.assertTrue(manager.is_model_loaded("chat-model"))
            self.assertTrue(manager.is_model_loaded("chat-model:1"))

    def test_ensure_model_loaded_does_not_reload_loaded_model_and_loads_unloaded_model(self):
        calls = []
        loaded_payload = {"models": [{"key": "chat-model", "type": "llm", "loaded_instances": [{"id": "chat-model:1"}]}]}

        def get_loaded(url, headers=None, timeout=None):
            calls.append((url, None))
            return FakeResponse(loaded_payload)

        with mock.patch("requests.get", get_loaded):
            result = LMStudioConnectionManager(config()).ensure_model_loaded("chat-model")
        self.assertEqual(result["status"], "already_loaded")
        self.assertEqual(len(calls), 1)

        unloaded_payload = {"models": [{"key": "embed-model", "type": "embedding", "loaded_instances": []}]}

        def get_unloaded(url, headers=None, timeout=None):
            calls.append((url, None))
            if url.endswith("/models"):
                return FakeResponse(unloaded_payload)
            return FakeResponse({"ok": True})

        def post_unloaded(url, headers=None, json=None, timeout=None):
            calls.append((url, __import__("json").dumps(json).encode("utf-8")))
            return FakeResponse({"ok": True})

        calls.clear()
        with mock.patch("requests.get", get_unloaded), mock.patch("requests.post", post_unloaded):
            result = LMStudioConnectionManager(config()).ensure_model_loaded(
                "embed-model",
                expected_type="embedding",
                context_length=4096,
            )
        self.assertEqual(result["status"], "loaded")
        self.assertEqual(calls[1][0], "http://lm/api/v1/models/load")
        self.assertEqual(json.loads(calls[1][1].decode("utf-8")), {"model": "embed-model", "context_length": 4096, "echo_load_config": True})

    def test_ensure_model_loaded_rejects_type_mismatch(self):
        payload = {"models": [{"key": "chat-model", "type": "llm", "loaded_instances": []}]}
        with mock.patch("requests.get", lambda url, headers=None, timeout=None: FakeResponse(payload)):
            with self.assertRaises(LMStudioConnectionError) as cm:
                LMStudioConnectionManager(config()).ensure_model_loaded("chat-model", expected_type="embedding")
        self.assertEqual(cm.exception.code, "model_type_mismatch")

    def test_load_model_sends_only_supported_non_none_fields(self):
        seen = {}

        def post(url, headers=None, json=None, timeout=None):
            seen.update(json)
            return FakeResponse({"ok": True})

        with mock.patch("requests.post", post):
            LMStudioConnectionManager(config()).load_model(
                "chat-model",
                context_length=4096,
                flash_attention=True,
                eval_batch_size=None,
            )
        self.assertEqual(seen, {"model": "chat-model", "context_length": 4096, "flash_attention": True, "echo_load_config": True})

    def test_chat_native_sends_only_native_fields_and_retries_without_reasoning(self):
        attempts = []

        def post(url, headers=None, json=None, timeout=None):
            body = dict(json)
            attempts.append(body)
            if len(attempts) == 1:
                response = FakeResponse(status=400)
                response.reason = "bad reasoning"
                raise requests.HTTPError(response=response)
            return FakeResponse({"output": [{"type": "message", "content": "ok"}], "response_id": "resp_1"})

        with mock.patch("requests.post", post):
            result = LMStudioConnectionManager(config()).chat_native(
                model="chat-model",
                input="hi",
                integrations=[{"type": "plugin", "id": "mcp/x", "allowed_tools": ["t"]}],
                context_length=8000,
                reasoning="low",
                store=True,
                previous_response_id="resp_0",
                ttl=300,
            )
        self.assertEqual(result["messages"], ["ok"])
        self.assertIn("reasoning", attempts[0])
        self.assertNotIn("reasoning", attempts[1])
        self.assertIn("integrations", attempts[0])
        self.assertIn("context_length", attempts[0])
        self.assertNotIn("response_format", attempts[0])

    def test_integration_helpers(self):
        manager = LMStudioConnectionManager(config())
        self.assertEqual(
            manager.plugin_integration("mcp/aletheia-fastmcp-shim", allowed_tools=["mcp_agent_workflow_run"]),
            {"type": "plugin", "id": "mcp/aletheia-fastmcp-shim", "allowed_tools": ["mcp_agent_workflow_run"]},
        )
        self.assertEqual(
            manager.ephemeral_mcp_integration(server_label="a", server_url="http://s", headers={"X": "Y"}),
            {"type": "ephemeral_mcp", "server_label": "a", "server_url": "http://s", "headers": {"X": "Y"}},
        )

    def test_compatible_json_schema_uses_response_format_and_parses_content(self):
        seen = {}

        def post(url, headers=None, json=None, timeout=None):
            seen.update(json)
            return FakeResponse({"choices": [{"message": {"content": "{\"ok\": true}"}}]})

        with mock.patch("requests.post", post):
            result = LMStudioConnectionManager(config()).chat_compatible_json_schema(
                model="chat-model",
                messages=[{"role": "user", "content": "x"}],
                json_schema={"type": "object"},
                schema_name="s",
            )
        self.assertEqual(result, {"ok": True})
        self.assertIn("response_format", seen)
        self.assertNotIn("integrations", seen)
        self.assertNotIn("context_length", seen)
        self.assertNotIn("reasoning", seen)

    def test_compatible_json_rejects_non_json_and_tool_call_markup(self):
        manager = LMStudioConnectionManager(config())
        with self.assertRaises(LMStudioConnectionError):
            manager.parse_compatible_json_content({"choices": [{"message": {"content": "not json"}}]})
        with self.assertRaises(LMStudioConnectionError):
            manager.parse_compatible_json_content({"choices": [{"message": {"content": "<tool_call>{}"}}]})

    def test_ttl_health_and_error_paths_are_compact(self):
        manager = LMStudioConnectionManager(config(api_token="secret", max_response_bytes=10))
        self.assertEqual(manager.with_ttl({"model": "m"}, 300), {"model": "m", "ttl": 300})
        self.assertEqual(manager.with_ttl({"model": "m"}, None), {"model": "m"})
        summary = manager.connection_summary()
        self.assertTrue(summary["token_configured"])
        self.assertNotIn("secret", json.dumps(summary))

        with mock.patch("requests.get", lambda url, headers=None, timeout=None: FakeResponse(raw=b"X" * 100)):
            with self.assertRaises(LMStudioConnectionError) as cm:
                manager.request_json("GET", "http://lm/api/v1/models")
        self.assertEqual(cm.exception.code, "response_too_large")

        with mock.patch("requests.get", lambda url, headers=None, timeout=None: FakeResponse(raw=b"{not json}")):
            with self.assertRaises(LMStudioConnectionError) as cm:
                LMStudioConnectionManager(config()).request_json("GET", "http://lm/api/v1/models")
        self.assertEqual(cm.exception.code, "malformed_json")

        with mock.patch("requests.get", side_effect=requests.Timeout("slow")):
            with self.assertRaises(LMStudioConnectionError) as cm:
                LMStudioConnectionManager(config()).request_json("GET", "http://lm/api/v1/models")
        self.assertEqual(cm.exception.code, "request_failed")


if __name__ == "__main__":
    unittest.main()
