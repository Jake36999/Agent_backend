import assert from "node:assert/strict";
import { test } from "node:test";

import { CONTRACTS, validateToolInput } from "../src/contracts.mjs";

const TOOL_NAMES = [
  "mcp_investigation_start",
  "mcp_investigation_filemap",
  "mcp_investigation_validate_manifest",
  "mcp_investigation_read_report",
  "mcp_investigation_compile_handoff",
];

test("investigation contracts exist", () => {
  for (const name of TOOL_NAMES) {
    assert.ok(CONTRACTS.find((contract) => contract.name === name));
  }
});

test("investigation contracts enforce required fields and reject unknowns", () => {
  assert.equal(validateToolInput("mcp_investigation_start", { target_repo: "x" }).ok, false);
  assert.equal(validateToolInput("mcp_investigation_filemap", {}).ok, false);
  assert.equal(validateToolInput("mcp_investigation_filemap", { session_path: "s", profile: "unsafe" }).ok, false);
  assert.equal(validateToolInput("mcp_investigation_validate_manifest", {}).ok, false);
  assert.equal(validateToolInput("mcp_investigation_read_report", { session_path: "s" }).ok, false);
  assert.equal(validateToolInput("mcp_investigation_read_report", { session_path: "s", artifact_key: "unknown_key" }).ok, false);
  assert.equal(validateToolInput("mcp_investigation_read_report", { session_path: "s", artifact_key: "manifest_csv", max_chars: 12001 }).ok, false);
  assert.equal(validateToolInput("mcp_investigation_compile_handoff", {}).ok, false);

  const unknown = validateToolInput("mcp_investigation_start", { objective: "o", target_repo: "r", extra: true });
  assert.equal(unknown.ok, false);
  assert.match(JSON.stringify(unknown.details), /additionalProperties/);
});

test("investigation contracts accept valid payloads", () => {
  assert.equal(validateToolInput("mcp_investigation_start", { objective: "o", target_repo: "r", profile: "safe" }).ok, true);
  assert.equal(validateToolInput("mcp_investigation_filemap", { session_path: "s", profile: "safe" }).ok, true);
  assert.equal(validateToolInput("mcp_investigation_validate_manifest", { session_path: "s" }).ok, true);
  assert.equal(validateToolInput("mcp_investigation_read_report", { session_path: "s", artifact_key: "manifest_csv", max_chars: 1000 }).ok, true);
  assert.equal(validateToolInput("mcp_investigation_compile_handoff", { session_path: "s" }).ok, true);
});
