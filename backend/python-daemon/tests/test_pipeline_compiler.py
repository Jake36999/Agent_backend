from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
import yaml

from orchestrator.pipeline.models import PipelineDefinition, PipelineStep
from orchestrator.pipeline.compiler import PipelineCompiler, PipelineCompileError
from orchestrator.pipeline.loader import PipelineLoader, PipelineLoadError


def _simple_definition(steps=None, max_steps=20) -> PipelineDefinition:
    if steps is None:
        steps = (
            PipelineStep(
                step_id="step_a",
                tool_name="mcp_investigation_start",
                args_template={"objective": "${objective}", "target_repo": "${target_repo}"},
                description="Start investigation",
            ),
            PipelineStep(
                step_id="step_b",
                tool_name="mcp_investigation_filemap",
                args_template={"session_path": "${session_path}"},
                description="Build file map",
                depends_on=("step_a",),
            ),
        )
    return PipelineDefinition(
        pipeline_id="test_pipeline",
        version="1.0.0",
        name="Test Pipeline",
        description="A test pipeline",
        steps=steps,
        variables={"profile": "safe"},
        max_steps=max_steps,
    )


class TestPipelineCompiler:
    def test_compile_produces_correct_plan_list(self):
        compiler = PipelineCompiler()
        definition = _simple_definition()
        plan = compiler.compile_to_plan_list(
            definition,
            runtime_vars={"objective": "find bugs", "target_repo": "/tmp/repo"},
        )
        assert len(plan) == 2
        assert plan[0]["id"] == "step_a"
        assert plan[0]["tool_name"] == "mcp_investigation_start"
        assert plan[0]["args"]["objective"] == "find bugs"
        assert plan[0]["args"]["target_repo"] == "/tmp/repo"
        assert plan[0]["status"] == "pending"
        assert plan[1]["id"] == "step_b"
        assert plan[1]["args"]["session_path"] == "${session_path}"

    def test_compile_resolves_declared_variables(self):
        compiler = PipelineCompiler()
        definition = _simple_definition()
        plan = compiler.compile_to_plan_list(
            definition,
            runtime_vars={"objective": "test", "target_repo": "/repo", "session_path": "/tmp/sess"},
        )
        assert plan[1]["args"]["session_path"] == "/tmp/sess"

    def test_compile_preserves_topological_order(self):
        steps = (
            PipelineStep(step_id="c", tool_name="mcp_commit_memory", args_template={}, description="C", depends_on=("b",)),
            PipelineStep(step_id="a", tool_name="mcp_investigation_start", args_template={}, description="A"),
            PipelineStep(step_id="b", tool_name="mcp_investigation_filemap", args_template={}, description="B", depends_on=("a",)),
        )
        compiler = PipelineCompiler()
        plan = compiler.compile_to_plan_list(_simple_definition(steps=steps))
        ids = [t["id"] for t in plan]
        assert ids.index("a") < ids.index("b")
        assert ids.index("b") < ids.index("c")

    def test_compile_rejects_cycle(self):
        steps = (
            PipelineStep(step_id="a", tool_name="mcp_investigation_start", args_template={}, description="A", depends_on=("b",)),
            PipelineStep(step_id="b", tool_name="mcp_investigation_filemap", args_template={}, description="B", depends_on=("a",)),
        )
        compiler = PipelineCompiler()
        with pytest.raises(PipelineCompileError, match="cycle"):
            compiler.compile_to_plan_list(_simple_definition(steps=steps))

    def test_compile_rejects_unknown_dependency(self):
        steps = (
            PipelineStep(step_id="a", tool_name="mcp_investigation_start", args_template={}, description="A", depends_on=("nonexistent",)),
        )
        compiler = PipelineCompiler()
        with pytest.raises(PipelineCompileError, match="unknown step"):
            compiler.compile_to_plan_list(_simple_definition(steps=steps))

    def test_compile_rejects_unknown_tool(self):
        steps = (
            PipelineStep(step_id="a", tool_name="mcp_bad_tool", args_template={}, description="A"),
        )
        compiler = PipelineCompiler(allowed_tools={"mcp_investigation_start"})
        with pytest.raises(PipelineCompileError, match="not in allowed_tools"):
            compiler.compile_to_plan_list(_simple_definition(steps=steps))

    def test_compile_rejects_empty_steps(self):
        compiler = PipelineCompiler()
        with pytest.raises(PipelineCompileError, match="no steps"):
            compiler.compile_to_plan_list(_simple_definition(steps=()))

    def test_compile_rejects_duplicate_step_ids(self):
        steps = (
            PipelineStep(step_id="a", tool_name="mcp_investigation_start", args_template={}, description="A"),
            PipelineStep(step_id="a", tool_name="mcp_commit_memory", args_template={}, description="B"),
        )
        compiler = PipelineCompiler()
        with pytest.raises(PipelineCompileError, match="duplicate"):
            compiler.compile_to_plan_list(_simple_definition(steps=steps))

    def test_compile_rejects_exceeding_max_steps(self):
        steps = tuple(
            PipelineStep(step_id=f"s{i}", tool_name="mcp_commit_memory", args_template={}, description=f"Step {i}")
            for i in range(5)
        )
        compiler = PipelineCompiler()
        with pytest.raises(PipelineCompileError, match="exceeds max_steps"):
            compiler.compile_to_plan_list(_simple_definition(steps=steps, max_steps=3))

    def test_compile_resolves_nested_args(self):
        steps = (
            PipelineStep(
                step_id="a",
                tool_name="mcp_commit_memory",
                args_template={"metadata": {"source": "${source_name}"}},
                description="A",
            ),
        )
        compiler = PipelineCompiler()
        plan = compiler.compile_to_plan_list(
            _simple_definition(steps=steps),
            runtime_vars={"source_name": "deep_research"},
        )
        assert plan[0]["args"]["metadata"]["source"] == "deep_research"


class TestPipelineLoader:
    def test_load_yaml_template(self):
        loader = PipelineLoader()
        templates = loader.list_templates()
        assert "investigation" in templates

    def test_load_investigation_template(self):
        loader = PipelineLoader()
        definition = loader.load("investigation")
        assert definition.pipeline_id == "investigation"
        assert len(definition.steps) == 5
        assert definition.steps[0].tool_name == "mcp_investigation_start"

    def test_load_nonexistent_template_raises(self):
        loader = PipelineLoader()
        with pytest.raises(PipelineLoadError, match="not found"):
            loader.load("nonexistent_pipeline")

    def test_load_custom_yaml_file(self):
        yaml_content = {
            "pipeline_id": "custom",
            "version": "0.1.0",
            "name": "Custom Pipeline",
            "steps": [
                {
                    "step_id": "s1",
                    "tool_name": "mcp_commit_memory",
                    "description": "Commit something",
                    "args": {"category": "summary", "content": "test"},
                },
            ],
        }
        with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False, encoding="utf-8") as f:
            yaml.dump(yaml_content, f)
            f.flush()
            loader = PipelineLoader()
            definition = loader.load_file(Path(f.name))
            assert definition.pipeline_id == "custom"
            assert len(definition.steps) == 1

    def test_load_missing_required_fields_raises(self):
        yaml_content = {"pipeline_id": "bad", "steps": []}
        with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False, encoding="utf-8") as f:
            yaml.dump(yaml_content, f)
            f.flush()
            loader = PipelineLoader()
            with pytest.raises(PipelineLoadError, match="missing required fields"):
                loader.load_file(Path(f.name))

    def test_roundtrip_compile_investigation_template(self):
        loader = PipelineLoader()
        compiler = PipelineCompiler()
        definition = loader.load("investigation")
        plan = compiler.compile_to_plan_list(
            definition,
            runtime_vars={"objective": "audit", "target_repo": "/tmp/repo", "session_path": "/tmp/sess"},
        )
        assert len(plan) == 5
        assert plan[0]["tool_name"] == "mcp_investigation_start"
        assert plan[0]["args"]["objective"] == "audit"
        assert plan[-1]["tool_name"] == "mcp_investigation_compile_handoff"
