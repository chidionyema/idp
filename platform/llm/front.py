#!/usr/bin/env python3
"""The laptop router's front door: 127.0.0.1:4000, forwarding bytes to whichever router slot is
active, and to the cloud router when no laptop slot is answering. It never changes, so it never
restarts on a router deploy.

WHY (2026-10-02). Every router deploy was a stop and a start of the one process on :4000. LiteLLM
takes about 90 s to boot, so every deploy refused every agent for 90 s ("Error: Connection
error." in every pi and Claude Code session; watchdog log 17:03-17:05 and 17:12-17:14 UTC).
Founder: "i dont want to see any more failures". `bin/litellm-local swap` now boots the new
router in the idle slot (4001 or 4002) beside the live one, waits until it answers, and only then
writes its port to the ACTIVE file. This front reads that file for each new connection, so new
requests reach the new router while requests already in flight finish on the old one, which
launchd then stops gracefully.

WHY (2026-10-21). The laptop ran out of memory (load 95, 4 GB in swap) and the router on 4001
went on accepting connections without answering them, so the twin fallback never fired: it only
caught a refused connect. Later that day the router's venv was missing and every slot refused,
with no twin booted. Both times every agent on the laptop lost every model, while the OKE router
(llm.mumchimp.com, which takes the same laptop key) was up. Founder: no laptop overload or OKE
outage may take out every model. So the front now asks each slot /health/liveliness every
PROBE_EVERY seconds; a slot that misses DOWN_AFTER probes in a row (refused, or slower than
PROBE_TIMEOUT) is passed over for new connections until it answers UP_AFTER in a row. With no
laptop slot up, new connections go to CLOUD. With the cloud unreachable too, the laptop slots are
still tried, so an OKE outage never costs the laptop anything. Connections already open stay
where they started; a caller whose router starves mid-request gets its answer on its own retry.

WHY (2026-10-30). The front decided on the answer but had no total budget: it could hold one
caller's request for the cloud's ANSWER_TIMEOUT plus each laptop slot's own lane timeout (600 s
each) -- 22 minutes. Claude Code's patience is 364 s, so on 2026-10-30 three sessions gave up
at once with "Request timed out" while the front went on holding their requests, and the answers
that finally came belonged to callers who had already left. (21 timeout events in the founder's
own seven sessions on 2026-10-28..30; 25 across ten sessions once the four subagent transcripts
the CLI spawned are counted. The machine-readable audit, produced by bin/estate-session-audit, is
docs/audits/2026-10-30-claude-code-session-stalls/.) The front now has ONE budget per
request (ANSWER_BUDGET, 240 s, below the client's patience): every target it may be asked of
shares that budget, and when the budget is spent the caller is told so at once (504) instead of
waiting for an answer it cannot use. A box too loaded to answer inside any budget is refused at
once (503) rather than joined to a queue it cannot serve -- the load reached 701 on 4 CPUs that
day. A laptop slot that did not answer inside the budget is passed over for a while, so the twin
answers the next caller instead of the front spending its whole budget on a dead slot.

WHY (2026-10-28). The OKE router was not answering authenticated requests when this was measured
on 2026-10-28: it took the connection, then stalled until the edge's 60 s proxy timeout answered
504, and on some requests answered 503 with the edge's own "Starting up" page. The front decided
on the CONNECT, so a cloud that accepted and then failed was never passed over: every caller on
the laptop was handed the cloud's 503/504 while a perfectly healthy local slot sat unused. That
is the outage the 2026-10-21 law forbids ("no OKE outage may take out every model"). So the front
now decides on the ANSWER: it holds the request, asks the cloud, and if the answer is a
server-side failure (5xx) or there is no answer at all (a stall past ANSWER_TIMEOUT), it asks
the NEXT target the same question and the caller gets that answer instead of the cloud's
failure. A caller-side failure (4xx) is the caller's own business and is relayed untouched; the
cloud stays the first target (the founder's 2026-10-26 ruling: the cloud is the default route,
the laptop is the fallback), and a cloud that just failed is passed over for CLOUD_DOWN_S seconds
so one outage costs one request the wait and not every request.

WHY (2026-10-30, second half). The cloud is the default route and the laptop is the fallback,
but the cloud does not carry every lane the laptop has: the founder's Claude Code subscription is
his own account, not a key, so the cloud has no claude lane (docs/diagnoses/
2026-10-22-claude-code-403-cloud-has-no-claude-lane.yaml) and must not grow one. So the cloud
answers a Claude Code request with a refusal that NAMES THE MODEL -- measured on the recovery
router on 2026-10-30: HTTP 400 "Invalid model name passed in model=claude-sonnet-4-5. Call
`/v1/models` to view available models for your key." The front relayed that refusal as if it
were the answer, so Claude Code failed at once on a cloud that was perfectly healthy. A refusal
that says the model is not there is not the caller's answer: it is the target saying "not mine",
and the front already passes over a cloud whose key may not carry the model (403,
key_model_access_denied). So the front now reads that refusal too, and asks the next target.

WHY (2026-10-30, third part). The cloud leg forwarded the CALLER's own User-Agent to the
cloud route, which sits behind Cloudflare. Cloudflare's browser-signature rules answer some
client signatures with "403 error code: 1010" BEFORE the request ever reaches the router, and
the front relayed that refusal as if it were the answer: a caller whose own signature the edge
disliked lost every model while a healthy laptop slot sat unused. Measured through the live
front on 127.0.0.1:4000 with one credential and one body: curl/8.7.1 -> 200,
Python-urllib/3.12 -> 403 {"error code: 1010"}, estate-router-front/1.0 -> 200. So the front
now presents ONE stable estate signature of its own to the cloud -- dropping the caller's
header, never appending to it, because two User-Agent headers still carry the caller's
signature -- and it recognises the edge's own refusal by its BODY and passes over the cloud
for that request instead of relaying the edge's refusal as the answer.

WHY (2026-10-29). The pass-over decided WHICH targets were tried but not IN WHAT ORDER: route()
built healthy + [CLOUD] + sick, so a cloud already known not to answer sat AHEAD of the slots
that had merely missed a probe. Under fleet load the slot's 3 s probe missed, the slot was marked
down, and every caller was handed the cloud the front had just proved dead -- 753 requests in a
row, each stalled on it. So a cloud in cooldown is now tried LAST, behind even the sick slots: a
slot that is slow under load still answers, a cloud in cooldown is known not to. The cloud is
still the default route whenever it is answering, so the founder's 2026-10-26 ruling stands.
The record of the reasoning is docs/diagnoses/2026-10-29-the-front-put-the-dead-cloud-first.yaml.

The cloud leg parses the request (head, then body) because a replay needs the request again.
The laptop leg stays bytes only: no parsing, no buffering, exactly as before.
"""

from __future__ import annotations

import asyncio
import os
import pathlib
import re
import ssl
import sys
import time
from urllib.parse import urlsplit

LISTEN = ("127.0.0.1", int(os.environ.get("ESTATE_ROUTER_FRONT_PORT", "4000")))
ACTIVE = pathlib.Path(
    os.environ.get("ESTATE_ROUTER_ACTIVE")
    or pathlib.Path.home() / ".estate/router-state/active"
)
SLOTS = (4001, 4002)
# Empty turns the cloud leg off.
CLOUD = os.environ.get("ESTATE_ROUTER_CLOUD", "https://llm.mumchimp.com")
# The User-Agent the front presents to the cloud route, in place of the caller's own.
# The cloud route sits behind Cloudflare, whose browser-signature rules refuse some client
# signatures with "403 error code: 1010" before the request reaches the router at all.
# Measured on 2026-10-30 through the live front on 127.0.0.1:4000, one credential and one
# body: curl/8.7.1 -> 200, Python-urllib/3.12 -> 403 {"error code: 1010},
# estate-router-front/1.0 -> 200. One stable estate signature is what the edge accepts.
CLOUD_USER_AGENT = "estate-router-front/1.0"
PROBE_EVERY = 2.0
PROBE_TIMEOUT = 3.0
DOWN_AFTER = 2
UP_AFTER = 2
CHUNK = 65536
# The most the front holds of a request, so the same request can be asked of another target.
MAX_BODY = 8 * 1024 * 1024
# The most of an error answer the front reads to judge it.
MAX_ERROR = 65536
# A target that has not answered in this long is treated as failed.
ANSWER_TIMEOUT = 120.0
# How long a target that just failed is passed over. Consecutive failures double it, so a
# cloud that fails slowly (its 503 arrives after 30 s) is not paid for on every request.
CLOUD_DOWN_S = 60.0
CLOUD_DOWN_MAX_S = 600.0
# How long the front waits for the rest of a caller's body before it gives up on a replay.
DRAIN_TIMEOUT = 30.0
# The most the front may spend on ONE caller's request, from the first byte to the answer.
#
# WHY (2026-10-30). The front had no total budget. It tried the cloud for up to ANSWER_TIMEOUT
# and then each laptop slot for as long as that slot's own lane timeout (600 s), so one request
# could hold the front for 120 + 600 + 600 s -- 22 minutes. Claude Code's patience is 364 s.
# Measured over the transcripts of 2026-10-28..30 by bin/estate-session-audit (the audit:
# docs/audits/2026-10-30-claude-code-session-stalls/): 21 "Request timed out" events in the
# founder's own seven sessions, and the gap from the request that went out to the timeout that
# came back lands in a 361.3-374.4 s band on all 21, so the caller had already gone when the
# front finally answered. The answers that can be paired with the request that produced them
# (n=1,284): p50 7.9 s, p90 31.5 s, p95 69.6 s, p99 260.1 s. (The transcripts hold 6,949
# assistant messages; the rest have no request of their own to pair with, the older Claude Code
# versions not recording one, so their latency is not measurable and is not counted.) So 240 s is
# 3.4x the p95 of the work and 124 s below the patience. 14 answers (1.1%) were slower than the
# budget, and all 14 were inside the patience: they would have reached the client, and the front
# spent its whole budget on them anyway. The slow tail is the front's own cloud-first wait: the
# cloud leg burns up to ANSWER_TIMEOUT before the laptop is asked.
ANSWER_BUDGET = float(os.environ.get("ESTATE_FRONT_ANSWER_BUDGET", "240"))
# The client's patience, written down so a gate can hold this budget to it.
CLIENT_PATIENCE = 364.0
# The load above which the front refuses new work instead of joining a queue it cannot serve.
# On 2026-10-30 the host's load reached 701 on 4 CPUs: no budget could have been answered then,
# and holding the request only made the box worse.
LOAD_MAX = float(os.environ.get("ESTATE_FRONT_LOAD_MAX", "0")) or 8.0 * (
    os.cpu_count() or 4
)
# How long a laptop slot that did not answer inside the budget is passed over. Consecutive
# failures double it, like the cloud's pass-over: a slot that is slow under load answers again
# later, and until then the twin answers instead.
SLOT_DOWN_S = 60.0
SLOT_DOWN_MAX_S = 600.0
SLOT_DOWN_UNTIL: dict = {}
SLOT_FAILURES: dict = {}

DOWN: set = set()  # slots that missed DOWN_AFTER probes in a row
CLOUD_DOWN_UNTIL = 0.0  # monotonic time until which the cloud is passed over
CLOUD_FAILURES = 0  # how many times the cloud has failed in a row


def backends() -> list:
    """The active slot first, then its twin."""
    try:
        active = int(ACTIVE.read_text().strip())
    except (OSError, ValueError):
        active = SLOTS[0]
    return [active] + [p for p in SLOTS if p != active]


def route() -> list:
    """Cloud first (the founder's 2026-10-26 ruling: the cloud is the default route, the
    laptop is the fallback), then the answering laptop slots, then the slots that stopped
    answering. A cloud that just failed moves LAST for CLOUD_DOWN_S seconds -- behind every
    laptop slot, including the ones that only missed their probes: the laptop answers while the
    cloud is down, and the cloud is still in the route so a laptop with no slot at all still
    reaches it."""
    slots = backends()
    now = time.monotonic()
    healthy = [p for p in slots if p not in DOWN and SLOT_DOWN_UNTIL.get(p, 0) <= now]
    sick = [p for p in slots if p not in healthy]
    if not CLOUD:
        return healthy + sick
    if now < CLOUD_DOWN_UNTIL:
        # A cloud that just failed is tried last, behind even the slots that missed probes: a
        # slot that is slow under load still answers; a cloud in cooldown is known not to. Put
        # ahead of the sick slots, it took every request when the fleet's load slowed the slot's
        # 3 s probe (2026-10-29: 24 cloud failures in a row, each request stalled on the dead leg).
        return healthy + sick + [CLOUD]
    return [CLOUD] + healthy + sick


def mark_cloud_down(reason: str = "the cloud failed to answer") -> None:
    """The cloud cannot answer now. Pass over it for a while so the laptop answers instead.

    Each failure in a row doubles the pass-over, up to CLOUD_DOWN_MAX_S: a cloud that fails
    slowly (the edge's 503 arrives after half a minute) would otherwise be paid for again on
    every request, and one outage would cost every caller half a minute.
    """
    global CLOUD_DOWN_UNTIL, CLOUD_FAILURES
    CLOUD_FAILURES += 1
    cooldown = min(CLOUD_DOWN_S * 2 ** (CLOUD_FAILURES - 1), CLOUD_DOWN_MAX_S)
    CLOUD_DOWN_UNTIL = time.monotonic() + cooldown
    print(
        f"front: {reason} ({CLOUD_FAILURES} in a row); "
        f"the laptop answers for {cooldown:.0f}s",
        file=sys.stderr,
        flush=True,
    )


def mark_cloud_up() -> None:
    """The cloud answered. It is the default route again, and the backoff is forgotten."""
    global CLOUD_DOWN_UNTIL, CLOUD_FAILURES
    CLOUD_DOWN_UNTIL = 0.0
    CLOUD_FAILURES = 0


def mark_slot_down(port: int) -> None:
    """A laptop slot did not answer inside the budget. Pass over it for a while, so the twin
    answers the next caller instead of the front spending its whole budget on a dead slot."""
    failures = SLOT_FAILURES.get(port, 0) + 1
    SLOT_FAILURES[port] = failures
    cooldown = min(SLOT_DOWN_S * 2 ** (failures - 1), SLOT_DOWN_MAX_S)
    SLOT_DOWN_UNTIL[port] = time.monotonic() + cooldown
    print(
        f"front: slot {port} did not answer inside the budget ({failures} in a row); "
        f"it is passed over for {cooldown:.0f}s",
        file=sys.stderr,
        flush=True,
    )


def mark_slot_up(port: int) -> None:
    """A laptop slot answered. The pass-over is forgotten."""
    SLOT_FAILURES.pop(port, None)
    SLOT_DOWN_UNTIL.pop(port, None)


async def answers(port: int) -> bool:
    try:
        r, w = await asyncio.wait_for(
            asyncio.open_connection("127.0.0.1", port), PROBE_TIMEOUT
        )
    except (OSError, asyncio.TimeoutError):
        return False
    try:
        w.write(b"GET /health/liveliness HTTP/1.0\r\nHost: 127.0.0.1\r\n\r\n")
        await w.drain()
        status = await asyncio.wait_for(r.readline(), PROBE_TIMEOUT)
        return b" 200 " in status
    except (OSError, asyncio.TimeoutError):
        return False
    finally:
        w.close()


async def watch() -> None:
    streak: dict = {}  # >0 probes answered in a row, <0 missed in a row
    laptop_up = True
    while True:
        results = await asyncio.gather(*(answers(p) for p in SLOTS))
        # Indexed, not zip(): the router's venv is 3.12, but the estate's test python is 3.9,
        # and zip(..., strict=) is a TypeError there -- which killed this watcher (and every
        # slot's cover) silently, on the first loop, in every test run.
        for i, port in enumerate(SLOTS):
            ok = results[i]
            s = streak.get(port, 0)
            streak[port] = max(s, 0) + 1 if ok else min(s, 0) - 1
            if streak[port] <= -DOWN_AFTER:
                DOWN.add(port)
            elif streak[port] >= UP_AFTER:
                DOWN.discard(port)
        now_up = any(p not in DOWN for p in SLOTS)
        if now_up != laptop_up:
            where = f"slots {[p for p in SLOTS if p not in DOWN]}" if now_up else CLOUD
            print(f"front: new connections -> {where}", file=sys.stderr, flush=True)
            laptop_up = now_up
        await asyncio.sleep(PROBE_EVERY)


def tls_context() -> ssl.SSLContext:
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


async def connect(target):
    if isinstance(target, int):
        return await asyncio.wait_for(asyncio.open_connection("127.0.0.1", target), 5)
    u = urlsplit(target)
    tls = u.scheme == "https"
    return await asyncio.wait_for(
        asyncio.open_connection(
            u.hostname,
            u.port or (443 if tls else 80),
            ssl=tls_context() if tls else None,
            server_hostname=u.hostname if tls else None,
        ),
        10,
    )


def _rewrite(head: bytes, host_line: bytes, connection, drop=(), add=()) -> bytes:
    """The request head with one Host, one Connection policy and no Expect.

    `drop` names headers the target must not see (the cloud leg drops the caller's
    User-Agent); `add` names the headers the front puts there instead.
    """
    hop = (b"host", b"connection", b"keep-alive", b"proxy-connection", b"expect")
    gone = {name.lower() for name in drop}
    lines = [
        line
        for line in head.split(b"\r\n")[1:]
        if line
        and line.split(b":", 1)[0].strip().lower() not in hop
        and line.split(b":", 1)[0].strip().lower() not in gone
    ]
    out = [head.split(b"\r\n", 1)[0]] + lines + [host_line]
    if connection:
        out.append(connection)
    out.extend(add)
    return b"\r\n".join(out + [b"", b""])


def for_cloud(head: bytes, host: str) -> bytes:
    """The request head with the cloud's Host, the front's own User-Agent, and a close after
    the answer.

    The caller's User-Agent is REPLACED, not forwarded: the cloud route sits behind Cloudflare,
    whose browser-signature rules answer some client signatures with "403 error code: 1010"
    before the request reaches the router at all. Measured on 2026-10-30 through the live front
    on 127.0.0.1:4000, one credential and one body: curl/8.7.1 -> 200, Python-urllib/3.12 ->
    403 {"error code": 1010}, estate-router-front/1.0 -> 200. The caller's header is dropped
    rather than appended to: two User-Agent headers would still carry the caller's signature.
    """
    return _rewrite(
        head,
        b"Host: " + host.encode(),
        b"Connection: close",
        drop=(b"user-agent",),
        add=(b"User-Agent: " + CLOUD_USER_AGENT.encode(),),
    )


def for_slot(head: bytes, port: int) -> bytes:
    """The request head as the caller wrote it, with the Host the slot expects."""
    return _rewrite(head, b"Host: 127.0.0.1:" + str(port).encode(), None)


def framing_of(head: bytes) -> tuple:
    """How the caller's body is framed: ('length', n), ('chunked', 0) or ('none', 0)."""
    for line in head.split(b"\r\n"):
        low = line.lower()
        if low.startswith(b"transfer-encoding:") and b"chunked" in low:
            return ("chunked", 0)
    for line in head.split(b"\r\n"):
        low = line.lower()
        if low.startswith(b"content-length:"):
            try:
                n = int(line.split(b":", 1)[1].strip())
            except ValueError:
                return ("none", 0)
            return ("length", n) if n > 0 else ("none", 0)
    return ("none", 0)


def expects_continue(head: bytes) -> bool:
    """The caller asked for a 100-continue. The front answers it, so the target never does."""
    return any(
        line.lower().startswith(b"expect:") and b"100-continue" in line.lower()
        for line in head.split(b"\r\n")
    )


def status_code(line: bytes) -> int:
    parts = line.split()
    if len(parts) >= 2 and parts[1].isdigit():
        return int(parts[1])
    return 0


# How a target says it does not carry the caller's model. LiteLLM's shapes, measured on the
# recovery router on 2026-10-30: HTTP 400 with "Invalid model name passed in model=<name>. Call
# `/v1/models` to view available models for your key.", and, when the caller's key may not use
# the model, HTTP 403 with "key_model_access_denied".
_NOT_HERE = (
    b"invalid model name passed in model=",
    b"key_model_access_denied",
    b"model not found",
    b"no such model",
    b"not found for model",
)
# A chunked body can split the phrase across chunk boundaries; the chunk headers are not
# part of the message, so they are taken out before the message is read.
_CHUNKED = re.compile(rb"\r\n[0-9a-fA-F]+\r\n")


# How the edge says it refused the request ITSELF, before the router behind it saw it:
# "error code: 1010" (the browser signature the edge insists on) and "error code: 1020" (the
# edge's own access rule). Measured on 2026-10-30 with the caller's User-Agent forwarded to
# the cloud: HTTP 403 with the body {"error code": 1010}, while a healthy laptop slot sat
# unused. The BODY is the evidence, not the status: an ordinary authenticated 403 from the
# router is the caller's own business and is still relayed untouched.
_EDGE_CODE = re.compile(rb"errorcode(1010|1020)")


def edge_blocked(complaint: bytes) -> bool:
    """Did the edge refuse the request itself, rather than the router answering it?

    Such a refusal is neither the caller's answer nor the router's: the request never got
    past the edge. The next target may still carry the model, so the front asks it.

    The body is squeezed to its letters and digits before the match, because the edge has
    more than one way to write it: the body measured on 2026-10-30 was {"error code": 1010},
    while the same refusal served to a browser reads "error code: 1010". Both squeeze to
    "errorcode1010". An ordinary router refusal does not: {"error":{"code":"invalid_api_key"}}
    squeezes to "errorcodeinvalidapikey".
    """
    return bool(_EDGE_CODE.search(re.sub(rb"[^a-z0-9]+", b"", complaint.lower())))


def model_not_here(complaint: bytes) -> bool:
    """Does this refusal say the target does not carry the caller's model?

    Such a refusal is the target saying "not mine", not the caller's answer: the next target
    may have the model. Anything else is the caller's own business and is relayed untouched.
    """
    low = complaint.lower()
    if any(marker in low for marker in _NOT_HERE):
        return True
    flat = _CHUNKED.sub(b"", low)
    return any(marker in flat for marker in _NOT_HERE)


def remaining(deadline: float) -> float:
    """How much of the answer budget is left."""
    return max(0.0, deadline - time.monotonic())


def saturated() -> tuple:
    """Is the box too loaded to answer? (True, load) when it is, (False, load) when it is not."""
    try:
        load = os.getloadavg()[0]
    except OSError:
        return (False, 0.0)
    return (load > LOAD_MAX, load)


async def refuse(client_w, status: bytes, extra: bytes = b"") -> None:
    """Tell the caller, at once, that the front cannot answer -- so the caller may retry.

    A refusal is an answer: the caller gets a status inside its own patience instead of waiting
    for an answer that arrives after it has already given up.
    """
    head = status + b"\r\n"
    if extra:
        head += extra + b"\r\n"
    head += b"Content-Length: 0\r\n\r\n"
    try:
        client_w.write(head)
        await client_w.drain()
    except (ConnectionError, OSError):
        pass


class Counter:
    """How many bytes of an answer have already reached the caller.

    A front that has started an answer cannot replace it with a status line: the caller is
    holding half a response, and a second status line would corrupt it.
    """

    def __init__(self) -> None:
        self.n = 0


class Held:
    """The request the front is holding while it asks a target: its head, and a copy of the
    body made while the body is forwarded. The copy is what lets the front ask the next
    target the same question."""

    def __init__(self, head: bytes) -> None:
        self.head = head
        self.framing, self.length = framing_of(head)
        self.buf = bytearray()
        self.overflow = False
        self.complete = False
        self.forward = None  # the target the body is being forwarded to

    def replayable(self) -> bool:
        """The whole request is in hand, so another target can be asked the same question."""
        return self.complete and not self.overflow


class Refusal:
    """A target's answer, kept so it can still be relayed if no other target can answer."""

    def __init__(self, status: bytes, body: bytes, rest, sock) -> None:
        self.status = status
        self.body = body
        self.rest = rest  # the reader for whatever is left of the answer
        self.sock = sock  # the writer for that connection (a reader has no close())


async def emit(held: Held, data: bytes) -> None:
    """Keep a copy of the body, and forward it to the target while it arrives."""
    if len(held.buf) + len(data) <= MAX_BODY:
        held.buf.extend(data)
    else:
        held.overflow = True
    if held.forward is not None:
        try:
            held.forward.write(data)
            await held.forward.drain()
        except (ConnectionError, OSError):
            held.forward = (
                None  # the target is gone; keep holding the body for the replay
            )


async def read_body(held: Held, client_r) -> None:
    """Read the caller's body, forward it to the target and hold a copy for a replay."""
    try:
        if held.framing == "length":
            remaining = held.length
            while remaining > 0:
                data = await client_r.read(min(CHUNK, remaining))
                if not data:
                    return
                remaining -= len(data)
                await emit(held, data)
        elif held.framing == "chunked":
            while True:
                line = await client_r.readline()
                if not line:
                    return
                await emit(held, line)
                try:
                    size = int(line.split(b";", 1)[0].strip() or b"0", 16)
                except ValueError:
                    return
                if size == 0:
                    while True:
                        trailer = await client_r.readline()
                        if not trailer:
                            return
                        await emit(held, trailer)
                        if trailer in (b"\r\n", b"\n"):
                            break
                    break
                remaining = size
                while remaining > 0:
                    data = await client_r.read(min(CHUNK, remaining))
                    if not data:
                        return
                    remaining -= len(data)
                    await emit(held, data)
                await emit(held, await client_r.readexactly(2))
    except (OSError, asyncio.IncompleteReadError, asyncio.LimitOverrunError):
        return
    held.complete = True


async def read_some(reader, limit: int) -> bytes:
    """Read up to limit bytes of an answer, without waiting for the rest of it."""
    out = bytearray()
    while len(out) < limit:
        try:
            data = await asyncio.wait_for(reader.read(min(CHUNK, limit - len(out))), 5)
        except (asyncio.TimeoutError, OSError):
            break
        if not data:
            break
        out.extend(data)
    return bytes(out)


async def drain(held: Held, body) -> None:
    """Let the caller's body finish, so the request can be asked of another target."""
    try:
        await asyncio.wait_for(asyncio.shield(body), DRAIN_TIMEOUT)
    except asyncio.TimeoutError:
        body.cancel()
        held.complete = False


async def read_head(reader, timeout: float = 300.0):
    try:
        return await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), timeout)
    except (
        asyncio.IncompleteReadError,
        asyncio.LimitOverrunError,
        asyncio.TimeoutError,
        OSError,
    ):
        return None


async def pipe(src, dst, counter: Counter = None) -> None:
    try:
        while data := await src.read(CHUNK):
            dst.write(data)
            if counter is not None:
                counter.n += len(data)
            await dst.drain()
        if dst.can_write_eof():
            dst.write_eof()  # half-close: the other direction may still be streaming
    except (ConnectionError, OSError):
        pass


async def ask_cloud(
    client_r, client_w, target: str, held: Held, deadline: float, sent: Counter
):
    """Ask the cloud for the request.

    Returns ('ok', None) when the answer is on its way to the caller, and ('retry', refusal)
    when the cloud failed: its answer is a server-side failure, or there was no answer at all.
    """
    try:
        back_r, back_w = await connect(target)
    except (OSError, asyncio.TimeoutError):
        mark_cloud_down()
        await read_body(held, client_r)  # nothing was forwarded; hold it for the replay
        return ("retry", Refusal(b"", b"", None, None))
    held.forward = back_w
    try:
        back_w.write(for_cloud(held.head, urlsplit(target).netloc))
        await back_w.drain()
    except (ConnectionError, OSError):
        held.forward = None
        await read_body(held, client_r)
        back_w.close()
        mark_cloud_down()
        return ("retry", Refusal(b"", b"", None, back_w))
    body = asyncio.create_task(read_body(held, client_r))
    left = remaining(deadline)
    try:
        status = await asyncio.wait_for(back_r.readline(), min(ANSWER_TIMEOUT, left))
    except (asyncio.TimeoutError, OSError):
        held.forward = None
        await drain(held, body)
        back_w.close()
        if left > 0:
            mark_cloud_down()  # the cloud had time and did not answer
        return ("retry", Refusal(b"", b"", None, back_w))
    # A 1xx is not the answer; read on to the one that is.
    while status_code(status) // 100 == 1:
        left = remaining(deadline)
        try:
            status = await asyncio.wait_for(
                back_r.readline(), min(ANSWER_TIMEOUT, left)
            )
        except (asyncio.TimeoutError, OSError):
            held.forward = None
            await drain(held, body)
            back_w.close()
            if left > 0:
                mark_cloud_down()  # the cloud had time and did not answer
            return ("retry", Refusal(b"", b"", None, back_w))
    code = status_code(status)
    if code >= 500:
        # The cloud is broken, not the request. Hold its complaint, and ask the next target.
        complaint = await read_some(back_r, MAX_ERROR)
        held.forward = None
        await drain(held, body)
        back_w.close()
        mark_cloud_down()
        return ("retry", Refusal(status, complaint, back_r, back_w))
    if code in (400, 403, 404):
        # The cloud's key may not carry this model, or the cloud may not have the model at all.
        # Read the refusal and look.
        complaint = await read_some(back_r, MAX_ERROR)
        if edge_blocked(complaint):
            # The edge refused the request itself: it never reached the router behind it, so
            # neither the caller's request nor the cloud's key is at fault. The cloud cannot
            # answer this request now, so it is passed over and the next target is asked the
            # same question -- exactly as for a cloud that failed to answer. The edge's own
            # refusal is never relayed as the answer while a healthy target is still free.
            held.forward = None
            await drain(held, body)
            back_w.close()
            mark_cloud_down("the edge refused the request (Cloudflare)")
            return ("retry", Refusal(status, complaint, back_r, back_w))
        mark_cloud_up()  # the cloud is answering; it is the refusal that is wrong, not the cloud
        if model_not_here(complaint):
            held.forward = None
            await drain(held, body)
            back_w.close()
            return ("retry", Refusal(status, complaint, back_r, back_w))
        client_w.write(status + complaint)
        sent.n += len(status + complaint)
        await client_w.drain()
        await pipe(back_r, client_w, sent)
        body.cancel()
        back_w.close()
        return ("ok", None)
    mark_cloud_up()  # the cloud answered: it is the default route again
    client_w.write(status)
    sent.n += len(status)
    await client_w.drain()
    await pipe(back_r, client_w, sent)
    body.cancel()
    back_w.close()
    return ("ok", None)


async def ask_again(
    client_r, client_w, target, held: Held, deadline: float, sent: Counter
) -> bool:
    """Ask another target the same question, from the copy of the request in hand.

    True means the caller has been dealt with: the answer is on its way, or half of it already
    reached the caller. False means the caller still needs an answer.
    """
    if not held.replayable():
        return False
    try:
        back_r, back_w = await connect(target)
    except (OSError, asyncio.TimeoutError):
        return False
    head = (
        for_slot(held.head, target)
        if isinstance(target, int)
        else for_cloud(held.head, urlsplit(target).netloc)
    )
    try:
        back_w.write(head + bytes(held.buf))
        await back_w.drain()
    except (ConnectionError, OSError):
        back_w.close()
        return False
    up = asyncio.create_task(pipe(client_r, back_w))
    try:
        await asyncio.wait_for(pipe(back_r, client_w, sent), remaining(deadline))
    except asyncio.TimeoutError:
        # The target did not answer inside the budget. If nothing reached the caller yet, the
        # caller still needs an answer and the front may try the next target.
        return sent.n > 0
    finally:
        up.cancel()
        for w in (back_w, client_w):
            w.close()
    return True


async def handle(client_r, client_w) -> None:
    # One budget for the whole request, every target it may be asked of.
    deadline = time.monotonic() + ANSWER_BUDGET
    over, load = saturated()
    if over:
        # The box cannot answer inside any budget. Say so at once, so the caller may retry
        # instead of waiting for an answer that is never coming.
        print(
            f"front: the box is saturated (load {load:.1f} > {LOAD_MAX:.1f}); refusing",
            file=sys.stderr,
            flush=True,
        )
        await refuse(client_w, b"HTTP/1.1 503 Service Unavailable", b"Retry-After: 30")
        client_w.close()
        return
    sent = Counter()
    targets = route()
    for index, target in enumerate(targets):
        if isinstance(target, str):
            head = await read_head(client_r, min(300.0, remaining(deadline)))
            if head is None:
                client_w.close()
                return
            held = Held(head)
            if expects_continue(head):
                client_w.write(b"HTTP/1.1 100 Continue\r\n\r\n")
                await client_w.drain()
            verdict, refusal = await ask_cloud(
                client_r, client_w, target, held, deadline, sent
            )
            if verdict == "ok":
                return
            for nxt in targets[index + 1 :]:
                if remaining(deadline) <= 0:
                    break
                if await ask_again(client_r, client_w, nxt, held, deadline, sent):
                    if refusal is not None and refusal.sock is not None:
                        refusal.sock.close()  # the cloud's half-answer is not needed now
                    return
            # Nothing else could answer: the caller gets the cloud's own complaint.
            if sent.n:
                client_w.close()  # half an answer is already with the caller
                return
            if remaining(deadline) <= 0:
                await refuse(
                    client_w, b"HTTP/1.1 504 Gateway Timeout", b"Retry-After: 10"
                )
            elif refusal is not None and refusal.status:
                client_w.write(refusal.status + refusal.body)
                await client_w.drain()
                if refusal.rest is not None:
                    await pipe(refusal.rest, client_w)
            else:
                client_w.write(b"HTTP/1.1 502 Bad Gateway\r\nContent-Length: 0\r\n\r\n")
                await client_w.drain()
            client_w.close()
            return
        # A laptop slot: bytes only, exactly as before.
        try:
            back_r, back_w = await connect(target)
        except (OSError, asyncio.TimeoutError):
            continue
        up = asyncio.create_task(pipe(client_r, back_w))
        try:
            # The router closing its side ends the exchange (a finished response, or a draining
            # router closing an idle keep-alive); the client then reconnects through the front.
            await asyncio.wait_for(pipe(back_r, client_w, sent), remaining(deadline))
            if sent.n:
                mark_slot_up(target)
        except asyncio.TimeoutError:
            # The slot did not answer inside the budget. Its body was forwarded byte for byte,
            # so the request cannot be asked of another target: the caller is told, at once,
            # that the front could not answer in time, and may retry.
            mark_slot_down(target)
            if not sent.n:
                await refuse(
                    client_w, b"HTTP/1.1 504 Gateway Timeout", b"Retry-After: 10"
                )
        finally:
            up.cancel()
            for w in (back_w, client_w):
                w.close()
        return
    print(f"front: no router answers ({route()})", file=sys.stderr, flush=True)
    client_w.close()


async def main() -> None:
    # The previous owner of :4000 may still be releasing it during the one-time move to the front.
    for _ in range(60):
        try:
            server = await asyncio.start_server(handle, *LISTEN, reuse_address=True)
            break
        except OSError:
            await asyncio.sleep(0.5)
    else:
        sys.exit(f"front: {LISTEN} stayed busy for 30 s")
    print(f"front: {LISTEN[0]}:{LISTEN[1]} -> {route()}", file=sys.stderr, flush=True)
    watcher = asyncio.create_task(watch())
    try:
        async with server:
            await server.serve_forever()
    finally:
        watcher.cancel()


if __name__ == "__main__":
    asyncio.run(main())
