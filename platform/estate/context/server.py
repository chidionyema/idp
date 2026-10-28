"""server -- the estate context broker: the one public door to the context engine.

WHAT THIS IS. A policy-enforcing MCP server. An agent calls `estate_context` through the
estate's existing MCP gateway (agentgateway, decision 0006), the gateway hands the call here,
and here the claim, the freshness, the budget, the secrets and the provenance are settled
BEFORE the private engine is asked anything. The engine has no public route, so a client that
bypasses its own harness still cannot reach it.

WHY IT IS HAND-WRITTEN AND NOT BUILT ON THE MCP SDK. The broker is the estate's enforcement
point; an enforcement point that depends on a library whose transport API can change under it is
a worse enforcement point. The MCP 2026 streamable-HTTP shape used here is small and written
down (the gortex server doc describes the same transport on the other side of the wire):
JSON-RPC 2.0 frames POSTed to /mcp, notifications answered with 202 and no body, `initialize`
minting a session id, a 404 for an unknown session. Standard library only, so the image carries
no dependency that can be swapped underneath the policy.

THE TOOLS. Two, and two is enough:
    estate_context       ask the engine a question about the tree, inside a claim, at a commit
    estate_context_status what the broker knows: the indexed commit, the engine's health, the claims

WHAT IT WILL NOT DO. It will not serve an answer for a path outside the caller's claim, from an
index that does not match the commit asked about, when the engine is down, or with a credential
in it. Each of those is a refusal with a verdict a client can act on.
"""

from __future__ import annotations

import json
import os
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Mapping

from . import claims as claim_rules
from . import plan as plan_rules
from .broker import (
    BrokerState,
    ContextRequest,
    Decision,
    EngineClient,
    EngineError,
    envelope,
    provenance,
    scrub,
)

PROTOCOL_VERSION = "2026-06-18"
SERVER_NAME = "estate-context-broker"

# --- configuration, all by name --------------------------------------------------------------
ENGINE_URL = os.environ.get("ESTATE_CONTEXT_ENGINE_URL", "http://127.0.0.1:7411")
ENGINE_TOKEN_FILE = os.environ.get(
    "ESTATE_CONTEXT_ENGINE_TOKEN_FILE", "/run/secrets/gortex-engine/token"
)
INDEX_DIR = os.environ.get("ESTATE_CONTEXT_INDEX_DIR", "/data")
SOURCE_DIR = os.environ.get("ESTATE_CONTEXT_SOURCE_DIR", "/data/repo")
SECRET_DIR = os.environ.get("ESTATE_CONTEXT_SECRET_DIR", "/run/secrets/estate-context")
GITHUB_TOKEN_FILE = os.environ.get(
    "ESTATE_CONTEXT_GITHUB_TOKEN_FILE", "/run/secrets/github/token"
)
GITHUB_REPO = os.environ.get("ESTATE_CONTEXT_GITHUB_REPO", "chidionyema/idp")
DEFAULT_TOKEN_BUDGET = int(os.environ.get("ESTATE_CONTEXT_TOKEN_BUDGET", "4000"))
MAX_TOKEN_BUDGET = int(os.environ.get("ESTATE_CONTEXT_MAX_TOKEN_BUDGET", "32000"))
# How many lines of a file the broker hands back. Bounded, because one answer has to fit the
# budget the caller asked for.
EXCERPT_LINES = int(os.environ.get("ESTATE_CONTEXT_EXCERPT_LINES", "120"))
PORT = int(os.environ.get("ESTATE_CONTEXT_PORT", "8002"))

# The claim record is read from GitHub, not from a second ledger. It is cached briefly so a
# burst of calls does not become a burst of API calls; a minute is short enough that a claim
# taken in the last minute is honoured.
CLAIM_CACHE_TTL_S = float(os.environ.get("ESTATE_CONTEXT_CLAIM_CACHE_TTL_S", "60"))

_lock = threading.Lock()
_cache: dict[str, tuple[float, str, list[dict[str, Any]]]] = {}

# --- telemetry -------------------------------------------------------------------------------
# The broker's own numbers, because "the context engine is better than the tools it replaces" is
# a claim that needs a measurement and not an opinion. What is counted here is what the broker
# can measure without a baseline corpus: requests, refusals by verdict, answers, the tokens
# handed back, and the engine's latency. Time-to-first-correct-file is a property of the CALLER's
# search, so the broker publishes the engine latency and the excerpt count and leaves the
# ranking to whoever holds the corpus.
_telemetry: dict[str, float] = {
    "estate_context_requests_total": 0,
    "estate_context_answers_total": 0,
    "estate_context_refusals_total": 0,
    "estate_context_excerpts_total": 0,
    "estate_context_engine_ms_total": 0,
    "estate_context_tokens_total": 0,
    "estate_context_redactions_total": 0,
}


def _tally(name: str, amount: float = 1) -> None:
    with _lock:
        _telemetry[name] = _telemetry.get(name, 0) + amount


def telemetry() -> dict[str, float]:
    with _lock:
        return dict(_telemetry)


def _metrics_text() -> str:
    """Prometheus text exposition. The estate's evidence layer scrapes /metrics everywhere else."""
    data = telemetry()
    lines = []
    for name in sorted(data):
        lines.append(f"# TYPE {name} counter")
        lines.append(f"{name} {data[name]}")
    return "\n".join(lines) + "\n"


def _read_secret_file(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read().strip()
    except OSError:
        return ""


def _load_named_secrets() -> dict[str, str]:
    """The names and values of the secrets the broker scrubs, read from a mounted directory.

    A Kubernetes Secret mounts as a directory: one file per secret, the file's NAME is the
    secret's name and its content is the value. That is the shape the estate's own Secret
    mounts already have, so no second format is invented here. The directory never leaves the
    pod: only the NAMES are ever logged, and each value is used only to replace itself in an
    answer before that answer goes out.
    """
    out: dict[str, str] = {}
    try:
        names = sorted(os.listdir(SECRET_DIR))
    except OSError:
        return out
    for name in names:
        if name.startswith(".") or name in (".", ".."):
            continue
        path = os.path.join(SECRET_DIR, name)
        if not os.path.isfile(path):
            continue
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                value = fh.read().strip()
        except OSError:
            continue
        if value:
            out[name] = value
    return out


def _index_manifest() -> dict[str, Any]:
    """What CI built: the commit that was indexed, and when.

    The manifest is written by the CI job that builds the index (see
    .github/workflows/context-index.yml). It is the broker's ground truth for freshness: the
    engine's answers are from THIS commit or they are refused.
    """
    path = os.path.join(INDEX_DIR, "index.json")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def _issue_record(issue_number: int) -> tuple[str, list[dict[str, Any]]]:
    """The issue's state and its comments, from the estate's own record (GitHub).

    Returns ("", []) when the record cannot be read -- and the caller then refuses, because a
    claim that cannot be checked is not a claim.
    """
    key = str(issue_number)
    now = time.time()
    with _lock:
        hit = _cache.get(key)
        if hit and now - hit[0] < CLAIM_CACHE_TTL_S:
            return hit[1], hit[2]
    token = _read_secret_file(GITHUB_TOKEN_FILE)
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    state = ""
    comments: list[dict[str, Any]] = []
    try:
        req = urllib.request.Request(
            f"https://api.github.com/repos/{GITHUB_REPO}/issues/{issue_number}",
            headers=headers,
        )
        with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310
            state = str(json.loads(resp.read().decode("utf-8")).get("state", ""))
        req = urllib.request.Request(
            f"https://api.github.com/repos/{GITHUB_REPO}/issues/{issue_number}/comments",
            headers=headers,
        )
        with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310
            comments = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        state, comments = "", []
    with _lock:
        _cache[key] = (now, state, comments)
    return state, comments


def _engine_client() -> EngineClient:
    return EngineClient(ENGINE_URL, _read_secret_file(ENGINE_TOKEN_FILE))


def _engine_reachable() -> bool:
    try:
        # S310: the engine's own configured address, http/https, never caller-supplied.
        req = urllib.request.Request(f"{ENGINE_URL}/healthz")  # noqa: S310
        with urllib.request.urlopen(req, timeout=3) as resp:  # noqa: S310
            return 200 <= resp.status < 300
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def _digest_of(path: str) -> str | None:
    """sha256 of a file in the indexed source tree, for the provenance envelope.

    The engine's path is normalised FIRST: it stores files under the tracked repository's
    NAME ("repo/pkg/broker.py"), which is the engine's storage detail, not the repository's.
    A digest looked up under the engine's prefix would find nothing, and an excerpt with no
    digest is an excerpt nobody can check.
    """
    rel = plan_rules.normalize_path(path, SOURCE_DIR) or path
    full = os.path.join(SOURCE_DIR, rel)
    try:
        import hashlib

        h = hashlib.sha256()
        with open(full, "rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def _read_head(raw_path: str) -> tuple[str, int, int]:
    """The head of a file in the indexed tree, and the lines it covers.

    The engine does not send file text -- MEASURED against gortex v0.64.11, its answer carries
    the path, the symbol and the line, and the text is not in it. So the broker READS the head
    of the file it holds, which is the only copy of that text the broker can vouch for. A
    bounded head keeps one answer inside the budget the caller asked for.
    """
    rel = plan_rules.normalize_path(raw_path, SOURCE_DIR)
    if not rel:
        return "", 0, 0
    try:
        with open(
            os.path.join(SOURCE_DIR, rel), "r", encoding="utf-8", errors="replace"
        ) as fh:
            lines = []
            for i, line in enumerate(fh):
                if i >= EXCERPT_LINES:
                    break
                lines.append(line.rstrip("\n"))
    except OSError:
        return "", 0, 0
    if not lines:
        return "", 0, 0
    return "\n".join(lines) + "\n", 1, len(lines)


def _excerpts_from(
    payload: Any, commit: str, secrets: Mapping[str, str] | None = None
) -> list[dict[str, Any]]:
    """Pull the file-shaped pieces out of an engine answer and envelope each one.

    The engine names files two ways and both are read: `working_set` (the ranked files) and
    `relevant_symbols` (the symbols it chose). The RANKING is the engine's: the working set is
    read in the engine's order and that order is the answer's order, because a second opinion
    about which file matters most is the second ranker this estate deleted.

    MEASURED against gortex v0.64.11, the engine does not send the file's text -- it sends the
    path, the symbol and the line. So the broker reads the head of each file from the tree it
    holds, and that read is what the agent receives: the engine decides WHICH files, the broker
    says WHAT they say, and the excerpt carries a digest of the file it read.

    Every path is normalised to the repository's own path before it is recorded, and every
    excerpt is scrubbed with the broker's rule -- an excerpt that leaves the broker with a
    credential in it is a leak with a provenance envelope around it.
    """
    out: list[dict[str, Any]] = []
    if not isinstance(payload, dict):
        return out
    seen: set[str] = set()

    symbols_by_file: dict[str, list[dict[str, Any]]] = {}
    for item in payload.get("relevant_symbols") or []:
        if not isinstance(item, dict):
            continue
        raw = str(item.get("file_path") or item.get("path") or item.get("file") or "")
        if not raw:
            continue
        symbols_by_file.setdefault(raw, []).append(item)

    def _add(
        raw_path: str, content: str, line: int, end_line: int | None = None
    ) -> None:
        rel = plan_rules.normalize_path(raw_path, SOURCE_DIR) or raw_path
        if rel in seen:
            return
        seen.add(rel)
        out.append(
            envelope(
                content,
                provenance(rel, commit, line, end_line or line, _digest_of(raw_path)),
                secrets=secrets,
            )
        )

    for item in payload.get("working_set") or []:
        if not isinstance(item, dict):
            continue
        raw = str(item.get("file") or item.get("path") or "")
        if not raw:
            continue
        symbols = symbols_by_file.get(raw) or []
        source = ""
        line = 0
        for symbol in symbols:
            source = str(symbol.get("source") or "")
            if source:
                line = int(symbol.get("start_line") or 0)
                break
        if not source:
            source, line, end_line = _read_head(raw)
            _add(raw, source, line, end_line)
            continue
        _add(raw, source, line)

    for raw, symbols in symbols_by_file.items():
        for symbol in symbols:
            source = str(symbol.get("source") or "")
            if not source:
                continue
            _add(raw, source, int(symbol.get("start_line") or 0))

    return out


# --- the tools --------------------------------------------------------------------------------
def tool_estate_context(args: Mapping[str, Any]) -> dict[str, Any]:
    """Ask the engine a question, inside a claim, at a commit, within a budget.

    The order is the argument: the claim is checked first (it is the cheapest to check and the
    most load-bearing), then freshness, then the engine, then the answer.
    """
    task = str(args.get("task") or "").strip()
    if not task:
        return _error("the request has no task")
    issue_number = args.get("claim_issue")
    agent = str(args.get("claim_agent") or "").strip()
    if not issue_number or not agent:
        return _error(
            "a context request states its claim: claim_issue and claim_agent are required"
        )
    paths = [str(p) for p in (args.get("paths") or [])]
    mode = str(args.get("mode") or "committed")
    commit = str(args.get("commit") or "").strip() or None
    budget = int(args.get("token_budget") or DEFAULT_TOKEN_BUDGET)
    budget = max(1, min(budget, MAX_TOKEN_BUDGET))
    _tally("estate_context_requests_total")

    state, comments = _issue_record(int(issue_number))
    verdict = claim_rules.verify_claim(
        issue_state=state,
        issue_comments=claim_rules.github_comment_bodies(comments),
        agent=agent,
        requested_paths=paths,
        issue_number=int(issue_number),
    )
    if not verdict.allow:
        _tally("estate_context_refusals_total")
        return _refusal(verdict)

    manifest = _index_manifest()
    index_commit = manifest.get("commit") or None
    head_commit = manifest.get("head_commit") or index_commit
    broker_state = BrokerState(
        index_commit=index_commit,
        head_commit=head_commit,
        claim_paths=claim_rules.paths_held_by(
            claim_rules.parse_claims(claim_rules.github_comment_bodies(comments)), agent
        ),
        secrets=_load_named_secrets(),
        engine_reachable=_engine_reachable(),
    )
    request = ContextRequest(
        tool="smart_context",
        paths=paths,
        request_commit=commit,
        mode=mode,
        token_budget=budget,
    )
    decision = decide(request, broker_state)
    if not decision.allow:
        _tally("estate_context_refusals_total")
        return _refusal(decision)

    client = _engine_client()
    engine_args: dict[str, Any] = {"task": task, "token_budget": budget}
    if paths:
        engine_args["paths"] = paths
    if args.get("view"):
        engine_args["view"] = args["view"]
    started = time.monotonic()
    try:
        payload = client.call("smart_context", engine_args)
    except EngineError as exc:
        _tally("estate_context_refusals_total")
        return _error(f"the engine could not answer: {exc}", verdict=exc.verdict)
    engine_ms = int((time.monotonic() - started) * 1000)

    answer = (
        json.dumps(payload, sort_keys=True) if not isinstance(payload, str) else payload
    )
    clean, removed = scrub(answer, broker_state.secrets)
    excerpts = _excerpts_from(payload, str(index_commit or ""), broker_state.secrets)
    _tally("estate_context_answers_total")
    _tally("estate_context_engine_ms_total", engine_ms)
    _tally("estate_context_excerpts_total", len(excerpts))
    _tally("estate_context_tokens_total", len(clean) // 4)
    _tally("estate_context_redactions_total", len(removed))
    print(
        json.dumps(
            {
                "event": "estate_context",
                "verdict": decision.verdict,
                "tool": request.tool,
                "commit": index_commit,
                "engine_ms": engine_ms,
                "excerpts": len(excerpts),
                "redacted": removed,
                "paths": paths,
            }
        ),
        flush=True,
    )
    return {
        "content": [{"type": "text", "text": clean}],
        "structuredContent": {
            "verdict": decision.verdict,
            "reason": decision.reason,
            "commit": index_commit,
            "redacted": removed,
            "excerpts": excerpts,
            "answer": clean,
        },
        "isError": False,
    }


def tool_estate_context_status(args: Mapping[str, Any]) -> dict[str, Any]:
    """What the broker knows right now: the indexed commit, the engine's health, the claims."""
    manifest = _index_manifest()
    issue_number = args.get("claim_issue")
    claims: dict[str, Any] = {}
    if issue_number:
        state, comments = _issue_record(int(issue_number))
        claims = claim_rules.claim_state(
            issue_state=state,
            issue_comments=claim_rules.github_comment_bodies(comments),
            agent=str(args.get("claim_agent") or ""),
            issue_number=int(issue_number),
        )
    body = {
        "indexed_commit": manifest.get("commit"),
        "head_commit": manifest.get("head_commit"),
        "built_at": manifest.get("built_at"),
        "engine_url": ENGINE_URL,
        "engine_reachable": _engine_reachable(),
        "source_dir": SOURCE_DIR,
        "claims": claims,
    }
    return {
        "content": [
            {"type": "text", "text": json.dumps(body, indent=2, sort_keys=True)}
        ],
        "structuredContent": body,
        "isError": False,
    }


def decide(request: ContextRequest, state: BrokerState) -> Decision:
    """The policy call, named so the tests can reach it without a socket."""
    from .broker import decide_request

    return decide_request(request, state)


def _refusal(decision: Decision) -> dict[str, Any]:
    body = {
        "verdict": decision.verdict,
        "reason": decision.reason,
        "evidence": dict(decision.evidence),
        "allowed": False,
    }
    return {
        "content": [
            {"type": "text", "text": json.dumps(body, indent=2, sort_keys=True)}
        ],
        "structuredContent": body,
        "isError": True,
    }


def _error(message: str, verdict: str = "BAD_REQUEST") -> dict[str, Any]:
    body = {"verdict": verdict, "reason": message, "allowed": False}
    return {
        "content": [
            {"type": "text", "text": json.dumps(body, indent=2, sort_keys=True)}
        ],
        "structuredContent": body,
        "isError": True,
    }


TOOLS = [
    {
        "name": "estate_context",
        "description": (
            "Answer a question about the estate's code from the private context engine, inside "
            "the caller's live claim, at a commit whose index is proven. Returns the answer, the "
            "verdict, and a provenance envelope for every excerpt."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "task": {"type": "string", "description": "The question, as a task."},
                "paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "The paths this question is about. Each must be inside the claim.",
                },
                "commit": {
                    "type": "string",
                    "description": "The commit asked about. Defaults to HEAD.",
                },
                "mode": {
                    "type": "string",
                    "enum": ["committed", "working_copy"],
                    "description": "committed: the index must match the commit exactly.",
                },
                "token_budget": {
                    "type": "integer",
                    "description": "The token ceiling for the answer.",
                },
                "claim_issue": {
                    "type": "integer",
                    "description": "The issue holding the caller's claim.",
                },
                "claim_agent": {
                    "type": "string",
                    "description": "The agent holding the claim.",
                },
                "view": {
                    "type": "string",
                    "description": "The engine view (worktree) to read.",
                },
            },
            "required": ["task", "claim_issue", "claim_agent"],
        },
    },
    {
        "name": "estate_context_status",
        "description": "The indexed commit, the engine's health, and the caller's claim state.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "claim_issue": {"type": "integer"},
                "claim_agent": {"type": "string"},
            },
        },
    },
]

TOOL_FUNCS = {
    "estate_context": tool_estate_context,
    "estate_context_status": tool_estate_context_status,
}


# --- the MCP transport ------------------------------------------------------------------------
class Handler(BaseHTTPRequestHandler):
    """The MCP 2026 streamable-HTTP transport, minimal and stateless.

    Stateless on purpose: agentgateway proxies this backend in stateless mode, so a session id
    is minted and echoed but never required. That keeps the broker horizontally scalable with
    no session store, which is one less thing to be wrong.
    """

    server_version = f"{SERVER_NAME}/1.0"
    # NOT BaseHTTPRequestHandler.protocol_version: that attribute names the HTTP protocol
    # ("HTTP/1.1"), and putting the MCP version there makes the server answer with a status
    # line no client can parse.
    http_protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args: Any) -> None:  # noqa: A003
        # The estate's evidence layer reads structured logs; an unstructured access line would
        # be noise. One line per call, with the verdict.
        print(f"{SERVER_NAME} {fmt % args}", flush=True)

    def _send_json(
        self, payload: Any, status: int = 200, session: str | None = None
    ) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        if session:
            self.send_header("Mcp-Session-Id", session)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        path = self.path.rstrip("/")
        if path == "/healthz":
            self._send_json({"status": "ok", "service": SERVER_NAME})
            return
        if path == "/metrics":
            body = _metrics_text().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        # The SSE stream of server-initiated notifications is not something this broker does;
        # saying so plainly beats a hanging request.
        self._send_json(
            {"error": "not supported: this broker serves request/response only"},
            status=405,
        )

    def do_DELETE(self) -> None:  # noqa: N802
        self.send_response(204)
        self.end_headers()

    def do_POST(self) -> None:  # noqa: N802
        if self.path.rstrip("/") != "/mcp":
            self._send_json({"error": "not found"}, status=404)
            return
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        try:
            frames = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            self._send_json(
                {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32700, "message": "parse error"},
                },
                status=400,
            )
            return
        if isinstance(frames, dict):
            frames = [frames]
        if not isinstance(frames, list):
            self._send_json(
                {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32600, "message": "invalid request"},
                },
                status=400,
            )
            return
        session = self.headers.get("Mcp-Session-Id")
        responses = []
        new_session = None
        for frame in frames:
            if not isinstance(frame, dict):
                continue
            result = self._handle(frame, session, new_session)
            if result is None:
                continue
            responses.append(result)
            if result.get("result", {}).get("protocolVersion"):
                new_session = session or f"ctx-{int(time.time() * 1000)}"
        if not responses:
            # A notification-only batch: 202 with no body, per the transport.
            self.send_response(202)
            self.send_header("Content-Length", "0")
            if new_session:
                self.send_header("Mcp-Session-Id", new_session)
            self.end_headers()
            return
        payload = responses[0] if len(responses) == 1 else responses
        self._send_json(payload, session=new_session)

    def _handle(
        self, frame: Mapping[str, Any], session: str | None, new_session: str | None
    ) -> dict[str, Any] | None:
        method = str(frame.get("method") or "")
        fid = frame.get("id")
        params = frame.get("params") or {}

        if method == "initialize":
            result = {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": SERVER_NAME, "version": "1.0"},
            }
            return {"jsonrpc": "2.0", "id": fid, "result": result}
        if method.startswith("notifications/"):
            return None
        if fid is None:
            return None
        if method == "ping":
            return {"jsonrpc": "2.0", "id": fid, "result": {}}
        if method == "tools/list":
            return {"jsonrpc": "2.0", "id": fid, "result": {"tools": TOOLS}}
        if method == "tools/call":
            name = str(params.get("name") or "")
            args = params.get("arguments") or {}
            func = TOOL_FUNCS.get(name)
            if func is None:
                return {
                    "jsonrpc": "2.0",
                    "id": fid,
                    "result": {
                        "content": [{"type": "text", "text": f"unknown tool: {name}"}],
                        "isError": True,
                    },
                }
            try:
                out = func(args)
            except Exception as exc:  # a tool that raises is a refusal, not a crash
                out = _error(
                    f"the broker failed to answer: {exc}", verdict="BROKER_ERROR"
                )
            return {"jsonrpc": "2.0", "id": fid, "result": out}
        return {
            "jsonrpc": "2.0",
            "id": fid,
            "error": {"code": -32601, "message": f"method not found: {method}"},
        }


def serve() -> None:
    """Run the broker. The pod's only job.

    The bind address is the loopback by default, and the pod's manifest sets it to the pod's
    own interface, because a Service reaches a container on the container's address. The
    default matters: a laptop that runs this broker must not publish it to the network, and
    the estate's port ledger records 8002 as a loopback door.
    """
    bind = os.environ.get("ESTATE_CONTEXT_BIND", "127.0.0.1")
    httpd = ThreadingHTTPServer((bind, PORT), Handler)
    httpd.daemon_threads = True
    print(f"{SERVER_NAME} listening on {bind}:{PORT} -> {ENGINE_URL}", flush=True)
    httpd.serve_forever()


if __name__ == "__main__":
    serve()
