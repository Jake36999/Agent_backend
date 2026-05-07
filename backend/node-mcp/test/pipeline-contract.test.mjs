import assert from "node:assert/strict";
import { test } from "node:test";

import { CONTRACTS, validateToolInput } from "../src/contracts.mjs";

test("mcp_pipeline_run is not in public contracts", () => {
  assert.equal(CONTRACTS.find((c) => c.name === "mcp_pipeline_run"), undefined);
});

test("mcp_agent_workflow_run rejects invalid pipeline_id", () => {
  const result = validateToolInput("mcp_agent_workflow_run", {
    objective: "audit",
    target_repo: "/tmp/repo",
    pipeline_id: "../bad",
  });
  assert.equal(result.ok, false);
});

test("mcp_agent_workflow_run accepts valid pipeline_id with pipeline_vars", () => {
  const result = validateToolInput("mcp_agent_workflow_run", {
    objective: "audit",
    target_repo: "/tmp/repo",
    pipeline_id: "investigation",
    pipeline_vars: { max_chars: "4000" },
  });
  assert.equal(result.ok, true);
});

test("mcp_agent_workflow_run rejects pipeline_vars with non-string value", () => {
  const result = validateToolInput("mcp_agent_workflow_run", {
    objective: "audit",
    target_repo: "/tmp/repo",
    pipeline_id: "investigation",
    pipeline_vars: { max_chars: 4000 },
  });
  assert.equal(result.ok, false);
});

test("mcp_agent_workflow_run rejects pipeline_id exceeding maxLength", () => {
  const result = validateToolInput("mcp_agent_workflow_run", {
    objective: "audit",
    target_repo: "/tmp/repo",
    pipeline_id: "a".repeat(65),
  });
  assert.equal(result.ok, false);
});
