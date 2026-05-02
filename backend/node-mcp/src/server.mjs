import { stdin, stdout, stderr } from "node:process";

import { bridgeCall } from "./bridge.mjs";
import { CONTRACTS, validateToolInput } from "./contracts.mjs";

export async function makeToolResult(name, args, bridge = bridgeCall) {
  const validation = validateToolInput(name, args);
  if (!validation.ok) {
    return {
      isError: true,
      content: [{ type: "text", text: JSON.stringify(validation) }],
      structuredContent: { ok: false, ...validation },
    };
  }
  const result = await bridge(name, args);
  return {
    isError: result?.ok === false,
    content: [{ type: "text", text: JSON.stringify(result) }],
    structuredContent: result,
  };
}

export function listTools() {
  return CONTRACTS.map(({ name, description, inputSchema }) => ({ name, description, inputSchema }));
}

export async function handleJsonRpc(message, bridge = bridgeCall) {
  if (message.method === "initialize") {
    return { jsonrpc: "2.0", id: message.id, result: { protocolVersion: "2025-06-18", serverInfo: { name: "aletheia-orchestrator", version: "0.1.0" } } };
  }
  if (message.method === "tools/list") {
    return { jsonrpc: "2.0", id: message.id, result: { tools: listTools() } };
  }
  if (message.method === "tools/call") {
    const name = message.params?.name;
    const args = message.params?.arguments ?? {};
    return { jsonrpc: "2.0", id: message.id, result: await makeToolResult(name, args, bridge) };
  }
  return { jsonrpc: "2.0", id: message.id, error: { code: -32601, message: "Method not found" } };
}

export async function serveStdio() {
  let buffer = "";
  stdin.setEncoding("utf8");
  stdin.on("data", async (chunk) => {
    buffer += chunk;
    const lines = buffer.split(/\r?\n/);
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      if (!line.trim()) continue;
      try {
        const response = await handleJsonRpc(JSON.parse(line));
        stdout.write(`${JSON.stringify(response)}\n`);
      } catch (error) {
        stderr.write(`${String(error)}\n`);
      }
    }
  });
}

if (import.meta.url === `file://${process.argv[1]}`) {
  serveStdio();
}
