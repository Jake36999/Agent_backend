from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from orchestrator.code_review.review_drafter import (
    _DRAFT_CAP,
    _PROMPT_CAP,
    build_review_prompt,
    draft_review,
)
from orchestrator.code_review.artifact_writer import persist_draft_review


_SAMPLE_KWARGS = {
    "architecture_overview": "# Overview\n10 files, 500 lines.",
    "code_review_summary": "# Summary\nAll clear.",
    "heuristics_json": '{"largest_files": []}',
    "next_actions_yaml": "suggested_followups:\n  - id: test",
    "target_repo": "/tmp/my-repo",
}


class TestBuildReviewPrompt:
    def test_prompt_contains_repo_name(self):
        prompt = build_review_prompt(**_SAMPLE_KWARGS)
        assert "my-repo" in prompt

    def test_prompt_contains_all_sections(self):
        prompt = build_review_prompt(**_SAMPLE_KWARGS)
        assert "## Architecture Overview" in prompt
        assert "## Code Review Summary" in prompt
        assert "## Heuristics (JSON)" in prompt
        assert "## Suggested Follow-ups" in prompt

    def test_prompt_bounded(self):
        huge = {k: ("x" * 20000 if isinstance(v, str) else v) for k, v in _SAMPLE_KWARGS.items()}
        prompt = build_review_prompt(**huge)
        assert len(prompt) <= _PROMPT_CAP

    def test_prompt_includes_constraint_language(self):
        prompt = build_review_prompt(**_SAMPLE_KWARGS)
        assert "Do NOT claim bugs" in prompt
        assert "neutral language" in prompt

    def test_prompt_includes_artifact_content(self):
        prompt = build_review_prompt(**_SAMPLE_KWARGS)
        assert "10 files, 500 lines" in prompt
        assert "All clear" in prompt


class TestDraftReview:
    def test_returns_none_when_no_lm_client(self):
        result = draft_review(lm_client=None, **_SAMPLE_KWARGS)
        assert result is None

    def test_returns_draft_from_lm_client(self):
        client = MagicMock()
        client.complete.return_value = "## Draft Review\nThis repo looks well-structured."
        result = draft_review(lm_client=client, **_SAMPLE_KWARGS)
        assert result is not None
        assert "Draft Review" in result

    def test_lm_client_called_with_prompt(self):
        client = MagicMock()
        client.complete.return_value = "draft"
        draft_review(lm_client=client, **_SAMPLE_KWARGS)
        client.complete.assert_called_once()
        prompt_arg = client.complete.call_args[0][0]
        assert "my-repo" in prompt_arg

    def test_draft_bounded(self):
        client = MagicMock()
        client.complete.return_value = "x" * (_DRAFT_CAP + 5000)
        result = draft_review(lm_client=client, **_SAMPLE_KWARGS)
        assert result is not None
        assert len(result) <= _DRAFT_CAP

    def test_returns_none_on_lm_client_exception(self):
        client = MagicMock()
        client.complete.side_effect = RuntimeError("model unavailable")
        result = draft_review(lm_client=client, **_SAMPLE_KWARGS)
        assert result is None

    def test_returns_none_on_empty_response(self):
        client = MagicMock()
        client.complete.return_value = "   "
        result = draft_review(lm_client=client, **_SAMPLE_KWARGS)
        assert result is None

    def test_returns_none_on_non_string_response(self):
        client = MagicMock()
        client.complete.return_value = 42
        result = draft_review(lm_client=client, **_SAMPLE_KWARGS)
        assert result is None

    def test_strips_whitespace(self):
        client = MagicMock()
        client.complete.return_value = "\n  Draft content here.  \n"
        result = draft_review(lm_client=client, **_SAMPLE_KWARGS)
        assert result == "Draft content here."

    def test_custom_max_tokens_forwarded(self):
        client = MagicMock()
        client.complete.return_value = "draft"
        draft_review(lm_client=client, **_SAMPLE_KWARGS, max_tokens=4096)
        _, kwargs = client.complete.call_args
        assert kwargs["max_tokens"] == 4096


class TestPersistDraftReview:
    def test_writes_file(self, tmp_path: Path):
        path = persist_draft_review("## Draft\nGood repo.", "run-1", tmp_path)
        assert Path(path).exists()
        assert Path(path).read_text(encoding="utf-8") == "## Draft\nGood repo."

    def test_file_named_review_draft_md(self, tmp_path: Path):
        path = persist_draft_review("content", "run-2", tmp_path)
        assert path.endswith("review_draft.md")

    def test_creates_run_directory(self, tmp_path: Path):
        persist_draft_review("content", "run-3", tmp_path)
        assert (tmp_path / "run-3").is_dir()


