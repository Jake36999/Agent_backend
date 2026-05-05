from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GuardrailResult:
    allowed: bool
    reason: str = ""


class GitGuardrailsService:
    allowed_git_read = {"status", "diff", "log", "show"}
    blocked_git = {"push", "clean"}
    blocked_roots = {"docker", "npm", "yarn", "pnpm", "pip", "uv", "poetry", "env", "set"}
    destructive = {"rm", "rmdir", "del", "remove-item"}

    def check_command(self, argv: list[str] | tuple[str, ...]) -> GuardrailResult:
        if not argv:
            return GuardrailResult(False, "empty command")
        lowered = [str(part).lower() for part in argv]
        root = lowered[0]
        if root == "git":
            subcommand = lowered[1] if len(lowered) > 1 else ""
            if subcommand in self.allowed_git_read:
                return GuardrailResult(True)
            if subcommand == "apply" and "--check" in lowered and not {"--index", "--cached", "--3way"}.intersection(lowered):
                return GuardrailResult(True)
            if subcommand in self.blocked_git or (subcommand == "reset" and "--hard" in lowered):
                return GuardrailResult(False, "blocked git mutation")
            return GuardrailResult(False, "git command is not read-only")
        if root in self.destructive:
            return GuardrailResult(False, "blocked destructive filesystem command")
        if root == "docker" and "compose" in lowered and {"up", "down", "build"}.intersection(lowered):
            return GuardrailResult(False, "blocked deployment command")
        if root in self.blocked_roots:
            return GuardrailResult(False, "blocked mutation or secret-dump command")
        if any(part in {"install", "add"} for part in lowered) and root in {"npm", "yarn", "pnpm", "pip", "uv", "poetry"}:
            return GuardrailResult(False, "blocked dependency installation")
        return GuardrailResult(False, "command is not explicitly allowed")
