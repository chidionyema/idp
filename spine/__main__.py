"""The spine, as it runs: two commands, one image.

    python -m spine bridge    NATS in, Temporal signals out.
    python -m spine worker    The Temporal side: the observer workflow, served.
    python -m spine describe  What this build is wired to, for the readiness log.

One image, two commands, so the bridge and the worker roll together and cannot drift
apart: a bridge that signals a workflow nobody serves is a bus with nobody listening.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys

# The NATS server the estate's bus runs (platform/event-bus: nats.event-bus.svc:4222).
NATS_URL = os.environ.get("NATS_URL", "nats://nats.event-bus.svc:4222")
# The Temporal frontend (platform/temporal/worker.yaml).
TEMPORAL_ADDRESS = os.environ.get(
    "TEMPORAL_ADDRESS", "temporal-frontend.temporal.svc:7233"
)
TEMPORAL_NAMESPACE = os.environ.get("TEMPORAL_NAMESPACE", "estate")


async def _bridge() -> int:
    import nats

    from .bridge import Bridge
    from .signaller import TemporalSignaller

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    log = logging.getLogger("spine")

    nc = await nats.connect(NATS_URL)
    js = nc.jetstream()
    signaller = await TemporalSignaller.connect(TEMPORAL_ADDRESS, TEMPORAL_NAMESPACE)
    bridge = Bridge(js, signaller, log=log.info)
    try:
        await bridge.run()
    finally:
        await nc.close()
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="spine",
        description="The event spine: Flux -> NATS -> Temporal -> receipt.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("bridge", help="consume flux events and signal workflows")
    sub.add_parser("worker", help="serve the observer workflow")
    sub.add_parser("describe", help="print what this build is wired to")
    args = parser.parse_args(argv)

    if args.command == "bridge":
        return asyncio.run(_bridge())
    if args.command == "worker":
        from .worker import main as worker_main

        worker_main()
        return 0
    if args.command == "describe":
        from .bridge import describe

        sys.stdout.write(describe() + "\n")
        return 0
    return 2


if __name__ == "__main__":  # pragma: no cover - module entry
    raise SystemExit(main())
