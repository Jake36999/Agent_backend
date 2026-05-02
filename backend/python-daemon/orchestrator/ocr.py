from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .adapters import AdapterFailure
from .shell import CommandSpec, ShellAdapter


Runner = Callable[[str, list[str], float], str]


@dataclass(frozen=True)
class CommandOCRProvider:
    shell_adapter: ShellAdapter
    command: str
    timeout_seconds: float = 30.0
    runner: Runner | None = None

    def extract_image_text(self, absolute_path: str, page: int | None, region: dict[str, int] | None) -> str:
        args = [absolute_path]
        if page is not None:
            args.extend(["--page", str(page)])
        if region is not None:
            args.extend(["--region", ",".join(f"{key}={value}" for key, value in sorted(region.items()))])
        try:
            if self.runner is not None:
                return self.runner(self.command, args, self.timeout_seconds)
            spec = CommandSpec(
                executable=self.command,
                args=tuple(args),
                timeout_seconds=self.timeout_seconds,
            )
            _, stdout, _ = self.shell_adapter.sync_run(spec)
            return stdout
        except Exception as exc:
            raise AdapterFailure(f"OCR extraction failed: {exc}") from exc
