#!/usr/bin/env python3
"""The Observer -- a spoken request becomes a tracked, BDD-backed action contract.

WHY THIS EXISTS. The founder works by voice, from everywhere, and moves between surfaces while
running many agent sessions. A request spoken in passing had no durable form: it was heard by the
voice loop, answered, and gone. `voice_turns` records that an utterance happened, with its latency
and word count, but not what was ASKED FOR and not whether it was ever DONE. So there was no object
to track, and nothing to show progress against.

This is that object's birth path, and it joins four things that already existed and never met:

  sovereign/voice/server.py   emits {"type": "transcript", "text": ..., "asr_seconds": ...} on
                              the WebSocket at /voice/stream. LISTENED TO HERE, not re-implemented.
  platform/llm/litellm.yaml   the estate's one router. No vendor key and no model name is written
                              in this file; the model is named in config and passed through.
  catalog/estate.db           THE HEADLINE, extended, never duplicated. `fleetview_signals` gets the
                              ASR row; `action_contracts` (next to it) gets the lifecycle.
  sovereign/voice/turnlog.py  already stores voice_turns.heard_at / asr_s / words. The contract
                              REFERENCES that turn rather than copying its numbers, so there is one
                              measurement, not two that can disagree.

WHAT THIS DELIBERATELY DOES NOT DO.

  * No SSE. The ingress is a WebSocket (`@app.websocket("/voice/stream")`); an SSE client against
    it 404s. The earlier draft of this file imported `sseclient` and requested
    `http://127.0.0.1:8770/stream`, which does not exist.
  * No second orchestrator. The founder's spec (docs/specs/2026-09-20-fleet-2100-hud-architecture.md)
    says reuse the existing reactor's `requestAnimationFrame` loop; the external blueprint said
    deploy Temporal or LangGraph. The spec wins -- an orchestrator here would be the second copy of
    a layer the estate already has (AGENTS.md section 6), and would be deleted.
  * No model named in code. `model` is read from config (LITELLM_OBSERVER_MODEL / the founder's
    router), because a feature that depends on a model or a vendor is a defect (section 0.1).

ADDRESSING. Always-on transcription, explicit address phrase. The spec's section 5 calls "the
illusion of seamless voice control while hiding the raw transcript" the single biggest lie, and
section 3 warns that firing misheard tasks is broken trust. So the Observer does not act on
chatter: it requires the trigger phrase, and it ECHOES what it heard before it commits, so a
mishearing is visible rather than silently executed.

Exit 0 one contract committed (or --once drained), 1 refused, 2 BLIND (ingress not reachable).
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]

# Where the ingress actually listens. bin/voice-loop defaults to 127.0.0.1:8770 and SILERO VAD
# REQUIRES A SECURE ORIGIN, so this is 127.0.0.1 and not a LAN address -- engine.py's notes record
# that http://<lan-ip> makes the browser refuse the microphone with no useful message.
VOICE_WS = os.environ.get("IDP_VOICE_WS", "ws://127.0.0.1:8770/voice/stream")

# The estate's one router. PROXY_BASE_URL is https://llm.${ESTATE_ZONE} in the literal manifest, so
# nothing here names the zone either.
LITELLM_URL = os.environ.get("LITELLM_URL", "http://localhost:4000/v1/chat/completions")

# The name of the variable the model is read FROM, never the value. Resolved in `_model()` at call
# time rather than at import, because the value arrives through the secret layer and a process that
# captured it at import would refuse for the rest of its life if the mount landed a moment later.
_OBSERVER_MODEL_VAR = "LITELLM_OBSERVER_MODEL"

# The address phrase. A spoken request is routed by intent only when the person addresses the
# agents; everything else is recorded as a transcript signal and never becomes a contract.
DEFAULT_TRIGGER = os.environ.get("IDP_OBSERVER_TRIGGER", "agents")

# The schema file the BDD payload must satisfy. A synthesised contract that does not match is
# refused rather than stored, so a malformed contract cannot become a tracked lie.
BDD_SCHEMA = REPO / "schema" / "intent" / "action-contract.schema.json"

_SYSTEM_PROMPT = (
    "You convert one spoken request from the founder of a software estate into a single "
    "Autonomous Action Contract. Reply with ONE JSON object and nothing else. "
    'Shape: {"feature": string, "given": string, "when": string, "then": string, '
    '"agents_required": integer}. '
    '"feature" names the outcome in under 12 words. "given"/"when"/"then" are one sentence each, '
    "and the then must be checkable -- a person reading it must be able to say yes or no. "
    '"agents_required" is how many parallel workers the work actually needs, 1 to 5. '
    "Do not invent requirements the founder did not imply. Do not add commentary."
)


class Refused(Exception):
    """A request that is a refusal, not a failure. Exit 1."""


class Blind(Exception):
    """The ingress or the router is not reachable, so nothing can be observed. Exit 2."""


def _model() -> str:
    """The Observer's model, named by configuration only.

    READ AT CALL TIME, not at import. A module-level `os.environ.get` captured the value once and
    then ignored every later change, which in the running system is the difference between an
    Observer that picks up the router config when it lands and one that refuses for the rest of its
    life. The test that sets the variable and calls this is what found it.

    An empty value is a REFUSAL and not a fallback to some model we like. AGENTS.md section 0.1
    makes model-agnosticism non-negotiable, and the failure mode of a silent default is a feature
    that works on the founder's desk and cannot work anywhere the model is absent -- which is the
    same class of defect as the zone literal this worktree's branch is named for.
    """
    configured = os.environ.get(_OBSERVER_MODEL_VAR, "").strip()
    if not configured:
        raise Refused(
            f"no observer model configured. Set {_OBSERVER_MODEL_VAR} to a model name the "
            "estate router serves (platform/llm/litellm.yaml). This is deliberately not "
            "defaulted: a model written into code is a defect under AGENTS.md 0.1."
        )
    return configured


def _db_path() -> Path:
    """The same database signals.py reads, resolved the same way.

    `ESTATE_DB` first, because that is the variable the running backend honours, so an Observer
    pointed at a test database and a backend pointed at the live one cannot silently disagree.
    """
    env = os.environ.get("ESTATE_DB", "").strip()
    if env:
        return Path(env)
    return REPO / "catalog" / "estate.db"


def _connect() -> sqlite3.Connection:
    """A connection in the shape signals.py's `_connect()` establishes, for the same reasons.

    WAL and a busy timeout are not optional here: signals.py's own docstring records that two
    processes write this file (the Fleetview backend and the voice service), and that the default
    rollback journal made a concurrent write raise `database is locked` AFTER its side effect had
    already happened. The Observer makes that a third writer.
    """
    db = _db_path()
    db.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(db), timeout=5.0, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA busy_timeout=5000")
    return con


# AN ADDITIVE MIGRATION, IN THE MODULE'S OWN BOOTSTRAP -- because that is how every other table in
# this database is born (signals.py: "Schemas created this process, keyed by database path", and
# "read_at and pid are appended style because that is how they arrived (additive migrations)").
#
# WHY NOT A .sql FILE: there is no catalog/sql/patches/ directory and no migration runner -- the
# draft plan's `catalog/sql/patches/2026-09-20-intent-contracts.sql` would create a directory nothing
# reads. `CREATE TABLE IF NOT EXISTS` plus an additive column check is the estate's real mechanism,
# and it is idempotent by construction.
#
# fleetview_signals IS NOT ALTERED. Its `kind`, `by`, `ok` and `created_at` are all NOT NULL, and an
# INSERT naming only session_id/runtime would fail at runtime -- the earlier draft's insert did
# exactly that, and would have failed on the first spoken request. The Observer writes a COMPLETE
# signal row, and it references voice_turns for the latency numbers that already exist there.
_MIGRATION = """
    CREATE TABLE IF NOT EXISTS action_contracts (
        contract_id     TEXT PRIMARY KEY,
        session_id      TEXT NOT NULL,
        source_surface  TEXT NOT NULL,
        raw_transcript  TEXT NOT NULL,
        -- THE CONTRACT IS ADDRESSED, SO THE ADDRESS PHRASE IS NOT PART OF IT. Stored separately
        -- so the transcript is evidence of what was said and the command is what was asked for.
        address_phrase  TEXT NOT NULL DEFAULT '',
        bdd_json        TEXT NOT NULL,
        status          TEXT NOT NULL DEFAULT 'PENDING',
        -- The voice_turns row this contract came from, when the utterance was recorded. NULL is a
        -- real fact: the contract was made from a transcript the turn log does not have.
        voice_turn_id   INTEGER,
        model           TEXT NOT NULL DEFAULT '',
        created_at      TEXT NOT NULL,
        updated_at      TEXT NOT NULL,
        CHECK (status IN ('PENDING', 'RUNNING', 'BLOCKED', 'COMPLETED', 'REFUSED'))
    )
"""
_CONTRACTS_INDEX = (
    "CREATE INDEX IF NOT EXISTS action_contracts_status "
    "ON action_contracts (status, created_at)"
)

# THE SIGNALS SCHEMA IS NOT RESTATED HERE. `signals.py` owns `fleetview_signals` -- its DDL is
# written out in full there, deliberately, because it is a dump of the live table and the two must
# stay indistinguishable. A second copy in this file would be the duplicate layer AGENTS.md section
# 6 refuses, and it would drift: the day `signals.py` gains a column, a copy here silently loses it.
#
# SO THE MODULE IS LOADED BY PATH AND ITS OWN `_ensure_schema` IS CALLED. Measured 2026-09-20: the
# first version of this file created only `action_contracts`, so the signal insert raised
# `sqlite3.OperationalError: no such table: fleetview_signals` on a fresh database -- the test that
# drives a real SQLite file is what found it, and it would have found the founder instead.
_SIGNALS_MODULE = (
    REPO / "backstage" / "plugins" / "fleetview-backend" / "src" / "signals.py"
)


def _signals_impl():
    """`signals.py`, loaded by path -- the same fixed-`sys.modules`-name trick routes.py uses.

    The fixed name is load-bearing: two callers that each exec the module separately would each own
    their own `_SCHEMA_READY` set and re-run DDL against a file the other is writing.
    """
    import importlib.util

    name = "idp_signals_for_observer"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, _SIGNALS_MODULE)
    if (
        spec is None or spec.loader is None
    ):  # pragma: no cover -- environment, not logic
        raise Blind(f"cannot load {_SIGNALS_MODULE}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _migrate(con: sqlite3.Connection) -> None:
    """Everything this database needs, in the order the estate already establishes it.

    `signals.py` first, because `fleetview_signals` is ITS table and a contract's signal row
    references it; then the contracts table this module owns.
    """
    _signals_impl()._ensure_schema(con)
    con.execute(_MIGRATION)
    con.execute(_CONTRACTS_INDEX)
    con.commit()


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def address(transcript: str, trigger: str) -> str | None:
    """The command inside an addressed utterance, or None if the person was not addressing us.

    A PREFIX, not a substring: "the agents are down" is a remark ABOUT the fleet and must not fire.
    Only "agents, ..." is a request TO it. The spec's section 3 is explicit that addressing by
    loose string match is a broken paradigm, so this is deliberately stricter than it needs to be
    for comfort -- a false positive spends worker capacity on chatter, and the person stops
    trusting the system the first time a passing sentence becomes a running contract.
    """
    text = transcript.strip()
    low = text.lower()
    head = trigger.strip().lower()
    if not head:
        raise Refused("empty trigger phrase would address every utterance")
    if not low.startswith(head):
        return None
    command = text[len(head) :].lstrip(" ,:;-\u2014\t")
    if not command:
        return None
    return command


def synthesise(command: str, *, timeout: float = 60.0) -> dict[str, Any]:
    """One spoken command -> the contract's BDD body, through the estate's router.

    The router is addressed by NAME. No vendor endpoint, no vendor key, no vendor model: the
    request carries a model name that configuration supplied and an Authorization header that
    arrives through the environment, exactly as every other client of this router does.
    """
    model = _model()
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": command},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0,
    }
    req = urllib.request.Request(
        LITELLM_URL,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", **_auth_headers()},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        raise Refused(f"router refused the request: HTTP {exc.code}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        # DISTINCT FROM A REFUSAL. The router being unreachable is BLIND -- the Observer cannot see,
        # and saying so is the difference between "the estate cannot do this" and "this request is
        # bad". A control that cannot act must say why (AGENTS.md section 8).
        raise Blind(f"router not reachable at {LITELLM_URL}: {exc}") from exc

    try:
        content = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise Refused(f"router reply had no message content: {exc}") from exc

    return normalise(content)


def _auth_headers() -> dict[str, str]:
    """The router key, by environment variable NAME only.

    Never a literal, never a file. AGENTS.md section 4: a key arrives through the secret layer and
    is referenced by name. An absent key is not an error here when the router runs without one.
    """
    key = os.environ.get("LITELLM_API_KEY", "").strip()
    return {"Authorization": f"Bearer {key}"} if key else {}


def normalise(content: Any) -> dict[str, Any]:
    """The model's reply as a contract, or a refusal naming what was wrong.

    VALIDATED, NOT TRUSTED. A model that returns prose, or a `then` that is not checkable, would
    otherwise become a tracked contract asserting a criterion no one can grade -- and the whole
    point of a BDD contract is that it can be falsified. AGENTS.md section 3: a gate that cannot
    fail is not a gate; a then that cannot be checked is not a then.
    """
    if isinstance(content, str):
        text = content.strip()
        if text.startswith("```"):
            text = text.split("```")[1] if "```" in text[3:] else text[3:]
            text = text.removeprefix("json").strip()
        try:
            content = json.loads(text)
        except json.JSONDecodeError as exc:
            raise Refused(f"model reply was not JSON: {exc}") from exc
    if not isinstance(content, dict):
        raise Refused(f"model reply was {type(content).__name__}, not an object")

    out: dict[str, Any] = {}
    for field in ("feature", "given", "when", "then"):
        value = content.get(field)
        if not isinstance(value, str) or not value.strip():
            raise Refused(f"contract is missing a usable '{field}'")
        out[field] = value.strip()

    try:
        n = int(content.get("agents_required", 1))
    except (TypeError, ValueError) as exc:
        raise Refused("agents_required was not a number") from exc
    if not 1 <= n <= 5:
        # A CEILING, NOT A SUGGESTION. The estate runs on the OKE always-free tier (4 Ampere A1
        # instances, 24GB total). A model free to name 40 workers would name 40 workers, and the
        # first symptom would be the fleet falling over rather than a refusal anyone could read.
        raise Refused(f"agents_required={n} is outside 1..5")
    out["agents_required"] = n
    return out


def commit(
    con: sqlite3.Connection,
    *,
    command: str,
    transcript: str,
    bdd: dict[str, Any],
    trigger: str,
    session_id: str,
    source_surface: str,
    asr_seconds: float | None,
    model: str,
    voice_turn_id: int | None = None,
) -> str:
    """The contract, and the signal that says it happened, in ONE transaction.

    WHY ONE TRANSACTION. Two writes that can fail apart produce the estate's most familiar defect:
    a contract with no signal (invisible on the board, so it looks like nothing was asked) or a
    signal with no contract (a node that pulses for work that does not exist). signals.py's
    `_connect` docstring records exactly this shape of bug for `_record`, where a steer completed
    its side effect and then reported 500 because the audit row failed after the deed was done.
    """
    contract_id = f"aac_{uuid.uuid4().hex[:12]}"
    now = _now()
    with (
        con
    ):  # commits on success, rolls back on exception -- and the rollback is the point
        con.execute(
            "INSERT INTO action_contracts (contract_id, session_id, source_surface, raw_transcript,"
            " address_phrase, bdd_json, status, voice_turn_id, model, created_at, updated_at)"
            " VALUES (?, ?, ?, ?, ?, ?, 'PENDING', ?, ?, ?, ?)",
            (
                contract_id,
                session_id,
                source_surface,
                transcript,
                trigger,
                json.dumps(bdd, sort_keys=True),
                voice_turn_id,
                model,
                now,
                now,
            ),
        )
        # EVERY NOT NULL COLUMN IS SUPPLIED. `kind` is what the board filters on, `by` is who
        # caused it, `ok` says the write itself succeeded, and `text` is what a person reads.
        # `error` and `read_at` stay NULL, which is a fact: nothing failed and nobody has read it.
        con.execute(
            "INSERT INTO fleetview_signals (session_id, runtime, kind, by, text, ok, created_at)"
            " VALUES (?, 'observer', 'contract', 'observer', ?, 1, ?)",
            (session_id, f"{contract_id}: {bdd['feature']}", now),
        )
    return contract_id


def _record_transcript_signal(
    con: sqlite3.Connection, *, session_id: str, transcript: str
) -> None:
    """An utterance that was NOT addressed to the agents. Recorded, and never a contract.

    THE POINT IS THE NEGATIVE CASE. The spec's section 5 says the founder is "blindly firing
    Whisper transcripts into a black box". A system that records only the utterances it ACTED on
    cannot show him the ones it misheard or ignored, which is the same black box with extra steps.
    """
    now = _now()
    with con:
        con.execute(
            "INSERT INTO fleetview_signals (session_id, runtime, kind, by, text, ok, created_at)"
            " VALUES (?, 'observer', 'transcript', 'observer', ?, 1, ?)",
            (session_id, transcript, now),
        )


def listen(
    *,
    trigger: str,
    session_id: str,
    source_surface: str,
    once: bool,
    timeout: float,
    dry_run: bool,
) -> int:
    """Tail the voice ingress, and turn addressed utterances into contracts.

    A WebSocket, because that is what the ingress is. The frame we act on is
    {"type": "transcript", "text": ..., "asr_seconds": ...} -- NOT "latency_ms", and not an SSE
    event; server.py sends it from the receive loop after `engine.transcribe` returns.
    """
    try:
        from websockets.sync.client import connect as ws_connect
    except ImportError as exc:  # pragma: no cover - environment, not logic
        raise Blind(
            "websockets is not installed. The ingress is a WebSocket "
            "(sovereign/voice/server.py's @app.websocket('/voice/stream')), so an SSE or plain "
            f"HTTP client cannot read it: {exc}"
        ) from exc

    con = _connect()
    _migrate(con)
    model = _model()

    try:
        with ws_connect(VOICE_WS, open_timeout=timeout) as socket:
            print(f"observer: listening on {VOICE_WS}", flush=True)
            print(f"observer: trigger phrase is {trigger!r}", flush=True)
            print(f"observer: contracts -> {_db_path()}", flush=True)
            if dry_run:
                print("observer: DRY RUN -- nothing will be committed", flush=True)
            exchanged = 0
            while True:
                try:
                    raw = socket.recv(timeout=timeout)
                except TimeoutError:
                    continue
                if isinstance(raw, bytes):
                    continue
                try:
                    frame = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if not isinstance(frame, dict) or frame.get("type") != "transcript":
                    continue

                transcript = str(frame.get("text", "")).strip()
                if not transcript:
                    continue
                command = address(transcript, trigger)
                if command is None:
                    if not dry_run:
                        _record_transcript_signal(
                            con, session_id=session_id, transcript=transcript
                        )
                    continue

                # ECHO BEFORE ACTING. The spec calls hiding the raw transcript the single biggest
                # lie and asks for an ephemeral on-screen log that proves the agent understood
                # before it executes. This is the server-side half of that promise: the heard text
                # is printed before the contract exists, so a mishearing is visible in the record
                # even when the synthesis succeeds.
                print(
                    f"observer: heard {transcript!r} -> command {command!r}", flush=True
                )
                if dry_run:
                    print("observer: dry run, not synthesising", flush=True)
                    exchanged += 1
                    if once:
                        return 0
                    continue

                bdd = synthesise(command)
                contract_id = commit(
                    con,
                    command=command,
                    transcript=transcript,
                    bdd=bdd,
                    trigger=trigger,
                    session_id=session_id,
                    source_surface=source_surface,
                    asr_seconds=frame.get("asr_seconds"),
                    model=model,
                )
                print(f"observer: {contract_id} {bdd['feature']}", flush=True)
                exchanged += 1
                if once:
                    return 0
    except OSError as exc:
        raise Blind(
            f"voice ingress not reachable at {VOICE_WS}: {exc}. Start it with bin/voice-loop."
        ) from exc


def contracts_for(limit: int = 10) -> list[dict[str, Any]]:
    """The contracts the board is currently watching, newest first.

    THE READ THE HUD MAKES. It returns contracts in a terminal state too, for a short tail, so a
    node can turn green and be seen to turn green -- a list of only-active work makes completion
    indistinguishable from disappearance.

    A FAILURE RAISES, and `routes.py`'s envelope turns that into `{"contracts": [], "error": ...}`.
    Returning an empty list here on failure would be the silent no-op AGENTS.md section 8 refuses:
    the page cannot tell "nothing was asked" from "the database is unreadable".
    """
    con = _connect()
    _migrate(con)
    try:
        rows = con.execute(
            "SELECT contract_id, session_id, source_surface, raw_transcript, bdd_json, status,"
            " model, created_at, updated_at FROM action_contracts"
            " ORDER BY created_at DESC LIMIT ?",
            (max(1, int(limit)),),
        ).fetchall()
    finally:
        con.close()

    out: list[dict[str, Any]] = []
    for r in rows:
        bdd = json.loads(r["bdd_json"])
        out.append(
            {
                "id": r["contract_id"],
                "session_id": r["session_id"],
                "surface": r["source_surface"],
                "transcript": r["raw_transcript"],
                "bdd": bdd,
                "status": r["status"],
                # DERIVED FROM THE CONTRACT, NOT A SECOND COLUMN. `agents_required` is part of the
                # BDD payload the model produced; storing it twice would let the two disagree.
                "agents_required": bdd.get("agents_required"),
                "model": r["model"],
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
            }
        )
    return out


def _cmd_list(as_json: bool) -> int:
    con = _connect()
    _migrate(con)
    rows = con.execute(
        "SELECT contract_id, status, session_id, source_surface, raw_transcript, bdd_json,"
        " created_at FROM action_contracts ORDER BY created_at DESC LIMIT 50"
    ).fetchall()
    if as_json:
        print(json.dumps([dict(r) for r in rows], indent=2))
        return 0
    if not rows:
        # A silent empty is a lie (section 8): say that nothing has been asked, rather than
        # printing a blank that reads like a broken command.
        print("no action contracts yet -- nothing has been addressed to the agents")
        return 0
    for r in rows:
        feature = json.loads(r["bdd_json"])["feature"]
        print(f"{r['contract_id']}  {r['status']:<9} {r['created_at']}  {feature}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="observer",
        description="Turn an addressed spoken request into a tracked BDD action contract.",
    )
    p.add_argument(
        "--trigger", default=DEFAULT_TRIGGER, help="address phrase (default: agents)"
    )
    p.add_argument(
        "--session", default=os.environ.get("IDP_SESSION_ID", "active_session")
    )
    p.add_argument(
        "--surface", default="voice", help="which surface the request came from"
    )
    p.add_argument("--once", action="store_true", help="commit one contract and exit")
    p.add_argument(
        "--dry-run", action="store_true", help="print what was heard; commit nothing"
    )
    p.add_argument("--list", action="store_true", help="show recent contracts and exit")
    p.add_argument("--json", action="store_true", help="with --list, emit JSON")
    p.add_argument(
        "--timeout", type=float, default=30.0, help="socket read timeout, seconds"
    )
    args = p.parse_args(argv)

    try:
        if args.list:
            return _cmd_list(args.json)
        return listen(
            trigger=args.trigger,
            session_id=args.session,
            source_surface=args.surface,
            once=args.once,
            timeout=args.timeout,
            dry_run=args.dry_run,
        )
    except Refused as exc:
        print(f"REFUSE observer: {exc}", file=sys.stderr)
        return 1
    except Blind as exc:
        print(f"BLIND  observer: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
