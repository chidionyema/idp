"""The memory snapshot: memory's second home, so a dead cluster costs freshness, not memory (idp#7397).

WHY (2026-10-28). Oracle removed the tenancy's OKE entitlement (Container Engine limits
cluster-count=0, node-count=0) and the cluster went dark. Unified memory had exactly one home --
Postgres estate-db on that cluster, no backup stanza, no copy anywhere else -- so the door
answered `URLError EOF (_ssl.c)` and every reader had nothing. Active Memory's only fallback was
the last good brief held in router RAM for 30 minutes: the laptop router logged 841 brief reads
that ended "nothing to serve" against 57 that served stale. The same evening the laptop disk hit
zero, so the laptop was no second home either.

WHAT. One JSON document, the same everywhere it is kept:

    {"version": 1, "namespace": "estate", "source": "<writer>",
     "facts_at": <epoch>, "facts": [<brief rows: key, content, provenance, recorded_at>],
     "focus_at": <epoch>, "focus": [<focus.register_from_issues rows>]}

`facts_at` and `focus_at` are separate because the two halves have separate sources: facts come
through the memory door (down with the cluster), focus from the GitHub claim ledger (up). A
writer that cannot reach the door keeps the old facts and their old stamp, and still refreshes
the focus -- a reader is always told how old each half is, never handed an old fact as new.

Homes, read in this order:

  1. Cloudflare R2, object memory/snapshot.json in the estate's private bucket: a second cloud,
     not OCI and not the laptop. Written by bin/memory-snapshot from a scheduled GitHub Actions
     job (.github/workflows/memory-snapshot.yml, ADR 0034 rung 2) and read back before the run
     counts. idp is a public repository, so the snapshot never lives in git.
  2. A local copy (~/.estate/memory/snapshot.json): the last remote copy this machine read.
     Bounded to MAX_BYTES, written atomically, and never written while the disk is below
     ESTATE_DISK_FLOOR_MB -- a cache must not be what fills the disk (the 2026-10-28 JetStream
     store wrote until `no space left on device`).

Every read fails open: a missing key, a dead network or a corrupt file returns None, and the
caller goes on without the snapshot. Python 3.9 runs this file (focus.py's rule).
"""

from __future__ import annotations

import contextlib
import datetime
import hashlib
import hmac
import json
import os
import re
import shutil
import tempfile
import time
import urllib.parse
import urllib.request

VERSION = 1
OBJECT_KEY = "memory/snapshot.json"
# A brief is a few KB; the snapshot is the union of a few dozen briefs. 4 MiB is two orders of
# magnitude of headroom and still nothing next to the disk floor.
MAX_BYTES = 4 * 1024 * 1024
DISK_FLOOR_MB = int(os.environ.get("ESTATE_DISK_FLOOR_MB", "1024"))
# The local copy is re-read from R2 once it is this old (the writer runs every 15 minutes).
PULL_AFTER_S = 900
R2_TIMEOUT_S = 5.0
RECENT_KINDS = ("decision", "incident")  # unified-memory-server BRIEF_RECENT_KINDS
R2_ENV = ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET")


def _home() -> str:
    return os.environ.get("ESTATE_MEMORY_HOME") or os.path.join(
        os.path.expanduser("~"), ".estate", "memory"
    )


def local_path() -> str:
    return os.path.join(_home(), "snapshot.json")


# --- the document --------------------------------------------------------------------------------


def valid(snap) -> bool:
    return (
        isinstance(snap, dict)
        and snap.get("version") == VERSION
        and isinstance(snap.get("facts"), list)
        and isinstance(snap.get("focus"), list)
    )


def encode(snap: dict, max_bytes: int = 0) -> bytes:
    """The bytes every home stores, bounded to MAX_BYTES by dropping the oldest facts first."""
    max_bytes = max_bytes or MAX_BYTES
    snap = dict(snap)
    facts = sorted(
        snap.get("facts") or [], key=lambda f: str(f.get("recorded_at") or "")
    )
    while True:
        snap["facts"] = facts
        body = json.dumps(snap, sort_keys=True, separators=(",", ":")).encode()
        if len(body) <= max_bytes or not facts:
            return body
        facts = facts[max(1, len(facts) // 10) :]


def decode(body) -> dict | None:
    try:
        snap = json.loads(body)
    except Exception:
        return None
    return snap if valid(snap) else None


# --- home 2: the local copy ----------------------------------------------------------------------


def free_mb(path: str) -> int:
    d = os.path.dirname(path) or "."
    while d and not os.path.isdir(d):
        d = os.path.dirname(d)
    try:
        return shutil.disk_usage(d or "/").free // (1024 * 1024)
    except OSError:
        return 0


def write_local(snap: dict, path: str = "", floor_mb: int = -1) -> str:
    """Write the local copy; "" when written, else why not. Atomic: a reader sees the old copy or
    the new one, never half of either, and a full disk leaves the old copy standing."""
    path = path or local_path()
    floor_mb = DISK_FLOOR_MB if floor_mb < 0 else floor_mb
    body = encode(snap)
    free = free_mb(path)
    if free - len(body) // (1024 * 1024) < floor_mb:
        return f"disk floor: {free} MB free, floor {floor_mb} MB"
    tmp = ""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=".snapshot.", dir=os.path.dirname(path))
        with os.fdopen(fd, "wb") as f:
            f.write(body)
        os.replace(tmp, path)
        return ""
    except OSError as exc:
        if tmp:
            with contextlib.suppress(OSError):
                os.unlink(tmp)
        return f"write failed: {exc}"


def read_local(path: str = "") -> dict | None:
    try:
        with open(path or local_path(), "rb") as f:
            return decode(f.read())
    except OSError:
        return None


# --- home 1: R2 ----------------------------------------------------------------------------------


def r2_config(env=None) -> dict | None:
    """The bucket, from the environment by name (AGENTS.md section 4); None when any is unset."""
    env = os.environ if env is None else env
    vals = {k: str(env.get(k) or "").strip() for k in R2_ENV}
    if not all(vals.values()):
        return None
    return {
        "host": f"{vals['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
        "bucket": vals["R2_BUCKET"],
        "access_key": vals["R2_ACCESS_KEY_ID"],
        "secret_key": vals["R2_SECRET_ACCESS_KEY"],
        "region": "auto",
    }


def _hmac(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode(), hashlib.sha256).digest()


def sign(
    method: str,
    host: str,
    path: str,
    headers: dict,
    payload_sha: str,
    access_key: str,
    secret_key: str,
    region: str,
    amz_date: str,
    service: str = "s3",
) -> str:
    """The AWS Signature Version 4 Authorization header R2 checks (no query string)."""
    hdrs = {k.lower(): " ".join(str(v).split()) for k, v in headers.items()}
    hdrs["host"] = host
    hdrs["x-amz-content-sha256"] = payload_sha
    hdrs["x-amz-date"] = amz_date
    names = sorted(hdrs)
    canonical = "\n".join(
        [
            method,
            urllib.parse.quote(path, safe="/~"),
            "",
            "".join(f"{n}:{hdrs[n]}\n" for n in names),
            ";".join(names),
            payload_sha,
        ]
    )
    day = amz_date[:8]
    scope = f"{day}/{region}/{service}/aws4_request"
    to_sign = "\n".join(
        [
            "AWS4-HMAC-SHA256",
            amz_date,
            scope,
            hashlib.sha256(canonical.encode()).hexdigest(),
        ]
    )
    k = _hmac(("AWS4" + secret_key).encode(), day)
    for part in (region, service, "aws4_request"):
        k = _hmac(k, part)
    sig = hmac.new(k, to_sign.encode(), hashlib.sha256).hexdigest()
    return (
        f"AWS4-HMAC-SHA256 Credential={access_key}/{scope}, "
        f"SignedHeaders={';'.join(names)}, Signature={sig}"
    )


def _r2(cfg: dict, method: str, body: bytes, timeout: float) -> bytes:
    path = f"/{cfg['bucket']}/{OBJECT_KEY}"
    sha = hashlib.sha256(body).hexdigest()
    amz_date = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    extra = {"content-type": "application/json"} if method == "PUT" else {}
    auth = sign(
        method,
        cfg["host"],
        path,
        extra,
        sha,
        cfg["access_key"],
        cfg["secret_key"],
        cfg["region"],
        amz_date,
    )
    req = urllib.request.Request(  # noqa: S310 - https to the bucket host built above
        f"https://{cfg['host']}{path}",
        data=body if method == "PUT" else None,
        method=method,
        headers={
            **extra,
            "x-amz-content-sha256": sha,
            "x-amz-date": amz_date,
            "Authorization": auth,
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310 - as above
        return r.read()


def r2_get(cfg: dict, timeout: float = R2_TIMEOUT_S) -> bytes:
    return _r2(cfg, "GET", b"", timeout)


def r2_put(cfg: dict, body: bytes, timeout: float = R2_TIMEOUT_S) -> None:
    _r2(cfg, "PUT", body, timeout)


# --- reading: remote when the local copy is old, local always as the floor -----------------------


def stamp(snap: dict) -> float:
    return max(float(snap.get("facts_at") or 0), float(snap.get("focus_at") or 0))


def load(path: str = "", cfg=None, now: float = 0.0, getter=None) -> dict | None:
    """The freshest snapshot this machine can see, or None. Never raises.

    A local copy younger than PULL_AFTER_S is used as it is. An older one is replaced by the R2
    copy when R2 answers with something newer; when R2 cannot be read the old local copy is still
    the answer -- an old fact with its age stated beats no fact.
    """
    now = now or time.time()
    path = path or local_path()
    local = read_local(path)
    if local and now - stamp(local) < PULL_AFTER_S:
        return local
    cfg = r2_config() if cfg is None else cfg
    if cfg:
        try:
            remote = decode((getter or r2_get)(cfg))
        except Exception:
            remote = None
        if remote and (not local or stamp(remote) > stamp(local)):
            write_local(remote, path)
            return remote
    return local


# --- answering from it ---------------------------------------------------------------------------

# Four characters or more: "the", "why" and "did" match every fact and rank nothing.
_WORD = re.compile(r"[a-z0-9][a-z0-9_.-]{3,}")


def _words(text: str) -> set:
    return set(_WORD.findall(str(text or "").lower()))


def _fact_text(f: dict) -> str:
    return str(f.get("text") or f.get("content") or "")


def _kind(f: dict) -> str:
    meta = f.get("metadata") or f.get("provenance") or {}
    return str(meta.get("kind") or "") if isinstance(meta, dict) else ""


def brief(snap: dict, task: str, limit: int = 5, now: float = 0.0) -> dict:
    """A brief in the server's own shape, answered from the snapshot.

    `relevant` is ranked by words shared with the task -- not by meaning, and it says so
    (`search_by_meaning: False`). `recent` is the newest decisions and incidents, as the server's.
    `snapshot` carries the facts' age, so the reader can tell the model how old they are.
    """
    now = now or time.time()
    facts = [
        f for f in snap.get("facts") or [] if isinstance(f, dict) and _fact_text(f)
    ]
    want = _words(task)
    scored = []
    for i, f in enumerate(facts):
        hits = len(want & _words(_fact_text(f) + " " + str(f.get("key") or "")))
        if hits:
            scored.append((hits, str(f.get("recorded_at") or ""), i))
    scored.sort(reverse=True)
    picked = [i for _, _, i in scored[:limit]]
    recent = sorted(
        (
            i
            for i, f in enumerate(facts)
            if i not in picked and _kind(f) in RECENT_KINDS
        ),
        key=lambda i: str(facts[i].get("recorded_at") or ""),
        reverse=True,
    )[:limit]
    return {
        "namespace": snap.get("namespace", "estate"),
        "relevant": [facts[i] for i in picked],
        "recent": [facts[i] for i in recent],
        "search_by_meaning": False,
        "snapshot": {
            "source": snap.get("source"),
            "facts_age_s": int(now - float(snap.get("facts_at") or 0)),
        },
    }


def focus_rows(snap: dict, now: float = 0.0) -> list:
    """The snapshot's focus register, aged to now (focus.age_rows: a lapsed claim is not live)."""
    import focus  # noqa: PLC0415 - the sibling module; late, so this file imports standalone

    now = now or time.time()
    return focus.age_rows(
        snap.get("focus") or [], now - float(snap.get("focus_at") or 0)
    )
