import assert from "node:assert/strict";
import { test } from "node:test";

import { CONTRACTS, validateToolInput } from "../src/contracts.mjs";

test("agent workflow run contract exists", () => {
  const contract = CONTRACTS.find((item) => item.name === "mcp_agent_workflow_run");
  assert.ok(contract);
  assert.match(contract.description, /absolute local path/);
});

test("agent workflow run contract is strict and validates profile", () => {
  assert.equal(validateToolInput("mcp_agent_workflow_run", { objective: "o", target_repo: "r", extra: true }).ok, false);
  assert.equal(validateToolInput("mcp_agent_workflow_run", { objective: "o", target_repo: "r", profile: "unsafe" }).ok, false);
  assert.equal(validateToolInput("mcp_agent_workflow_run", { objective: "o" }).ok, false);
});

test("agent workflow run contract accepts compact default payload and booleans", () => {
  assert.equal(validateToolInput("mcp_agent_workflow_run", { objective: "o", target_repo: "r" }).ok, true);
  assert.equal(validateToolInput("mcp_agent_workflow_run", {
    objective: "o",
    target_repo: "r",
    profile: "safe",
    allow_ingest: false,
    include_report_preview: false,
    use_model_phases: false,
  }).ok, true);
});
