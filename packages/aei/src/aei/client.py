"""Bounded, best-effort async emitter. Never blocks agent work on network IO."""

from __future__ import annotations
import json
import queue
import threading
import time
import urllib.request
from .core import make_event


class Emitter:
    def __init__(self, endpoint, token, identity, max_queue=512, timeout=0.4):
        self.endpoint = endpoint.rstrip("/") + "/api/events"
        self.token = token
        self.identity = dict(identity)
        self.q = queue.Queue(maxsize=max_queue)
        self.timeout = timeout
        self.dropped = 0
        self.sent = 0
        self.errors = 0
        self.stop = threading.Event()
        self.worker = threading.Thread(target=self._work, daemon=True)
        self.worker.start()

    def emit(self, event_type, **kwargs):
        try:
            event = make_event(event_type, **self.identity, **kwargs)
            self.q.put_nowait(event)
            return event["event_id"]
        except queue.Full:
            self.dropped += 1
            return None

    def _work(self):
        while not self.stop.is_set() or not self.q.empty():
            try:
                event = self.q.get(timeout=0.1)
            except queue.Empty:
                continue
            try:
                body = json.dumps(event).encode()
                req = urllib.request.Request(  # noqa: S310 - http to the estate's own collector, configured by the caller
                    self.endpoint,
                    data=body,
                    headers={
                        "Authorization": "Bearer " + self.token,
                        "Content-Type": "application/json",
                    },
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=self.timeout) as response:  # noqa: S310 - same endpoint, http scheme only
                    response.read(512)
                self.sent += 1
            except Exception:
                self.errors += 1
            finally:
                self.q.task_done()

    def close(self, timeout=1.0):
        self.stop.set()
        self.worker.join(timeout=timeout)

    def flush(self, timeout=5.0):
        """Wait for the queue to drain, WITHOUT stopping the emitter.

        The verification step needs the events it is about to verify to be in the collector's
        ledger already, and it needs to keep observing afterwards. close() would stop the
        worker, so there is a third door: wait for the queue and carry on.
        """
        deadline = time.monotonic() + timeout
        while not self.q.empty() and time.monotonic() < deadline:
            time.sleep(0.02)
        time.sleep(0.1)
        return self.stats()

    def stats(self):
        return {
            "sent": self.sent,
            "dropped": self.dropped,
            "errors": self.errors,
            "pending": self.q.qsize(),
        }
