#!/usr/bin/env python3
"""forensic_extract.py - faithful replay of agent transcripts (Pi + Cline) into a classified work ledger.

v2. Every mutation is replayed with the runtime's own semantics (forensic_replay.py, validated
against the real Pi runtime and the real upstream Cline executors), globally ordered by wall-clock
timestamp, with base recovery for paths whose first mutation was an edit.

Read-only on the transcripts. Writes only under --out.

  python3 forensic_extract.py --out ~/claude-forensics/forensic-$(date +%Y%m%d)

Outputs
  manifest.json / manifest.csv  every path the agents mutated, classified, with the reconstructed
                                sha256, the provenance of every byte, and the replay evidence
  recovered/                     the rebuilt file tree
  sessions.json                  per session: model, prompt, tools, plans, intent usage
  commands_ledger.jsonl          destructive / landing commands with issue refs
  streams.md                     the classification summary
"""

import argparse
import collections
import csv
import datetime
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import forensic_replay as FR  # noqa: E402

# Git is resolved to an absolute path once: a partial executable path is a PATH-hijack
# surface, and the extractor runs on transcripts that describe other agents' commands.
GIT = shutil.which("git") or "git"

HOME = os.path.expanduser("~")

STREAMS = [  # first match wins as primary; every match is kept as a tag
    ("router-spof", r"router|ladder|failover|fallback|spof|litellm|gateway|selector"),
    (
        "headless-agents",
        r"headless|pi-agent|pi_agent|supervisor|dept-launch|fleetview|agent-launch|executor|daemon|\.pi/",
    ),
    (
        "founder-surfaces",
        r"telegram|cockpit|desktop|founder|face\b|surface|meridian|voice|fleet|public.?domain",
    ),
    (
        "memory-discovery",
        r"memory|memdoor|retriev|oracle|discover|growmos|estate-graph|recall|embedding",
    ),
    (
        "metrics",
        r"metric|telemetry|observab|prometheus|grafana|usage|token|cost|dashboard|\bslo\b|friction",
    ),
    (
        "governance-gates",
        r"gate|gherkin|plan.?lock|fs_guard|prepush|enforce|firewall|claim|bdd",
    ),
    (
        "infra-oci-disk",
        r"\boci\b|nodepool|disk|reclaim|terraform|tfvars|kube|k8s|tailscale|launchd",
    ),
    ("departments", r"department|dept|media|charter|autonomous"),
    ("estate-intent", r"\.estate/intents|/intents/"),
    ("docs-tickets", r"\.md$|/docs/|tickets"),
]
DESTRUCTIVE = re.compile(
    r"git\s+clean|git\s+reset\s+--hard|git\s+worktree\s+(remove|prune)|git\s+branch\s+-D"
    r"|git\s+stash\s+(drop|clear)|git\s+push\s+.*(--force|-f\b)"
    r"|rm\s+-[a-zA-Z]*r[a-zA-Z]*f|rm\s+-[a-zA-Z]*f[a-zA-Z]*r|gc\s+--prune"
    r"|\bkill\s+-9|pkill|killall|launchctl\s+(bootout|remove|unload)"
)
LANDING = re.compile(
    r"git\s+commit|git\s+push|gh\s+pr\s+(create|merge)|lane-submit|git\s+worktree\s+add"
    r"|git\s+checkout\s+-b|git\s+switch\s+-c|gh\s+api\s+.*(merge|pulls)"
)
REFS = re.compile(r"(?:#|issues/|pull/)(\d{3,5})\b")
RM_PATH = re.compile(r"(?:^|[;&|]\s*)rm\s+(?:-[A-Za-z-]+\s+)*([^\s;&|]+)")
UNICODE_SPACES = re.compile("[\\u00a0\\u1680\\u2000-\\u200a\\u202f\\u205f\\u3000]")
TRUNCATION_MARKS = ("Showing lines ", "more lines in file", " limit. Use bash:")


# ---------------------------------------------------------------------------
# helpers (kept compatible with v1 so the manifest contract does not move)
# ---------------------------------------------------------------------------


def iso(ts):
    try:
        if isinstance(ts, (int, float)) or (isinstance(ts, str) and ts.isdigit()):
            return (
                datetime.datetime.fromtimestamp(
                    int(ts) / 1000, datetime.timezone.utc
                ).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]
                + "Z"
            )
    except Exception:  # noqa: S110 -- the raw timestamp is the fallback, not an error
        pass
    return ts


def canon(p):
    if not p:
        return p
    p = os.path.normpath(p.replace("~", HOME, 1) if p.startswith("~") else p)
    # macOS resolves /tmp to /private/tmp; the comparison is a path canonicalisation and
    # writes nothing, so the literal is safe here.
    return "/private" + p if p.startswith("/tmp/") or p == "/tmp" else p  # noqa: S108


def location_class(p):
    if "/.estate/intents/" in p:
        return "estate-intent-store"
    if "/.estate/worktrees/" in p:
        return "estate-worktree"
    if "/Documents/code/.lanes" in p:
        return "lane"
    if "/Documents/code/idp-worktrees" in p or "/Documents/code/idp-wt" in p:
        return "idp-worktree"
    if p.startswith("/private/tmp"):
        return "VOLATILE-tmp"
    if "/Documents/code/" in p:
        return "repo"
    return "other"


def stream_of(text):
    tags = [n for n, rx in STREAMS if re.search(rx, text, re.I)]
    return (tags[0] if tags else "unclassified"), tags


def sha(s):
    return hashlib.sha256(s.encode("utf-8", "replace")).hexdigest()


def resolve_pi(p, cwd):
    """Port of resolveToCwd (normalizePath + resolvePath) from pi's utils/paths.js."""
    if not isinstance(p, str) or not p:
        return None
    p = UNICODE_SPACES.sub(" ", p)
    if p.startswith("@"):
        p = p[1:]
    if p == "~":
        p = HOME
    elif p.startswith("~/"):
        p = os.path.join(HOME, p[2:])
    if os.path.isabs(p):
        return os.path.normpath(p)
    return os.path.normpath(os.path.join(cwd or os.getcwd(), p))


def read_text(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace", newline="") as f:
            return f.read()
    except Exception:
        return None


def extract_text(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        out = []
        for block in content:
            if isinstance(block, dict):
                if isinstance(block.get("text"), str):
                    out.append(block["text"])
                elif isinstance(block.get("content"), str):
                    out.append(block["content"])
            elif isinstance(block, str):
                out.append(block)
        return "\n".join(out)
    return ""


# ---------------------------------------------------------------------------
# content store: big payloads live on disk, not in memory
# ---------------------------------------------------------------------------


class Store(object):
    def __init__(self, root):
        self.root = root
        os.makedirs(root, exist_ok=True)
        self.writes = 0
        self.bytes = 0

    def put(self, text):
        raw = text.encode("utf-8", "surrogatepass")
        # Content addressing for a dedupe store, not a security primitive: the manifest
        # carries the sha256 of every file's final bytes. Changing this would invalidate the
        # 343 MiB store the authoritative extraction already wrote.
        h = hashlib.sha1(raw).hexdigest()  # noqa: S324
        p = os.path.join(self.root, h[:2], h)
        if not os.path.exists(p):
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "wb") as f:
                f.write(raw)
            self.writes += 1
            self.bytes += len(raw)
        return h

    def get(self, ref):
        if not ref:
            return None
        p = os.path.join(self.root, ref[:2], ref)
        try:
            with open(p, "rb") as f:
                return f.read().decode("utf-8", "replace")
        except Exception:
            return None


# ---------------------------------------------------------------------------
# indexing
# ---------------------------------------------------------------------------


class Recorder(object):
    def __init__(self, store):
        self.store = store
        self.ops = []
        self.reads = []
        self.reads_by_call = {}
        self.pending_reads = {}
        self.results = {}
        self.sessions = []
        self.ledger = []
        self.seq = 0
        # 2026-10-31: a transcript record that cannot be parsed must cost that record, not
        # the run. parse_errors names every one of them, so a silent gap is never mistaken
        # for "the agent never touched this file".
        self.parse_errors = []

    def add_op(self, op):
        op["seq"] = self.seq
        self.seq += 1
        self.ops.append(op)
        return op

    def result_text(self, cid):
        r = self.results.get(cid)
        if not r:
            return None
        if r.get("text") is not None:
            return r["text"]
        return self.store.get(r.get("text_ref"))


def ingest_command(cmd, ledger, sess, ts, tool):
    if not cmd or not isinstance(cmd, str):
        return
    flag = []
    if DESTRUCTIVE.search(cmd):
        flag.append("DESTRUCTIVE")
    if LANDING.search(cmd):
        flag.append("LANDING")
    refs = sorted(set(REFS.findall(cmd)))
    if flag or refs:
        ledger.append(
            dict(session=sess, ts=ts, tool=tool, flags=flag, refs=refs, cmd=cmd[:600])
        )


def rm_targets(cmd):
    out = []
    if not isinstance(cmd, str):
        return out
    for m in RM_PATH.finditer(cmd):
        t = m.group(1).strip("'\"")
        if t.startswith("/") or t.startswith("./") or "/" in t:
            out.append(t)
    return out


def parse_pi(path, rec):
    sid = os.path.basename(path).split("_")[-1].replace(".jsonl", "")
    info = dict(
        session=sid,
        agent="pi",
        file=path,
        model=None,
        cwd=None,
        started=None,
        ended=None,
        prompt=None,
        tool_calls=0,
        intents=collections.Counter(),
        plans=[],
        files=set(),
    )
    cwd = None
    with open(path, errors="replace") as f:
        for line in f:
            try:
                r = json.loads(line)
            except Exception as err:
                # A malformed line costs that line, not the session, and it is reported: a
                # silent gap must never look like "the agent never touched this file".
                rec.parse_errors.append(
                    dict(
                        file=path,
                        session=sid,
                        error="json: %s: %s" % (type(err).__name__, err),
                    )
                )
                continue
            if not isinstance(r, dict):
                continue
            # 2026-10-31: one malformed record (a plan whose subgoal id was a dict, not a
            # string) killed the whole run at parse time and left a 343 MiB store with no
            # manifest. A transcript is a foreign, concurrently-written file: a record that
            # cannot be understood must cost that record, not the corpus. The guard is
            # per record, so the rest of the session is still indexed.
            try:
                _parse_pi_record(rec, info, r, cwd)
            except Exception as err:  # noqa: BLE001 -- a bad record must not end the run
                rec.parse_errors.append(
                    dict(
                        file=path,
                        session=sid,
                        error="%s: %s" % (type(err).__name__, err),
                    )
                )
                continue
            cwd = info.get("cwd")
    rec.sessions.append(info)


def _parse_pi_record(rec, info, r, cwd):
    t = r.get("type")
    if t == "session":
        cwd = r.get("cwd")
        info["cwd"] = cwd
        info["started"] = r.get("timestamp")
        info["ended"] = r.get("timestamp")
    elif t == "model_change":
        info["model"] = "%s/%s" % (r.get("provider"), r.get("modelId"))
    elif t == "message":
        m = r.get("message")
        if not isinstance(m, dict):
            return
        role = m.get("role")
        ts = m.get("timestamp") or 0
        if role == "user":
            if not info["prompt"]:
                info["prompt"] = extract_text(m.get("content"))[:300]
            info["ended"] = r.get("timestamp") or info["ended"]
        elif role == "toolResult":
            cid = m.get("toolCallId")
            details = m.get("details") if isinstance(m.get("details"), dict) else {}
            patch = details.get("patch") if isinstance(details, dict) else None
            text = extract_text(m.get("content"))
            rec.results[cid] = {
                "is_error": bool(m.get("isError")),
                "ts": ts,
                "tool": m.get("toolName"),
                "text_ref": rec.store.put(text),
                "patch_ref": rec.store.put(patch) if isinstance(patch, str) else None,
                "truncated": bool(
                    isinstance(details, dict) and details.get("truncation")
                ),
            }
            entry = rec.reads_by_call.get(cid)
            if entry is not None:
                entry["snapshot_ref"] = rec.store.put(text)
                entry["truncated"] = bool(
                    isinstance(details, dict) and details.get("truncation")
                )
        elif role == "assistant":
            blocks = m.get("content")
            if isinstance(blocks, list):
                for blk in blocks:
                    if not isinstance(blk, dict) or blk.get("type") != "toolCall":
                        continue
                    handle_pi_call(rec, info, blk, ts, cwd)


def handle_pi_call(rec, info, blk, ts, cwd):
    name = blk.get("name")
    args = blk.get("arguments")
    if not isinstance(args, dict):
        args = {}
    cid = blk.get("id")
    info["tool_calls"] += 1
    if name == "write":
        p = args.get("path")
        target = resolve_pi(p, cwd) if isinstance(p, str) else None
        content = args.get("content")
        ref = rec.store.put(content) if isinstance(content, str) else None
        if target:
            info["files"].add(canon(target))
            rec.add_op(
                dict(
                    agent="pi",
                    kind="write",
                    session=info["session"],
                    ts=ts,
                    tool=name,
                    call_id=cid,
                    path=canon(target),
                    content_ref=ref,
                    args_ref=None,
                    cwd=cwd,
                )
            )
    elif name == "edit":
        p = args.get("path")
        target = resolve_pi(p, cwd) if isinstance(p, str) else None
        if target:
            info["files"].add(canon(target))
            rec.add_op(
                dict(
                    agent="pi",
                    kind="edit",
                    session=info["session"],
                    ts=ts,
                    tool=name,
                    call_id=cid,
                    path=canon(target),
                    args_ref=rec.store.put(json.dumps(args)),
                    cwd=cwd,
                )
            )
    elif name == "read":
        p = args.get("path")
        target = resolve_pi(p, cwd) if isinstance(p, str) else None
        if target:
            entry = dict(
                agent="pi",
                kind="read",
                session=info["session"],
                ts=ts,
                tool=name,
                call_id=cid,
                path=canon(target),
                offset=args.get("offset"),
                limit=args.get("limit"),
                cwd=cwd,
                snapshot_ref=None,
                truncated=False,
                lossy=False,
            )
            rec.reads.append(entry)
            rec.reads_by_call[cid] = entry
    elif name in ("bash", "estate_execute"):
        cmd = args.get("command")
        ingest_command(cmd, rec.ledger, info["session"], ts, name)
        for t in rm_targets(cmd):
            target = resolve_pi(t, cwd)
            if target:
                rec.add_op(
                    dict(
                        agent="pi",
                        kind="delete",
                        session=info["session"],
                        ts=ts,
                        tool=name,
                        call_id=cid,
                        path=canon(target),
                        args_ref=None,
                        cwd=cwd,
                    )
                )
    elif name == "estate_invoke":
        info["intents"][args.get("intent")] += 1
        ingest_command(
            "%s %s" % (args.get("intent"), json.dumps(args.get("args"))[:400]),
            rec.ledger,
            info["session"],
            ts,
            name,
        )
    elif name == "declare_plan":
        goal = args.get("goal")
        subgoals = {}
        for s in args.get("subgoals") or []:
            if not isinstance(s, dict):
                continue
            key = s.get("id")
            if not isinstance(key, str):
                key = json.dumps(key, sort_keys=True, default=str)
            text = s.get("text")
            if not isinstance(text, str):
                text = "" if text is None else str(text)
            subgoals[key] = text[:160]
        plan = dict(
            goal=(goal[:300] if isinstance(goal, str) else ""),
            subgoals=subgoals,
            done=[],
        )
        info["plans"].append(plan)
    elif name == "complete_goal":
        for p in info["plans"]:
            p["done"].append(args.get("goal_id"))


def parse_cline(path, rec):
    try:
        with open(path, errors="replace") as f:
            d = json.load(f)
    except Exception:
        return
    meta0 = {}
    jp = path.replace(".messages.json", ".json")
    try:
        with open(jp, errors="replace") as f:
            meta0 = json.load(f)
    except Exception:
        meta0 = {}
    sid = d.get("sessionId") or os.path.basename(path).split(".")[0]
    cwd = meta0.get("cwd") or (d.get("metadata") or {}).get("cwd")
    info = dict(
        session=sid,
        agent="cline",
        file=path,
        model=meta0.get("model"),
        cwd=cwd,
        started=meta0.get("started_at"),
        ended=meta0.get("ended_at"),
        status=meta0.get("status"),
        prompt=(meta0.get("prompt") or "")[:300],
        tool_calls=0,
        intents=collections.Counter(),
        plans=[],
        files=set(),
        checkpoints=[
            x.get("ref")
            for x in ((meta0.get("metadata") or {}).get("checkpoint") or {}).get(
                "history", []
            )
        ],
    )
    messages = d.get("messages") if isinstance(d, dict) else None
    for m in messages or []:
        if not isinstance(m, dict):
            continue
        ts = m.get("ts") or 0
        content = m.get("content")
        if not isinstance(content, list):
            continue
        for blk in content:
            if not isinstance(blk, dict):
                continue
            btype = blk.get("type")
            if btype == "tool_use":
                handle_cline_call(rec, info, blk, ts, cwd)
            elif btype == "tool_result":
                cid = blk.get("tool_use_id")
                body = blk.get("content")
                text = body if isinstance(body, str) else extract_text(body)
                parsed = None
                try:
                    parsed = json.loads(text)
                except Exception:
                    parsed = None
                rec.results[cid] = {
                    "is_error": bool(blk.get("is_error")),
                    "ts": ts,
                    "tool": blk.get("name"),
                    "text": text,
                    "raw": body,
                    "parsed": parsed if isinstance(parsed, dict) else None,
                    "truncated": False,
                }
                if cid in rec.pending_reads:
                    attach_cline_reads(rec, cid, ts, info)
    rec.sessions.append(info)


def handle_cline_call(rec, info, blk, ts, cwd):
    name = blk.get("name")
    args = blk.get("input")
    if not isinstance(args, dict):
        args = {}
    cid = blk.get("id")
    info["tool_calls"] += 1
    if name == "editor":
        p = args.get("path")
        if isinstance(p, str) and p:
            try:
                target = FR.cline_resolve_file_path(cwd or os.getcwd(), p, False)
            except Exception:
                target = None
            if target:
                info["files"].add(canon(target))
                rec.add_op(
                    dict(
                        agent="cline",
                        kind="editor",
                        session=info["session"],
                        ts=ts,
                        tool=name,
                        call_id=cid,
                        path=canon(target),
                        args_ref=rec.store.put(json.dumps(args)),
                        cwd=cwd,
                    )
                )
    elif name == "apply_patch":
        patch = args.get("input")
        if isinstance(patch, str) and patch:
            rec.add_op(
                dict(
                    agent="cline",
                    kind="patch",
                    session=info["session"],
                    ts=ts,
                    tool=name,
                    call_id=cid,
                    path=None,
                    args_ref=rec.store.put(json.dumps(args)),
                    cwd=cwd,
                )
            )
            for f in patch_files(patch, cwd):
                info["files"].add(f)
    elif name == "read_files":
        rec.pending_reads[cid] = (ts, info["session"])
    elif name == "run_commands":
        for c in args.get("commands") or []:
            cmd = c if isinstance(c, str) else json.dumps(c)
            ingest_command(cmd, rec.ledger, info["session"], ts, name)
            for t in rm_targets(cmd):
                target = resolve_pi(t, cwd)
                if target:
                    rec.add_op(
                        dict(
                            agent="cline",
                            kind="delete",
                            session=info["session"],
                            ts=ts,
                            tool=name,
                            call_id=cid,
                            path=canon(target),
                            args_ref=None,
                            cwd=cwd,
                        )
                    )


def cline_numbered_to_text(listing):
    """Rebuild file content from a Cline `read_files` numbered listing ('  7 | line')."""
    if not isinstance(listing, str) or not listing:
        return None
    raw = listing.split("\n")
    if raw and raw[-1] == "":
        raw.pop()
    lines = []
    for line in raw:
        m = re.match(r"^\s*(\d+) \|( ?)(.*)$", line)
        if not m:
            return None
        lines.append(m.group(3))
    return "\n".join(lines)


def attach_cline_reads(rec, cid, ts, info):
    """Turn a Cline read_files result into per-path content snapshots."""
    res = rec.results.get(cid) or {}
    body = res.get("raw")
    if body is None:
        body = res.get("text")
    items = []
    if isinstance(body, str):
        try:
            body = json.loads(body)
        except Exception:
            body = None
    if isinstance(body, list):
        items = [b for b in body if isinstance(b, dict)]
    elif isinstance(body, dict):
        items = [body]
    for item in items:
        path = item.get("query") or item.get("path")
        listing = item.get("result")
        if not isinstance(path, str) or not isinstance(listing, str):
            continue
        text = cline_numbered_to_text(listing)
        if text is None:
            continue
        target = canon(path)
        entry = dict(
            agent="cline",
            kind="read",
            session=info["session"],
            ts=ts,
            tool="read_files",
            call_id="%s|%s" % (cid, target),
            path=target,
            snapshot_ref=rec.store.put(text),
            truncated=False,
            lossy=True,
        )
        rec.reads.append(entry)


def patch_files(patch_text, cwd):
    out = []
    for line in FR.cline_normalize_patch_input(patch_text):
        for marker in (FR.PATCH_ADD, FR.PATCH_UPDATE, FR.PATCH_DELETE):
            if line.startswith(marker):
                rel = line[len(marker) :].strip()
                try:
                    out.append(
                        canon(
                            FR.cline_resolve_file_path(cwd or os.getcwd(), rel, False)
                        )
                    )
                except Exception:  # noqa: S110 -- an unresolvable marker names no file
                    pass
    return out


# ---------------------------------------------------------------------------
# base recovery
# ---------------------------------------------------------------------------


def git_repo_for(path):
    d = os.path.dirname(path)
    for _ in range(40):
        if os.path.exists(os.path.join(d, ".git")):
            return d
        nd = os.path.dirname(d)
        if nd == d:
            break
        d = nd
    return None


def git_candidates(path, limit=5):
    repo = git_repo_for(path)
    if not repo:
        return []
    rel = os.path.relpath(path, repo)
    try:
        out = subprocess.run(  # noqa: S603 -- a fixed git argv, no user input
            [GIT, "-C", repo, "log", "--all", "--format=%H", "--", rel],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=30,
        )
    except Exception:
        return []
    shas = [x for x in out.stdout.decode("utf-8", "replace").split() if x][:limit]
    cands = []
    for sh in shas:
        try:
            blob = subprocess.run(  # noqa: S603 -- a fixed git argv, no user input
                [GIT, "-C", repo, "show", "%s:%s" % (sh, rel)],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                timeout=30,
            )
        except Exception:  # noqa: S112 -- one unreadable blob is one lost candidate
            continue
        if blob.returncode != 0:
            continue
        cands.append(("git:%s" % sh[:12], blob.stdout.decode("utf-8", "replace")))
    return cands


def patch_applies(base, patch, expected):
    """True when the runtime's own patch transforms base into expected."""
    if not patch:
        return None
    try:
        body = FR.pi_split_bom(base)[1]
        want = FR.pi_normalize_to_lf(FR.pi_split_bom(expected)[1])
        got = FR.apply_unified_patch(FR.pi_normalize_to_lf(body), patch)
    except Exception:
        return False
    return got == want


def diff_matches(old, new, recorded):
    """True when the runtime's own diff of (old -> new) equals the recorded diff."""
    if not recorded:
        return None
    try:
        got = FR.cline_create_line_diff(old, new)
    except Exception:
        return False
    return got.strip() == recorded.strip()


def extract_diff(text):
    """The ```diff block of a Cline editor result (the human-readable `result` field).

    The diff body can itself contain markdown fences (```bash), so the block ends at
    the LAST fence, not the first one after the opening.
    """
    if not text or "```diff" not in text:
        return None
    start = text.index("```diff")
    end = text.rfind("```")
    if end < start:
        return None
    return text[start : end + 3]


def cline_result_text(res):
    """The human-readable result of a Cline tool result (JSON `result` field)."""
    parsed = (res or {}).get("parsed")
    if isinstance(parsed, dict) and isinstance(parsed.get("result"), str):
        return parsed["result"]
    return (res or {}).get("text") or ""


def cline_expected_action(text):
    """What the runtime did, from its own result string: create / edit / insert."""
    if not text:
        return None
    if "File created successfully at" in text:
        return "create"
    if (
        text.startswith("Inserted content at line")
        or "Inserted content at line" in text
    ):
        return "insert"
    if text.startswith("Edited ") or "\n```diff" in text:
        return "edit"
    return None


# ---------------------------------------------------------------------------
# replay
# ---------------------------------------------------------------------------


class PathState(object):
    def __init__(self):
        self.content = None
        self.known = False
        self.deleted = False
        self.events = []
        self.ops = 0
        self.uncertain = 0
        self.failed = 0
        self.holes = 0
        self.covered = 0
        self.pending = []  # ops skipped for want of a base
        self.base_source = None
        self.validation = "n/a"
        self.engines = set()
        self.last_ts = 0
        self.last_uncertain_ts = 0


def replay(rec, store, git_budget=200):
    states = {}
    ops = sorted(rec.ops, key=lambda o: (o["ts"], o["session"], o["seq"]))
    reads_by_path = collections.defaultdict(list)
    for r in sorted(rec.reads, key=lambda o: (o["ts"], o["session"])):
        reads_by_path[r["path"]].append(r)
    ops_by_path = collections.defaultdict(list)
    for o in rec.ops:
        ops_by_path[o["path"]].append(o)

    git_calls = [0]

    def st(path):
        s = states.get(path)
        if s is None:
            s = PathState()
            states[path] = s
        return s

    def disk_text(path):
        return read_text(path)

    def fs_read(path):
        """What the runtime would have read at that moment: replayed state, else the disk."""
        c = canon(path)
        s = states.get(c)
        if s is not None and s.known:
            return s.content
        return disk_text(c)

    def args_of(op):
        ref = op.get("args_ref")
        if not ref:
            return {}
        raw = store.get(ref)
        try:
            v = json.loads(raw)
        except Exception:
            return {}
        return v if isinstance(v, dict) else {}

    def snapshot_candidates(op, path):
        """Content snapshots of `path` taken before `op`, newest first."""
        s = states.get(path)
        floor = s.last_uncertain_ts if s else 0
        out = []
        for r in sorted(reads_by_path.get(path, []), key=lambda x: -x["ts"]):
            if r["ts"] > op["ts"] or r["ts"] <= floor:
                continue
            if r.get("truncated"):
                continue
            if r.get("agent") == "pi" and not is_full_read(r, rec):
                continue
            text = store.get(r.get("snapshot_ref"))
            if not text:
                continue
            label = "%s-read:%s" % (r.get("agent"), r.get("session"))
            if r.get("lossy"):
                out.append((label, text))
                if not text.endswith("\n"):
                    out.append((label + "+nl", text + "\n"))
            else:
                out.append((label, text))
        return out

    def prior_no_result_candidates(op, path, kinds):
        """Content hypothesised from an earlier call of this path whose result was lost."""
        out = []
        for prior in sorted(ops_by_path.get(path, []), key=lambda x: x["ts"]):
            if prior["ts"] >= op["ts"] or prior.get("kind") not in kinds:
                continue
            if prior.get("call_id") in rec.results:
                continue
            if prior.get("kind") == "editor":
                args = args_of(prior)
                nt = args.get("new_text")
                # An empty old_text can only have been a create: replacing "" would match
                # everywhere and the runtime would have refused it.
                if isinstance(nt, str) and not (args.get("old_text") or ""):
                    out.append(("prior-no-result-create", nt))
            elif prior.get("kind") == "write":
                ref = prior.get("content_ref")
                text = store.get(ref) if ref else None
                if isinstance(text, str):
                    out.append(("prior-no-result-write", text))
        return out

    def recover_base_pi(op, s):
        """Find a trustworthy pre-edit base for a path whose first mutation was an edit."""
        path = op["path"]
        args = args_of(op)
        res = rec.results.get(op.get("call_id"))
        patch = store.get(res.get("patch_ref")) if res else None
        candidates = []
        for label, text in snapshot_candidates(op, path):
            candidates.append((label, text))
        candidates.extend(prior_no_result_candidates(op, path, ("write",)))
        disk = disk_text(path)
        if disk is not None:
            candidates.append(("disk", disk))
        if git_calls[0] < git_budget:
            git_calls[0] += 1
            for label, text in git_candidates(path):
                candidates.append((label, text))
        for label, text in candidates:
            try:
                out = FR.pi_apply_edit(text, args, path)
            except Exception:  # noqa: S112 -- one unapplicable candidate is one lost candidate
                continue
            if patch:
                if patch_applies(text, patch, out["content"]):
                    return text, label, True
                continue
            return text, label, False
        return None, None, False

    def recover_base_cline(op, s):
        path = op["path"]
        args = args_of(op)
        res = rec.results.get(op.get("call_id"))
        recorded = extract_diff(cline_result_text(res))
        candidates = []
        for label, text in snapshot_candidates(op, path):
            candidates.append((label, text))
        candidates.extend(prior_no_result_candidates(op, path, ("editor",)))
        disk = disk_text(path)
        if disk is not None:
            candidates.append(("disk", disk))
        if git_calls[0] < git_budget:
            git_calls[0] += 1
            for label, text in git_candidates(path):
                candidates.append((label, text))
        for label, text in candidates:
            try:
                out = FR.cline_editor_apply(
                    args,
                    op.get("cwd") or os.getcwd(),
                    lambda p, _text=text: _text if canon(p) == path else None,
                )
            except Exception:  # noqa: S112 -- one inapplicable candidate is one lost candidate
                continue
            if out.get("action") == "create":
                return text, label, True
            ok = diff_matches(text, out["content"], recorded)
            if recorded:
                if ok:
                    return text, label, True
                continue
            return text, label, False
        return None, None, False

    for op in ops:
        path = op.get("path")
        res = rec.results.get(op.get("call_id"))
        kind = op["kind"]

        if kind == "delete":
            s = st(path)
            s.ops += 1
            s.engines.add(op["agent"])
            s.deleted = True
            s.known = False
            s.content = None
            s.events.append(
                dict(
                    op="delete",
                    ts=op["ts"],
                    session=op["session"],
                    tool=op["tool"],
                    status="applied",
                )
            )
            s.last_ts = op["ts"]
            continue

        if res is None:
            s = st(path)
            s.ops += 1
            s.uncertain += 1
            s.last_uncertain_ts = op["ts"]
            s.pending.append(op)
            s.events.append(
                dict(
                    op=kind,
                    ts=op["ts"],
                    session=op["session"],
                    tool=op["tool"],
                    status="no-result",
                )
            )
            s.last_ts = op["ts"]
            continue

        if kind == "write":
            s = st(path)
            s.ops += 1
            s.engines.add(op["agent"])
            if res.get("is_error"):
                s.failed += 1
                s.events.append(
                    dict(
                        op="write",
                        ts=op["ts"],
                        session=op["session"],
                        tool=op["tool"],
                        status="error",
                        detail=(rec.result_text(op["call_id"]) or "")[:200],
                    )
                )
            else:
                content = store.get(op.get("content_ref"))
                if content is None:
                    s.uncertain += 1
                    s.events.append(
                        dict(
                            op="write",
                            ts=op["ts"],
                            session=op["session"],
                            tool=op["tool"],
                            status="no-content",
                        )
                    )
                else:
                    s.content = content
                    s.known = True
                    s.deleted = False
                    s.base_source = "write"
                    s.validation = "runtime-confirmed"
                    s.covered += len(s.pending)
                    s.pending = []
                    s.events.append(
                        dict(
                            op="write",
                            ts=op["ts"],
                            session=op["session"],
                            tool=op["tool"],
                            status="applied",
                        )
                    )
            s.last_ts = op["ts"]
            continue

        if kind == "edit":
            s = st(path)
            s.ops += 1
            s.engines.add(op["agent"])
            if res.get("is_error"):
                s.failed += 1
                s.events.append(
                    dict(
                        op="edit",
                        ts=op["ts"],
                        session=op["session"],
                        tool=op["tool"],
                        status="error",
                        detail=(rec.result_text(op["call_id"]) or "")[:200],
                    )
                )
                s.last_ts = op["ts"]
                continue
            if not s.known:
                base, source, ok = recover_base_pi(op, s)
                if base is None:
                    s.holes += 1
                    s.last_uncertain_ts = op["ts"]
                    s.pending.append(op)
                    s.events.append(
                        dict(
                            op="edit",
                            ts=op["ts"],
                            session=op["session"],
                            tool=op["tool"],
                            status="no-base",
                        )
                    )
                    s.last_ts = op["ts"]
                    continue
                s.content = base
                s.known = True
                s.base_source = source
                s.validation = "patch-confirmed" if ok else "unvalidated"
                s.covered += len(s.pending)
                s.pending = []
            args = args_of(op)
            try:
                out = FR.pi_apply_edit(s.content, args, path)
            except FR.ReplayError as exc:
                s.failed += 1
                s.events.append(
                    dict(
                        op="edit",
                        ts=op["ts"],
                        session=op["session"],
                        tool=op["tool"],
                        status="error",
                        detail=str(exc)[:200],
                    )
                )
                s.last_ts = op["ts"]
                continue
            except Exception as exc:
                s.failed += 1
                s.events.append(
                    dict(
                        op="edit",
                        ts=op["ts"],
                        session=op["session"],
                        tool=op["tool"],
                        status="error",
                        detail="%s: %s" % (type(exc).__name__, exc),
                    )
                )
                s.last_ts = op["ts"]
                continue
            patch = store.get(res.get("patch_ref")) if res.get("patch_ref") else None
            if patch:
                ok = patch_applies(s.content, patch, out["content"])
                s.validation = "patch-confirmed" if ok else "patch-mismatch"
                if not ok:
                    s.uncertain += 1
            s.content = out["content"]
            s.deleted = False
            s.events.append(
                dict(
                    op="edit",
                    ts=op["ts"],
                    session=op["session"],
                    tool=op["tool"],
                    status="applied",
                    base=s.base_source,
                )
            )
            s.last_ts = op["ts"]
            continue

        if kind == "editor":
            res_text = res.get("text") or ""
            parsed = res.get("parsed") or {}
            success = parsed.get("success")
            if res.get("is_error") or success is False:
                s = st(path)
                s.ops += 1
                s.engines.add("cline")
                s.failed += 1
                s.events.append(
                    dict(
                        op="editor",
                        ts=op["ts"],
                        session=op["session"],
                        tool=op["tool"],
                        status="error",
                        detail=res_text[:200],
                    )
                )
                s.last_ts = op["ts"]
                continue
            args = args_of(op)
            s = st(path)
            expected = cline_expected_action(cline_result_text(res))
            if not s.known and expected in ("edit", "insert"):
                # The runtime edited an existing file: our state says otherwise, so the
                # pre-edit base must be recovered before the call can be replayed.
                base, source, ok = recover_base_cline(op, s)
                if base is not None:
                    s.content = base
                    s.known = True
                    s.base_source = source
                    s.validation = "diff-confirmed" if ok else "unvalidated"
                    s.covered += len(s.pending)
                    s.pending = []
            try:
                out = FR.cline_editor_apply(args, op.get("cwd") or os.getcwd(), fs_read)
            except Exception as exc:
                s = st(path)
                s.ops += 1
                s.engines.add("cline")
                s.failed += 1
                s.events.append(
                    dict(
                        op="editor",
                        ts=op["ts"],
                        session=op["session"],
                        tool=op["tool"],
                        status="error",
                        detail=str(exc)[:200],
                    )
                )
                s.last_ts = op["ts"]
                continue
            key = canon(out.get("path") or path)
            if key != path:
                prev = st(path)
                cur = st(key)
                if not cur.known and prev.known:
                    cur.content = prev.content
                    cur.known = prev.known
                    cur.base_source = prev.base_source
                    cur.validation = prev.validation
                    cur.last_uncertain_ts = prev.last_uncertain_ts
                s = cur
            else:
                s = st(key)
            s.ops += 1
            s.engines.add("cline")
            if out.get("action") == "create":
                if expected in ("edit", "insert"):
                    # The runtime edited an existing file but we only had an empty base.
                    s.known = False
                    s.content = None
                    s.holes += 1
                    s.uncertain += 1
                    s.last_uncertain_ts = op["ts"]
                    s.pending.append(op)
                    s.events.append(
                        dict(
                            op="editor",
                            ts=op["ts"],
                            session=op["session"],
                            tool=op["tool"],
                            status="no-base",
                        )
                    )
                    s.last_ts = op["ts"]
                    continue
                s.content = out["content"]
                s.known = True
                s.deleted = False
                s.base_source = "create"
                s.validation = "runtime-confirmed"
                s.covered += len(s.pending)
                s.pending = []
            else:
                if not s.known:
                    base, source, ok = recover_base_cline(op, s)
                    if base is None:
                        s.holes += 1
                        s.last_uncertain_ts = op["ts"]
                        s.pending.append(op)
                        s.events.append(
                            dict(
                                op="editor",
                                ts=op["ts"],
                                session=op["session"],
                                tool=op["tool"],
                                status="no-base",
                            )
                        )
                        s.last_ts = op["ts"]
                        continue
                    s.content = base
                    s.known = True
                    s.base_source = source
                    s.validation = "diff-confirmed" if ok else "unvalidated"
                    s.covered += len(s.pending)
                    s.pending = []
                recorded = extract_diff(cline_result_text(res))
                ok = diff_matches(s.content, out["content"], recorded)
                if recorded:
                    s.validation = "diff-confirmed" if ok else "diff-mismatch"
                    if not ok:
                        s.uncertain += 1
                s.content = out["content"]
                s.deleted = False
            s.events.append(
                dict(
                    op="editor",
                    ts=op["ts"],
                    session=op["session"],
                    tool=op["tool"],
                    status="applied",
                )
            )
            s.last_ts = op["ts"]
            continue

        if kind == "patch":
            args = args_of(op)
            patch_text = args.get("input") or ""
            touched = patch_files(patch_text, op.get("cwd"))
            parsed = res.get("parsed") or {}
            if res.get("is_error") or parsed.get("success") is False:
                for p in touched:
                    ps = st(p)
                    ps.ops += 1
                    ps.failed += 1
                    ps.engines.add("cline")
                    ps.events.append(
                        dict(
                            op="patch",
                            ts=op["ts"],
                            session=op["session"],
                            tool=op["tool"],
                            status="error",
                            detail=res_text[:200],
                        )
                    )
                    ps.last_ts = op["ts"]
                continue
            try:
                changes = FR.cline_apply_patch_changes(
                    patch_text, op.get("cwd") or os.getcwd(), fs_read, False
                )
            except Exception as exc:
                for p in touched:
                    ps = st(p)
                    ps.ops += 1
                    ps.failed += 1
                    ps.engines.add("cline")
                    ps.events.append(
                        dict(
                            op="patch",
                            ts=op["ts"],
                            session=op["session"],
                            tool=op["tool"],
                            status="error",
                            detail=str(exc)[:200],
                        )
                    )
                    ps.last_ts = op["ts"]
                continue
            for rel, change in changes["changes"].items():
                p = canon(change.get("absolute_path") or change.get("path"))
                ps = st(p)
                ps.ops += 1
                ps.engines.add("cline")
                if change["type"] == "delete":
                    ps.content = None
                    ps.known = False
                    ps.deleted = True
                else:
                    ps.content = change["new_content"]
                    ps.known = True
                    ps.deleted = False
                    if ps.base_source is None:
                        ps.base_source = "patch"
                    ps.validation = "runtime-confirmed"
                ps.events.append(
                    dict(
                        op="patch",
                        ts=op["ts"],
                        session=op["session"],
                        tool=op["tool"],
                        status="applied",
                        file=rel,
                    )
                )
                ps.last_ts = op["ts"]
            continue

    return states


def is_full_read(r, rec):
    """True when a Pi read returned the whole file (no offset/limit, no truncation)."""
    offset = r.get("offset")
    limit = r.get("limit")
    if offset is not None and not (isinstance(offset, int) and offset <= 1):
        return False
    if limit is not None:
        return False
    res = rec.results.get(r.get("call_id"))
    if res and res.get("truncated"):
        return False
    text = rec.result_text(r.get("call_id")) or ""
    for mark in TRUNCATION_MARKS:
        if mark in text:
            return False
    return True


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Codex harness (2026-11-11): Codex Desktop rollouts
# ---------------------------------------------------------------------------
#
# Codex Desktop writes one JSONL rollout per thread under
# <CODEX_HOME>/sessions/YYYY/MM/DD/rollout-<timestamp>-<uuid>.jsonl. The rollout is the
# transcript of record. The producer's own file oracle is the `FileChange` item inside
# `event_msg.item_completed`: `changes[path].unified_diff` is a git-style hunk-only diff
# (no ---/+++ headers) and `item.id` is exactly the producing tool call's `call_id`, so
# every diff is joined to its call by identity, never by proximity (AGENTS.md 3a: the
# producer's oracle is the judge).

CODEX_HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
CODEX_ROLLOUT = re.compile(
    r"rollout-(\d{4}-\d{2}-\d{2}T[\d:.-]+)-([0-9a-f-]{36})\.jsonl$"
)


class CodexDiffError(Exception):
    """A producer diff that does not apply to the candidate base."""


def codex_ms(ts):
    """Codex timestamps are ISO-8601 UTC strings; normalise them to epoch milliseconds."""
    if isinstance(ts, bool):
        return 0
    if isinstance(ts, (int, float)):
        return int(ts)
    if not isinstance(ts, str):
        return 0
    text = ts.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.datetime.fromisoformat(text)
    except ValueError:
        return 0
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return int(dt.timestamp() * 1000)


def codex_in_window(ts, window):
    if not window:
        return True
    start, end = window
    if start and ts < start:
        return False
    if end and ts >= end:
        return False
    return True


def codex_split_hunks(diff):
    """Split a git-style hunk-only diff into (old_start, old_count, new_start, new_count, body)."""
    hunks = []
    cur = None
    for raw in (diff or "").splitlines():
        m = CODEX_HUNK.match(raw)
        if m:
            cur = (
                int(m.group(1)),
                int(m.group(2) or 1),
                int(m.group(3)),
                int(m.group(4) or 1),
                [],
            )
            hunks.append(cur)
            continue
        if cur is None:
            continue
        if raw.startswith("\\"):  # "\ No newline at end of file"
            continue
        cur[4].append(raw)
    return hunks


def _codex_locate(lines, expect, approx):
    """Find `expect` in `lines` at or near `approx` (git-style bounded fuzz)."""
    n = len(expect)
    if not n:
        return max(0, min(approx, len(lines)))

    def same(a, b):
        return a.rstrip("\n") == b.rstrip("\n")

    if approx >= 0 and approx + n <= len(lines):
        if all(same(lines[approx + i], expect[i]) for i in range(n)):
            return approx
    for delta in range(1, 41):
        for cand in (approx - delta, approx + delta):
            if cand < 0 or cand + n > len(lines):
                continue
            if all(same(lines[cand + i], expect[i]) for i in range(n)):
                return cand
    return None


def codex_apply(diff, base, reverse=False):
    """Apply (or reverse) a Codex producer diff to `base`; returns the new text.

    Codex's diffs are hunk-only, so the ---/+++ headers FR.apply_unified_patch tolerates
    are simply absent; the hunk headers carry the line numbers.
    """
    nl = "\r\n" if "\r\n" in (base or "") else "\n"
    lines = (base or "").splitlines(keepends=True)
    for hunk in codex_split_hunks(diff):
        old_start, _old_count, new_start, _new_count, body = hunk
        if reverse:
            expect = [l[1:] for l in body if l[:1] in (" ", "+")]
            replace = [l[1:] for l in body if l[:1] in (" ", "-")]
            approx = new_start - 1
        else:
            expect = [l[1:] for l in body if l[:1] in (" ", "-")]
            replace = [l[1:] for l in body if l[:1] in (" ", "+")]
            approx = old_start - 1
        idx = _codex_locate(lines, expect, approx)
        if idx is None:
            raise CodexDiffError("hunk at %d does not apply" % (approx + 1))
        out = list(lines[:idx])
        for line in replace:
            out.append(line + nl if line else line)
        out.extend(lines[idx + len(expect) :])
        lines = out
    return "".join(lines)


def _codex_text_of(content):
    """Flatten a Codex content block (list of typed parts) into plain text."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, dict):
        content = [content]
    if not isinstance(content, list):
        return ""
    parts = []
    for item in content:
        if isinstance(item, str):
            parts.append(item)
        elif isinstance(item, dict):
            text = item.get("text")
            if isinstance(text, str):
                parts.append(text)
    return "\n".join(p for p in parts if p)


def parse_codex(path, rec):
    """Index one Codex rollout: sessions, environments, conversation, calls, file changes."""
    window = rec.codex_window
    info = dict(
        session=os.path.basename(path),
        agent="codex",
        file=path,
        model=None,
        cwd=None,
        started=None,
        ended=None,
        prompt=None,
        tool_calls=0,
        intents=collections.Counter(),
        plans=[],
        files=set(),
    )
    cx = dict(
        thread_id=None,
        session_id=None,
        originator=None,
        cli_version=None,
        source=None,
        thread_source=None,
        model_provider=None,
        model=None,
        parent_thread_id=None,
        agent_path=None,
        workspace_roots=[],
        environments={},
        filesystem_roots=[],
        sandbox_policy=None,
        approval_policy=None,
        permission_profile=None,
        collaboration_mode=None,
        effort=None,
        turns=0,
        records=0,
        records_in_window=0,
        tool_calls=0,
        tool_calls_in_window=0,
        subagents=[],
        compactions=0,
        turn_aborts=0,
        token_totals={},
        history_mode=None,
    )
    conv = []
    seen_conv = set()
    calls = {}
    patch_inputs = {}
    ordinal = 0
    with open(path, errors="replace") as f:
        for line in f:
            try:
                r = json.loads(line)
            except Exception as err:  # noqa: BLE001 -- a bad record costs that record
                rec.parse_errors.append(
                    dict(file=path, error="json: %s: %s" % (type(err).__name__, err))
                )
                continue
            if not isinstance(r, dict):
                continue
            ordinal += 1
            payload = r.get("payload")
            if not isinstance(payload, dict):
                payload = {}
            ts = codex_ms(r.get("timestamp"))
            rtype = r.get("type")
            cx["records"] += 1
            in_window = codex_in_window(ts, window)
            if in_window:
                cx["records_in_window"] += 1
            if ts:
                if not info["started"] or ts < info["started"]:
                    info["started"] = ts
                if not info["ended"] or ts > info["ended"]:
                    info["ended"] = ts

            if rtype == "session_meta":
                cx["thread_id"] = payload.get("session_id") or payload.get("id")
                cx["session_id"] = payload.get("id") or payload.get("session_id")
                cx["originator"] = payload.get("originator")
                cx["cli_version"] = payload.get("cli_version")
                cx["model_provider"] = payload.get("model_provider")
                cx["history_mode"] = payload.get("history_mode")
                src = payload.get("source")
                if isinstance(src, dict):
                    cx["source"] = (
                        src.get("subagent") or src.get("app") or json.dumps(src)
                    )
                    cx["parent_thread_id"] = src.get("parent_thread_id") or src.get(
                        "parent_id"
                    )
                else:
                    cx["source"] = src
                cx["thread_source"] = payload.get("thread_source")
                cx["parent_thread_id"] = (
                    payload.get("parent_thread_id") or cx["parent_thread_id"]
                )
                cx["agent_path"] = payload.get("agent_path")
                roots = payload.get("runtime_workspace_roots")
                if isinstance(roots, list):
                    cx["workspace_roots"] = [str(x) for x in roots]
                if payload.get("cwd"):
                    info["cwd"] = payload.get("cwd")
                    cx["environments"].setdefault(
                        "local",
                        {
                            "cwd": payload.get("cwd"),
                            "status": "available",
                            "shell": "bash",
                        },
                    )
                prov = payload.get("provenance")
                if isinstance(prov, dict) and prov.get("model"):
                    cx["model"] = prov.get("model")
                base = payload.get("base_instructions")
                if isinstance(base, dict) and base.get("text") and not info["prompt"]:
                    info["prompt"] = base["text"][:2000]

            elif rtype == "turn_context":
                cx["turns"] += 1
                if payload.get("cwd"):
                    info["cwd"] = payload.get("cwd")
                if payload.get("model"):
                    cx["model"] = payload.get("model")
                    info["model"] = payload.get("model")
                cx["sandbox_policy"] = payload.get("sandbox_policy")
                cx["approval_policy"] = payload.get("approval_policy")
                cx["permission_profile"] = payload.get("permission_profile")
                cm = payload.get("collaboration_mode")
                if isinstance(cm, dict):
                    cx["collaboration_mode"] = cm.get("mode")
                if payload.get("effort"):
                    cx["effort"] = payload.get("effort")

            elif rtype == "world_state":
                state = payload.get("state")
                if isinstance(state, dict):
                    envs = state.get("environments")
                    if isinstance(envs, dict):
                        inner = envs.get("environments")
                        if isinstance(inner, dict):
                            cx["environments"].update(inner)
                        if envs.get("current_date"):
                            cx["current_date"] = envs.get("current_date")
                        if envs.get("timezone"):
                            cx["timezone"] = envs.get("timezone")
                    if state.get("model"):
                        cx["model"] = state.get("model")
                        info["model"] = state.get("model")
                    fs = state.get("filesystem")
                    if isinstance(fs, str):
                        roots = re.findall(r"<root>(.*?)</root>", fs)
                        if roots:
                            cx["filesystem_roots"] = roots

            elif rtype == "response_item":
                itype = payload.get("type")
                if itype == "function_call":
                    cx["tool_calls"] += 1
                    if in_window:
                        cx["tool_calls_in_window"] += 1
                    info["tool_calls"] += 1
                    cid = payload.get("call_id") or payload.get("id")
                    name = payload.get("name")
                    raw_args = payload.get("arguments")
                    args = {}
                    if isinstance(raw_args, str):
                        try:
                            args = json.loads(raw_args)
                        except ValueError:
                            args = {"_raw": raw_args[:400]}
                    elif isinstance(raw_args, dict):
                        args = raw_args
                    calls[cid] = dict(name=name, args=args, ts=ts, in_window=in_window)
                    cmd = None
                    if name == "exec_command":
                        cmd = args.get("cmd")
                        if isinstance(cmd, list):
                            cmd = " ".join(str(x) for x in cmd)
                    elif name == "js":
                        code = args.get("code")
                        cmd = ("js: " + code) if isinstance(code, str) else None
                    elif name == "request_permissions":
                        cmd = "request_permissions " + json.dumps(args)[:300]
                    elif name in ("spawn_agent", "followup_task", "wait_agent"):
                        cmd = "%s %s" % (name, json.dumps(args)[:300])
                    if cmd:
                        ingest_command(cmd, rec.ledger, info["session"], ts, name)
                    if name == "spawn_agent" and isinstance(args, dict):
                        cx["subagents"].append(
                            dict(
                                ts=ts,
                                agent_path=args.get("agent_path") or args.get("name"),
                                model=args.get("model"),
                                in_window=in_window,
                            )
                        )
                elif itype == "custom_tool_call":
                    cx["tool_calls"] += 1
                    if in_window:
                        cx["tool_calls_in_window"] += 1
                    info["tool_calls"] += 1
                    cid = payload.get("call_id") or payload.get("id")
                    calls[cid] = dict(
                        name=payload.get("name"),
                        args={"input": payload.get("input")},
                        ts=ts,
                        in_window=in_window,
                    )
                    if payload.get("name") == "apply_patch":
                        patch_inputs[cid] = payload.get("input")
                elif itype == "message":
                    role = payload.get("role")
                    text = _codex_text_of(payload.get("content"))
                    if text:
                        key = (role, sha(text))
                        if key not in seen_conv:
                            seen_conv.add(key)
                            conv.append(
                                dict(
                                    ts=ts,
                                    ordinal=ordinal,
                                    role=role,
                                    text=text,
                                    source="response_item.message",
                                )
                            )
                elif itype == "agent_message":
                    text = _codex_text_of(payload.get("content")) or str(
                        payload.get("text") or ""
                    )
                    if text:
                        key = ("assistant", sha(text))
                        if key not in seen_conv:
                            seen_conv.add(key)
                            conv.append(
                                dict(
                                    ts=ts,
                                    ordinal=ordinal,
                                    role="assistant",
                                    text=text,
                                    source="response_item.agent_message",
                                )
                            )

            elif rtype == "event_msg":
                etype = payload.get("type")
                if etype == "item_completed":
                    item = payload.get("item")
                    if not isinstance(item, dict):
                        item = {}
                    itype = item.get("type")
                    item_id = item.get("id")
                    if itype in ("UserMessage", "AgentMessage"):
                        role = "user" if itype == "UserMessage" else "assistant"
                        text = _codex_text_of(item.get("content"))
                        if text:
                            key = (role, sha(text))
                            if key not in seen_conv:
                                seen_conv.add(key)
                                conv.append(
                                    dict(
                                        ts=ts,
                                        ordinal=ordinal,
                                        role=role,
                                        text=text,
                                        source="event_msg.item_completed",
                                        phase=item.get("phase"),
                                    )
                                )
                    elif itype == "CommandExecution":
                        cid = item_id
                        out = item.get("aggregated_output")
                        if not isinstance(out, str):
                            out = ""
                        argv = item.get("command")
                        if isinstance(argv, list):
                            cmdline = " ".join(str(x) for x in argv)
                        else:
                            cmdline = str(argv or "")
                        exit_code = item.get("exit_code")
                        is_error = bool(exit_code) and exit_code != 0
                        rec.results[cid] = dict(
                            text=out,
                            text_ref=None,
                            is_error=is_error,
                            patch_ref=None,
                        )
                        if cmdline:
                            ingest_command(
                                cmdline, rec.ledger, info["session"], ts, "exec_command"
                            )
                    elif itype == "FileChange":
                        changes = item.get("changes")
                        if isinstance(changes, dict):
                            for raw_path, ch in changes.items():
                                if not isinstance(ch, dict):
                                    continue
                                target = canon(raw_path)
                                info["files"].add(target)
                                rec.codex_changes.append(
                                    dict(
                                        session=info["session"],
                                        ts=ts,
                                        ordinal=ordinal,
                                        call_id=item_id,
                                        path=target,
                                        raw_path=raw_path,
                                        change_type=ch.get("type") or "update",
                                        diff=ch.get("unified_diff") or "",
                                        move_path=canon(ch["move_path"])
                                        if ch.get("move_path")
                                        else None,
                                        in_window=in_window,
                                    )
                                )
                    elif itype == "McpToolCall":
                        result = item.get("result")
                        text = ""
                        is_error = False
                        if isinstance(result, dict):
                            text = _codex_text_of(result.get("content"))
                            is_error = bool(result.get("isError"))
                        rec.results[item_id] = dict(
                            text=text, text_ref=None, is_error=is_error, patch_ref=None
                        )
                    elif itype == "SubAgentActivity":
                        agent = dict(
                            ts=ts,
                            agent_thread_id=item.get("agent_thread_id"),
                            agent_path=item.get("agent_path"),
                            kind=item.get("kind"),
                            model=item.get("model"),
                            reasoning_effort=item.get("reasoning_effort"),
                            in_window=in_window,
                        )
                        cx["subagents"].append(agent)
                    elif itype == "ContextCompaction":
                        cx["compactions"] += 1
                elif etype == "turn_aborted":
                    cx["turn_aborts"] += 1
                elif etype == "token_count":
                    info2 = payload.get("info")
                    if isinstance(info2, dict):
                        last = info2.get("last_token_usage")
                        if isinstance(last, dict):
                            for k, v in last.items():
                                if isinstance(v, (int, float)):
                                    cx["token_totals"][k] = (
                                        cx["token_totals"].get(k, 0) + v
                                    )

            elif rtype == "token_usage_record":
                usage = payload.get("usage")
                if isinstance(usage, dict):
                    for k, v in usage.items():
                        if isinstance(v, (int, float)):
                            cx["token_totals"][k] = cx["token_totals"].get(k, 0) + v

    conv.sort(key=lambda c: (c["ts"], c["ordinal"]))
    info["codex"] = cx
    info["conversation"] = len(conv)
    rec.sessions.append(info)
    rec.codex_conversations.append(dict(session=info["session"], records=conv))
    rec.codex_calls.setdefault(info["session"], {}).update(calls)
    rec.codex_patch_inputs.setdefault(info["session"], {}).update(patch_inputs)
    return info


def codex_reconstruct(rec, store, git_budget=200):
    """Rebuild every path Codex changed from the producer's own diffs.

    The chain for a path is the producer diffs in wall-clock order. The pre-image is
    recovered by reversing the producer diffs against the on-disk bytes and then proving
    the chain by applying it forward again (AGENTS.md 3a: the producer's oracle is the
    judge). A git blob is the fallback base. When no base survives, the path is recorded
    as EDIT-ONLY, never silently dropped.
    """
    by_path = collections.defaultdict(list)
    for ch in rec.codex_changes:
        by_path[ch["path"]].append(ch)
    reconstructed = {}
    for path, evs in by_path.items():
        evs.sort(key=lambda e: (e["ts"], e["ordinal"]))
        types = [e["change_type"] for e in evs]
        base = None
        base_label = "none"
        states = []
        if types and types[0] == "add":
            base, base_label = "", "producer-add"
        else:
            disk = read_text(path)
            if disk is not None and all(t == "update" for t in types):
                cur = disk
                ok = True
                for e in reversed(evs):
                    try:
                        cur = codex_apply(e["diff"], cur, reverse=True)
                    except CodexDiffError:
                        ok = False
                        break
                if ok:
                    fwd = cur
                    try:
                        for e in evs:
                            fwd = codex_apply(e["diff"], fwd)
                    except CodexDiffError:
                        ok = False
                    if ok and fwd == disk:
                        base, base_label = cur, "disk-reverse-verified"
            if base is None and git_budget > 0:
                git_budget -= 1
                try:
                    for label, text in git_candidates(path, limit=1):
                        fwd = text
                        try:
                            for e in evs:
                                fwd = codex_apply(e["diff"], fwd)
                        except CodexDiffError:
                            continue
                        base, base_label = text, label
                        break
                except Exception:  # noqa: BLE001 -- git is a best-effort base source
                    base = None
        if base is None:
            states = [None] * len(evs)
            base_label = "no-base"
        else:
            cur = base
            for e in evs:
                if e["change_type"] == "delete":
                    states.append(None)
                    cur = ""
                    continue
                try:
                    cur = codex_apply(e["diff"], cur)
                except CodexDiffError:
                    states.append(None)
                    continue
                states.append(cur)
        for e, content in zip(evs, states, strict=False):
            cid = "codex:%s:%s" % (e["call_id"], e["path"])
            if e["change_type"] == "delete":
                rec.add_op(
                    dict(
                        agent="codex",
                        kind="delete",
                        session=e["session"],
                        ts=e["ts"],
                        tool="codex-filechange",
                        call_id=cid,
                        path=e["path"],
                        content_ref=None,
                        args_ref=rec.store.put(
                            json.dumps(
                                dict(
                                    call_id=e["call_id"],
                                    change_type=e["change_type"],
                                    move_path=e["move_path"],
                                    diff_head=e["diff"].splitlines()[:1],
                                )
                            )
                        ),
                        cwd=None,
                        in_window=e["in_window"],
                    )
                )
                rec.results[cid] = dict(
                    text="", text_ref=None, is_error=False, patch_ref=None
                )
                continue
            ref = rec.store.put(content) if content is not None else None
            rec.add_op(
                dict(
                    agent="codex",
                    kind="write",
                    session=e["session"],
                    ts=e["ts"],
                    tool="codex-filechange",
                    call_id=cid,
                    path=e["path"],
                    content_ref=ref,
                    args_ref=rec.store.put(
                        json.dumps(
                            dict(
                                call_id=e["call_id"],
                                change_type=e["change_type"],
                                move_path=e["move_path"],
                                base_source=base_label,
                                diff_head=e["diff"].splitlines()[:1],
                            )
                        )
                    ),
                    cwd=None,
                    in_window=e["in_window"],
                )
            )
            rec.results[cid] = dict(
                text="", text_ref=None, is_error=False, patch_ref=None
            )
            if e["move_path"]:
                rec.add_op(
                    dict(
                        agent="codex",
                        kind="write",
                        session=e["session"],
                        ts=e["ts"],
                        tool="codex-move",
                        call_id=cid + ":move",
                        path=e["move_path"],
                        content_ref=ref,
                        args_ref=None,
                        cwd=None,
                        in_window=e["in_window"],
                    )
                )
                rec.results[cid + ":move"] = dict(
                    text="", text_ref=None, is_error=False, patch_ref=None
                )
        reconstructed[path] = dict(
            events=len(evs),
            base_source=base_label,
            content_known=sum(1 for s in states if s is not None),
        )
    return reconstructed


def _quote_ident(name):
    """Quote a SQLite identifier. The names come from sqlite_master or PRAGMA."""
    return '"' + str(name).replace('"', '""') + '"'


def _sql_count(table):
    return "SELECT COUNT(*) FROM " + _quote_ident(table)  # noqa: S608 - quoted, from sqlite_master


def _sql_select(table, cols=None):
    if cols:
        return (
            "SELECT "  # noqa: S608 - quoted identifiers, from sqlite_master / PRAGMA
            + ", ".join(_quote_ident(c) for c in cols)
            + " FROM "
            + _quote_ident(table)
        )
    return "SELECT * FROM " + _quote_ident(table)  # noqa: S608 - quoted, from sqlite_master


def codex_object_store(path, window, rec):
    """Read the Codex thread-history object store and cross-check it against the rollouts."""
    import sqlite3

    out = dict(
        path=path,
        exists=os.path.exists(path),
        tables={},
        threads=[],
        totals={},
        window_items=0,
        duplicate_items=0,
        by_type={},
        read_only=True,
    )
    if not out["exists"]:
        return out
    con = sqlite3.connect("file:%s?mode=ro" % path, uri=True)
    con.row_factory = sqlite3.Row
    try:
        tabs = [
            r[0]
            for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")
        ]
        for t in tabs:
            try:
                out["tables"][t] = con.execute(_sql_count(t)).fetchone()[0]
            except sqlite3.Error:
                out["tables"][t] = None
        if "thread_items" in tabs:
            cols = [r[1] for r in con.execute("PRAGMA table_info(thread_items)")]
            tcol = "thread_id" if "thread_id" in cols else None
            tscol = next(
                (
                    c
                    for c in ("created_at", "created_at_ms", "timestamp", "updated_at")
                    if c in cols
                ),
                None,
            )
            typecol = next(
                (c for c in ("item_type", "type", "kind") if c in cols), None
            )
            idcol = next((c for c in ("id", "item_id", "uuid") if c in cols), None)
            sel = ", ".join([c for c in (tcol, tscol, typecol, idcol) if c])
            seen = set()
            per_thread = collections.defaultdict(
                lambda: dict(
                    items=0,
                    window=0,
                    first=None,
                    last=None,
                    by_type=collections.Counter(),
                )
            )
            for row in con.execute(_sql_select("thread_items", [sel])):
                d = dict(row)
                tid = d.get(tcol)
                raw_ts = d.get(tscol)
                ts = codex_ms(raw_ts) if isinstance(raw_ts, str) else int(raw_ts or 0)
                if ts and ts < 10**11:
                    ts *= 1000
                itype = d.get(typecol)
                iid = d.get(idcol)
                key = (tid, iid)
                if key in seen:
                    out["duplicate_items"] += 1
                    continue
                seen.add(key)
                t = per_thread[tid]
                t["items"] += 1
                t["by_type"][str(itype)] += 1
                if ts:
                    t["first"] = ts if not t["first"] else min(t["first"], ts)
                    t["last"] = ts if not t["last"] else max(t["last"], ts)
                if codex_in_window(ts, window):
                    t["window"] += 1
                    out["window_items"] += 1
                    out["by_type"][str(itype)] = out["by_type"].get(str(itype), 0) + 1
            out["threads"] = [
                dict(
                    thread_id=tid,
                    items=t["items"],
                    window_items=t["window"],
                    first=iso(t["first"]) if t["first"] else None,
                    last=iso(t["last"]) if t["last"] else None,
                    by_type=dict(t["by_type"].most_common(20)),
                )
                for tid, t in sorted(per_thread.items(), key=lambda kv: str(kv[0]))
            ]
            out["totals"] = dict(
                threads=len(per_thread),
                items=sum(t["items"] for t in per_thread.values()),
                window_items=out["window_items"],
                duplicate_items=out["duplicate_items"],
            )
    except sqlite3.Error as err:
        out["error"] = str(err)
    finally:
        con.close()
    return out


def codex_catalog(path):
    """Read the Codex Desktop local thread catalog (read-only) for host/thread evidence."""
    import sqlite3

    out = dict(path=path, exists=os.path.exists(path), tables={}, threads=[], hosts=[])
    if not out["exists"]:
        return out
    con = sqlite3.connect("file:%s?mode=ro" % path, uri=True)
    con.row_factory = sqlite3.Row
    try:
        tabs = [
            r[0]
            for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")
        ]
        out["tables"] = {t: con.execute(_sql_count(t)).fetchone()[0] for t in tabs}
        for t in ("local_thread_catalog", "local_thread_catalog_hosts"):
            if t not in tabs:
                continue
            rows = []
            for row in con.execute(_sql_select(t)):
                d = dict(row)
                for k, v in list(d.items()):
                    if isinstance(v, bytes):
                        d[k] = v.decode("utf-8", "replace")
                rows.append(d)
            if t == "local_thread_catalog":
                out["threads"] = rows
            else:
                out["hosts"] = rows
    except sqlite3.Error as err:
        out["error"] = str(err)
    finally:
        con.close()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cline", default=HOME + "/.cline/data/sessions")
    ap.add_argument("--pi", default=HOME + "/.pi/agent/sessions")
    ap.add_argument(
        "--codex",
        action="append",
        default=[],
        help="a Codex sessions root (repeatable): <root>/YYYY/MM/DD/rollout-*.jsonl",
    )
    ap.add_argument(
        "--codex-window-start", default="", help="ISO-8601 UTC window start"
    )
    ap.add_argument("--codex-window-end", default="", help="ISO-8601 UTC window end")
    ap.add_argument(
        "--codex-object-store", default="", help="Codex thread_history sqlite"
    )
    ap.add_argument(
        "--codex-catalog", default="", help="Codex Desktop local_thread_catalog db"
    )
    ap.add_argument("--out", default="")
    ap.add_argument("--limit-sessions", type=int, default=0)
    ap.add_argument("--no-git", action="store_true")
    ap.add_argument(
        "--log",
        default="",
        help="redirect this process's stdout and stderr into this file",
    )
    ap.add_argument("--pid-file", default="", help="write this process's pid here")
    ap.add_argument(
        "--pointer",
        default="",
        help="write the output directory here (the pointer to the current extraction)",
    )
    ap.add_argument(
        "--pointer-only",
        action="store_true",
        help="write the pointer and exit; do not extract",
    )
    a = ap.parse_args()

    # 2026-10-31: the door that launches this writes nothing itself -- the estate's own
    # fs_guard bans shell redirects (`> file`) -- so the extractor writes its own log, its own
    # pid file and the pointer that says which extraction is current. Redirecting stdout here
    # also releases the executor's capture pipe: a background child that still holds it makes
    # the door wait for the child instead of for the launch.
    if a.log:
        d = os.path.dirname(a.log)
        if d:
            os.makedirs(d, exist_ok=True)
        fd = os.open(a.log, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
        os.dup2(fd, 1)
        os.dup2(fd, 2)
        os.close(fd)
    if a.pid_file:
        d = os.path.dirname(a.pid_file)
        if d:
            os.makedirs(d, exist_ok=True)
        with open(a.pid_file, "w") as f:
            f.write("%d\n" % os.getpid())
    if a.pointer:
        d = os.path.dirname(a.pointer)
        if d:
            os.makedirs(d, exist_ok=True)
        with open(a.pointer, "w") as f:
            f.write(a.out + "\n")
    if a.pointer_only:
        print("pointer: %s -> %s" % (a.pointer, a.out))
        return
    if not a.out:
        ap.error("--out is required unless --pointer-only is used")
    os.makedirs(a.out, exist_ok=True)
    store = Store(os.path.join(a.out, ".store"))
    rec = Recorder(store)

    # The Codex window is a record-timestamp window, not a filename or mtime window.
    rec.codex_window = (
        codex_ms(a.codex_window_start) if a.codex_window_start else 0,
        codex_ms(a.codex_window_end) if a.codex_window_end else 0,
    )
    rec.codex_changes = []
    rec.codex_conversations = []
    rec.codex_calls = {}
    rec.codex_patch_inputs = {}

    cline_files = sorted(glob.glob(a.cline + "/*/*.messages.json"))
    pi_files = sorted(glob.glob(a.pi + "/*/*.jsonl"))
    codex_files = []
    for root in a.codex:
        codex_files.extend(
            sorted(
                glob.glob(os.path.join(root, "**", "rollout-*.jsonl"), recursive=True)
            )
        )
    codex_files = sorted(set(codex_files))
    if a.limit_sessions:
        cline_files = cline_files[: a.limit_sessions]
        pi_files = pi_files[: a.limit_sessions]
        codex_files = codex_files[: a.limit_sessions]

    # 2026-10-31: a session that cannot be parsed must cost that session, not the corpus.
    # The parse is already guarded per record; this is the outer wall that keeps a file that
    # is being written right now (truncated JSONL) from ending the extraction.
    for p in cline_files:
        try:
            parse_cline(p, rec)
        except Exception as err:  # noqa: BLE001
            rec.parse_errors.append(
                dict(file=p, error="%s: %s" % (type(err).__name__, err))
            )
    for p in pi_files:
        try:
            parse_pi(p, rec)
        except Exception as err:  # noqa: BLE001
            rec.parse_errors.append(
                dict(file=p, error="%s: %s" % (type(err).__name__, err))
            )
    codex_sessions = []
    for p in codex_files:
        try:
            codex_sessions.append(parse_codex(p, rec))
        except Exception as err:  # noqa: BLE001
            rec.parse_errors.append(
                dict(file=p, error="%s: %s" % (type(err).__name__, err))
            )
    codex_reconstruction = (
        codex_reconstruct(rec, store, git_budget=0 if a.no_git else 200)
        if rec.codex_changes
        else {}
    )
    if rec.parse_errors:
        json.dump(rec.parse_errors, open(a.out + "/parse_errors.json", "w"), indent=1)
        print(
            "WARNING: %d records/sessions could not be parsed (see parse_errors.json)"
            % len(rec.parse_errors)
        )

    print(
        "indexed: %d cline sessions, %d pi sessions, %d codex rollouts, %d ops, %d reads, "
        "%d results, store %.1f MiB"
        % (
            len(cline_files),
            len(pi_files),
            len(codex_files),
            len(rec.ops),
            len(rec.reads),
            len(rec.results),
            store.bytes / 1048576.0,
        )
    )

    states = replay(rec, store, git_budget=0 if a.no_git else 200)

    rows = []
    for p in sorted(states):
        s = states[p]
        body = s.content if s.known else None
        text = p + " " + (body or "")[:1500]
        prim, tags = stream_of(text)
        loc = location_class(p)
        if body is None:
            rec_state = "DELETED-BY-AGENT" if s.deleted else "EDIT-ONLY"
        elif s.uncertain or s.holes:
            rec_state = "PARTIAL"
        else:
            rec_state = "FULL"
        if body is not None:
            dest = os.path.join(a.out, "recovered", p.lstrip("/"))
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, "w", encoding="utf-8", errors="replace", newline="") as f:
                f.write(body)
        rows.append(
            dict(
                path=p,
                location=loc,
                stream=prim,
                tags=tags,
                recoverability=rec_state,
                ops=s.ops,
                sessions=sorted(
                    {e.get("session") for e in s.events if e.get("session")}
                ),
                last_ts=iso(s.last_ts) if s.last_ts else "",
                bytes=len(body) if body is not None else 0,
                sha256=sha(body) if body is not None else None,
                at_risk=(loc == "VOLATILE-tmp"),
                deleted=bool(s.deleted and body is None),
                engines=sorted(s.engines),
                base_source=s.base_source or "none",
                validation=s.validation,
                uncertain_ops=s.uncertain,
                failed_ops=s.failed,
                holes=s.holes,
                covered_ops=s.covered,
                in_window=any(
                    codex_in_window(e.get("ts") or 0, rec.codex_window)
                    for e in s.events
                ),
            )
        )

    json.dump(rows, open(a.out + "/manifest.json", "w"), indent=1)
    cols = [
        "path",
        "location",
        "stream",
        "recoverability",
        "ops",
        "bytes",
        "at_risk",
        "last_ts",
        "sessions",
        "deleted",
        "engines",
        "base_source",
        "validation",
        "uncertain_ops",
        "failed_ops",
        "holes",
        "covered_ops",
        "in_window",
    ]
    with open(a.out + "/manifest.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for r in rows:
            w.writerow(
                [
                    r["path"],
                    r["location"],
                    r["stream"],
                    r["recoverability"],
                    r["ops"],
                    r["bytes"],
                    r["at_risk"],
                    r["last_ts"],
                    ";".join(r["sessions"]),
                    r["deleted"],
                    ";".join(r["engines"]),
                    r["base_source"],
                    r["validation"],
                    r["uncertain_ops"],
                    r["failed_ops"],
                    r["holes"],
                    r["covered_ops"],
                    r["in_window"],
                ]
            )

    for s in rec.sessions:
        s["files"] = len(s["files"])
        s["intents"] = dict(s["intents"].most_common(12))
        s["stream"] = stream_of(
            (s.get("prompt") or "") + " " + " ".join(p["goal"] for p in s["plans"])
        )[0]
        for p in s["plans"]:
            p["subgoals_total"] = len(p["subgoals"])
            p["subgoals_done"] = len(set(p["done"]) & set(p["subgoals"]))
            p["subgoals"] = list(p["subgoals"].values())[:8]
    json.dump(rec.sessions, open(a.out + "/sessions.json", "w"), indent=1, default=str)
    with open(a.out + "/commands_ledger.jsonl", "w") as f:
        for l in rec.ledger:
            f.write(json.dumps(l) + "\n")

    # 2026-11-11: the Codex conversation, environments and cross-check artifacts. The
    # conversation is the transcript of record (rollout), the object store is the
    # projection, and the two are counted against each other so a gap is named.
    if rec.codex_conversations:
        os.makedirs(os.path.join(a.out, "conversation"), exist_ok=True)
        for block in rec.codex_conversations:
            name = os.path.basename(block["session"])
            with open(os.path.join(a.out, "conversation", name + ".jsonl"), "w") as f:
                for rec_row in block["records"]:
                    f.write(json.dumps(rec_row, default=str) + "\n")
    environments = []
    for s in rec.sessions:
        cx = s.get("codex")
        if not cx:
            continue
        environments.append(
            dict(
                session=s["session"],
                thread_id=cx.get("thread_id"),
                session_id=cx.get("session_id"),
                parent_thread_id=cx.get("parent_thread_id"),
                originator=cx.get("originator"),
                source=cx.get("source"),
                thread_source=cx.get("thread_source"),
                cli_version=cx.get("cli_version"),
                model=cx.get("model"),
                model_provider=cx.get("model_provider"),
                cwd=s.get("cwd"),
                workspace_roots=cx.get("workspace_roots"),
                filesystem_roots=cx.get("filesystem_roots"),
                environments=cx.get("environments"),
                sandbox_policy=cx.get("sandbox_policy"),
                approval_policy=cx.get("approval_policy"),
                permission_profile=cx.get("permission_profile"),
                collaboration_mode=cx.get("collaboration_mode"),
                effort=cx.get("effort"),
                turns=cx.get("turns"),
                records=cx.get("records"),
                records_in_window=cx.get("records_in_window"),
                tool_calls=cx.get("tool_calls"),
                tool_calls_in_window=cx.get("tool_calls_in_window"),
                conversation=s.get("conversation"),
                subagents=cx.get("subagents"),
                compactions=cx.get("compactions"),
                turn_aborts=cx.get("turn_aborts"),
                token_totals=cx.get("token_totals"),
                started=iso(s.get("started")),
                ended=iso(s.get("ended")),
                files=s.get("files"),
            )
        )
    if environments:
        json.dump(
            environments, open(a.out + "/environments.json", "w"), indent=1, default=str
        )
    if codex_reconstruction:
        json.dump(
            codex_reconstruction,
            open(a.out + "/codex_reconstruction.json", "w"),
            indent=1,
            default=str,
        )
    if a.codex_object_store:
        obj = codex_object_store(a.codex_object_store, rec.codex_window, rec)
        json.dump(
            obj, open(a.out + "/codex_object_store.json", "w"), indent=1, default=str
        )
    if a.codex_catalog:
        cat = codex_catalog(a.codex_catalog)
        json.dump(cat, open(a.out + "/codex_catalog.json", "w"), indent=1, default=str)

    by = collections.defaultdict(collections.Counter)
    for r in rows:
        c = by[r["stream"]]
        c["files"] += 1
        c[r["recoverability"]] += 1
        if r["at_risk"]:
            c["volatile"] += 1
    out = [
        "# Forensic classification",
        "",
        "files: %d | sessions: %d | ledger entries: %d | destructive commands: %d"
        % (
            len(rows),
            len(rec.sessions),
            len(rec.ledger),
            sum("DESTRUCTIVE" in l["flags"] for l in rec.ledger),
        ),
        "",
        "| stream | files | FULL | PARTIAL | EDIT-ONLY | DELETED | in /tmp (at risk) |",
        "|---|---|---|---|---|---|---|",
    ]
    for k, c in sorted(by.items(), key=lambda kv: -kv[1]["files"]):
        out.append(
            "| %s | %d | %d | %d | %d | %d | %d |"
            % (
                k,
                c["files"],
                c["FULL"],
                c["PARTIAL"],
                c["EDIT-ONLY"],
                c["DELETED-BY-AGENT"],
                c["volatile"],
            )
        )
    out += ["", "## Sessions", ""]
    for s in sorted(rec.sessions, key=lambda s: str(s.get("started"))):
        pl = (
            ", ".join(
                "%d/%d" % (p["subgoals_done"], p["subgoals_total"]) for p in s["plans"]
            )
            or "-"
        )
        out.append(
            "- %s %s [%s] %s | %d files | plans done %s | %s"
            % (
                s["agent"],
                s["session"][:12],
                s["stream"],
                s.get("model"),
                s["files"],
                pl,
                (s.get("prompt") or "")[:110].replace("\n", " "),
            )
        )
    open(a.out + "/streams.md", "w").write("\n".join(out) + "\n")
    print("\n".join(out[:16]))

    # 2026-10-31: the completion marker. The corpus is ~780 MiB and the extraction runs
    # detached, so "the intent returned" says nothing about "the extraction finished". The
    # marker is written only after the manifest, the recovered tree and the streams summary
    # are on disk, and it carries the counts, so a waiter can read the result instead of
    # guessing from a pid.
    summary = dict(
        files=len(rows),
        sessions=len(rec.sessions),
        ops=len(rec.ops),
        reads=len(rec.reads),
        results=len(rec.results),
        parse_errors=len(rec.parse_errors),
        store_bytes=store.bytes,
        full=sum(1 for r in rows if r["recoverability"] == "FULL"),
        partial=sum(1 for r in rows if r["recoverability"] == "PARTIAL"),
        edit_only=sum(1 for r in rows if r["recoverability"] == "EDIT-ONLY"),
        deleted=sum(1 for r in rows if r["recoverability"] == "DELETED-BY-AGENT"),
        finished_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    )
    with open(a.out + "/EXTRACTED", "w") as f:
        f.write(json.dumps(summary, indent=1) + "\n")
    print("EXTRACTED %s" % json.dumps(summary))


if __name__ == "__main__":
    main()
