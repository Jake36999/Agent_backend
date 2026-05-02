import assert from "node:assert/strict";
import { test } from "node:test";

import { CONTRACTS, validateToolInput } from "../src/contracts.mjs";

test("mcp_scout_workspace contract is strict and validates expected payload", () => {
  const contract = CONTRACTS.find((item) => item.name === "mcp_scout_workspace");

  assert.ok(contract);
  assert.equal(contract.inputSchema.additionalProperties, false);
  assert.equal(validateToolInput("mcp_scout_workspace", { project_id: "p", absolute_path: "C:/x" }).ok, true);
  const invalid = validateToolInput("mcp_scout_workspace", { project_id: "p", absolute_path: "C:/x", extra: true });
  assert.equal(invalid.ok, false);
  assert.match(JSON.stringify(invalid.details), /additionalProperties/);
});
