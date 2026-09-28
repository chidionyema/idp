"""A surface we poll. IMAP, RSS, legacy APIs, anything that won't push."""

import time

from ..net import open_https, https_request


class PollTransport:
    def __init__(self, url_fn, headers_fn=None, interval=30):
        self.url_fn = url_fn
        self.headers_fn = headers_fn or (lambda: {})
        self.interval = interval
        self.last = time.time()

    def poll(self):
        if time.time() - self.last < self.interval:
            return None
        self.last = time.time()
        req = https_request(self.url_fn(), headers=self.headers_fn())
        with open_https(req, timeout=30) as r:
            return r.read()
