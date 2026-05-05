from __future__ import annotations

import re
from typing import Any

from .models import CandidateAnalysisInput, RankedCandidate
from .scorer import parse_manifest_candidates, score_path, tokenize


class CandidateAnalysisService:
    ranking_policy = (
        "score desc, evidence count desc, path lexical asc; score uses objective/log/workspace/RAG token "
        "matches and penalizes generated, bundled, vendor, build, cache, and VCS paths."
    )

    def analyze(self, request: CandidateAnalysisInput | dict[str, Any]) -> dict[str, object]:
        if isinstance(request, dict):
            request = CandidateAnalysisInput(**request)
        max_candidates = max(1, min(int(request.max_candidates), 50))
        context_text = "\n".join(
            part
            for part in [request.objective, request.logs, request.failing_test_output, request.workspace_summary]
            if part
        )
        context_tokens = tokenize(context_text)
        rag_tokens = tokenize(request.rag_context)
        manifest_candidates = list(request.manifest_candidates or [])
        if not manifest_candidates and request.manifest_csv:
            manifest_candidates = parse_manifest_candidates(request.manifest_csv)
        missing_context: list[dict[str, object]] = []
        if not manifest_candidates:
            missing_context.append({"item": "manifest_csv", "reason": "No file manifest candidates provided."})
            return {
                "ok": False,
                "status": "WARN",
                "summary": "No target repository source candidates were available for deterministic ranking.",
                "ranked_candidates": [],
                "ranking_policy_applied": self.ranking_policy,
                "missing_context": missing_context,
                "next_action": "Provide a readable manifest_csv containing target_repo source files.",
            }

        scored: list[dict[str, Any]] = []
        for candidate in manifest_candidates:
            path = str(candidate.get("path") or "")
            if not path:
                continue
            item = score_path(path, context_tokens, rag_tokens)
            if candidate.get("rel_path"):
                item["rel_path"] = str(candidate["rel_path"])
            if item["score"] > -20:
                scored.append(item)
        scored.sort(key=lambda item: (-float(item["score"]), -len(item["evidence"]), item["path"]))
        ranked = [
            RankedCandidate(
                rank=index + 1,
                path=item["path"],
                rel_path=str(item.get("rel_path") or item["path"]),
                score=round(float(item["score"]), 3),
                confidence=round(float(item["confidence"]), 3),
                evidence=list(item["evidence"]),
                risk_notes=list(item["risk_notes"]),
                test_seams=list(item["test_seams"]),
            )
            for index, item in enumerate(scored[:max_candidates])
        ]
        return {
            "ok": True,
            "status": "OK",
            "summary": f"Ranked {len(ranked)} candidate paths deterministically.",
            "ranked_candidates": [item.to_dict() for item in ranked],
            "ranking_policy_applied": self.ranking_policy,
            "missing_context": missing_context,
            "next_action": "Use the top ranked candidates for triage or TDD planning."
            if ranked
            else "Provide manifest_csv or workspace summary for ranking.",
        }

    def _infer_paths_from_context(self, text: str) -> list[str]:
        matches = re.findall(r"(?:[A-Za-z0-9_.-]+[/\\])+[A-Za-z0-9_.-]+", text or "")
        return sorted({match.replace("\\", "/") for match in matches})[:100]
