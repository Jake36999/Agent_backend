import assert from "node:assert/strict";
import { test } from "node:test";

import { makeToolResult } from "../src/server.mjs";

test("invalid tool input is returned as a model-observable error result", async () => {
  const result = await makeToolResult("mcp_semantic_search", { project_id: "p" }, async () => {
    throw new Error("bridge should not run");
  });

  assert.equal(result.isError, true);
  assert.equal(result.structuredContent.ok, false);
  assert.equal(result.structuredContent.error, "schema_validation_failed");
});

test("valid tool input is forwarded to bridge", async () => {
  const result = await makeToolResult("mcp_semantic_search", { project_id: "p", query: "q" }, async (name, args) => {
    return { ok: true, name, args };
  });

  assert.equal(result.isError, false);
  assert.equal(result.structuredContent.name, "mcp_semantic_search");
  assert.equal(result.structuredContent.args.query, "q");
});
