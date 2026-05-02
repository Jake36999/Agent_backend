from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


@dataclass(frozen=True)
class RuntimeConfig:
    project_root: Path
    project_id: str
    state_dir: Path
    allowed_roots: tuple[Path, ...]
    chroma_path: Path
    lm_studio_base_url: str
    lm_studio_api_base_url: str
    lm_studio_api_token: str | None
    embedding_model: str
    auto_load_embedding_model: bool
    bridge_host: str
    bridge_port: int
    bridge_shared_secret: str | None
    enable_admin_bridge: bool
    approval_secret: bytes
    ocr_command: str | None
    log_level: str
    worker_id: str
    lease_seconds: int
    idle_sleep_seconds: float

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "RuntimeConfig":
        env = env or os.environ
        project_root = Path(env.get("ALETHEIA_PROJECT_ROOT", Path.cwd())).resolve()
        project_id = env.get("ALETHEIA_PROJECT_ID", project_root.name)
        state_dir = Path(env.get("ALETHEIA_STATE_DIR", project_root / ".aletheia_state")).resolve()
        allowed_roots_raw = env.get("ALETHEIA_ALLOWED_ROOTS", str(project_root))
        allowed_roots = tuple(Path(part).resolve() for part in allowed_roots_raw.split(";") if part.strip())
        enable_admin_bridge = env.get("ALETHEIA_ENABLE_ADMIN_BRIDGE", "false").lower() == "true"
        lm_studio_base_url = env.get("ALETHEIA_LM_STUDIO_BASE_URL", "http://localhost:1234/v1")
        lm_studio_api_base_url = env.get(
            "ALETHEIA_LM_STUDIO_API_BASE_URL",
            lm_studio_base_url.rstrip("/").replace("/v1", "/api/v1") if "/v1" in lm_studio_base_url else "http://127.0.0.1:1234/api/v1"
        )
        lm_studio_api_token = env.get("ALETHEIA_LM_STUDIO_API_TOKEN")
        auto_load_embedding_model = env.get("ALETHEIA_AUTO_LOAD_EMBEDDING_MODEL", "true").lower() == "true"
        return cls(
            project_root=project_root,
            project_id=project_id,
            state_dir=state_dir,
            allowed_roots=allowed_roots or (project_root,),
            chroma_path=Path(env.get("ALETHEIA_CHROMA_PATH", state_dir / "chroma")).resolve(),
            lm_studio_base_url=lm_studio_base_url,
            lm_studio_api_base_url=lm_studio_api_base_url,
            lm_studio_api_token=lm_studio_api_token,
            embedding_model=env.get("ALETHEIA_EMBEDDING_MODEL", "text-embedding-nomic-embed-text-v1.5"),
            auto_load_embedding_model=auto_load_embedding_model,
            bridge_host=env.get("ALETHEIA_BRIDGE_HOST", "127.0.0.1"),
            bridge_port=int(env.get("ALETHEIA_BRIDGE_PORT", "8765")),
            bridge_shared_secret=env.get("ALETHEIA_BRIDGE_SECRET"),
            enable_admin_bridge=enable_admin_bridge,
            approval_secret=env.get("ALETHEIA_APPROVAL_SECRET", "dev-approval-secret").encode("utf-8"),
            ocr_command=env.get("ALETHEIA_OCR_COMMAND"),
            log_level=env.get("ALETHEIA_LOG_LEVEL", "INFO"),
            worker_id=env.get("ALETHEIA_WORKER_ID", "aletheia-worker-1"),
            lease_seconds=int(env.get("ALETHEIA_LEASE_SECONDS", "60")),
            idle_sleep_seconds=float(env.get("ALETHEIA_IDLE_SLEEP_SECONDS", "0.25")),
        )
