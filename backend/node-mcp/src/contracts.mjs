const DRAFT7 = "http://json-schema.org/draft-07/schema#";

export const CONTRACTS = [
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
    name: "mcp_commit_memory",
    description: "Commit a bounded memory record to the active LM Studio partition.",
    strict: true,
    inputSchema: {
      $schema: DRAFT7,
      type: "object",
      additionalProperties: false,
      properties: {
        category: {
          type: "string",
          enum: ["architecture", "decision", "summary", "bug_fix", "preference", "artifact"],
        },
        content: { type: "string", minLength: 10, maxLength: 8000 },
        confidence_score: { type: "number", minimum: 0.0, maximum: 1.0, default: 1.0 },
        metadata: { type: "object", additionalProperties: true },
      },
      required: ["category", "content"],
    },
  },
  {
    name: "mcp_agent_workflow_run",
    description: "Run the deterministic LM Studio-facing workflow controller.",
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
        pipeline_id: { type: "string", pattern: "^[a-z][a-z0-9_]*$", maxLength: 64 },
        pipeline_vars: { type: "object", maxProperties: 20, additionalProperties: { type: "string", maxLength: 2000 } },
      },
      required: ["objective", "target_repo"],
    },
  },
  {
    name: "mcp_get_active_partition",
    description: "Return the current active LM Studio partition from SQLite state.",
    strict: true,
    inputSchema: {
      $schema: DRAFT7,
      type: "object",
      additionalProperties: false,
      properties: {},
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
    name: "mcp_list_memory_projects",
    description: "List known LM Studio memory projects from SQLite state.",
    strict: true,
    inputSchema: {
      $schema: DRAFT7,
      type: "object",
      additionalProperties: false,
      properties: {},
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
    name: "mcp_semantic_search_active",
    description: "Run semantic search within the active LM Studio partition only.",
    strict: true,
    inputSchema: {
      $schema: DRAFT7,
      type: "object",
      additionalProperties: false,
      properties: {
        query: { type: "string", minLength: 1 },
        k: { type: "integer", minimum: 1, maximum: 50, default: 8 },
      },
      required: ["query"],
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
    name: "mcp_set_active_partition",
    description: "Set the active LM Studio partition from a conversation path.",
    strict: true,
    inputSchema: {
      $schema: DRAFT7,
      type: "object",
      additionalProperties: false,
      properties: {
        conversation_path: { type: "string", minLength: 1 },
      },
      required: ["conversation_path"],
    },
  },
  {
    name: "mcp_set_active_project_manual",
    description: "Manually override the active LM Studio project for admin/debug use.",
    strict: true,
    inputSchema: {
      $schema: DRAFT7,
      type: "object",
      additionalProperties: false,
      properties: {
        project_id: { type: "string", minLength: 1 },
        display_name: { type: "string", minLength: 1 },
      },
      required: ["project_id"],
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
  {
    name: "mcp_code_intelligence",
    description: "Analyze a repository for code maps, dependency graphs, repo context summaries, or Mermaid diagrams.",
    strict: true,
    inputSchema: {
      $schema: DRAFT7,
      type: "object",
      additionalProperties: false,
      properties: {
        target_repo: { type: "string", minLength: 1 },
        mode: { type: "string", enum: ["code_map", "dependency_graph", "repo_context", "mermaid"] },
        max_files: { type: "integer", minimum: 1, maximum: 2000 },
        max_edges: { type: "integer", minimum: 1, maximum: 2000 },
        max_chars: { type: "integer", minimum: 100, maximum: 12000 },
        focus_paths: { type: "array", items: { type: "string", minLength: 1 } },
      },
      required: ["target_repo", "mode"],
    },
  },
  {
    name: "mcp_list_capabilities",
    description: "List registered capabilities from the unified capability registry.",
    strict: true,
    inputSchema: {
      $schema: DRAFT7,
      type: "object",
      additionalProperties: false,
      properties: {
        capability_type: {
          type: "string",
          enum: ["adapter", "sandbox_provider", "indexer", "pipeline_template", "integration_provider"],
        },
        status: {
          type: "string",
          enum: ["verified", "quarantined", "disabled"],
        },
      },
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
  const result = validateObject(contract.inputSchema, args ?? {}, "");
  if (!result.ok) {
    return result;
  }
  if (name === "mcp_set_active_partition") {
    const hasConversation = typeof args?.conversation_path === "string" && args.conversation_path.length > 0;
    if (!hasConversation) {
      return {
        ok: false,
        error: "schema_validation_failed",
        details: [{ path: "", keyword: "required", message: "conversation_path is required" }],
      };
    }
  }
  return result;
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
    if (schema.maxProperties !== undefined && Object.keys(value).length > schema.maxProperties) {
      details.push({ path, keyword: "maxProperties", message: `object has more than ${schema.maxProperties} properties` });
    }
    if (schema.additionalProperties === false) {
      for (const key of Object.keys(value)) {
        if (!Object.hasOwn(properties, key)) {
          details.push({ path: joinPath(path, key), keyword: "additionalProperties", message: `${key} is not allowed` });
        }
      }
    } else if (schema.additionalProperties !== undefined && typeof schema.additionalProperties === "object") {
      for (const [key, val] of Object.entries(value)) {
        if (!Object.hasOwn(properties, key)) {
          details.push(...validateValue(schema.additionalProperties, val, joinPath(path, key)));
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
      if (schema.maxLength !== undefined && value.length > schema.maxLength) {
        details.push({ path, keyword: "maxLength", message: `length must be <= ${schema.maxLength}` });
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
  if (schema.type === "number") {
    if (typeof value !== "number" || Number.isNaN(value)) {
      details.push({ path, keyword: "type", message: "must be number" });
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
