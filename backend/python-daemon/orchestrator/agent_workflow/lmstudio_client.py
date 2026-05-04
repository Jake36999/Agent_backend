from __future__ import annotations

import json
import logging
import os
from typing import Any
from urllib import request


class ModelOutputInvalid(ValueError):
    pass


logger = logging.getLogger(__name__)


class LMStudioClient:
    def __init__(self) -> None:
        self.api_mode = os.getenv("ALETHEIA_AGENT_API_MODE", "native").strip().lower()
        if self.api_mode in {"openai", "openai-compatible", "compat"}:
            self.api_mode = "compatible"
        default_url = "http://127.0.0.1:1234/api/v1/chat" if self.api_mode == "native" else "http://127.0.0.1:1234/v1/chat/completions"
        self.url = os.getenv("ALETHEIA_AGENT_CHAT_URL", default_url)
        self.model = os.getenv("ALETHEIA_AGENT_MODEL") or "qwen3-8b"
        self.token = os.getenv("ALETHEIA_LM_STUDIO_API_TOKEN", "")

    def chat_json(
        self,
        *,
        messages: list[dict[str, str]],
        schema: dict[str, Any],
        reasoning: str,
        max_tokens: int = 300,
        phase: str | None = None,
    ) -> tuple[dict[str, Any], bool]:
        used_fallback = False
        try:
            text = self._post(messages, schema, reasoning, max_tokens, include_reasoning=True)
        except Exception:
            if self.api_mode == "native" and reasoning:
                used_fallback = True
                text = self._post(messages, schema, reasoning, max_tokens, include_reasoning=False)
            else:
                raise
        try:
            return self._parse_json_object(text), used_fallback
        except ModelOutputInvalid:
            repair_messages = list(messages) + [{"role": "system", "content": "Return ONLY valid JSON matching schema. No prose."}]
            repair_text = self._post(repair_messages, schema, reasoning, max_tokens, include_reasoning=not used_fallback)
            return self._parse_json_object(repair_text), used_fallback

    def _post(
        self,
        messages: list[dict[str, str]],
        schema: dict[str, Any],
        reasoning: str,
        max_tokens: int,
        *,
        include_reasoning: bool,
    ) -> str:
        payload = self._payload(messages, schema, reasoning, max_tokens, include_reasoning=include_reasoning)
        logger.debug(
            "LM request model=%s, auth=%s",
            payload["model"],
            "present" if self.token else "missing",
        )
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        req = request.Request(
            self.url,
            data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with request.urlopen(req, timeout=60) as response:
            body = json.loads(response.read().decode("utf-8"))
        if self.api_mode == "native":
            message = body.get("message", {})
            return str(message.get("content", body.get("content", "")))
        return str(body.get("choices", [{}])[0].get("message", {}).get("content", ""))

    def _payload(
        self,
        messages: list[dict[str, str]],
        schema: dict[str, Any],
        reasoning: str,
        max_tokens: int,
        *,
        include_reasoning: bool,
    ) -> dict[str, Any]:
        if not self.model:
            raise ModelOutputInvalid("Model must be specified")
        if self.api_mode == "compatible":
            return {
                "model": self.model,
                "messages": messages,
                "max_tokens": max_tokens,
                "response_format": {"type": "json_schema", "json_schema": schema},
                "stream": False,
            }
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "max_output_tokens": max_tokens,
            "stream": False,
        }
        if include_reasoning and reasoning:
            payload["reasoning"] = {"effort": reasoning}
        return payload

    def _parse_json_object(self, text: str) -> dict[str, Any]:
        stripped = text.strip()
        if "<tool_call>" in stripped or "[TOOL_REQUEST]" in stripped:
            raise ModelOutputInvalid("model output contained tool-call markup")
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise ModelOutputInvalid(str(exc)) from exc
        if not isinstance(parsed, dict):
            raise ModelOutputInvalid("model output was not a JSON object")
        return parsed
