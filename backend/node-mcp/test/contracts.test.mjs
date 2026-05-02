import assert from "node:assert/strict";
import { test } from "node:test";

import { CONTRACTS, validateToolInput } from "../src/contracts.mjs";

test("contracts are deterministic and strict host metadata is outside input schema", () => {
  const names = CONTRACTS.map((contract) => contract.name);
  assert.deepEqual(names, [...names].sort());
  for (const contract of CONTRACTS) {
    assert.equal(contract.strict, true);
    assert.equal(contract.inputSchema.additionalProperties, false);
    assert.equal(Object.hasOwn(contract.inputSchema, "strict"), false);
  }
});

test("schema validation returns structured exact failures", () => {
  const result = validateToolInput("mcp_semantic_search", { project_id: "p", extra: true });

  assert.equal(result.ok, false);
  assert.equal(result.error, "schema_validation_failed");
  assert.match(JSON.stringify(result.details), /query/);
  assert.match(JSON.stringify(result.details), /additionalProperties/);
});
