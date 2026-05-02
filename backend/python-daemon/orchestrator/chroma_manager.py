from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable

import chromadb
import requests

from .lm_studio_manager import LMStudioManager, LMStudioManagerConfig, LMStudioManagerError


class ChromaAdapterError(ValueError):
    pass


@dataclass(frozen=True)
class ChromaConfig:
    chroma_path: Path
    collection_name: str = "aletheia_chunks"
    lm_studio_base_url: str = "http://localhost:1234/v1"
    lm_studio_api_base_url: str = "http://127.0.0.1:1234/api/v1"
    lm_studio_api_token: str | None = None
    embedding_model: str = "text-embedding-nomic-embed-text-v1.5"
    nomic_prefix: str = "search_document: "
    request_timeout_seconds: float = 30.0
    auto_load_embedding_model: bool = True


class ChromaManager:
    def __init__(
        self,
        config: ChromaConfig,
        *,
        http_post: Callable[..., Any] = requests.post,
        chroma_client: Any | None = None,
        lm_studio_manager: LMStudioManager | None = None,
    ) -> None:
        self.config = config
        self.http_post = http_post
        self.client = chroma_client or chromadb.PersistentClient(path=str(config.chroma_path))
        self.collection = self.client.get_or_create_collection(name=config.collection_name)
        self._active_scope_hash: str | None = None
        if config.auto_load_embedding_model:
            self.lm_studio_manager = lm_studio_manager or LMStudioManager(
                LMStudioManagerConfig(
                    api_base_url=config.lm_studio_api_base_url,
                    api_token=config.lm_studio_api_token,
                    request_timeout_seconds=config.request_timeout_seconds,
                )
            )
        else:
            self.lm_studio_manager = None

    def project_scope_hash(self, project_id: str, params: dict[str, Any] | None = None) -> str:
        if not project_id:
            raise ChromaAdapterError("project_id is required")
        material = {"project_id": project_id, "params": params or {}}
        encoded = json.dumps(material, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha1(encoded).hexdigest()

    def switch_project(self, project_id: str, params: dict[str, Any] | None = None) -> str:
        scope_hash = self.project_scope_hash(project_id, params)
        if scope_hash != self._active_scope_hash:
            self.embed_text.cache_clear()
            self._active_scope_hash = scope_hash
        return scope_hash

    @lru_cache(maxsize=2048)
    def embed_text(self, text: str) -> list[float]:
        if not text or not text.strip():
            raise ChromaAdapterError("cannot embed empty text")
        if self.lm_studio_manager is not None:
            try:
                self.lm_studio_manager.ensure_embedding_model_loaded(self.config.embedding_model)
            except LMStudioManagerError as exc:
                raise ChromaAdapterError(f"LM Studio embedding model readiness failed: {exc}") from exc
        payload = {
            "input": f"{self.config.nomic_prefix}{text}",
            "model": self.config.embedding_model,
        }
        headers = {"Content-Type": "application/json"}
        if self.config.lm_studio_api_token:
            headers["Authorization"] = f"Bearer {self.config.lm_studio_api_token}"
        try:
            response = self.http_post(
                url=f"{self.config.lm_studio_base_url.rstrip('/')}/embeddings",
                json=payload,
                headers=headers,
                timeout=self.config.request_timeout_seconds,
            )
            if response.status_code == 401:
                raise ChromaAdapterError(
                    "LM Studio embeddings endpoint rejected request; set ALETHEIA_LM_STUDIO_API_TOKEN or disable LM Studio API auth"
                )
            response.raise_for_status()
            embedding = response.json()["data"][0]["embedding"]
        except ChromaAdapterError:
            raise
        except Exception as exc:
            raise ChromaAdapterError(f"embedding generation failed: {exc}") from exc
        if not isinstance(embedding, list) or not embedding:
            raise ChromaAdapterError("embedding response did not contain a vector")
        return [float(value) for value in embedding]

    def upsert_chunks(
        self,
        *,
        project_id: str,
        chunks: list[dict[str, Any]],
        project_params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        scope_hash = self.switch_project(project_id, project_params)
        if not chunks:
            raise ChromaAdapterError("no chunks supplied")

        ids: list[str] = []
        documents: list[str] = []
        embeddings: list[list[float]] = []
        metadatas: list[dict[str, Any]] = []

        for chunk in chunks:
            content = str(chunk["content"])
            metadata = dict(chunk.get("metadata") or {})
            chunk_id = str(chunk.get("chunk_id") or self._chunk_id(scope_hash, metadata, content))
            metadata["project_id"] = project_id
            metadata["project_scope_hash"] = scope_hash
            ids.append(chunk_id)
            documents.append(content)
            embeddings.append(self.embed_text(content))
            metadatas.append(metadata)

        try:
            self.collection.upsert(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)
        except Exception as exc:
            raise ChromaAdapterError(f"ChromaDB upsert failed: {exc}") from exc

        return {"project_id": project_id, "project_scope_hash": scope_hash, "chunks_indexed": len(ids)}

    def search(
        self,
        project_id: str,
        query: str,
        k: int = 8,
        project_params: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        if k < 1 or k > 50:
            raise ChromaAdapterError("k must be between 1 and 50")
        scope_hash = self.switch_project(project_id, project_params)
        try:
            query_embedding = self.embed_text(query)
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=k,
                where={"project_scope_hash": scope_hash},
                include=["documents", "metadatas", "distances"],
            )
        except Exception as exc:
            raise ChromaAdapterError(f"ChromaDB query failed: {exc}") from exc
        return self._normalize_results(results)

    def delete_chunks(self, *, project_id: str, absolute_path: str, project_params: dict[str, Any] | None = None) -> None:
        scope_hash = self.switch_project(project_id, project_params)
        path = str(Path(absolute_path).resolve())
        try:
            self.collection.delete(
                where={
                    "$and": [
                        {"project_scope_hash": {"$eq": scope_hash}},
                        {"absolute_path": {"$eq": path}},
                    ]
                }
            )
        except Exception as exc:
            raise ChromaAdapterError(f"ChromaDB delete failed: {exc}") from exc

    def rebuild_from_chunks(self, project_id: str, chunks: list[dict[str, Any]]) -> dict[str, Any]:
        return self.upsert_chunks(project_id=project_id, chunks=chunks)

    def _chunk_id(self, scope_hash: str, metadata: dict[str, Any], content: str) -> str:
        material = {
            "scope": scope_hash,
            "source_path": metadata.get("absolute_path") or metadata.get("file_path"),
            "chunk_index": metadata.get("chunk_index"),
            "content_sha1": hashlib.sha1(content.encode("utf-8", errors="ignore")).hexdigest(),
        }
        return hashlib.sha1(json.dumps(material, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()

    def _normalize_results(self, results: dict[str, Any]) -> list[dict[str, Any]]:
        ids = (results.get("ids") or [[]])[0]
        docs = (results.get("documents") or [[]])[0]
        metas = (results.get("metadatas") or [[]])[0]
        distances = (results.get("distances") or [[]])[0]
        output: list[dict[str, Any]] = []
        for index, result_id in enumerate(ids):
            output.append(
                {
                    "id": result_id,
                    "content": docs[index] if index < len(docs) else "",
                    "metadata": metas[index] if index < len(metas) else {},
                    "distance": distances[index] if index < len(distances) else None,
                }
            )
        return output
