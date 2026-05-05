from __future__ import annotations

import re
from typing import Any

from .models import CandidateAnalysisInput, RankedCandidate
from .scorer import parse_manifest_candidates, score_path, tokenize


class CandidateAnalysisService:
    ranking_policy = (
        "score = direct path/token matches + filename/stem matches + test seam proximity + "
        "provided semantic context hits - generated/cache/vendor penalties; stable ordering by score, evidence count, path."
    )

    def analyze(self, request: CandidateAnalysisInput | dict[str, Any]) -> dict[str, object]:
        if isinstance(request, dict):
            request = CandidateAnalysisInput(**request)
        max_candidates = max(1, min(int(request.max_candidates), 50))
        context_text = "\n".join(
            part for part in [request.objective, request.logs, request.failing_test_output, request.workspace_summary] if part
        )
        context_tokens = tokenize(context_text)
        rag_tokens = tokenize(request.rag_context)
        manifest_candidates = parse_manifest_candidates(request.manifest_csv)
        missing_context: list[dict[str, object]] = []
        if not manifest_candidates:
            missing_context.append({"item": "manifest_csv", "reason": "No file manifest candidates provided."})
            inferred = self._infer_paths_from_context(context_text + "\n" + (request.rag_context or ""))
            manifest_candidates = [{"path": path, "row": {}} for path in inferred]

        scored = []
        for candidate in manifest_candidates:
            path = str(candidate.get("path") or "")
            if not path:
                continue
            item = score_path(path, context_tokens, rag_tokens)
            if item["score"] > -5:
                scored.append(item)
        scored.sort(key=lambda item: (-float(item["score"]), -len(item["evidence"]), item["path"]))
        ranked = [
            RankedCandidate(
                rank=i + 1,
                path=item["path"],
                score=round(float(item["score"]), 3),
                confidence=round(float(item["confidence"]), 3),
                evidence=list(item["evidence"]),
                risk_notes=list(item["risk_notes"]),
                test_seams=list(item["test_seams"]),
            )
            for i, item in enumerate(scored[:max_candidates])
        ]
        return {
            "ok": True,
            "status": "OK",
            "summary": f"Ranked {len(ranked)} candidate paths deterministically.",
            "ranked_candidates": [item.to_dict() for item in ranked],
            "ranking_policy_applied": self.ranking_policy,
            "missing_context": missing_context,
            "next_action": "Use the top ranked candidates for triage or TDD planning." if ranked else "Provide manifest_csv or workspace summary for ranking.",
        }

    def _infer_paths_from_context(self, text: str) -> list[str]:
        matches = re.findall(r"(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+", text or "")
        return sorted(set(match.replace("\\", "/") for match in matches))[:100]
