from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable
import requests


class LMStudioManagerError(ValueError):
    pass


@dataclass(frozen=True)
class LMStudioModel:
    key: str
    type: str
    state: str | None = None
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
                models.append(
                    LMStudioModel(
                        key=key,
                        type=item.get("type", "unknown"),
                        state=item.get("state"),
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

    def ensure_embedding_model_loaded(self, model_key: str) -> None:
        model = self.find_model(model_key)
        if model is None:
            raise LMStudioManagerError(f"embedding model not found in LM Studio: {model_key}")
        if model.type not in {"embedding", "embeddings"}:
            raise LMStudioManagerError(f"configured embedding model is not an embedding model: {model_key} (type: {model.type})")
        if model.state in {"loaded", "running", "ready"}:
            return
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