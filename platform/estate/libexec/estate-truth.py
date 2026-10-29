#!/usr/bin/env python3
"""estate-truth -- the instrument that measures whether the founder's path actually works.

WHY THIS EXISTS. The estate has a process for ownership (claims) and a process for code (gates,
CI, Greenlane). It had no process for TRUTH: nothing standing said whether the founder's own
path answered. So a claim could carry no proof and still land, a fix could not be judged, and
on 2026-10-29 the estate was "totally out of touch with reality" while every gate was green.

This is that instrument. It measures a declared set of predicates over the founder's real path
and gives each one a verdict:

    MEASURED_OK    the predicate was attempted and its expectation was met
    MEASURED_FAIL  the predicate was attempted and its expectation was NOT met
    UNKNOWN        the predicate could not be attempted from here (no credential, no host)

THE RULE THAT MAKES IT WORTH HAVING: UNKNOWN IS NEVER OK. A predicate nobody could measure
counts against the verdict exactly as a failure does, because "we did not look" and "it works"
are not the same statement. The aggregate verdict is therefore a total function over the
predicate set -- there is no way for the estate to be reported as healthy by omission.

    verdict = MEASURED_FAIL if any predicate failed
            = UNKNOWN      if any predicate is unknown
            = MEASURED_OK  otherwise

WHAT IT WRITES.

    ~/.estate/results/truth/latest.json   the measurement, for a later session
    catalog/truth-verdicts.json            the machine-generated snapshot, committed like the
                                            capability registry, so a gate can verify it

WHAT IT NEVER DOES. It never prints a credential, a prompt body or a response body: a verdict
carries a status, a latency and a short reason. The probe prompt is the fixed string
"Reply with exactly: PONG" and the expected token is PONG, so a passing predicate is provable
from the transcript without leaking anything.

EXIT. 0 the verdict is MEASURED_OK, 1 it is MEASURED_FAIL, 2 it is UNKNOWN. A door that
cannot fail is not a door.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import re
import socket
import subprocess  # noqa: S404 -- the command predicates are declared in the contract, not typed
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

OK = "MEASURED_OK"
FAIL = "MEASURED_FAIL"
UNKNOWN = "UNKNOWN"

PROBE_PROMPT = "Reply with exactly: PONG"
EXPECTED_REPLY = "PONG"

CONTRACT_DEFAULT = "catalog/truth-contract.json"
RESULTS_DEFAULT = "~/.estate/results/truth/latest.json"
SNAPSHOT_DEFAULT = "catalog/truth-verdicts.json"

# The scope a predicate can be measured from. "any" is measured everywhere; "laptop" only on
# the machine that carries the founder's own path; "cluster" only where the cluster runs.
SCOPE_ANY = "any"
SCOPE_LAPTOP = "laptop"
SCOPE_CLUSTER = "cluster"


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def expand(path: str) -> Path:
    return Path(os.path.expanduser(os.path.expandvars(path)))


def host_scope() -> str:
    """Which scope this host can measure: the laptop, the cluster, or neither."""
    if os.environ.get("KUBERNETES_SERVICE_HOST"):
        return SCOPE_CLUSTER
    if sys.platform == "darwin":
        return SCOPE_LAPTOP
    return "none"


def verdict_of(results: list) -> str:
    """The aggregate. Total by construction: every predicate contributes, and UNKNOWN counts
    against the verdict exactly as a failure does."""
    verdicts = [r["verdict"] for r in results]
    if FAIL in verdicts:
        return FAIL
    if UNKNOWN in verdicts:
        return UNKNOWN
    return OK


def counts_of(results: list) -> dict:
    out = {OK: 0, FAIL: 0, UNKNOWN: 0}
    for r in results:
        out[r["verdict"]] = out.get(r["verdict"], 0) + 1
    return out


SECRET_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_\-]{6,}"),
    re.compile(r"(?i)\b(bearer|token|api[_-]?key|password|secret)\b\s*[:=]?\s*\S{8,}"),
    re.compile(r"\b[A-Za-z0-9_\-]{40,}\b"),
)


def redact(text: str) -> str:
    """A verdict carries a reason, never a credential.

    The detail can quote an upstream error body, and an upstream error body can quote the key
    that was refused (the router's own answer once named the env var it wanted). The
    instrument that reports the estate's state must never become the leak.
    """
    out = str(text)
    for pattern in SECRET_PATTERNS:
        out = pattern.sub("<redacted>", out)
    return out


def result(
    predicate_id: str, verdict: str, detail: str, scope: str, seconds: float
) -> dict:
    return {
        "id": predicate_id,
        "verdict": verdict,
        "detail": redact(detail)[:400],
        "scope": scope,
        "duration_s": round(seconds, 3),
        "measured_at": now_iso(),
    }


# ---------------------------------------------------------------- the kinds of predicate


def eval_http(pred: dict) -> tuple:
    """One HTTP request. The verdict is about the ANSWER, never about the connect: a path
    that refuses the connection has been measured, and it did not work."""
    url = pred["url"]
    timeout = float(pred.get("timeout_s", 30))
    method = pred.get("method", "GET").upper()
    headers = {"User-Agent": "estate-truth/1.0"}
    for k, v in (pred.get("headers") or {}).items():
        headers[k] = expand(str(v)).as_posix() if str(v).startswith("~") else str(v)
    body = None
    if pred.get("body") is not None:
        body = json.dumps(pred["body"]).encode("utf-8")
        headers.setdefault("Content-Type", "application/json")
    auth_env = pred.get("auth_env")
    cred_missing = ""
    if auth_env:
        token = os.environ.get(auth_env, "")
        if token:
            scheme = pred.get("auth_scheme", "Bearer")
            headers["Authorization"] = ("%s %s" % (scheme, token)).strip()
        else:
            # The credential is not on this host. That does not stop the measurement: the
            # path still gets asked, and its ANSWER is the truth. A refusal is a failure of
            # the founder's path; a success without the credential proves the endpoint
            # answers, not that the founder's credentialed path works, so that is UNKNOWN.
            cred_missing = auth_env
    req = urllib.request.Request(url, data=body, headers=headers, method=method)  # noqa: S310 -- the URL is declared in the contract
    started = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 -- the URL is declared in the contract
            payload = resp.read(65536).decode("utf-8", "replace")
            status = resp.status
    except urllib.error.HTTPError as exc:
        payload = ""
        with contextlib.suppress(
            Exception
        ):  # the body is a nicety, the status is the verdict
            payload = exc.read(65536).decode("utf-8", "replace")
        status = exc.code
        elapsed = time.time() - started
        want = int(pred.get("expect_status", 200))
        if status == want:
            if cred_missing:
                return (
                    UNKNOWN,
                    "HTTP %d without %s: the endpoint answers, the founder's credentialed "
                    "path is not proven" % (status, cred_missing),
                    elapsed,
                )
            return OK, "HTTP %d" % status, elapsed
        return (
            FAIL,
            "HTTP %d (expected %d): %s%s"
            % (
                status,
                want,
                payload[:200],
                " (no %s on this host)" % cred_missing if cred_missing else "",
            ),
            elapsed,
        )
    except (urllib.error.URLError, socket.timeout, OSError) as exc:
        elapsed = time.time() - started
        return (
            FAIL,
            "no answer: %s%s"
            % (
                str(exc)[:200],
                " (no %s on this host)" % cred_missing if cred_missing else "",
            ),
            elapsed,
        )
    elapsed = time.time() - started
    want = int(pred.get("expect_status", 200))
    if status != want:
        return FAIL, "HTTP %d (expected %d)" % (status, want), elapsed
    expect = pred.get("expect_contains")
    if expect and expect not in payload:
        return (
            FAIL,
            "HTTP %d but the answer did not contain %r" % (status, expect),
            elapsed,
        )
    if cred_missing:
        return (
            UNKNOWN,
            "HTTP %d in %.2fs without %s: the endpoint answers, the founder's credentialed "
            "path is not proven" % (status, elapsed, cred_missing),
            elapsed,
        )
    return OK, "HTTP %d in %.2fs" % (status, elapsed), elapsed


def eval_command(pred: dict) -> tuple:
    """One declared command. The argv comes from the contract, never from a shell string."""
    argv = [str(a) for a in pred.get("command") or []]
    if not argv:
        return UNKNOWN, "the predicate declares no command", 0.0
    timeout = float(pred.get("timeout_s", 30))
    started = time.time()
    try:
        proc = subprocess.run(  # noqa: S603 -- argv is a list, never a shell string
            argv,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError:
        return (
            UNKNOWN,
            "%s is not installed on this host" % argv[0],
            time.time() - started,
        )
    except subprocess.TimeoutExpired:
        return FAIL, "no answer within %.0fs" % timeout, time.time() - started
    elapsed = time.time() - started
    want_rc = int(pred.get("expect_rc", 0))
    if proc.returncode != want_rc:
        err = (proc.stderr or proc.stdout or "").strip().splitlines()
        tail = err[-1][:200] if err else ""
        return (
            FAIL,
            "exit %d (expected %d): %s" % (proc.returncode, want_rc, tail),
            elapsed,
        )
    expect = pred.get("expect_contains")
    out = proc.stdout or ""
    if expect and expect not in out:
        return FAIL, "exit 0 but the answer did not contain %r" % expect, elapsed
    return OK, "exit 0 in %.2fs" % elapsed, elapsed


def _refused_lanes(refused) -> set:
    """The lanes a refusal list names.

    A refusal is either a lane NAME or an object that carries the lane and WHY it was refused.
    The reason is the point: a lane refused without its reason is a lane that vanished in
    silence, which is the defect the ledger was written to end. So both shapes are read, and
    neither shape is an excuse for the instrument to answer UNKNOWN: measured 2026-10-29, the
    ledger's objects raised `TypeError: unhashable type: 'dict'` here and the predicate could
    not be measured at all.
    """
    lanes = set()
    for item in refused or []:
        if isinstance(item, str):
            lanes.add(item)
        elif isinstance(item, dict):
            name = item.get("lane") or item.get("model_name") or ""
            if name:
                lanes.add(name)
    return lanes


def eval_file(pred: dict) -> tuple:
    """One file in the estate's own state. The estate's state missing IS a failure: the
    founder's path cannot work without it."""
    path = expand(pred["path"])
    started = time.time()
    if not path.is_file():
        return FAIL, "%s is absent" % path, time.time() - started
    assertion = pred.get("assert", "exists")
    if assertion == "exists":
        return OK, "%s exists" % path, time.time() - started
    try:
        doc = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        return FAIL, "%s cannot be read: %s" % (path, exc), time.time() - started
    if assertion == "declared_accounted":
        if not isinstance(doc, dict):
            return (
                FAIL,
                "%s does not account for its declared lanes (it is a %s, not a ledger)"
                % (path, type(doc).__name__),
                time.time() - started,
            )
        declared = doc.get("declared")
        served = doc.get("served")
        refused = doc.get("refused")
        if (
            not isinstance(declared, list)
            or not isinstance(served, list)
            or not isinstance(refused, list)
        ):
            return (
                FAIL,
                "%s does not account for its declared lanes (declared/served/refused missing)"
                % path,
                time.time() - started,
            )
        unaccounted = sorted(set(declared) - set(served) - _refused_lanes(refused))
        if unaccounted:
            return (
                FAIL,
                "%d declared lane(s) are neither served nor refused: %s"
                % (len(unaccounted), ",".join(unaccounted[:5])),
                time.time() - started,
            )
        return (
            OK,
            "%d declared lane(s) accounted for: %d served, %d refused"
            % (
                len(declared),
                len(set(declared) & set(served)),
                len(_refused_lanes(refused)),
            ),
            time.time() - started,
        )
    if assertion == "door_present":
        door = (doc or {}).get("door") or {}
        if not door.get("url"):
            return FAIL, "%s carries no door url" % path, time.time() - started
        return OK, "the door is at %s" % door.get("url"), time.time() - started
    return FAIL, "unknown assertion %r" % assertion, time.time() - started


EVALUATORS = {"http": eval_http, "command": eval_command, "file": eval_file}


# ---------------------------------------------------------------- the measurement


def measure(contract: dict, scope: str, only: str = "") -> list:
    """Every predicate is asked, in parallel: the instrument's wall time is the slowest
    question, not the sum of them, so a door can hold the whole board inside its ceiling."""
    preds = [
        p
        for p in (contract.get("predicates") or [])
        if not only or (p.get("id") or "?") == only
    ]
    if not preds:
        return []
    results = [None] * len(preds)

    def one(index: int) -> None:
        pred = preds[index]
        pid = pred.get("id") or "?"
        want_scope = pred.get("scope", SCOPE_ANY)
        if want_scope != SCOPE_ANY and want_scope != scope:
            results[index] = result(
                pid,
                UNKNOWN,
                "measurable only from the %s scope; this host is %s"
                % (want_scope, scope),
                want_scope,
                0.0,
            )
            return
        evaluator = EVALUATORS.get(pred.get("kind", ""))
        if evaluator is None:
            results[index] = result(
                pid,
                UNKNOWN,
                "unknown predicate kind %r" % pred.get("kind"),
                want_scope,
                0.0,
            )
            return
        try:
            verdict, detail, elapsed = evaluator(pred)
        except Exception as exc:  # noqa: BLE001 -- an instrument that raises is not an instrument
            verdict, detail, elapsed = (
                UNKNOWN,
                "the measurement raised %s: %s" % (type(exc).__name__, exc),
                0.0,
            )
        results[index] = result(pid, verdict, detail, want_scope, elapsed)

    with ThreadPoolExecutor(max_workers=max(1, len(preds))) as pool:
        list(pool.map(one, range(len(preds))))
    return [r for r in results if r is not None]


def snapshot(contract: dict, results: list, scope: str) -> dict:
    by_scope = {}
    for want in (SCOPE_ANY, SCOPE_LAPTOP, SCOPE_CLUSTER):
        subset = [r for r in results if r["scope"] == want]
        if subset:
            by_scope[want] = {
                "verdict": verdict_of(subset),
                "counts": counts_of(subset),
            }
    verdict = verdict_of(results)
    return {
        "generated_at": now_iso(),
        "generator": "bin/idp-estate-truth",
        "contract_version": contract.get("version"),
        "host": {"hostname": socket.gethostname(), "scope": scope},
        "verdict": verdict,
        "ok": verdict == OK,
        "counts": counts_of(results),
        "scopes": by_scope,
        "predicates": results,
    }


def render(report: dict) -> str:
    lines = []
    for r in report["predicates"]:
        lines.append(
            "%-8s %-26s %-8s %s" % (r["verdict"], r["id"], r["scope"], r["detail"])
        )
    lines.append(
        "TRUTH VERDICT: %s  (ok=%d fail=%d unknown=%d) host=%s scope=%s"
        % (
            report["verdict"],
            report["counts"].get(OK, 0),
            report["counts"].get(FAIL, 0),
            report["counts"].get(UNKNOWN, 0),
            report["host"]["hostname"],
            report["host"]["scope"],
        )
    )
    return "\n".join(lines)


def load_contract(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        sys.stderr.write("FAIL estate-truth  the contract cannot be read: %s\n" % exc)
        raise SystemExit(2) from exc


def resolve_contract(explicit: str) -> Path:
    """Find the contract wherever this copy of the instrument lives.

    The instrument is staged twice: in the repo (platform/estate/libexec) and in the runtime
    (~/.estate/libexec), and the runtime tree is a clone of origin/main, so the contract is
    next to the code in every layout. The search is explicit rather than clever, because an
    instrument that cannot find its own questions is worse than no instrument.
    """
    if explicit:
        return expand(explicit)
    here = Path(__file__).resolve()
    candidates = [Path.cwd() / CONTRACT_DEFAULT]
    for parent in here.parents:
        candidates.append(parent / CONTRACT_DEFAULT)
    candidates.append(Path.home() / ".estate" / "runtime" / "idp" / CONTRACT_DEFAULT)
    candidates.append(Path.home() / ".estate" / "truth-contract.json")
    for cand in candidates:
        try:
            if cand.is_file():
                return cand
        except OSError:
            continue
    return Path.cwd() / CONTRACT_DEFAULT


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="measure the founder's path and say so")
    ap.add_argument("--contract", default="")
    ap.add_argument("--results", default=RESULTS_DEFAULT)
    ap.add_argument("--write-snapshot", default="", metavar="PATH")
    ap.add_argument("--predicate", default="", metavar="ID")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    contract_path = resolve_contract(args.contract)
    if not contract_path.is_file():
        # A missing contract is a blind instrument, not an all-clear.
        sys.stderr.write("FAIL estate-truth  no contract at %s\n" % contract_path)
        return 2
    contract = load_contract(contract_path)
    scope = host_scope()
    results = measure(contract, scope, args.predicate)
    report = snapshot(contract, results, scope)

    results_path = expand(args.results)
    try:
        results_path.parent.mkdir(parents=True, exist_ok=True)
        results_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    except OSError as exc:
        sys.stderr.write(
            "WARN estate-truth  the results file could not be written: %s\n" % exc
        )

    if args.write_snapshot:
        snap_path = expand(args.write_snapshot)
        try:
            snap_path.parent.mkdir(parents=True, exist_ok=True)
            snap_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
            sys.stderr.write("ok      estate-truth  snapshot written: %s\n" % snap_path)
        except OSError as exc:
            sys.stderr.write(
                "FAIL estate-truth  the snapshot could not be written: %s\n" % exc
            )
            return 2

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render(report))
    return {OK: 0, FAIL: 1, UNKNOWN: 2}[report["verdict"]]


if __name__ == "__main__":
    raise SystemExit(main())
