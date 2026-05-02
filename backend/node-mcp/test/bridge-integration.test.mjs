import assert from "node:assert/strict";
import net from "node:net";
import { test } from "node:test";

import { bridgeCall, buildAuthEnvelope } from "../src/bridge.mjs";
import { makeToolResult } from "../src/server.mjs";

test("default bridge refuses runtime stub mode without a Python bridge path", async () => {
  const previous = process.env.ALETHEIA_PYTHON_BRIDGE;
  delete process.env.ALETHEIA_PYTHON_BRIDGE;
  await assert.rejects(() => bridgeCall("mcp_scout_workspace", { project_id: "p" }), /ALETHEIA_PYTHON_BRIDGE/);
  if (previous !== undefined) process.env.ALETHEIA_PYTHON_BRIDGE = previous;
});

test("tools call reaches Python JSON-RPC bridge path", async () => {
  const seen = [];
  const server = net.createServer((socket) => {
    let buffer = "";
    socket.on("data", (chunk) => {
      buffer += chunk.toString("utf8");
      const line = buffer.split(/\r?\n/)[0];
      if (!line) return;
      const request = JSON.parse(line);
      seen.push(request);
      socket.write(JSON.stringify({
        jsonrpc: "2.0",
        id: request.id,
        result: { ok: true, python: true, params: request.params },
      }) + "\n");
    });
  });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const address = server.address();
  const path = `tcp://127.0.0.1:${address.port}`;
  const previous = process.env.ALETHEIA_PYTHON_BRIDGE;
  process.env.ALETHEIA_PYTHON_BRIDGE = path;
  try {
    const result = await makeToolResult("mcp_scout_workspace", { project_id: "p", absolute_path: "C:/x" });
    assert.equal(result.isError, false);
    assert.equal(result.structuredContent.python, true);
    assert.equal(seen[0].method, "tools.call");
    assert.equal(seen[0].params.toolName, "mcp_scout_workspace");
  } finally {
    if (previous === undefined) delete process.env.ALETHEIA_PYTHON_BRIDGE;
    else process.env.ALETHEIA_PYTHON_BRIDGE = previous;
    await new Promise((resolve) => server.close(resolve));
  }
});

test("bridge rejects with a clear timeout error", async () => {
  const server = net.createServer((socket) => {
    socket.on("data", () => {
      // Hold the connection open without responding.
    });
  });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const address = server.address();
  try {
    await assert.rejects(
      () => bridgeCall(
        "mcp_scout_workspace",
        { project_id: "p" },
        null,
        { bridgePath: `tcp://127.0.0.1:${address.port}`, timeoutMs: 20 },
      ),
      /Python bridge request timed out/,
    );
  } finally {
    await new Promise((resolve) => server.close(resolve));
  }
});

test("bridge includes configured HMAC auth envelope in JSON-RPC params", async () => {
  const seen = [];
  const server = net.createServer((socket) => {
    socket.on("data", (chunk) => {
      const request = JSON.parse(chunk.toString("utf8").split(/\r?\n/)[0]);
      seen.push(request);
      socket.write(JSON.stringify({ jsonrpc: "2.0", id: request.id, result: { ok: true } }) + "\n");
    });
  });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const address = server.address();
  const previous = process.env.ALETHEIA_BRIDGE_SECRET;
  process.env.ALETHEIA_BRIDGE_SECRET = "secret";
  try {
    await bridgeCall("mcp_scout_workspace", { project_id: "p" }, null, {
      bridgePath: `tcp://127.0.0.1:${address.port}`,
      timeoutMs: 1000,
    });
    assert.equal(typeof seen[0].params.auth.timestamp, "string");
    assert.equal(typeof seen[0].params.auth.signature, "string");
    assert.equal(typeof seen[0].params.auth.nonce, "string");
    assert.match(seen[0].params.auth.signature, /^[a-f0-9]{64}$/);
  } finally {
    if (previous === undefined) delete process.env.ALETHEIA_BRIDGE_SECRET;
    else process.env.ALETHEIA_BRIDGE_SECRET = previous;
    await new Promise((resolve) => server.close(resolve));
  }
});
