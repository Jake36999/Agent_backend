import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { test } from "node:test";

import { CONTRACTS } from "../src/contracts.mjs";

const manifestPath = resolve(fileURLToPath(new URL(".", import.meta.url)), "..", "..", "tool_manifest.json");
const manifest = JSON.parse(readFileSync(manifestPath, "utf8"));

function toolById(toolId) {
  return manifest.tools.find((tool) => tool.tool_id === toolId);
}

test("manifest entries cover public Node contracts and use valid scaffold fields", () => {
  const contractNames = new Set(CONTRACTS.map((contract) => contract.name));
  const manifestNames = new Set(manifest.tools.map((tool) => tool.tool_id));

  for (const name of contractNames) {
    assert.ok(manifestNames.has(name), `missing manifest entry for ${name}`);
  }

  for (const tool of manifest.tools) {
    assert.equal(typeof tool.tool_id, "string");
    assert.equal(typeof tool.display_name, "string");
    assert.equal(typeof tool.description, "string");
    assert.equal(typeof tool.input_schema, "object");
    assert.equal(typeof tool.dispatcher, "string");
    assert.equal(Array.isArray(tool.surfaces), true);
    assert.equal(typeof tool.default_exposed_to_lmstudio, "boolean");
    assert.equal(typeof tool.risk_level, "string");
    assert.equal(typeof tool.requires_active_partition, "boolean");
    assert.equal(typeof tool.requires_allowed_root, "boolean");
    assert.equal(typeof tool.version, "string");
    assert.ok(["read_only", "write_memory", "write_files", "admin"].includes(tool.risk_level));
    for (const surface of tool.surfaces) {
      assert.ok(["node-mcp", "fastmcp", "python-daemon", "internal"].includes(surface));
    }
    if (tool.tool_id === "mcp_agent_workflow_run") {
      assert.equal(tool.default_exposed_to_lmstudio, true);
      assert.ok(tool.output_schema);
    } else {
      assert.equal(tool.default_exposed_to_lmstudio, false);
    }
    if (tool.tool_id === "mcp_set_active_project_manual") {
      assert.equal(tool.default_exposed_to_lmstudio, false);
      assert.equal(tool.internal_only, true);
    }
  }
});

test("manifest only contains tools that are in contracts or explicitly internal", () => {
  const contractNames = new Set(CONTRACTS.map((contract) => contract.name));
  for (const tool of manifest.tools) {
    const inContracts = contractNames.has(tool.tool_id);
    const internalOnly = tool.internal_only === true;
    const internalSurfaceOnly = Array.isArray(tool.surfaces) && tool.surfaces.every((surface) => surface === "python-daemon" || surface === "internal");
    assert.ok(inContracts || internalOnly || internalSurfaceOnly, `tool ${tool.tool_id} must exist in contracts or be internal`);
  }
});

test("workflow manifest output schema is compact", () => {
  const workflow = toolById("mcp_agent_workflow_run");
  assert.ok(workflow);
  assert.equal(workflow.output_schema.type, "object");
  assert.equal(workflow.output_schema.additionalProperties, false);
  assert.deepEqual(workflow.output_schema.required, ["ok", "status", "summary", "artifacts"]);
  assert.equal(workflow.output_schema.properties.error.type.includes("null"), true);
});
