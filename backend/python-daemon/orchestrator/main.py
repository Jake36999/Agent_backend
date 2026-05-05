from __future__ import annotations

import asyncio

from .bridge_server import serve_tcp_bridge
from .config import RuntimeConfig
from .observability import configure_logging
import logging
from pathlib import Path

from .runtime import build_runtime
from .worker import DaemonWorker

from orchestrator.skills.importer import SkillImporter
from orchestrator.skills.registry import SkillRegistry


def maybe_import_skills(config: RuntimeConfig, queue_db_path: Path) -> dict | None:
    if not config.skill_registry_root:
        return None

    registry_root = Path(config.skill_registry_root)
    queue_db_path.parent.mkdir(parents=True, exist_ok=True)
    registry = SkillRegistry(queue_db_path)
    return SkillImporter(registry_root, registry).import_all()


async def amain() -> None:
    config = RuntimeConfig.from_env()
    configure_logging(config.log_level)

    runtime = build_runtime(config)
    import_report = maybe_import_skills(config, runtime.repo.queue_db)
    if import_report:
        logging.getLogger("aletheia").info(f"Skill import report: {import_report}")

    bridge = await serve_tcp_bridge(
        config.bridge_host,
        config.bridge_port,
        runtime.tool_adapters,
        runtime.bridge_security,
        runtime,
    )
    stop_event = asyncio.Event()
    worker = DaemonWorker(
        runtime.repo,
        runtime.tool_adapters,
        project_id=config.project_id,
        worker_id=config.worker_id,
        lease_seconds=config.lease_seconds,
        idle_sleep_seconds=config.idle_sleep_seconds,
    )
    try:
        await asyncio.gather(bridge.serve_forever(), worker.run_forever(stop_event))
    finally:
        stop_event.set()
        bridge.close()
        await bridge.wait_closed()
        runtime.close()


def main() -> None:
    asyncio.run(amain())


if __name__ == "__main__":
    main()
