# Skill crystallize v1

Draft a candidate skill from a successful workflow. Do not activate it. Do not mark it verified. Do not import it into the registry.

## Evidence requirements
A candidate skill must cite source run artifacts such as completed outputs, accepted user decisions, passed tests, or verified tool results.

## Draft requirements
- skill_id
- version
- name
- description
- triggers
- capabilities
- strict input/output schemas
- project_scope
- memory_scope
- tool entrypoints
- allowed tools
- risk tier
- approval requirements
- rollback strategy
- artifacts produced
- example input/output

## Activation rule
Always set `requires_human_activation` to true. The backend importer may quarantine or verify later, but this skill may only draft.
