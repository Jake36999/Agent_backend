const DRAFT7 = "http://json-schema.org/draft-07/schema#";

export const CONTRACTS = [
  {
    name: "mcp_agent_workflow_run",
    description: "Run the deterministic high-level Tool Assist workflow controller once. target_repo must be an existing absolute local path.",
    strict: true,
    inputSchema: {
      $schema: DRAFT7,
      type: "object",
      additionalProperties: false,
      properties: {
        objective: { type: "string", minLength: 1 },
        target_repo: { type: "string", minLength: 1 },
        profile: { type: "string", enum: ["safe"], default: "safe" },
        allow_ingest: { type: "boolean", default: false },
        include_report_preview: { type: "boolean", default: false },
        use_model_phases: { type: "boolean", default: false },
      },
      required: ["objective", "target_repo"],
    },
  },
  {
    name: "mcp_extract_image",
    description: "Run OCR fallback against non-selectable text content.",
    strict: true,
    inputSchema: {
      $schema: DRAFT7,
      type: "object",
      additionalProperties: false,
      properties: {
        absolute_path: { type: "string", minLength: 1 },
        page: { type: "integer", minimum: 1 },
        region: {
          type: "object",
          additionalProperties: false,
          properties: {
            x: { type: "integer", minimum: 0 },
            y: { type: "integer", minimum: 0 },
            width: { type: "integer", minimum: 1 },
            height: { type: "integer", minimum: 1 },
          },
          required: ["x", "y", "width", "height"],
        },
      },
      required: ["absolute_path"],
    },
  },
  {
    name: "mcp_investigation_start",
    description: "Start a safe external ToolSet investigation session.",
    strict: true,
    inputSchema: {
      $schema: DRAFT7,
      type: "object",
      additionalProperties: false,
      properties: {
        objective: { type: "string", minLength: 1 },
        target_repo: { type: "string", minLength: 1 },
        profile: { type: "string", enum: ["safe"] },
      },
      required: ["objective", "target_repo"],
    },
  },
  {
    name: "mcp_investigation_filemap",
    description: "Build constrained file map summaries for an investigation session.",
    strict: true,
    inputSchema: {
      $schema: DRAFT7,
      type: "object",
      additionalProperties: false,
      properties: {
        session_path: { type: "string", minLength: 1 },
        profile: { type: "string", enum: ["safe"] },
      },
      required: ["session_path"],
    },
  },
  {
    name: "mcp_investigation_validate_manifest",
    description: "Validate a ToolSet investigation manifest.",
    strict: true,
    inputSchema: {
      $schema: DRAFT7,
      type: "object",
      additionalProperties: false,
      properties: {
        session_path: { type: "string", minLength: 1 },
      },
      required: ["session_path"],
    },
  },
  {
    name: "mcp_investigation_read_report",
    description: "Read bounded investigation report content from ToolSet artifacts.",
    strict: true,
    inputSchema: {
      $schema: DRAFT7,
      type: "object",
      additionalProperties: false,
      properties: {
        session_path: { type: "string", minLength: 1 },
        artifact_key: { type: "string", enum: ["manifest_csv", "manifest_health_json", "manifest_doctor_json", "manifest_doctor_md", "command_lint_json", "slicer_json", "slicer_md", "final_markdown", "final_python_bundle", "archive_yaml"] },
        max_chars: { type: "integer", minimum: 1, maximum: 12000 },
      },
      required: ["session_path", "artifact_key"],
    },
  },
  {
    name: "mcp_investigation_compile_handoff",
    description: "Compile investigation handoff metadata and artifact paths.",
    strict: true,
    inputSchema: {
      $schema: DRAFT7,
      type: "object",
      additionalProperties: false,
      properties: {
        session_path: { type: "string", minLength: 1 },
      },
      required: ["session_path"],
    },
  },
  {
    name: "mcp_ingest_target",
    description: "Route a local file to PDFProcessor or CodebaseProcessor by MIME type.",
    strict: true,
    inputSchema: {
      $schema: DRAFT7,
      type: "object",
      additionalProperties: false,
      properties: {
        project_id: { type: "string", minLength: 1 },
        absolute_path: { type: "string", minLength: 1 },
        mime_type: { type: "string", minLength: 1 },
        force_reindex: { type: "boolean", default: false },
      },
      required: ["project_id", "absolute_path"],
    },
  },
  {
    name: "mcp_semantic_search",
    description: "Run cosine similarity search inside an isolated project namespace.",
    strict: true,
    inputSchema: {
      $schema: DRAFT7,
      type: "object",
      additionalProperties: false,
      properties: {
        project_id: { type: "string", minLength: 1 },
        query: { type: "string", minLength: 1 },
        k: { type: "integer", minimum: 1, maximum: 50, default: 8 },
      },
      required: ["project_id", "query"],
    },
  },
  {
    name: "mcp_scout_workspace",
    description: "Return a deterministic read-only workspace scout without indexing vectors.",
    strict: true,
    inputSchema: {
      $schema: DRAFT7,
      type: "object",
      additionalProperties: false,
      properties: {
        project_id: { type: "string", minLength: 1 },
        absolute_path: { type: "string", minLength: 1 },
        max_files: { type: "integer", minimum: 1, maximum: 5000, default: 500 },
        include_summaries: { type: "boolean", default: true },
      },
      required: ["project_id", "absolute_path"],
    },
  },
  {
    name: "mcp_verify_integrity",
    description: "Verify a file against expected metadata and cryptographic hashes.",
    strict: true,
    inputSchema: {
      $schema: DRAFT7,
      type: "object",
      additionalProperties: false,
      properties: {
        absolute_path: { type: "string", minLength: 1 },
        expected_sha256: { type: "string", pattern: "^[a-fA-F0-9]{64}$" },
        expected_metadata_hash: { type: "string", minLength: 1 },
      },
      required: ["absolute_path", "expected_sha256", "expected_metadata_hash"],
    },
  },
].sort((a, b) => a.name.localeCompare(b.name));

export function findContract(name) {
  return CONTRACTS.find((contract) => contract.name === name);
}

export function validateToolInput(name, args) {
  const contract = findContract(name);
  if (!contract) {
    return { ok: false, error: "unknown_tool", details: [{ message: `Unknown tool: ${name}` }] };
  }
  return validateObject(contract.inputSchema, args ?? {}, "");
}

function validateObject(schema, value, path) {
  const details = [];
  if (schema.type === "object") {
    if (!value || typeof value !== "object" || Array.isArray(value)) {
      return { ok: false, error: "schema_validation_failed", details: [{ path, keyword: "type", message: "must be object" }] };
    }
    const properties = schema.properties ?? {};
    for (const required of schema.required ?? []) {
      if (!Object.hasOwn(value, required)) {
        details.push({ path: joinPath(path, required), keyword: "required", message: `${required} is required` });
      }
    }
    if (schema.additionalProperties === false) {
      for (const key of Object.keys(value)) {
        if (!Object.hasOwn(properties, key)) {
          details.push({ path: joinPath(path, key), keyword: "additionalProperties", message: `${key} is not allowed` });
        }
      }
    }
    for (const [key, childSchema] of Object.entries(properties)) {
      if (Object.hasOwn(value, key)) {
        details.push(...validateValue(childSchema, value[key], joinPath(path, key)));
      }
    }
  }
  return details.length === 0
    ? { ok: true }
    : { ok: false, error: "schema_validation_failed", details };
}

function validateValue(schema, value, path) {
  if (schema.type === "object") {
    return validateObject(schema, value, path).details ?? [];
  }
  const details = [];
  if (schema.type === "string") {
    if (typeof value !== "string") {
      details.push({ path, keyword: "type", message: "must be string" });
    } else {
      if (schema.minLength && value.length < schema.minLength) {
        details.push({ path, keyword: "minLength", message: `length must be >= ${schema.minLength}` });
      }
      if (schema.pattern && !(new RegExp(schema.pattern).test(value))) {
        details.push({ path, keyword: "pattern", message: `must match ${schema.pattern}` });
      }
      if (schema.enum && !schema.enum.includes(value)) {
        details.push({ path, keyword: "enum", message: `must be one of: ${schema.enum.join(", ")}` });
      }
    }
  }
  if (schema.type === "boolean" && typeof value !== "boolean") {
    details.push({ path, keyword: "type", message: "must be boolean" });
  }
  if (schema.type === "integer") {
    if (!Number.isInteger(value)) {
      details.push({ path, keyword: "type", message: "must be integer" });
    } else {
      if (schema.minimum !== undefined && value < schema.minimum) {
        details.push({ path, keyword: "minimum", message: `must be >= ${schema.minimum}` });
      }
      if (schema.maximum !== undefined && value > schema.maximum) {
        details.push({ path, keyword: "maximum", message: `must be <= ${schema.maximum}` });
      }
    }
  }
  return details;
}

function joinPath(prefix, key) {
  return `${prefix}/${key}`;
}
