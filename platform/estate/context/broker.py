#!/usr/bin/env python3
"""broker -- the estate context broker's POLICY. One door; every answer passes here.

WHY THIS FILE EXISTS. The founder's requirement, 2026-10-27: agents must be unable to bypass the
context, the freshness check and the policy. The estate's own measurement (docs/reference/
estate-agent-surface-map.md, gaps G1-G7) says why that is not already true: the policy plane (what
an agent may DO) and the context plane (what an agent may READ) are decoupled, and three
different runtimes reach the estate through three different doors, two of them ungated.

THE SHAPE (founder-approved 2026-10-27, consultant-reviewed). One door, in the cluster:

    agent runtime  --MCP/HTTPS-->  BROKER  --(private, token held only here)-->  gortex engine
                                          |
                                          +-- claim-scoped path allowlist
                                          +-- freshness: index commit == requested commit
                                          +-- token budget
                                          +-- secret scrubbing (values -> REF:<NAME>)
                                          +-- provenance envelope on every excerpt
                                          +-- refusal, with a reason a machine can read

The engine has no public route. That is the whole enforcement argument: a client that bypasses
its own harness still cannot reach the engine, because the only path to it is this policy.

WHAT IS DELIBERATELY NOT HERE. Retrieval, ranking, symbol resolution, impact selection and
change-contract verdicts are gortex's (zzet/gortex v0.64.11, Apache-2.0). Writing a second
ranker is the stitching AGENTS.md 6 forbids. This file decides; the engine answers.

HOW IT IS PROVEN. tests/test_estate_context_broker.py drives every branch below: a refusal that
cannot fail is not a gate, and a decision that is not tested is a comment.

FAIL-CLOSED, AND WHERE IT FAILS OPEN. A stale index, an unproven index, an unreachable engine and
a path outside the claim are all REFUSALS: the caller gets a verdict, not a stale answer. The one
deliberate fail-open is `working_copy` mode, where the engine publishes an incremental route
within a bounded wait (ASYNC_REINDEX): there the answer is allowed but carries the freshness
reason, because the caller asked for the working copy and the engine has one.
"""

from __future__ import annotations

import dataclasses
import fnmatch
import hashlib
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Iterable, Mapping, Sequence

# --- verdicts ---------------------------------------------------------------------------------
# A verdict is a stable string, not an exception: the broker is a service, and a service answers
# with a body. The strings are the contract a client can switch on.
ALLOW = "ALLOW"
STALE_REJECT = "STALE_REJECT"
ASYNC_REINDEX = "ASYNC_REINDEX"
UNPROVEN_INDEX = "UNPROVEN_INDEX"
ENGINE_UNREACHABLE = "ENGINE_UNREACHABLE"
PATH_REFUSED = "PATH_REFUSED"
TOOL_REFUSED = "TOOL_REFUSED"
BUDGET_REFUSED = "BUDGET_REFUSED"
REDACTED = "REDACTED"

# --- the engine's read-only surface ------------------------------------------------------------
# The context plane may ASK questions. It may not change the tree: an edit goes through the
# executor door (intents), which is a different law with a different audit trail. A context tool
# that mutates is refused here rather than trusted, because "the broker only exposes read tools"
# is only true if something refuses the rest.
#
# THE ENGINE'S SURFACE, MEASURED. 2026-10-27, gortex v0.64.11+c7abb9b, on the transport the
# broker actually uses: the engine's REST surface, POST /v1/tools/{name}.
#
# HOW IT WAS MEASURED, IN ONE CALL. Asking the engine for a name it does not have answers
# {"error": "tool_not_found", "available_tools": [...]} -- the engine names what it does have.
# That list was then probed name by name: every one of the 81 names is served (an answer, or the
# tool's own argument error, which is the tool saying it is there and wants an argument), and the
# only refusal is a name that is not on the list.
#
# WHY THE ENGINE'S CATALOGUE IS NOT THE AUTHORITY. `gortex tools list` is preset-filtered: on
# the daemon it published 47 of these 81. Absence from that catalogue proves nothing, which is
# why the allowlist below is checked against THIS surface and not against the catalogue. A name
# the estate invented is refused by the engine with "unknown tool" -- `affected` was on this
# list until the engine was asked, and the engine answered 'unknown tool "affected"'.
#
# WHY THE VERSION LIVES HERE. The allowlist is a claim about one specific engine build. If the
# image the cluster runs is a different engine, the allowlist is a claim about an engine that is
# not there -- so the version sits next to the names, and bin/estate-context-gate fails when the
# Dockerfile's pin and this record disagree.
ENGINE_SURFACE = {
    "engine": "gortex",
    "engine_version": "v0.64.11",
    "engine_build": "v0.64.11+c7abb9b",
    "measured_on": "2026-10-27",
    "surface": "POST /v1/tools/{name}",
    "how_measured": (
        "one call for a name the engine does not have; the engine answers with the names it has "
        "(available_tools). Each of those names was then called: all of them are served. The "
        "engine's own catalogue (`gortex tools list`) is preset-filtered -- it published 47 of "
        "these 81 -- so it is not the authority on what the transport accepts."
    ),
    "tools": frozenset(
        {
            "analyze",
            "ask",
            "batch_edit",
            "capabilities",
            "change",
            "change_contract",
            "check_guards",
            "compare_branches",
            "compare_with_overlay",
            "context_closure",
            "detect_changes",
            "diff_context",
            "edit",
            "edit_file",
            "edit_symbol",
            "explain_view",
            "explore",
            "export_context",
            "find_files",
            "find_implementations",
            "find_usages",
            "get_architecture",
            "get_artifact",
            "get_call_chain",
            "get_callers",
            "get_dependencies",
            "get_dependents",
            "get_diagnostics",
            "get_editing_context",
            "get_file_summary",
            "get_repo_outline",
            "get_symbol",
            "get_symbol_source",
            "get_test_targets",
            "graph_stats",
            "index_health",
            "overlay",
            "overlay_branches",
            "overlay_delete",
            "overlay_drop",
            "overlay_drop_branch",
            "overlay_fork",
            "overlay_keepalive",
            "overlay_list",
            "overlay_merge",
            "overlay_push",
            "overlay_register",
            "overlay_switch",
            "pr",
            "preview_edit",
            "proxy_disable",
            "proxy_enable",
            "proxy_status",
            "publish_review",
            "read",
            "read_file",
            "recall",
            "refactor",
            "relations",
            "remember",
            "rename_symbol",
            "response",
            "review",
            "save_note",
            "search",
            "search_artifacts",
            "search_ast",
            "search_symbols",
            "search_text",
            "session",
            "simulate_chain",
            "smart_context",
            "store_memory",
            "surface_memories",
            "tool_profile",
            "tools_search",
            "trace",
            "verify_change",
            "workspace",
            "workspace_admin",
            "write_file",
        }
    ),
}

# The read-only surface the context plane may ask about. Every name here was measured against
# the surface above -- all of them are served by the engine -- and bin/estate-context-gate
# proves that from the tree alone (check 7: read_only is inside the recorded surface, and the
# deployed image is the engine the surface was measured on). A name that is not on this list is
# refused by tool_decision below, whatever the engine would do with it.
READ_ONLY_TOOLS = frozenset(
    {
        "smart_context",
        "explore",
        "context_closure",
        "search_symbols",
        "get_symbol_source",
        "find_usages",
        "get_test_targets",
        "detect_changes",
        "diff_context",
        "change_contract",
        "verify_change",
        "get_architecture",
        "search_artifacts",
        "get_artifact",
        "index_health",
        "graph_stats",
        "analyze",
        "search_ast",
    }
)

# Tools the engine exposes that write to the tree or the index. Named so the refusal can say WHY
# rather than "not allowed" -- a refusal a client can act on names the door that would work.
#
# THIS LIST IS THE ENGINE'S, MEASURED. gortex v0.64.11's own catalogue
# (`gortex tools list --format json`) classifies each tool as read or mutating, and this list
# is aligned with that classification: a tool the engine calls read-only is NOT here, because
# telling a client "this changes the tree" about a tool that only reads is a lie, and a lie in
# a refusal is worse than a shorter refusal. bin/estate-context-gate checks the alignment
# against the LIVE catalogue and fails when the two disagree; a name the engine does not
# publish (a preset filter, or a version difference) is a warning, not a failure.
MUTATING_TOOLS = frozenset(
    {
        # the tree
        "edit",
        "edit_file",
        "edit_symbol",
        "edit_memory",
        "batch_edit",
        "write_file",
        "apply_code_action",
        "preview_edit",
        # the index and the graph
        "reindex_repository",
        "index_repository",
        "enrich_churn",
        "enrich_releases",
        "export_graph",
        "delete_scope",
        "overlay_push",
        "overlay_drop",
        "simulate_chain",
        # the agent's own learning state
        "feedback",
    }
)

# A secret value is only substituted when it is long enough to be one. The rule is warden's
# (platform/warden/prove.py: "a value shorter than eight characters is not a secret worth
# trusting, and substituting it would mangle unrelated text"), reused here so the estate has one
# rule about what a secret is, not two.
MIN_SECRET_LEN = 8

# Shapes that are a credential wherever they appear, even when the broker was not told the name.
# These are the "unknown name" net under the named-secret pass; each is replaced by an opaque
# reference, never by a value.
SECRET_SHAPES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("OPENAI_KEY", re.compile(r"\bsk-[A-Za-z0-9_\-]{16,}\b")),
    ("GITHUB_TOKEN", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")),
    ("AWS_ACCESS_KEY", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("ANTHROPIC_KEY", re.compile(r"\bsk-ant-[A-Za-z0-9_\-]{16,}\b")),
    ("SLACK_TOKEN", re.compile(r"\bxox[baprs]-[A-Za-z0-9\-]{10,}\b")),
    (
        "PRIVATE_KEY_BLOCK",
        re.compile(
            r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----"
        ),
    ),
    (
        "BEARER_HEADER",
        re.compile(r"(?i)\b(bearer|authorization:\s*bearer)\s+[A-Za-z0-9._\-]{16,}"),
    ),
)

# A credential ASSIGNED to a name: GITHUB_TOKEN = "...", api_key: "...", jwt_secret = "...".
# The name is kept -- the estate refers to a secret by name (AGENTS.md 4) -- and the value never
# leaves. This is a third pass of scrub(), and it lives here rather than in a caller because the
# estate has ONE rule about what a secret is, not two (the same reason MIN_SECRET_LEN is shared
# with platform/warden/prove.py).
ASSIGNED_SECRET = re.compile(
    r"(?i)\b(?P<name>[A-Za-z0-9_]*"
    r"(?:api[_-]?key|secret|token|password|passwd|credential|private[_-]?key|bearer)"
    r"[A-Za-z0-9_]*)\s*[:=]\s*[\"']?(?P<value>[^\s\"',)]{8,})"
)


def _opaque_value(text: str) -> bool:
    """Is this an opaque value, or an ordinary number or path?

    A path ("/run/secrets/x") and a plain number (a token budget) are not credentials, and
    redacting them would mangle the estate's own configuration. A credential value has a letter
    and a digit and no path separator.
    """
    if "/" in text or "\\" in text:
        return False
    return any(c.isalpha() for c in text) and any(c.isdigit() for c in text)


def _ref(name: str) -> str:
    """The opaque reference an agent gets instead of a value: REF:<NAME>, never the value."""
    return f"REF:{name}"


@dataclasses.dataclass(frozen=True)
class Decision:
    """One verdict, with the reason and the evidence that produced it.

    `allow` is the only thing a caller must read to act. `verdict` is the stable string a client
    switches on. `reason` is a sentence a human reads in a log. `evidence` is the machine-checkable
    part: what was compared, what was refused, what was replaced.
    """

    allow: bool
    verdict: str
    reason: str
    evidence: Mapping[str, Any] = dataclasses.field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "allow": self.allow,
            "verdict": self.verdict,
            "reason": self.reason,
            "evidence": dict(self.evidence),
        }


def _allow(reason: str, **evidence: Any) -> Decision:
    return Decision(True, ALLOW, reason, evidence)


def _refuse(verdict: str, reason: str, **evidence: Any) -> Decision:
    return Decision(False, verdict, reason, evidence)


# --- freshness --------------------------------------------------------------------------------
def freshness_decision(
    *,
    index_commit: str | None,
    request_commit: str | None,
    mode: str = "committed",
) -> Decision:
    """Is the index we would answer from the index the caller asked about?

    The estate's law is that a stale answer is not an answer. So the mismatch is a refusal, not a
    warning -- EXCEPT in working-copy mode, where the engine publishes an incremental route for
    the live tree within a bounded wait and the answer carries the freshness reason with it.

    mode="committed": the caller wants the tree at a commit. index_commit must equal it.
    mode="working_copy": the caller wants the live tree. A mismatch is ASYNC_REINDEX -- allowed,
        but the evidence says the answer was served from the last published route.

    UNPROVEN_INDEX (no index commit at all) is always a refusal: an index nobody can tie to a
    commit is not evidence of anything.
    """
    if mode not in ("committed", "working_copy"):
        raise ValueError(f"unknown freshness mode: {mode!r}")
    if not index_commit:
        return _refuse(
            UNPROVEN_INDEX,
            "no index commit is proven for this repository; the index was never built or never stamped",
            index_commit=index_commit,
            request_commit=request_commit,
            mode=mode,
        )
    if request_commit and index_commit == request_commit:
        return _allow(
            "the index commit is the commit that was asked about",
            index_commit=index_commit,
            request_commit=request_commit,
            mode=mode,
        )
    if mode == "working_copy":
        return Decision(
            True,
            ASYNC_REINDEX,
            "the working copy moved past the indexed commit; the engine publishes an incremental route within the wait deadline",
            {
                "index_commit": index_commit,
                "request_commit": request_commit,
                "mode": mode,
                "freshness_reason": "stale_index_incremental_route",
            },
        )
    return _refuse(
        STALE_REJECT,
        f"the index is at {index_commit} and the request asked about {request_commit or 'an unstated commit'}",
        index_commit=index_commit,
        request_commit=request_commit,
        mode=mode,
    )


# --- claims and paths -------------------------------------------------------------------------
def path_allowed(path: str, allowed: Iterable[str]) -> bool:
    """Is this path inside the live claim's paths?

    Two rules, both load-bearing:

    1. The path must be repo-relative and must not escape the repository. A path that walks up
       with "..", or that is absolute, is refused before any glob is consulted: a glob match on a
       traversing path is a claim that reads the whole filesystem.
    2. The glob set is matched with fnmatch, the same matcher bin/claim-gate uses, so the broker
       and the CI gate agree about what a claim covers. One matcher, one answer.
    """
    if not path or path.startswith("/") or "\x00" in path:
        return False
    norm = os.path.normpath(path)
    if norm.startswith("..") or norm == ".":
        return False
    for pattern in allowed:
        if not pattern:
            continue
        if fnmatch.fnmatch(norm, pattern) or fnmatch.fnmatch(path, pattern):
            return True
        # A claim that names a directory covers what is under it, the way claim-gate's "web/**"
        # style glob does.
        if pattern.endswith("/**") and fnmatch.fnmatch(norm, pattern[:-3] + "/" + norm):
            return True
    return False


def path_decision(paths: Sequence[str], allowed: Iterable[str]) -> Decision:
    """Refuse the whole request when any path is outside the claim.

    All-or-nothing on purpose: a request that names one path outside the claim is refused as a
    whole, because a partially served request is how a boundary leaks.
    """
    allowed = list(allowed)
    outside = [p for p in paths if not path_allowed(p, allowed)]
    if outside:
        return _refuse(
            PATH_REFUSED,
            "a path in this request is outside the live claim's paths: "
            + ", ".join(outside[:5]),
            outside=outside,
            allowed=allowed,
        )
    return _allow(
        "every path in the request is inside the live claim", paths=list(paths)
    )


# --- tools ------------------------------------------------------------------------------------
def tool_decision(tool: str) -> Decision:
    """The context plane reads. It does not write.

    A mutating tool is refused with the door that would work, so the client is not stuck: an
    edit belongs to the executor (intents), a reindex belongs to CI.
    """
    if tool in MUTATING_TOOLS:
        return _refuse(
            TOOL_REFUSED,
            f"{tool} changes the tree or the index; the context broker only reads. "
            "Use the executor door for an action, and CI for an index",
            tool=tool,
        )
    if tool not in READ_ONLY_TOOLS:
        return _refuse(
            TOOL_REFUSED,
            f"{tool} is not on the broker's read-only surface; a context request may only ask "
            "questions of the engine",
            tool=tool,
        )
    return _allow(f"{tool} is read-only", tool=tool)


# --- budget -----------------------------------------------------------------------------------
def budget_decision(tokens: int, budget: int) -> Decision:
    """A context budget is a ceiling, not a suggestion.

    Over budget is a refusal with the number in it, so the caller can narrow the query instead
    of guessing. The engine has its own graceful degradation (it drops tiers and stamps the
    drop); this is the outer wall that the engine's own budget sits inside.
    """
    if budget <= 0:
        return _refuse(
            BUDGET_REFUSED, "no token budget was set for this request", budget=budget
        )
    if tokens > budget:
        return _refuse(
            BUDGET_REFUSED,
            f"the answer needs {tokens} tokens and the budget is {budget}; narrow the query",
            tokens=tokens,
            budget=budget,
        )
    return _allow("the answer fits the budget", tokens=tokens, budget=budget)


# --- secrets ----------------------------------------------------------------------------------
def scrub(text: str, secrets: Mapping[str, str] | None = None) -> tuple[str, list[str]]:
    """Remove every credential from text about to leave the broker, and say what was removed.

    Three passes, in this order, because they fail differently:

    1. Named: the broker is told the NAME and the VALUE of what the estate knows is a secret
       (from the vault, by name). A named value is replaced everywhere it appears, with the
       percent-encoded form too -- the same rule platform/warden/prove.py applies, so an echo of
       a key in an error body cannot escape.
    2. Shaped: a token that LOOKS like a credential is replaced even if nobody named it, because
       a value the broker never saw is exactly the value that leaks.
    3. Assigned: a value bound to a credential-shaped NAME (GITHUB_TOKEN = "...") is replaced even
       when its shape is unknown. The name stays, because a reference to a secret is by name.

    The agent receives REF:<NAME> -- an opaque reference it can ask the estate about by name.
    It never receives the value, and it never receives a blank that hides which secret it was.
    """
    out = text
    removed: list[str] = []
    for name, value in (secrets or {}).items():
        value = str(value or "")
        if len(value) < MIN_SECRET_LEN:
            continue
        if value in out:
            out = out.replace(value, _ref(name))
            removed.append(name)
        quoted = urllib.parse.quote(value, safe="")
        if quoted != value and quoted in out:
            out = out.replace(quoted, _ref(name))
            if name not in removed:
                removed.append(name)
    for name, pattern in SECRET_SHAPES:
        if pattern.search(out):
            out = pattern.sub(_ref(name), out)
            if name not in removed:
                removed.append(name)

    def _assigned(match: re.Match) -> str:
        value = match.group("value")
        if not _opaque_value(value):
            return match.group(0)
        name = match.group("name")
        if name not in removed:
            removed.append(name)
        return f"{name}={_ref(name)}"

    out = ASSIGNED_SECRET.sub(_assigned, out)
    return out, sorted(set(removed))


# --- provenance -------------------------------------------------------------------------------
def file_digest(path: str) -> str:
    """sha256 of a file's bytes. The digest the envelope quotes, so an excerpt can be checked."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def provenance(
    path: str, commit: str, start_line: int, end_line: int, digest: str | None = None
) -> dict[str, Any]:
    """The envelope every excerpt carries: which file, which commit, which lines, which digest.

    Without this, a context answer is a rumour. With it, any line can be checked against the
    commit it claims to come from.
    """
    return {
        "file": path,
        "commit": commit,
        "start_line": int(start_line),
        "end_line": int(end_line),
        "sha256": digest,
    }


def envelope(
    content: str,
    prov: Mapping[str, Any],
    *,
    secrets: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Wrap an excerpt with its provenance, with every credential in it scrubbed."""
    clean, removed = scrub(content, secrets)
    return {
        "provenance": dict(prov),
        "content": clean,
        "redacted": removed,
        "content_sha256": hashlib.sha256(clean.encode("utf-8")).hexdigest(),
    }


# --- the request -------------------------------------------------------------------------------
@dataclasses.dataclass(frozen=True)
class ContextRequest:
    """What a client asked the broker for."""

    tool: str
    paths: Sequence[str] = ()
    request_commit: str | None = None
    mode: str = "committed"
    token_budget: int = 0
    estimated_tokens: int = 0


@dataclasses.dataclass(frozen=True)
class BrokerState:
    """What the broker knows about the estate right now."""

    index_commit: str | None = None
    # The commit the repository is at. A caller that names no commit means "the tree as it is",
    # and the broker resolves that against the HEAD it already serves -- it never guesses a
    # commit to be kind.
    head_commit: str | None = None
    claim_paths: Sequence[str] = ()
    secrets: Mapping[str, str] = dataclasses.field(default_factory=dict)
    engine_reachable: bool = True


def decide_request(request: ContextRequest, state: BrokerState) -> Decision:
    """The one function every context request passes through. Order is the argument.

    1. the tool must be read-only      (the context plane cannot change the tree)
    2. the engine must be reachable     (no answer is better than a stale one)
    3. the index must match the commit  (a stale answer is not an answer)
    4. every path must be inside the claim  (no work outside a claim)
    5. the answer must fit the budget  (a budget is a ceiling)

    Each step refuses with its own verdict, so the caller learns WHICH law refused it -- a
    refusal that cannot be acted on is a refusal that gets worked around.
    """
    decision = tool_decision(request.tool)
    if not decision.allow:
        return decision
    if not state.engine_reachable:
        return _refuse(
            ENGINE_UNREACHABLE,
            "the context engine is unreachable; the broker will not serve an answer it cannot vouch for",
            tool=request.tool,
        )
    # The commit the answer must match: the one the caller named, or the HEAD the broker serves.
    effective_commit = request.request_commit or state.head_commit
    if not effective_commit:
        return _refuse(
            STALE_REJECT,
            "no commit was named and the broker does not know this repository's HEAD, so the "
            "freshness of any answer cannot be established",
            tool=request.tool,
            index_commit=state.index_commit,
        )
    decision = freshness_decision(
        index_commit=state.index_commit,
        request_commit=effective_commit,
        mode=request.mode,
    )
    if not decision.allow:
        return decision
    if request.paths:
        decision = path_decision(request.paths, state.claim_paths)
        if not decision.allow:
            return decision
    if request.estimated_tokens:
        decision = budget_decision(request.estimated_tokens, request.token_budget)
        if not decision.allow:
            return decision
    return _allow(
        "the request is inside the claim, the index matches the commit, and the answer fits the budget",
        tool=request.tool,
        paths=list(request.paths),
        index_commit=state.index_commit,
        request_commit=effective_commit,
        mode=request.mode,
    )


# --- the engine adapter ------------------------------------------------------------------------
class EngineError(RuntimeError):
    """The engine could not answer. The broker refuses rather than inventing an answer."""

    def __init__(self, message: str, *, verdict: str = ENGINE_UNREACHABLE):
        super().__init__(message)
        self.verdict = verdict


def unwrap_engine_envelope(tool: str, payload: Any) -> Any:
    """Open the engine's answer envelope and return the answer inside it.

    MEASURED against gortex v0.64.11's REST surface (POST /v1/tools/{name}): the engine
    answers in the MCP tool-result envelope -- {"content": [{"type": "text", "text": "<json>"}]}
    -- and not as the bare payload. A client that stops at the envelope gets a dictionary
    with a "content" key where the working set should be: no files, no symbols, no blast
    radius, and an answer that LOOKS like it worked.

    So the envelope is opened HERE, in the one place that speaks the engine's wire format.
    An answer that is already bare (a payload without a content list) is passed through
    unchanged -- the rule is "unwrap if it is wrapped", never "assume it is wrapped".
    """
    if not isinstance(payload, dict) or not isinstance(payload.get("content"), list):
        return payload
    for item in payload["content"]:
        if not isinstance(item, dict) or item.get("type") != "text":
            continue
        text = item.get("text")
        if not isinstance(text, str):
            continue
        try:
            return json.loads(text)
        except ValueError as exc:
            raise EngineError(
                f"the engine answered {tool} with JSON inside its envelope that is not JSON"
            ) from exc
    raise EngineError(
        f"the engine answered {tool} with an envelope that carried no text"
    )


class EngineClient:
    """A thin HTTP client for the private engine (gortex daemon --http-addr).

    The engine is reachable only from inside the cluster; this client holds the token and is the
    only thing in the estate that does. The client is deliberately dumb: it speaks the engine's
    REST surface (POST /v1/tools/{name}) and translates failures into EngineError. All judgement
    lives in the policy above, not here.
    """

    def __init__(self, base_url: str, token: str, *, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self._token = token
        self.timeout = timeout

    def call(self, tool: str, args: Mapping[str, Any]) -> Any:
        """Invoke a read-only tool on the engine, or raise EngineError."""
        if tool not in READ_ONLY_TOOLS:
            raise EngineError(
                f"{tool} is not on the broker's read-only surface",
                verdict=TOOL_REFUSED,
            )
        body = json.dumps(args).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self._token:
            # The header goes out only when there IS a token. An empty bearer is worse than no
            # bearer: it looks like an authenticated call to a reader of the wire.
            headers["Authorization"] = f"Bearer {self._token}"
        # S310: the scheme is the engine's own configured address (http/https), never a
        # caller-supplied one, and the token in the header is the only credential on the wire.
        req = urllib.request.Request(  # noqa: S310
            f"{self.base_url}/v1/tools/{tool}",
            data=body,
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:  # noqa: S310
                raw = resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:  # the engine answered, and said no
            detail = exc.read().decode("utf-8", "replace")[:500]
            raise EngineError(
                f"the engine refused {tool}: HTTP {exc.code} {detail}",
                verdict=ENGINE_UNREACHABLE,
            ) from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise EngineError(f"the engine is unreachable: {exc}") from exc
        try:
            payload = json.loads(raw)
        except ValueError as exc:
            raise EngineError(
                f"the engine answered {tool} with something that is not JSON"
            ) from exc
        return unwrap_engine_envelope(tool, payload)
