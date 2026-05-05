from __future__ import annotations

import re
from typing import Any

from .service import MemoryService

_ALLOWED_BASES = {
    "tool_result",
    "user_decision",
    "approved_plan",
    "completed_artifact",
    "verified_file_state",
}
_MAX_CONTENT = 8000
_SECRET_PATTERNS = [
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?i)\b(api[_-]?key|token|secret|password)\b\s*[:=]\s*['\"]?[^\s,'\"]{12,}"),
    re.compile(r"(?m)^\s*[A-Z0-9_]*(TOKEN|SECRET|PASSWORD|API_KEY)\s*="),
]
_VOLATILE_KEYS = {"pid", "process_id", "tmp", "temp", "timestamp", "nonce", "session_id"}
_CATEGORY_BY_LAYER = {
    "project_decision": "decision",
    "project_summary": "summary",
    "project_sop": "architecture",
    "project_artifact": "artifact",
}


def _bounded(text: object, limit: int = _MAX_CONTENT) -> str:
    return str(text or "")[:max(1, int(limit))]


class ConversationSummaryIngestor:
    """Deterministic implementation of conversation_summary_ingest_v1 policy."""

    def build_memory_candidate(
        self,
        *,
        conversation_events: list[dict[str, object]],
        target_repo: str | None = None,
        project_id: str | None = None,
        source_artifacts: list[dict[str, object]] | None = None,
        write_intent: str | None = None,
        selected_skill: dict[str, object] | None = None,
    ) -> dict[str, object]:
        volatile_removed: list[dict[str, object]] = []
        safe_events: list[dict[str, object]] = []
        for event in conversation_events or []:
            cleaned = {}
            for key, value in event.items():
                if str(key).lower() in _VOLATILE_KEYS:
                    volatile_removed.append({"key": str(key), "reason": "volatile"})
                    continue
                cleaned[str(key)] = value
            safe_events.append(cleaned)

        joined = "\n".join(_bounded(event.get("content") or event.get("summary") or event, 2000) for event in safe_events)
        if self._contains_secret(joined):
            return self._rejected("Secret-like content detected; memory write blocked.", volatile_removed)

        basis = self._infer_basis(safe_events, source_artifacts)
        if basis == "none":
            return self._rejected("No verified basis for durable project memory.", volatile_removed)

        layer = self._infer_layer(write_intent, basis, source_artifacts)
        category = _CATEGORY_BY_LAYER.get(layer, "summary")
        content = self._build_content(safe_events, source_artifacts, write_intent)
        if not content:
            return self._rejected("No durable content after filtering.", volatile_removed)

        metadata = {
            "target_repo": target_repo,
            "project_id": project_id,
            "verification_basis": basis,
            "memory_layer": layer,
            "selected_skill_id": (selected_skill or {}).get("skill_id") if isinstance(selected_skill, dict) else None,
        }
        return {
            "ok": True,
            "summary": _bounded(content, 500),
            "memory_candidate": {
                "category": category,
                "content": _bounded(content, _MAX_CONTENT),
                "metadata": {k: v for k, v in metadata.items() if v is not None},
            },
            "verification_basis": basis,
            "memory_layer": layer,
            "volatile_fields_removed": volatile_removed,
            "write_allowed": True,
            "next_action": "Commit bounded project memory through MemoryService.",
        }

    def commit_if_allowed(
        self,
        *,
        candidate_result: dict[str, object],
        memory_service: MemoryService,
    ) -> dict[str, object]:
        if not candidate_result.get("write_allowed"):
            return {"ok": True, "status": "SKIPPED", "reason": "write_allowed=false"}
        candidate = candidate_result.get("memory_candidate")
        if not isinstance(candidate, dict):
            return {"ok": False, "status": "INVALID_CANDIDATE"}
        category = str(candidate.get("category") or "summary")
        content = str(candidate.get("content") or "")
        metadata = candidate.get("metadata") if isinstance(candidate.get("metadata"), dict) else {}
        if hasattr(memory_service, "commit_memory"):
            return memory_service.commit_memory(category=category, content=content, metadata=metadata)
        if hasattr(memory_service, "commit"):
            return memory_service.commit(category=category, content=content, metadata=metadata)
        raise AttributeError("MemoryService does not expose commit_memory or commit")

    def _contains_secret(self, text: str) -> bool:
        return any(pattern.search(text or "") for pattern in _SECRET_PATTERNS)

    def _infer_basis(self, events: list[dict[str, object]], source_artifacts: list[dict[str, object]] | None) -> str:
        for event in events:
            event_type = str(event.get("type") or event.get("basis") or "")
            if event_type in _ALLOWED_BASES:
                if event_type == "verified_file_state":
                    return "tool_result"
                return event_type
        if source_artifacts:
            for artifact in source_artifacts:
                if artifact.get("verified") is True or artifact.get("status") in {"completed", "passed", "ok"}:
                    return "completed_artifact"
        return "none"

    def _infer_layer(self, write_intent: str | None, basis: str, source_artifacts: list[dict[str, object]] | None) -> str:
        intent = (write_intent or "").lower()
        if "decision" in intent or basis == "user_decision":
            return "project_decision"
        if "sop" in intent or "procedure" in intent:
            return "project_sop"
        if source_artifacts or basis == "completed_artifact":
            return "project_artifact"
        if basis in {"tool_result", "approved_plan"}:
            return "project_summary"
        return "none"

    def _build_content(self, events: list[dict[str, object]], source_artifacts: list[dict[str, object]] | None, write_intent: str | None) -> str:
        parts: list[str] = []
        if write_intent:
            parts.append(f"Intent: {write_intent}")
        for event in events[:20]:
            content = event.get("content") or event.get("summary") or event.get("decision")
            if content:
                parts.append(str(content))
        for artifact in (source_artifacts or [])[:20]:
            summary = artifact.get("summary") or artifact.get("path") or artifact.get("artifact")
            if summary:
                parts.append(f"Artifact: {summary}")
        return _bounded("\n".join(parts), _MAX_CONTENT)

    def _rejected(self, reason: str, volatile_removed: list[dict[str, object]]) -> dict[str, object]:
        return {
            "ok": True,
            "summary": reason,
            "memory_candidate": {"category": "summary", "content": "", "metadata": {}},
            "verification_basis": "none",
            "memory_layer": "none",
            "volatile_fields_removed": volatile_removed,
            "write_allowed": False,
            "next_action": "Do not commit memory.",
        }
