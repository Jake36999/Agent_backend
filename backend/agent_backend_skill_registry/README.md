# Agent Backend Core Skill Pack v0.1.0

This is a metadata-first, backend-native drop-in skill pack for `agent_backend`. It is designed for a headless Python/Node MCP runtime that validates strict manifests, selects skills by trigger/capability, lazy-loads `SKILL.md` only after selection, and enforces trust tiers before execution.

## Contents

- `manifest.schema.json` - strict schema for every `skill.json`
- `PACK_MANIFEST.json` - pack metadata and compatibility assumptions
- `SKILL_INDEX.json` - flat selector index for fast matching
- `TRUST_TIERS.md` - T1-T5 trust vocabulary
- `skills/*/skill.json` - registry source of truth
- `skills/*/SKILL.md` - lazy-loaded instruction payload
- `skills/*/example_input.json` and `example_output.json`
- `VALIDATION_REPORT.md` - generated validation status

## Design boundaries

- No UI or frontend artifacts.
- No autonomous git commit, push, deploy, or destructive filesystem operations.
- Diff generation is separate from approved diff application.
- Memory writes must be evidence-backed.
- Skill crystallisation produces candidate skills only; activation requires human/backend approval.

## Drop-in expectation

Place this folder under the configured local skill directory for `agent_backend`. The backend importer should load `skill.json`, validate it against `manifest.schema.json`, store the manifest in `skill_manifests`, and lazy-load `SKILL.md` only after the selector chooses a verified skill.
