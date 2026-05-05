from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from .models import NullPartitionResult, PartitionMappingResult


class PartitionMapper:
    def __init__(self, lmstudio_conversations_root: str | Path) -> None:
        self.lmstudio_conversations_root = Path(lmstudio_conversations_root).expanduser().resolve()

    def map(self, conversation_json_path: str | Path) -> PartitionMappingResult | NullPartitionResult:
        conversation_path = Path(conversation_json_path).expanduser().resolve()
        if not conversation_path.is_relative_to(self.lmstudio_conversations_root):
            return NullPartitionResult(
                status="POLICY_BLOCK",
                message="Conversation path must be under the configured LM Studio conversations root.",
                conversation_path=str(conversation_path),
            )
        conversation_id = conversation_path.stem
        folder_relpath = conversation_path.parent.relative_to(self.lmstudio_conversations_root)
        folder_relpath_text = "" if str(folder_relpath) in {"", "."} else folder_relpath.as_posix()
        if not folder_relpath_text:
            return NullPartitionResult(
                status="NEEDS_PROJECT_FOLDER",
                message="Move this chat into an LM Studio folder to enable persistent project memory.",
                conversation_id=conversation_id,
                folder_relpath="",
                conversation_path=str(conversation_path),
            )
        project_id = self._project_id_from_relpath(folder_relpath_text)
        project_scope_hash = hashlib.sha1(
            json.dumps({"project_id": project_id}, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        return PartitionMappingResult(
            ok=True,
            status="MAPPED",
            message="Conversation mapped to active partition.",
            conversation_id=conversation_id,
            folder_relpath=folder_relpath_text,
            project_id=project_id,
            project_scope_hash=project_scope_hash,
            conversation_path=str(conversation_path),
        )

    def _project_id_from_relpath(self, folder_relpath: str) -> str:
        normalized = re.sub(r"[^a-z0-9]+", "-", folder_relpath.lower()).strip("-")
        return f"lmstudio-{normalized or 'project'}"

