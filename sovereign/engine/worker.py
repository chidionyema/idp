"""The sovereign worker: one Temporal Worker process, polling the sovereign
task queue for SessionWorkflow tasks and its three activities. Restarting
this process (or SIGKILL-ing it) never loses a session -- cp1, cp2.
"""
from __future__ import annotations

import asyncio
import logging
import re
import signal

from temporalio.client import Client
from temporalio.worker import Worker

from sovereign import config
from sovereign.engine import activities
from sovereign.engine.workflow import SessionWorkflow

log = logging.getLogger("sovereign.worker")

_BOT_TOKEN_RE = re.compile(config.LOG_BOT_TOKEN_REDACT_PATTERN)


class _RedactBotTokenFilter(logging.Filter):
    """LAW 21: httpx's own INFO line for a chat-bot API call embeds the
    bearer token in the URL path (see the runner registry for which vendor,
    if any, is configured -- this module names none, to stay cp6-clean),
    so the token reaches the log verbatim at INFO. Strip it on every
    record on every handler, not just httpx's -- a token can travel
    formatted into a message on any logger."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str) and "bot" in record.msg:
            record.msg = _BOT_TOKEN_RE.sub("bot<redacted>", record.msg)
        if record.args:
            record.args = tuple(
                _BOT_TOKEN_RE.sub("bot<redacted>", a) if isinstance(a, str) else a for a in record.args
            )
        return True


async def run_worker() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    redact = _RedactBotTokenFilter()
    for handler in logging.getLogger().handlers:
        handler.addFilter(redact)
    # httpx/httpcore log every request at INFO (method + full URL, which for
    # a Telegram call embeds the bot token in the path) -- keep them at
    # WARNING so a token-bearing line is never emitted in the first place;
    # the redaction filter above is the second, independent line of defence
    # for anything else that logs a URL or a formatted message.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    config.ensure_dirs()
    client = await Client.connect(config.TEMPORAL_ADDRESS, namespace=config.TEMPORAL_NAMESPACE)
    worker = Worker(
        client,
        task_queue=config.TEMPORAL_TASK_QUEUE,
        workflows=[SessionWorkflow],
        activities=[activities.run_step, activities.append_receipt, activities.notify_change],
    )
    log.info(
        "sovereign worker starting: address=%s namespace=%s task_queue=%s",
        config.TEMPORAL_ADDRESS,
        config.TEMPORAL_NAMESPACE,
        config.TEMPORAL_TASK_QUEUE,
    )

    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, stop_event.set)
        except NotImplementedError:  # pragma: no cover - non-unix
            pass

    async with worker:
        await stop_event.wait()
    log.info("sovereign worker stopped")


def main() -> None:
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
