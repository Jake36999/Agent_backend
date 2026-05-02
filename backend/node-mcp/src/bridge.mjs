import net from "node:net";
import crypto from "node:crypto";

export function makeJsonRpcRequest(method, params, id = 1) {
  return { jsonrpc: "2.0", id, method, params };
}

export async function bridgeCall(toolName, args, transport = null, options = {}) {
  const sharedSecret = options.auth ?? process.env.ALETHEIA_BRIDGE_SECRET;
  const params = { toolName, args };
  const request = makeJsonRpcRequest("tools.call", params, Date.now());
  if (sharedSecret) {
    request.params.auth = buildAuthEnvelope(request, sharedSecret);
  }
  if (transport) {
    const response = await transport(request);
    return response?.result ?? response;
  }
  const bridgePath = options.bridgePath ?? process.env.ALETHEIA_PYTHON_BRIDGE;
  if (!bridgePath) {
    throw new Error("ALETHEIA_PYTHON_BRIDGE is required for runtime bridge calls");
  }
  return sendJsonRpcLine(bridgePath, request, options.timeoutMs);
}

export function stableStringify(value) {
  if (value === null || typeof value !== "object") return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map((item) => stableStringify(item)).join(",")}]`;
  return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${stableStringify(value[key])}`).join(",")}}`;
}

export function buildAuthEnvelope(request, sharedSecret, timestamp = `${Math.floor(Date.now() / 1000)}`, nonce = crypto.randomUUID()) {
  const sanitized = JSON.parse(JSON.stringify(request));
  if (sanitized.params && typeof sanitized.params === "object") {
    delete sanitized.params.auth;
  }
  const payload = `${timestamp}.${nonce}.${stableStringify(sanitized)}`;
  const signature = crypto.createHmac("sha256", sharedSecret).update(payload).digest("hex");
  return { timestamp, signature, nonce };
}

export function connectNamedPipe(path) {
  if (path.startsWith("tcp://")) {
    const url = new URL(path);
    return net.createConnection({ host: url.hostname, port: Number(url.port) });
  }
  return net.createConnection(path);
}

export function sendJsonRpcLine(path, request, timeoutMs = 30000) {
  return new Promise((resolve, reject) => {
    const socket = connectNamedPipe(path);
    let buffer = "";
    let settled = false;
    const timer = setTimeout(() => {
      if (settled) return;
      settled = true;
      socket.destroy();
      reject(new Error(`Python bridge request timed out after ${timeoutMs}ms`));
    }, timeoutMs);
    function finish(fn, value) {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      fn(value);
    }
    socket.setEncoding("utf8");
    socket.on("error", (error) => finish(reject, error));
    socket.on("connect", () => {
      socket.write(JSON.stringify(request) + "\n");
    });
    socket.on("data", (chunk) => {
      buffer += chunk;
      const newline = buffer.indexOf("\n");
      if (newline < 0) return;
      const line = buffer.slice(0, newline).trim();
      socket.end();
      try {
        const response = JSON.parse(line);
        if (response.error) {
          finish(reject, new Error(response.error.message || "Python bridge error"));
          return;
        }
        finish(resolve, response.result);
      } catch (error) {
        finish(reject, error);
      }
    });
  });
}
