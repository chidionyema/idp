#!/usr/bin/env python3
"""cp3 get_workload_logs tool: property + incident tests (crew#216 CP3).

Rungs, per ~/AGENTS.md "How to test":
  differential  tail_lines() is checked against a naive reference (read the whole
                file, slice the last N lines in Python) over many random file sizes
                and requested tail values -- the oracle is the obvious-but-slow
                implementation, tail_lines() is the bounded-memory one
                (cp3_get_workload_logs.feature scenario 2).
  property      tail is bounded to ESTATE_LOGS_MAX_TAIL over hundreds of
                (line-count x requested-tail) combinations, including a
                1,000,000-line request.
  incident      a scheduled_job asset with a real plist resolves to its own log
                and returns lines in one call (scenario 1); a non-scheduled_job
                asset degrades with an error, not an exception, proved both ways;
                get_workload_state and get_workload_logs are two distinct
                registered tools (scenario 3).
  static        the source never shells out (same guard shape as CP1/CP2).

Run directly: python3 tests/test_cp3_workload_logs.py (needs pyyaml). Wired into
bin/idp-ci. Exit 0 pass, 1 fail.
"""
import os
import plistlib
import random
import re
import sqlite3
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "mcp", "plugins"))
import workload_logs as wl  # noqa: E402

fail = False


def check(name, cond, detail=""):
    global fail
    if cond:
        print(f"ok    {name}")
    else:
        fail = True
        print(f"FAIL  {name}  {detail}")


# --- static: the source never shells out (same shape as CP1/CP2) ------------
SRC_PATH = os.path.join(ROOT, "mcp", "plugins", "workload_logs.py")
with open(SRC_PATH, encoding="utf-8") as fh:
    src = fh.read()
code_only = re.sub(r'^"""(?:[^"]|"(?!""))*"""', "", src, count=1)
check("cp3-no-shellout-in-prose", code_only != src)
SHELLOUT_RE = re.compile(
    r"^\s*(import subprocess\b|from subprocess\b)|subprocess\.(run|Popen|call|check_output|check_call)\(|os\.system\(|shell\s*=\s*True",
    re.M,
)
check("cp3-no-shellout", not SHELLOUT_RE.search(code_only))
check("cp3-no-shellout-guard-discriminates",
      bool(SHELLOUT_RE.search("import subprocess\nsubprocess.run(['ls'], shell=True)\n")))

# --- scenario 3: two distinct tools, not one tool with a hidden verbose flag -
STATE_SRC_PATH = os.path.join(ROOT, "mcp", "plugins", "workload_state.py")
with open(STATE_SRC_PATH, encoding="utf-8") as fh:
    state_src = fh.read()
check("cp3-distinct-tool-registered", "async def get_workload_logs(" in src
      and "async def get_workload_logs(" not in state_src)
check("cp3-state-tool-unchanged", "async def get_workload_state(" in state_src
      and "async def get_workload_state(" not in src)
check("cp3-no-cross-import", "import workload_state" not in src
      and "import workload_logs" not in state_src,
      "the two plugin files must load standalone, same as datasette --plugins-dir loads them")


def naive_tail(text, n):
    if n <= 0:
        return []
    return text.splitlines()[-n:]


with tempfile.TemporaryDirectory() as td:
    # --- differential: tail_lines() against the naive whole-file reference ------
    rng = random.Random(0)
    diff_ok = True
    for trial in range(60):
        nlines = rng.choice([0, 1, 2, 5, 50, 500, 3000])
        log = os.path.join(td, f"log-{trial}.log")
        lines = [f"line-{i:06d} {'x' * rng.randint(0, 40)}" for i in range(nlines)]
        with open(log, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + ("\n" if lines else ""))
        requested = rng.choice([0, 1, 2, 5, 49, 50, 51, 499, 500, 501, 1000000])
        max_tail = 500
        got, enforced, err = wl.tail_lines(log, requested, max_tail)
        want = naive_tail("\n".join(lines), min(max(requested, 0), max_tail))
        if got != want or err is not None:
            diff_ok = False
            print(f"      trial={trial} nlines={nlines} requested={requested} got_n={len(got)} want_n={len(want)}")
    check("cp3-tail-matches-naive-reference", diff_ok)

    # --- property: bound holds over (line-count x requested-tail) combinations --
    LINE_COUNTS = [0, 1, 5, 49, 50, 51, 499, 500, 501, 5000]
    REQUESTS = [0, 1, 5, 49, 50, 51, 499, 500, 501, 5000, 1000000]
    bound_ok = True
    total_cases = 0
    for nlines in LINE_COUNTS:
        log = os.path.join(td, "bound.log")
        with open(log, "w", encoding="utf-8") as fh:
            fh.write("\n".join(f"l{i}" for i in range(nlines)) + ("\n" if nlines else ""))
        for requested in REQUESTS:
            total_cases += 1
            got, enforced, err = wl.tail_lines(log, requested, 500)
            want_n = min(min(max(requested, 0), 500), nlines)
            if len(got) != want_n or enforced != min(max(requested, 0), 500) or err is not None:
                bound_ok = False
                print(f"      nlines={nlines} requested={requested} got={len(got)} want={want_n} enforced={enforced}")
    check("cp3-cases-at-least-100", total_cases >= 100, f"only {total_cases}")
    check("cp3-tail-bounded", bound_ok, "a request was not bounded to max_tail")
    check("cp3-million-line-request-bounded",
          len(wl.tail_lines(os.path.join(td, "bound.log"), 1000000, 500)[0]) <= 500)


    # --- incident: a scheduled_job asset resolves to its own plist's log, one call
    catalog = os.path.join(td, "catalog-info.yaml")
    db = os.path.join(td, "estate.db")
    plist_path = os.path.join(td, "ai.test.job.plist")
    log_path = os.path.join(td, "job.out.log")
    with open(log_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(f"job-line-{i}" for i in range(80)) + "\n")
    with open(plist_path, "wb") as fh:
        plistlib.dump({"Label": "ai.test.job", "StandardOutPath": log_path}, fh)
    with open(catalog, "w", encoding="utf-8") as fh:
        fh.write(
            "apiVersion: backstage.io/v1alpha1\nkind: Resource\nmetadata:\n"
            "  name: app-x\n  annotations:\n    estate/path: /repo/app-x\n"
            "spec:\n  owner: group:default/platform\n---\n"
            "apiVersion: backstage.io/v1alpha1\nkind: Component\nmetadata:\n"
            "  name: not-a-job\n  annotations:\n    estate/path: /repo/not-a-job\n"
            "spec:\n  owner: group:default/platform\n"
        )
    conn = sqlite3.connect(db)
    conn.execute("create table assets (path, kind, plist)")
    conn.execute("insert into assets values (?, 'scheduled_job', ?)", ("/repo/app-x", plist_path))
    conn.execute("insert into assets values (?, 'repo', NULL)", ("/repo/not-a-job",))
    conn.commit()
    conn.close()

    cfg = {"catalog_path": catalog, "estate_db_path": db, "max_tail": 500}
    result = wl.build_workload_logs("app-x", tail=50, cfg=cfg)
    check("cp3-drilldown-one-call", result["found"] is True and result["error"] is None
          and result["log_path"] == log_path and result["line_count"] == 50
          and result["lines"][-1] == "job-line-79" and result["lines"][0] == "job-line-30",
          f"got {result}")

    million = wl.build_workload_logs("app-x", tail=1000000, cfg=cfg)
    check("cp3-scenario2-bounded-not-a-million",
          million["line_count"] == 80 and million["tail_enforced"] == 500
          and million["max_tail"] == 500,
          f"got line_count={million['line_count']} tail_enforced={million['tail_enforced']}")

    # --- incident, both ways: a non-scheduled_job asset degrades, a job does not -
    not_job = wl.build_workload_logs("not-a-job", tail=50, cfg=cfg)
    check("cp3-non-job-degrades", not_job["found"] is True and not_job["error"] is not None
          and not_job["lines"] == [], f"got {not_job}")
    check("cp3-job-not-degraded", result["found"] is True and result["error"] is None)

    unknown = wl.build_workload_logs("app-does-not-exist", tail=50, cfg=cfg)
    check("cp3-unknown-app-degrades", unknown["found"] is False
          and unknown["error"] is not None and unknown["lines"] == [], f"got {unknown}")

print("PASS  cp3-workload-logs" if not fail else "FAIL  cp3-workload-logs")
sys.exit(1 if fail else 0)
