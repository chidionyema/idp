"""The cassette boundary: record a real trajectory once, replay it verbatim forever after.

WHY THIS EXISTS (founder, 2026-09-23). `temperature=0` does not make a model deterministic.
Mixture-of-Experts routing, floating-point non-associativity in GPU reductions, and provider-side
model updates all vary the output at the same input. Measured reasoning in the founder's own
words: "Achieving 100% deterministic, zero-cost agent testing requires shifting from trying to
force LLM determinism to intercepting, recording, and replaying agent trajectories at the
execution boundaries."

WHAT THAT MEANS HERE. Every model call on this estate passes through this router -- the same fact
`request_ceiling.py` is built on ("this is the router every call on the estate passes through,
and this hook can REFUSE"). So this file records at that boundary and replays there:

    ESTATE_CASSETTE_MODE=record   live call, and the request/response pair is appended
    ESTATE_CASSETTE_MODE=replay   the cassette is served; no network, no key, no cost
    ESTATE_CASSETTE_MODE=off      the hook is inert (the default, so nothing changes unasked)

WHAT THIS FIXES, each a measured estate defect:

  speed      a 50-scenario suite is 10-25 minutes live. The same suite replays in seconds,
             because a cassette lookup is a dict hit and the network is never touched.
  cost       every PR build against live APIs is money. Replay is $0 for every run; live calls
             happen once, at record time, deliberately.
  flakiness  `bin/prm_grader`, `bin/idp-prm` and `redteam_promoter` grade LIVE output, so their
             verdicts vary with sampling and cannot be a gate. Against a cassette the same input
             yields the same output, so a test fails only on a REAL regression -- prompt logic,
             tool routing, or a schema -- and never on the model rephrasing itself.
  security   CI runners need no provider key and no egress in replay mode. The cassette is a
             file in the checkout; an air-gapped runner executes the whole suite.

CASSETTE FORMAT. JSONL, one object per call, human-readable and diffable -- so a PR that changes
a recorded trajectory shows the change as a diff rather than as "LLM rephrased output":

    {"key": "<sha256 of the canonical request>", "request": {...}, "response": {...}, "at": "..."}

The key covers the model, messages, tools and the sampling parameters, and deliberately NOT the
caller's identity or a timestamp: two runs asking the same question must land on one cassette
entry, and a re-record must be a deliberate act rather than a side effect of when it ran.

A MISS IN REPLAY MODE IS A FAILURE, NOT A FALLBACK. Serving a live call because the cassette had
no entry would put the network, the cost and the non-determinism straight back into CI, and would
do it silently -- the exact class of defect this estate keeps paying for. A miss raises, and it
names the key so the fix is "record it", not "run it live again".

LAW 46: every path is env-driven; the checkout is computed, never named.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

log = logging.getLogger("estate.cassette")

RECORD = "record"
REPLAY = "replay"
OFF = "off"

#: The sampling parameters that decide an output. Two calls that differ only here are different
#: questions and must have different cassette entries; the order is fixed so the key is stable.
_KEYED_PARAMS = (
    "model",
    "messages",
    "tools",
    "temperature",
    "top_p",
    "max_tokens",
    "tool_choice",
    "response_format",
    "stop",
    "seed",
)


def mode() -> str:
    """The mode, from the environment. `off` unless set, so this is inert by default."""
    m = (os.environ.get("ESTATE_CASSETTE_MODE") or OFF).strip().lower()
    return m if m in (RECORD, REPLAY, OFF) else OFF


def cassette_path() -> Path:
    """Where the cassettes live. One directory, named by the caller; never a literal path."""
    p = os.environ.get("ESTATE_CASSETTE_DIR")
    if p:
        return Path(p)
    # Default to the checkout this file is in, so a test suite finds its cassettes beside it.
    return Path(__file__).resolve().parent / "cassettes"


def key_for(data: dict) -> str:
    """The cassette key: a hash of the question, not of who asked it or when.

    Unknown keys are included in sorted order rather than dropped, so a provider adding a
    parameter changes the key -- an unrecorded shape must miss and say so, never silently reuse
    the response to a different question.
    """
    canonical: dict[str, Any] = {}
    for k in sorted(data):
        if k in ("api_key", "user_api_key_dict", "proxy_server_request", "metadata"):
            continue  # identity and transport, not the question
        canonical[k] = data[k]
    blob = json.dumps(canonical, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()


def _load(path: Path) -> dict[str, dict]:
    """Every entry in one cassette. A malformed line is skipped and NAMED, never silently
    dropped -- a cassette that half-loads would replay a subset and look green."""
    entries: dict[str, dict] = {}
    if not path.is_file():
        return entries
    for n, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except ValueError:
            log.warning("cassette %s line %d does not parse; skipped", path.name, n)
            continue
        if isinstance(row, dict) and row.get("key"):
            entries[row["key"]] = row
    return entries


def _append(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as fh:
        fh.write(json.dumps(row, sort_keys=True, default=str) + "\n")


class CassetteMiss(RuntimeError):
    """A replay with no recorded answer. Refuses rather than falling back to the network."""


class EstateCassette:
    """The recorder/replayer, mounted as a LiteLLM callback.

    Registered beside `request_ceiling.proxy_handler_instance` in litellm_settings.callbacks,
    so it sees every call exactly as the ceiling hook does.
    """

    def __init__(self, name: str | None = None) -> None:
        stem = name or os.environ.get("ESTATE_CASSETTE_NAME") or "estate"
        self.path = cassette_path() / f"{stem}.jsonl"
        self._entries: dict[str, dict] | None = None

    def _all(self) -> dict[str, dict]:
        if self._entries is None:
            self._entries = _load(self.path)
        return self._entries

    async def async_pre_call_hook(
        self,
        user_api_key_dict: Any = None,
        cache: Any = None,
        data: dict | None = None,
        call_type: str = "",
        **_: Any,
    ):
        """Serve from the cassette in replay mode. Returns a dict to short-circuit the call.

        LiteLLM treats the returned dict as the completed response, so no provider is called:
        no key, no egress, no spend. In record mode this is inert -- the call proceeds live and
        the response hook writes it down.
        """
        if mode() != REPLAY or not isinstance(data, dict):
            return None
        k = key_for(data)
        row = self._all().get(k)
        if row is None:
            # A miss REFUSES. Falling through to a live call here would restore the network,
            # the cost and the sampling noise into CI, silently.
            raise CassetteMiss(
                f"no cassette entry for key {k[:16]} in {self.path}. "
                f"Record it: ESTATE_CASSETTE_MODE=record with the same request."
            )
        log.info("cassette hit %s (%s)", k[:16], self.path.name)
        return row.get("response")

    async def async_post_call_success_hook(
        self, data: dict | None = None, response: Any = None, **_: Any
    ) -> Any:
        """Record a live answer. Only in record mode; replay and off never write."""
        if mode() != RECORD or not isinstance(data, dict):
            return response
        k = key_for(data)
        if k in self._all():
            return response  # already recorded: a re-record is deliberate, not an append-on-rerun
        body = response.model_dump() if hasattr(response, "model_dump") else response
        _append(
            self.path,
            {
                "key": k,
                "request": {
                    kk: vv
                    for kk, vv in data.items()
                    if kk
                    not in ("api_key", "user_api_key_dict", "proxy_server_request")
                },
                "response": body,
                "at": datetime.now(timezone.utc).isoformat(),
            },
        )
        self._entries = None  # the cached view is stale the moment we write
        log.info("cassette record %s (%s)", k[:16], self.path.name)
        return response


proxy_handler_instance = EstateCassette()
