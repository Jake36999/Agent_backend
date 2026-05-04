from __future__ import annotations

from dataclasses import dataclass
import json
import logging
import os
from typing import Any, Literal

import requests


ReasoningLevel = Literal["off", "low", "medium", "high", "on"]
ApiMode = Literal["native", "openai_compat"]

logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class LMStudioConnectionConfig:
    native_base_url: str
    compat_base_url: str
    api_token: str | None
    request_timeout_seconds: float
    max_response_bytes: int
    chat_model: str | None
    embedding_model: str | None
    context_length: int | None
    max_output_tokens: int | None
    temperature: float
    reasoning: ReasoningLevel | None


class LMStudioConnectionError(RuntimeError):
    def __init__(self, code: str, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        payload = {"code": self.code, "message": self.message}
        if self.details:
            payload["details"] = self.details
        return payload


class LMStudioConnectionManager:
    def __init__(self, config: LMStudioConnectionConfig) -> None:
        self.config = config

    @classmethod
    def from_env(cls) -> "LMStudioConnectionManager":
        def optional_int(name: str) -> int | None:
            value = os.getenv(name)
            return int(value) if value else None

        reasoning = os.getenv("ALETHEIA_AGENT_REASONING")
        if reasoning and reasoning not in {"off", "low", "medium", "high", "on"}:
            raise LMStudioConnectionError("invalid_config", f"unsupported reasoning level: {reasoning}")
        return cls(
            LMStudioConnectionConfig(
                native_base_url=os.getenv("ALETHEIA_LM_STUDIO_API_BASE_URL", "http://127.0.0.1:1234/api/v1"),
                compat_base_url=os.getenv("ALETHEIA_LM_STUDIO_BASE_URL", "http://127.0.0.1:1234/v1"),
                api_token=os.getenv("ALETHEIA_LM_STUDIO_API_TOKEN") or None,
                request_timeout_seconds=float(os.getenv("ALETHEIA_LM_STUDIO_REQUEST_TIMEOUT_SECONDS", "180")),
                max_response_bytes=int(os.getenv("ALETHEIA_LM_STUDIO_MAX_RESPONSE_BYTES", "25000000")),
                chat_model=os.getenv("ALETHEIA_AGENT_MODEL") or "qwen3-8b",
                embedding_model=os.getenv("ALETHEIA_EMBEDDING_MODEL") or None,
                context_length=optional_int("ALETHEIA_AGENT_CONTEXT_LENGTH"),
                max_output_tokens=optional_int("ALETHEIA_AGENT_MAX_OUTPUT_TOKENS"),
                temperature=float(os.getenv("ALETHEIA_AGENT_TEMPERATURE", "0")),
                reasoning=reasoning,  # type: ignore[arg-type]
            )
        )

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.config.api_token:
            headers["Authorization"] = f"Bearer {self.config.api_token}"
        return headers

    def headers(self) -> dict[str, str]:
        return self._headers()

    def request_json(
        self,
        method: str,
        url: str,
        *,
        payload: dict[str, Any] | None = None,
        timeout_seconds: float | None = None,
    ) -> dict[str, Any]:
        method = method.upper()
        try:
            if method == "GET":
                response = requests.get(url, headers=self._headers(), timeout=timeout_seconds or self.config.request_timeout_seconds)
            elif method == "POST":
                response = requests.post(
                    url,
                    headers=self._headers(),
                    json=payload,
                    timeout=timeout_seconds or self.config.request_timeout_seconds,
                )
            else:
                response = requests.request(
                    method,
                    url,
                    headers=self._headers(),
                    json=payload,
                    timeout=timeout_seconds or self.config.request_timeout_seconds,
                )
            response.raise_for_status()
            raw = response.content
        except requests.HTTPError as exc:
            status_code = exc.response.status_code if exc.response is not None else 0
            reason = exc.response.reason if exc.response is not None else str(exc)
            raise LMStudioConnectionError(
                "http_error",
                f"LM Studio HTTP {status_code}: {reason}",
                details={"url": url, "status": status_code},
            ) from exc
        except (requests.Timeout, requests.RequestException, OSError, TimeoutError) as exc:
            raise LMStudioConnectionError("request_failed", f"LM Studio request failed: {exc}", details={"url": url}) from exc
        if len(raw) > self.config.max_response_bytes:
            raise LMStudioConnectionError(
                "response_too_large",
                f"LM Studio response exceeded {self.config.max_response_bytes} bytes",
                details={"url": url},
            )
        try:
            parsed = json.loads(raw.decode("utf-8"))
        except Exception as exc:
            raise LMStudioConnectionError("malformed_json", "LM Studio returned malformed JSON", details={"url": url}) from exc
        if not isinstance(parsed, dict):
            raise LMStudioConnectionError("invalid_response", "LM Studio response was not a JSON object", details={"url": url})
        return parsed

    def native_url(self, path: str) -> str:
        return f"{self.config.native_base_url.rstrip('/')}/{path.lstrip('/')}"

    def compat_url(self, path: str) -> str:
        return f"{self.config.compat_base_url.rstrip('/')}/{path.lstrip('/')}"

    def list_models(self) -> dict[str, Any]:
        return self.request_json("GET", self.native_url("/models"))

    def _require_model(self, model: str | None) -> str:
        if not model:
            raise LMStudioConnectionError("model_required", "Model must be specified")
        return model

    def _models(self) -> list[dict[str, Any]]:
        data = self.list_models()
        models = data.get("models") or data.get("data") or []
        return [model for model in models if isinstance(model, dict)]

    def find_model(self, model_key: str) -> dict[str, Any] | None:
        for model in self._models():
            if model.get("key") == model_key or model.get("id") == model_key:
                return model
            for instance in self._loaded_instances_from_model(model):
                if instance.get("id") == model_key:
                    return model
        return None

    def get_loaded_instances(self, model_key: str) -> list[dict[str, Any]]:
        model = self.find_model(model_key)
        return self._loaded_instances_from_model(model or {})

    def is_model_loaded(self, model_key: str) -> bool:
        model = self.find_model(model_key)
        if not model:
            return False
        for instance in self._loaded_instances_from_model(model):
            if instance.get("id") == model_key:
                return True
        return bool(self._loaded_instances_from_model(model))

    def ensure_model_loaded(
        self,
        model_key: str,
        *,
        expected_type: Literal["llm", "embedding"] | None = None,
        context_length: int | None = None,
        eval_batch_size: int | None = None,
        flash_attention: bool | None = None,
        offload_kv_cache_to_gpu: bool | None = None,
        num_experts: int | None = None,
        echo_load_config: bool = True,
    ) -> dict[str, Any]:
        model_key = self._require_model(model_key)
        model = self.find_model(model_key)
        if model is None:
            raise LMStudioConnectionError("model_not_found", f"LM Studio model not found: {model_key}")
        if expected_type and not self._type_matches(str(model.get("type", "")), expected_type):
            raise LMStudioConnectionError(
                "model_type_mismatch",
                f"LM Studio model {model_key} is type {model.get('type')}, expected {expected_type}",
            )
        if self._model_is_loaded(model, model_key):
            return {
                "ok": True,
                "status": "already_loaded",
                "model": str(model.get("key") or model_key),
                "loaded_instances": self._loaded_instances_from_model(model),
            }
        loaded = self.load_model(
            model_key,
            context_length=context_length,
            eval_batch_size=eval_batch_size,
            flash_attention=flash_attention,
            offload_kv_cache_to_gpu=offload_kv_cache_to_gpu,
            num_experts=num_experts,
            echo_load_config=echo_load_config,
        )
        return {"ok": True, "status": "loaded", "model": model_key, "result": loaded}

    def load_model(
        self,
        model_key: str,
        *,
        context_length: int | None = None,
        eval_batch_size: int | None = None,
        flash_attention: bool | None = None,
        offload_kv_cache_to_gpu: bool | None = None,
        num_experts: int | None = None,
        echo_load_config: bool = True,
    ) -> dict[str, Any]:
        model_key = self._require_model(model_key)
        payload: dict[str, Any] = {"model": model_key, "echo_load_config": echo_load_config}
        for key, value in {
            "context_length": context_length,
            "eval_batch_size": eval_batch_size,
            "flash_attention": flash_attention,
            "offload_kv_cache_to_gpu": offload_kv_cache_to_gpu,
            "num_experts": num_experts,
        }.items():
            if value is not None:
                payload[key] = value
        return self.request_json("POST", self.native_url("/models/load"), payload=payload)

    def unload_model(self, model_key_or_instance_id: str) -> dict[str, Any]:
        try:
            return self.request_json("POST", self.native_url("/models/unload"), payload={"model": model_key_or_instance_id})
        except LMStudioConnectionError as exc:
            if exc.code == "http_error" and exc.details.get("status") == 404:
                return {
                    "ok": False,
                    "status": "UNSUPPORTED",
                    "error": {"code": "unsupported_endpoint", "message": "/api/v1/models/unload is not available"},
                }
            raise

    def chat_native(
        self,
        *,
        model: str,
        input: str | list[dict[str, Any]],
        system_prompt: str | None = None,
        integrations: list[str | dict[str, Any]] | None = None,
        context_length: int | None = None,
        max_output_tokens: int | None = None,
        temperature: float | None = None,
        reasoning: ReasoningLevel | None = None,
        store: bool | None = None,
        previous_response_id: str | None = None,
        stream: bool = False,
        ttl: int | None = None,
    ) -> dict[str, Any]:
        model = self._require_model(model)
        logger.debug(
            "LM request model=%s, auth=%s",
            model,
            "present" if self.config.api_token else "missing",
        )
        payload: dict[str, Any] = {"model": model, "input": input, "stream": stream}
        for key, value in {
            "system_prompt": system_prompt,
            "integrations": integrations,
            "context_length": context_length or self.config.context_length,
            "max_output_tokens": max_output_tokens or self.config.max_output_tokens,
            "temperature": self.config.temperature if temperature is None else temperature,
            "reasoning": reasoning or self.config.reasoning,
            "store": store,
            "previous_response_id": previous_response_id,
        }.items():
            if value is not None:
                payload[key] = value
        payload = self.with_ttl(payload, ttl)
        try:
            return self.parse_native_chat_output(
                self.request_json("POST", self.native_url("/chat"), payload=payload)
            )
        except LMStudioConnectionError:
            if payload.get("reasoning") is not None:
                payload.pop("reasoning", None)
                parsed = self.parse_native_chat_output(
                    self.request_json("POST", self.native_url("/chat"), payload=payload)
                )
                parsed["reasoning_fallback"] = True
                return parsed
            raise

    def parse_native_chat_output(self, response: dict[str, Any]) -> dict[str, Any]:
        output = response.get("output") if isinstance(response.get("output"), list) else []
        messages: list[str] = []
        tool_calls: list[dict[str, Any]] = []
        invalid_tool_calls: list[dict[str, Any]] = []
        reasoning_count = 0
        for item in output:
            if not isinstance(item, dict):
                continue
            item_type = item.get("type")
            if item_type == "message":
                messages.append(str(item.get("content", "")))
            elif item_type == "tool_call":
                tool_calls.append(item)
            elif item_type == "invalid_tool_call":
                invalid_tool_calls.append(item)
            elif item_type == "reasoning":
                reasoning_count += 1
        return {
            "ok": True,
            "messages": messages,
            "tool_calls": tool_calls,
            "invalid_tool_calls": invalid_tool_calls,
            "reasoning_item_count": reasoning_count,
            "stats": response.get("stats", {}),
            "response_id": response.get("response_id", ""),
        }

    def plugin_integration(self, plugin_id: str, *, allowed_tools: list[str] | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {"type": "plugin", "id": plugin_id}
        if allowed_tools is not None:
            payload["allowed_tools"] = allowed_tools
        return payload

    def ephemeral_mcp_integration(
        self,
        *,
        server_label: str,
        server_url: str,
        allowed_tools: list[str] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"type": "ephemeral_mcp", "server_label": server_label, "server_url": server_url}
        if allowed_tools is not None:
            payload["allowed_tools"] = allowed_tools
        if headers is not None:
            payload["headers"] = headers
        return payload

    def aletheia_plugin_integration(self, *, allowed_tools: list[str] | None = None) -> dict[str, Any]:
        plugin_id = os.getenv("ALETHEIA_LM_STUDIO_PLUGIN_ID", "mcp/aletheia-fastmcp-shim")
        return self.plugin_integration(plugin_id, allowed_tools=allowed_tools)

    def chat_compatible_json_schema(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        json_schema: dict[str, Any],
        schema_name: str,
        temperature: float = 0,
        max_tokens: int | None = None,
        stream: bool = False,
    ) -> dict[str, Any]:
        model = self._require_model(model)
        logger.debug(
            "LM request model=%s, auth=%s",
            model,
            "present" if self.config.api_token else "missing",
        )
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": stream,
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": schema_name, "schema": json_schema},
            },
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        response = self.request_json("POST", self.compat_url("/chat/completions"), payload=payload)
        return self.parse_compatible_json_content(response)

    def parse_compatible_json_content(self, response: dict[str, Any]) -> dict[str, Any]:
        content = str(response.get("choices", [{}])[0].get("message", {}).get("content", ""))
        if "<tool_call>" in content or "[TOOL_REQUEST]" in content:
            raise LMStudioConnectionError("MODEL_OUTPUT_INVALID", "structured output contained tool-call markup")
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            raise LMStudioConnectionError("MODEL_OUTPUT_INVALID", "structured output was not valid JSON") from exc
        if not isinstance(parsed, dict):
            raise LMStudioConnectionError("MODEL_OUTPUT_INVALID", "structured output was not a JSON object")
        return parsed

    def embed_text(self, *, model: str, text: str, ensure_loaded: bool = True) -> list[float]:
        model = self._require_model(model)
        if ensure_loaded:
            self.ensure_model_loaded(model, expected_type="embedding")
        response = self.request_json(
            "POST",
            self.compat_url("/embeddings"),
            payload={"model": model, "input": text},
        )
        embedding = response.get("data", [{}])[0].get("embedding", [])
        return [float(value) for value in embedding]

    def with_ttl(self, payload: dict[str, Any], ttl_seconds: int | None) -> dict[str, Any]:
        copied = dict(payload)
        if ttl_seconds is not None:
            copied["ttl"] = ttl_seconds
        return copied

    def recommend_ttl(self, *, phase: str) -> int | None:
        normalized = phase.upper()
        if normalized in {"PLAN", "SYNTHESIZE", "FINAL"}:
            return 1800
        if normalized == "SMOKE":
            return 300
        return None

    def health(self) -> dict[str, Any]:
        summary = self.connection_summary()
        try:
            models = self._models()
            summary["ok"] = True
            summary["model_count"] = len(models)
            summary["chat_model_exists"] = self.config.chat_model is None or self.find_model(self.config.chat_model) is not None
            summary["embedding_model_exists"] = self.config.embedding_model is None or self.find_model(self.config.embedding_model) is not None
            summary["loaded_instance_ids"] = [
                str(instance.get("id"))
                for model in models
                for instance in self._loaded_instances_from_model(model)
                if instance.get("id")
            ]
            if self.config.chat_model:
                model = self.find_model(self.config.chat_model)
                summary["chat_model_max_context_length"] = model.get("max_context_length") if model else None
            return summary
        except LMStudioConnectionError as exc:
            summary["ok"] = False
            summary["error"] = exc.to_dict()
            return summary

    def connection_summary(self) -> dict[str, Any]:
        return {
            "native_base_url": self.config.native_base_url,
            "compat_base_url": self.config.compat_base_url,
            "token_configured": bool(self.config.api_token),
            "chat_model": self.config.chat_model,
            "embedding_model": self.config.embedding_model,
            "timeout": self.config.request_timeout_seconds,
        }

    def _loaded_instances_from_model(self, model: dict[str, Any]) -> list[dict[str, Any]]:
        instances = model.get("loaded_instances") if isinstance(model, dict) else []
        return [instance for instance in instances if isinstance(instance, dict)] if isinstance(instances, list) else []

    def _model_is_loaded(self, model: dict[str, Any], model_key: str) -> bool:
        for instance in self._loaded_instances_from_model(model):
            if instance.get("id") == model_key:
                return True
        return bool(self._loaded_instances_from_model(model))

    def _type_matches(self, actual: str, expected: Literal["llm", "embedding"]) -> bool:
        normalized = actual.lower()
        if expected == "llm":
            return normalized in {"llm", "chat"}
        return normalized in {"embedding", "embeddings"}
