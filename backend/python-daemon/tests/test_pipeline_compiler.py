from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
import yaml

from orchestrator.pipeline.models import ArgBinding, PipelineDefinition, PipelineStep
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
                outputs={"session_path": "artifacts.session_path"},
            ),
            PipelineStep(
                step_id="step_b",
                tool_name="mcp_investigation_filemap",
                args_template={"session_path": ArgBinding(from_step="step_a", path="artifacts.session_path")},
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
        binding = plan[1]["args"]["session_path"]
        assert isinstance(binding, dict) and binding.get("__binding__") is True
        assert binding["from_step"] == "step_a"
        assert binding["path"] == "artifacts.session_path"

    def test_compile_resolves_declared_variables(self):
        compiler = PipelineCompiler()
        definition = _simple_definition()
        plan = compiler.compile_to_plan_list(
            definition,
            runtime_vars={"objective": "test", "target_repo": "/repo"},
        )
        assert plan[0]["args"]["objective"] == "test"
        assert plan[0]["args"]["target_repo"] == "/repo"
        binding = plan[1]["args"]["session_path"]
        assert isinstance(binding, dict) and binding.get("__binding__") is True

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

    def test_compile_rejects_unresolved_variable(self):
        steps = (
            PipelineStep(
                step_id="a",
                tool_name="mcp_commit_memory",
                args_template={"content": "${missing_var}"},
                description="A",
            ),
        )
        compiler = PipelineCompiler()
        with pytest.raises(PipelineCompileError, match="unresolved variables"):
            compiler.compile_to_plan_list(_simple_definition(steps=steps))

    def test_compile_rejects_session_path_as_unresolved(self):
        """${session_path} in pipeline templates is no longer allowed — use bind: instead."""
        steps = (
            PipelineStep(
                step_id="a",
                tool_name="mcp_investigation_filemap",
                args_template={"session_path": "${session_path}"},
                description="A",
            ),
        )
        compiler = PipelineCompiler()
        with pytest.raises(PipelineCompileError, match="unresolved.*session_path"):
            compiler.compile_to_plan_list(_simple_definition(steps=steps))


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
        with pytest.raises(PipelineLoadError):
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
            with pytest.raises(PipelineLoadError):
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

    def test_pipeline_id_traversal_rejected(self):
        loader = PipelineLoader()
        with pytest.raises(PipelineLoadError):
            loader.load("../secrets")

    def test_pipeline_id_invalid_chars_rejected(self):
        loader = PipelineLoader()
        for bad in ("FOO", "foo/bar", "foo bar", "123abc", ".hidden"):
            with pytest.raises(PipelineLoadError):
                loader.load(bad)

    def test_reserved_pipeline_id_rejected(self):
        loader = PipelineLoader()
        for reserved in ("tools", "admin", "schema", "examples", "staging"):
            with pytest.raises(PipelineLoadError):
                loader.load(reserved)

    def test_active_templates_do_not_include_examples(self):
        loader = PipelineLoader()
        templates = loader.list_templates()
        # code_review is now active; deep_research and other examples remain inactive
        assert "code_review" in templates
        assert "deep_research" not in templates

    def test_code_review_template_loads_and_compiles(self):
        from orchestrator.agent_workflow.policies import ALLOWED_TOOLS
        loader = PipelineLoader()
        compiler = PipelineCompiler(allowed_tools=frozenset(ALLOWED_TOOLS))
        definition = loader.load("code_review")
        plan = compiler.compile_to_plan_list(
            definition,
            runtime_vars={"objective": "review", "target_repo": "/tmp/repo"},
        )
        step_ids = [t["id"] for t in plan]
        assert "repo_context" in step_ids
        assert "dependency_graph" in step_ids
        assert "mermaid" in step_ids

    def test_code_review_in_active_pipelines(self):
        from orchestrator.pipeline.loader import ACTIVE_PIPELINES
        assert "code_review" in ACTIVE_PIPELINES

    def test_investigation_uses_only_allowed_tools(self):
        from orchestrator.agent_workflow.policies import ALLOWED_TOOLS
        compiler = PipelineCompiler(allowed_tools=frozenset(ALLOWED_TOOLS))
        loader = PipelineLoader()
        definition = loader.load("investigation")
        compiler.compile_to_plan_list(
            definition,
            runtime_vars={"objective": "x", "target_repo": "/t", "session_path": "/s"},
        )

    def test_load_inactive_pipeline_rejected(self):
        loader = PipelineLoader()
        with pytest.raises(PipelineLoadError, match="not active"):
            loader.load("deep_research")

    def test_load_file_rejects_unknown_top_level_field(self):
        yaml_content = {
            "pipeline_id": "custom",
            "version": "0.1.0",
            "name": "Custom Pipeline",
            "unexpected_field": "nope",
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
            with pytest.raises(PipelineLoadError, match="schema validation failed"):
                loader.load_file(Path(f.name))


class TestArgBindingCompiler:
    """Compile-time binding validation tests."""

    def _two_step_def(self, a_args=None, b_args=None, b_deps=("a",)):
        steps = (
            PipelineStep(step_id="a", tool_name="mcp_investigation_start", args_template=a_args or {}, description="A"),
            PipelineStep(step_id="b", tool_name="mcp_investigation_filemap", args_template=b_args or {}, description="B", depends_on=b_deps),
        )
        return PipelineDefinition(pipeline_id="test_pipeline", version="1.0", name="T", description="", steps=steps)

    def test_valid_binding_serializes_to_sentinel(self):
        defn = self._two_step_def(b_args={"session_path": ArgBinding(from_step="a", path="artifacts.session_path")})
        plan = PipelineCompiler().compile_to_plan_list(defn)
        assert plan[1]["args"]["session_path"] == {
            "__binding__": True,
            "from_step": "a",
            "path": "artifacts.session_path",
        }

    def test_compiled_plan_has_outputs_field(self):
        steps = (
            PipelineStep(step_id="a", tool_name="mcp_investigation_start", args_template={}, description="A",
                         outputs={"session_path": "artifacts.session_path"}),
        )
        defn = PipelineDefinition(pipeline_id="test_pipeline", version="1.0", name="T", description="", steps=steps)
        plan = PipelineCompiler().compile_to_plan_list(defn)
        assert plan[0]["outputs"] == {"session_path": "artifacts.session_path"}

    def test_binding_from_unknown_step_rejected(self):
        defn = self._two_step_def(b_args={"x": ArgBinding(from_step="nonexistent", path="artifacts.foo")})
        with pytest.raises(PipelineCompileError, match="unknown step"):
            PipelineCompiler().compile_to_plan_list(defn)

    def test_binding_to_predecessor_is_valid(self):
        """a depends on b and binds to b — b precedes a, so this is valid."""
        steps = (
            PipelineStep(step_id="a", tool_name="mcp_investigation_start",
                         args_template={"x": ArgBinding(from_step="b", path="artifacts.foo")},
                         description="A", depends_on=("b",)),
            PipelineStep(step_id="b", tool_name="mcp_investigation_filemap", args_template={}, description="B"),
        )
        defn = PipelineDefinition(pipeline_id="test_pipeline", version="1.0", name="T", description="", steps=steps)
        plan = PipelineCompiler().compile_to_plan_list(defn)
        assert plan[0]["id"] == "b"
        assert plan[1]["id"] == "a"

    def test_binding_forward_reference_requires_cycle_is_rejected(self):
        """A references B's output but B depends on A → cycle → rejected."""
        steps = (
            PipelineStep(step_id="a", tool_name="mcp_investigation_start",
                         args_template={"x": ArgBinding(from_step="b", path="artifacts.foo")},
                         description="A", depends_on=("b",)),
            PipelineStep(step_id="b", tool_name="mcp_investigation_filemap", args_template={},
                         description="B", depends_on=("a",)),
        )
        defn = PipelineDefinition(pipeline_id="test_pipeline", version="1.0", name="T", description="", steps=steps)
        with pytest.raises(PipelineCompileError, match="cycle"):
            PipelineCompiler().compile_to_plan_list(defn)

    def test_binding_non_dependency_rejected(self):
        """from_step exists and precedes, but is not listed in depends_on."""
        steps = (
            PipelineStep(step_id="a", tool_name="mcp_investigation_start", args_template={}, description="A"),
            PipelineStep(step_id="b", tool_name="mcp_investigation_filemap",
                         args_template={"x": ArgBinding(from_step="a", path="artifacts.foo")},
                         description="B", depends_on=()),  # depends_on missing "a"
        )
        defn = PipelineDefinition(pipeline_id="test_pipeline", version="1.0", name="T", description="", steps=steps)
        with pytest.raises(PipelineCompileError, match="not listed in depends_on"):
            PipelineCompiler().compile_to_plan_list(defn)

    def test_binding_self_reference_rejected(self):
        steps = (
            PipelineStep(step_id="a", tool_name="mcp_investigation_start",
                         args_template={"x": ArgBinding(from_step="a", path="artifacts.foo")},
                         description="A"),
        )
        defn = PipelineDefinition(pipeline_id="test_pipeline", version="1.0", name="T", description="", steps=steps)
        with pytest.raises(PipelineCompileError, match="references itself"):
            PipelineCompiler().compile_to_plan_list(defn)

    def test_unresolved_session_path_rejected(self):
        """${session_path} in a pipeline template is now an error — use bind: instead."""
        steps = (
            PipelineStep(step_id="a", tool_name="mcp_investigation_filemap",
                         args_template={"session_path": "${session_path}"},
                         description="A"),
        )
        defn = PipelineDefinition(pipeline_id="test_pipeline", version="1.0", name="T", description="", steps=steps)
        with pytest.raises(PipelineCompileError, match="unresolved.*session_path"):
            PipelineCompiler().compile_to_plan_list(defn)


class TestArgBindingLoader:
    """Loader-level binding parsing tests."""

    def _write_yaml(self, content: dict) -> Path:
        import tempfile
        f = tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False, encoding="utf-8")
        yaml.dump(content, f)
        f.flush()
        f.close()
        return Path(f.name)

    def test_loader_parses_bind_tag(self):
        path = self._write_yaml({
            "pipeline_id": "investigation",
            "version": "1.1.0",
            "name": "Test",
            "steps": [
                {"step_id": "start", "tool_name": "mcp_investigation_start", "description": "A",
                 "outputs": {"session_path": "artifacts.session_path"}},
                {"step_id": "filemap", "tool_name": "mcp_investigation_filemap", "description": "B",
                 "depends_on": ["start"],
                 "args": {"session_path": {"bind": {"from_step": "start", "path": "artifacts.session_path"}}}},
            ],
        })
        loader = PipelineLoader()
        defn = loader.load_file(path)
        binding = defn.steps[1].args_template["session_path"]
        assert isinstance(binding, ArgBinding)
        assert binding.from_step == "start"
        assert binding.path == "artifacts.session_path"
        assert defn.steps[0].outputs == {"session_path": "artifacts.session_path"}

    def test_loader_rejects_deep_binding_path(self):
        path = self._write_yaml({
            "pipeline_id": "investigation",
            "version": "1.0.0",
            "name": "Test",
            "steps": [
                {"step_id": "a", "tool_name": "mcp_investigation_start", "description": "A"},
                {"step_id": "b", "tool_name": "mcp_investigation_filemap", "description": "B",
                 "depends_on": ["a"],
                 "args": {"x": {"bind": {"from_step": "a", "path": "artifacts.deep.nested"}}}},
            ],
        })
        with pytest.raises(PipelineLoadError, match="deep paths are not supported"):
            PipelineLoader().load_file(path)

    def test_loader_rejects_malformed_bind_missing_path(self):
        path = self._write_yaml({
            "pipeline_id": "investigation",
            "version": "1.0.0",
            "name": "Test",
            "steps": [
                {"step_id": "a", "tool_name": "mcp_investigation_start", "description": "A"},
                {"step_id": "b", "tool_name": "mcp_investigation_filemap", "description": "B",
                 "depends_on": ["a"],
                 "args": {"x": {"bind": {"from_step": "a"}}}},  # missing path
            ],
        })
        with pytest.raises(PipelineLoadError, match="malformed binding"):
            PipelineLoader().load_file(path)

    def test_plain_dict_without_bind_key_not_treated_as_binding(self):
        """A dict WITHOUT a 'bind' key is loaded as a normal nested arg, not a binding."""
        path = self._write_yaml({
            "pipeline_id": "investigation",
            "version": "1.0.0",
            "name": "Test",
            "steps": [
                {"step_id": "a", "tool_name": "mcp_commit_memory", "description": "A",
                 "args": {"metadata": {"source": "my_source"}}},
            ],
        })
        defn = PipelineLoader().load_file(path)
        assert defn.steps[0].args_template["metadata"] == {"source": "my_source"}

    def test_investigation_template_uses_bindings(self):
        """Migrated investigation.yaml loads with ArgBinding objects in steps 1-4."""
        loader = PipelineLoader()
        defn = loader.load("investigation")
        assert defn.version == "1.1.0"
        assert defn.steps[0].outputs == {"session_path": "artifacts.session_path"}
        for step in defn.steps[1:]:
            binding = step.args_template.get("session_path")
            assert isinstance(binding, ArgBinding), f"step {step.step_id} missing binding"
            assert binding.from_step == "start_investigation"
            assert binding.path == "artifacts.session_path"

    def test_patch_plan_uses_bind_syntax(self):
        """patch_plan.yaml uses bind: syntax for session_path (migrated from ${session_path})."""
        loader = PipelineLoader()
        defn = loader.load("patch_plan")
        assert defn.steps[0].outputs == {"session_path": "artifacts.session_path"}
        for step in defn.steps[1:]:
            binding = step.args_template.get("session_path")
            assert isinstance(binding, ArgBinding), f"step {step.step_id} missing binding"
            assert binding.from_step == "start_investigation"
            assert binding.path == "artifacts.session_path"


class TestPublicCapabilityDict:
    def test_source_path_stripped(self):
        from orchestrator.adapters import _to_public_capability_dict
        from orchestrator.capabilities.models import CapabilityManifest, CapabilityType

        m = CapabilityManifest(
            capability_id="test",
            capability_type=CapabilityType.ADAPTER,
            version="1.0",
            name="T",
            description="",
            risk_tier="T1",
            source_path="/etc/secret/path",
        )
        result = _to_public_capability_dict(m)
        assert "source_path" not in result
        assert result["capability_id"] == "test"
