from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from dataclasses import field
from typing import Any, Callable
import requests


class LMStudioManagerError(ValueError):
    pass


@dataclass(frozen=True)
class LMStudioModel:
    key: str
    type: str
    state: str | None = None
    loaded_instances: list[dict[str, Any]] = field(default_factory=list)
    raw: dict[str, Any] | None = None


@dataclass(frozen=True)
class LMStudioManagerConfig:
    api_base_url: str = "http://127.0.0.1:1234/api/v1"
    api_token: str | None = None
    request_timeout_seconds: float = 30.0


class LMStudioManager:
    def __init__(
        self,
        config: LMStudioManagerConfig,
        *,
        http_get: Callable[..., Any] = requests.get,
        http_post: Callable[..., Any] = requests.post,
    ) -> None:
        self.config = config
        self.http_get = http_get
        self.http_post = http_post
        self._embedding_load_lock = threading.Lock()

    @property
    def _logger(self) -> logging.Logger:
        return logging.getLogger(__name__)

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.config.api_token:
            headers["Authorization"] = f"Bearer {self.config.api_token}"
        return headers

    def list_models(self) -> list[LMStudioModel]:
        try:
            response = self.http_get(
                url=f"{self.config.api_base_url.rstrip('/')}/models",
                headers=self._headers(),
                timeout=self.config.request_timeout_seconds,
            )
            response.raise_for_status()
            data = response.json()
            models_data = data.get("models") or data.get("data") or []
            models = []
            for item in models_data:
                key = item.get("key") or item.get("id")
                if not key:
                    continue
                loaded_instances = item.get("loaded_instances") or []
                models.append(
                    LMStudioModel(
                        key=key,
                        type=item.get("type", "unknown"),
                        state=item.get("state"),
                        loaded_instances=[dict(instance) for instance in loaded_instances if isinstance(instance, dict)],
                        raw=item,
                    )
                )
            return models
        except requests.HTTPError as exc:
            if exc.response.status_code == 401:
                raise LMStudioManagerError(
                    "LM Studio API rejected request; set ALETHEIA_LM_STUDIO_API_TOKEN or disable LM Studio API auth."
                ) from exc
            raise LMStudioManagerError(f"LM Studio API request failed: {exc}") from exc
        except Exception as exc:
            raise LMStudioManagerError(f"LM Studio API request failed: {exc}") from exc

    def find_model(self, model_key: str) -> LMStudioModel | None:
        models = self.list_models()
        for model in models:
            if model.key == model_key:
                return model
        return None

    def connection_summary(self) -> dict[str, Any]:
        return {
            "api_base_url": self.config.api_base_url,
            "token_present": bool(self.config.api_token),
            "request_timeout_seconds": self.config.request_timeout_seconds,
        }

    def get_loaded_instances(self, model_key: str) -> list[dict[str, Any]]:
        model = self.find_model(model_key)
        if model is None:
            raise LMStudioManagerError(f"embedding model not found in LM Studio: {model_key}")
        return list(model.loaded_instances or [])

    def is_model_loaded(self, model_key: str) -> bool:
        model = self.find_model(model_key)
        if model is None:
            return False
        return bool(model.loaded_instances) or model.state in {"loaded", "running", "ready"}

    def ensure_embedding_model_loaded(self, model_key: str) -> None:
        with self._embedding_load_lock:
            model = self.find_model(model_key)
            if model is None:
                raise LMStudioManagerError(f"embedding model not found in LM Studio: {model_key}")
            if model.type not in {"embedding", "embeddings"}:
                raise LMStudioManagerError(f"configured embedding model is not an embedding model: {model_key} (type: {model.type})")

            loaded_instances = list(model.loaded_instances or [])
            loaded_count = len(loaded_instances)
            self._logger.debug(
                "LM Studio embedding readiness check model=%s loaded_instances=%d token_present=%s",
                model_key,
                loaded_count,
                bool(self.config.api_token),
            )
            if loaded_count > 1:
                self._logger.warning(
                    "LM Studio embedding model %s has multiple loaded instances (%d); skipping reload",
                    model_key,
                    loaded_count,
                )
            if loaded_count > 0 or model.state in {"loaded", "running", "ready"}:
                self._logger.debug(
                    "LM Studio embedding readiness skipped model=%s loaded_instances=%d",
                    model_key,
                    loaded_count,
                )
                return

            self._logger.debug(
                "LM Studio embedding readiness loading model=%s loaded_instances=%d",
                model_key,
                loaded_count,
            )
            payload = {"model": model_key}
            try:
                response = self.http_post(
                    url=f"{self.config.api_base_url.rstrip('/')}/models/load",
                    json=payload,
                    headers=self._headers(),
                    timeout=self.config.request_timeout_seconds,
                )
                if response.status_code == 400:
                    # Retry with model_key
                    payload = {"model_key": model_key}
                    response = self.http_post(
                        url=f"{self.config.api_base_url.rstrip('/')}/models/load",
                        json=payload,
                        headers=self._headers(),
                        timeout=self.config.request_timeout_seconds,
                    )
                response.raise_for_status()
            except requests.HTTPError as exc:
                if exc.response.status_code == 401:
                    raise LMStudioManagerError(
                        "LM Studio API rejected request; set ALETHEIA_LM_STUDIO_API_TOKEN or disable LM Studio API auth."
                    ) from exc
                raise LMStudioManagerError(f"failed to load embedding model {model_key}: {exc}") from exc
            except Exception as exc:
                raise LMStudioManagerError(f"failed to load embedding model {model_key}: {exc}") from exc
