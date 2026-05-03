from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path
from typing import Any


class ToolAssistAdapterError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class ToolAssistAdapter:
    def __init__(self, toolset_root: str | None = None, lta_output_root: str | None = None) -> None:
        self.toolset_root = Path(toolset_root or os.getenv("TOOLSET_ROOT", "")).expanduser().resolve() if (toolset_root or os.getenv("TOOLSET_ROOT")) else None
        self.lta_output_root = lta_output_root or os.getenv("LTA_OUTPUT_ROOT")
        self._backend_api: Any | None = None

    def _error(self, code: str, summary: str, status: str = "ERROR") -> dict[str, Any]:
        return {
            "ok": False,
            "status": status,
            "summary": summary,
            "artifacts": {},
            "top_candidates": [],
            "recommended_next_tool": "",
            "error": {"code": code, "message": summary},
        }

    def _normalize(self, response: Any, include_content_chars: int | None = None) -> dict[str, Any]:
        if not isinstance(response, dict):
            return self._error("toolset_call_failed", "ToolSet returned a non-object response.")
        raw_artifacts = response.get("artifacts") if isinstance(response.get("artifacts"), dict) else {}
        artifacts = {str(k): str(v) for k, v in raw_artifacts.items() if isinstance(k, str) and isinstance(v, str)}
        raw_candidates = response.get("top_candidates") if isinstance(response.get("top_candidates"), list) else []
        summary = str(response.get("summary", ""))[:2000]
        normalized: dict[str, Any] = {
            "ok": bool(response.get("ok", False)),
            "status": str(response.get("status", "ERROR")),
            "summary": summary,
            "artifacts": artifacts,
            "top_candidates": raw_candidates[:10],
            "recommended_next_tool": str(response.get("recommended_next_tool", "")),
        }
        raw_error = response.get("error")
        if isinstance(raw_error, dict):
            normalized["error"] = {
                "code": str(raw_error.get("code", "toolset_error")),
                "message": str(raw_error.get("message", summary))[:2000],
            }
        elif isinstance(raw_error, str):
            normalized["error"] = {"code": "toolset_error", "message": raw_error[:2000]}

        if include_content_chars is not None and isinstance(response.get("content"), str):
            normalized["content"] = response["content"][: max(1, include_content_chars)]
        return normalized

    def _load_backend_api(self) -> Any:
        if self._backend_api is not None:
            return self._backend_api
        if self.toolset_root is None:
            raise ToolAssistAdapterError("missing_toolset_root", "TOOLSET_ROOT is required for investigation tools.")
        if not self.toolset_root.exists():
            raise ToolAssistAdapterError("toolset_root_not_found", f"TOOLSET_ROOT does not exist: {self.toolset_root}")
        pkg_root = self.toolset_root / "local_tool_assist_mcp"
        if not pkg_root.exists():
            raise ToolAssistAdapterError("toolset_layout_invalid", "TOOLSET_ROOT must contain local_tool_assist_mcp.")
        if str(self.toolset_root) not in sys.path:
            sys.path.insert(0, str(self.toolset_root))
        try:
            self._backend_api = importlib.import_module("local_tool_assist_mcp.backend_api")
        except ModuleNotFoundError as exc:
            if exc.name == "local_tool_assist_mcp.backend_api":
                raise ToolAssistAdapterError(
                    "missing_backend_api",
                    "ToolSet is missing local_tool_assist_mcp/backend_api.py; add this stable API module in ToolSet.",
                ) from exc
            raise
        return self._backend_api

    def _session_allowed(self, session_path: str) -> bool:
        path = Path(session_path).expanduser().resolve()
        if self.lta_output_root:
            root = Path(self.lta_output_root).expanduser().resolve()
            return path == root or root in path.parents
        if self.toolset_root is not None and self.toolset_root.exists():
            root = (self.toolset_root / "local_tool_assist_outputs").resolve()
            return path == root or root in path.parents
        return True

    def _policy_block(self) -> dict[str, Any]:
        msg = "session_path is outside the configured Tool Assist output root."
        return {
            "ok": False,
            "status": "POLICY_BLOCK",
            "summary": msg,
            "artifacts": {},
            "top_candidates": [],
            "recommended_next_tool": "",
            "error": {"code": "session_path_outside_output_root", "message": msg},
        }

    def _invoke(self, method_name: str, include_content_chars: int | None = None, **kwargs: Any) -> dict[str, Any]:
        try:
            backend_api = self._load_backend_api()
            method = getattr(backend_api, method_name, None)
            if method is None:
                raise ToolAssistAdapterError("missing_backend_api_method", f"ToolSet backend_api missing method: {method_name}")
            return self._normalize(method(**kwargs), include_content_chars=include_content_chars)
        except ToolAssistAdapterError as exc:
            return self._error(exc.code, exc.message)
        except Exception as exc:
            return self._error("toolset_call_failed", f"ToolSet call failed: {exc}")

    def investigation_start(self, objective: str, target_repo: str, profile: str = "safe") -> dict[str, Any]:
        kwargs = {"objective": objective, "target_repo": target_repo, "profile": profile}
        if self.lta_output_root:
            kwargs["output_root"] = self.lta_output_root
        return self._invoke("create_session", **kwargs)

    def investigation_filemap(self, session_path: str, profile: str = "safe") -> dict[str, Any]:
        if not self._session_allowed(session_path):
            return self._policy_block()
        return self._invoke("scan_directory", session_path=session_path, profile=profile)

    def investigation_validate_manifest(self, session_path: str) -> dict[str, Any]:
        if not self._session_allowed(session_path):
            return self._policy_block()
        return self._invoke("validate_manifest", session_path=session_path)

    def investigation_read_report(self, session_path: str, artifact_key: str, max_chars: int = 12000) -> dict[str, Any]:
        if not self._session_allowed(session_path):
            return self._policy_block()
        capped_chars = max(1, min(int(max_chars), 12000))
        return self._invoke(
            "read_report",
            session_path=session_path,
            artifact_key=artifact_key,
            max_chars=capped_chars,
            include_content_chars=capped_chars,
        )

    def investigation_compile_handoff(self, session_path: str) -> dict[str, Any]:
        if not self._session_allowed(session_path):
            return self._policy_block()
        return self._invoke("compile_handoff_report", session_path=session_path)
