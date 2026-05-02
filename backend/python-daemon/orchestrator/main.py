from __future__ import annotations

import asyncio

from .bridge_server import serve_tcp_bridge
from .config import RuntimeConfig
from .observability import configure_logging
from .runtime import build_runtime
from .worker import DaemonWorker


async def amain() -> None:
    config = RuntimeConfig.from_env()
    configure_logging(config.log_level)
    runtime = build_runtime(config)
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
