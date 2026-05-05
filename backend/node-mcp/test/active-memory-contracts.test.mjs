import assert from "node:assert/strict";
import { test } from "node:test";

import { CONTRACTS, validateToolInput } from "../src/contracts.mjs";

const EXPECTED = [
  "mcp_agent_workflow_run",
  "mcp_commit_memory",
  "mcp_get_active_partition",
  "mcp_list_memory_projects",
  "mcp_semantic_search_active",
  "mcp_set_active_partition",
  "mcp_set_active_project_manual",
];

test("active memory contracts exist and are strict", () => {
  for (const name of EXPECTED) {
    const contract = CONTRACTS.find((item) => item.name === name);
    assert.ok(contract, `missing contract ${name}`);
    assert.equal(contract.strict, true);
    assert.equal(contract.inputSchema.additionalProperties, false);
  }
});

test("active search contract does not expose project_id", () => {
  const contract = CONTRACTS.find((item) => item.name === "mcp_semantic_search_active");
  assert.ok(contract);
  assert.equal(Object.hasOwn(contract.inputSchema.properties, "project_id"), false);
  assert.equal(validateToolInput("mcp_semantic_search_active", { project_id: "p", query: "q" }).ok, false);
});

test("workflow contract exists, is strict, and rejects unknown fields", () => {
  const contract = CONTRACTS.find((item) => item.name === "mcp_agent_workflow_run");
  assert.ok(contract);
  assert.equal(contract.strict, true);
  assert.equal(contract.inputSchema.additionalProperties, false);
  assert.equal(
    validateToolInput("mcp_agent_workflow_run", { objective: "o", target_repo: "C:/tmp", unexpected: true }).ok,
    false
  );
  assert.equal(
    validateToolInput("mcp_agent_workflow_run", { objective: "o", target_repo: "C:/tmp", profile: "safe" }).ok,
    true
  );
});

test("commit memory enforces category enum and content minimum length", () => {
  assert.equal(validateToolInput("mcp_commit_memory", { category: "unknown", content: "abcdefghijkl" }).ok, false);
  assert.equal(validateToolInput("mcp_commit_memory", { category: "decision", content: "short" }).ok, false);
  assert.equal(validateToolInput("mcp_commit_memory", { category: "decision", content: "sufficient content" }).ok, true);
  assert.equal(validateToolInput("mcp_commit_memory", { category: "decision", content: "sufficient content", confidence_score: "bad" }).ok, false);
  assert.equal(validateToolInput("mcp_commit_memory", { category: "decision", content: "sufficient content", confidence_score: -0.1 }).ok, false);
  assert.equal(validateToolInput("mcp_commit_memory", { category: "decision", content: "sufficient content", confidence_score: 1.1 }).ok, false);
});

test("set active partition requires conversation_path only", () => {
  assert.equal(validateToolInput("mcp_set_active_partition", {}).ok, false);
  assert.equal(validateToolInput("mcp_set_active_partition", { conversation_path: "C:/tmp/chat.json" }).ok, true);
  assert.equal(validateToolInput("mcp_set_active_partition", { project_id: "p" }).ok, false);
});
