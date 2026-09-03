#!/usr/bin/env python3
"""cp2 get_workload_state tool: property + incident tests (crew#216 CP2).

Rungs, per ~/AGENTS.md "How to test":
  property  the byte ceiling holds over many synthetic (dependency-count x
            metric-sample-count x ceiling) combinations, >= 500 generated cases
            in one run (features/self-aware-platform/cp2_get_workload_state.feature
            scenario 3).
  incident  no raw log line and no per-sample timeseries array ever leaves the
            payload (scenario 2); an app the catalog does not know degrades to
            found=False instead of raising; desired/actual state is present for
            an app the catalog and estate.db both know (scenario 1).
  static    the source never shells out (same guard shape as CP1).

Run directly: python3 tests/test_cp2_workload_state.py (needs pyyaml; .venv/bin/python
has it). Wired into bin/idp-ci. Exit 0 pass, 1 fail.
"""

import os
import re
import sqlite3
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "mcp", "plugins"))
import workload_state as ws  # noqa: E402

fail = False


def check(name, cond, detail=""):
    global fail
    if cond:
        print(f"ok    {name}")
    else:
        fail = True
        print(f"FAIL  {name}  {detail}")


# --- static: the source never shells out (same shape as CP1) ----------------
SRC_PATH = os.path.join(ROOT, "mcp", "plugins", "workload_state.py")
with open(SRC_PATH, encoding="utf-8") as fh:
    src = fh.read()
code_only = re.sub(r'^"""(?:[^"]|"(?!""))*"""', "", src, count=1)
check("cp2-no-shellout-in-prose", code_only != src)
SHELLOUT_RE = re.compile(
    r"^\s*(import subprocess\b|from subprocess\b)|subprocess\.(run|Popen|call|check_output|check_call)\(|os\.system\(|shell\s*=\s*True",
    re.M,
)
check("cp2-no-shellout", not SHELLOUT_RE.search(code_only))
check(
    "cp2-no-shellout-guard-discriminates",
    bool(SHELLOUT_RE.search("import subprocess\nsubprocess.run(['ls'], shell=True)\n")),
)


def synth_catalog_entity(path, app, owner, repo, depends_on, asset_path):
    ann_lines = [f"    github.com/project-slug: {repo}"] if repo else []
    if asset_path:
        ann_lines.append(f"    estate/path: {asset_path}")
    dep_lines = (
        ["  dependsOn:"] + [f"    - {d}" for d in depends_on] if depends_on else []
    )
    doc = (
        "\n".join(
            [
                "apiVersion: backstage.io/v1alpha1",
                "kind: Component",
                "metadata:",
                f"  name: {app}",
                "  annotations:",
            ]
            + ann_lines
            + [
                "spec:",
                f"  owner: {owner}",
            ]
            + dep_lines
        )
        + "\n"
    )
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(doc)


def synth_estate_db(path, rows):
    if os.path.exists(path):
        os.remove(path)
    conn = sqlite3.connect(path)
    cols = [
        "path",
        "loaded",
        "pinned",
        "max_age_days",
        "interval_s",
        "running",
        "last_status",
        "health",
        "stale",
        "age_h",
        "dirty",
        "collected",
    ]
    conn.execute(f"create table assets ({', '.join(cols)})")
    for r in rows:
        conn.execute(
            f"insert into assets ({', '.join(cols)}) values ({', '.join('?' * len(cols))})",  # noqa: S608
            tuple(r.get(c) for c in cols),
        )
    conn.commit()
    conn.close()


def _run():
    """The scenario. Runs once, when the test (or __main__) asks, never on import:
    measured 2026-08-27, on import it cost pytest collection 81s/24s (crew#513)."""
    global fail
    with tempfile.TemporaryDirectory() as td:
        cat = os.path.join(td, "catalog-info.yaml")
        db = os.path.join(td, "estate.db")
        ASSET_PATH = "/repo/app-x"
        synth_estate_db(
            db,
            [
                {
                    "path": ASSET_PATH,
                    "loaded": 1,
                    "pinned": 0,
                    "max_age_days": 7,
                    "interval_s": 3600,
                    "running": 1,
                    "last_status": "ok",
                    "health": "green",
                    "stale": 0,
                    "age_h": 1.5,
                    "dirty": 0,
                    "collected": 1,
                }
            ],
        )

        # --- property: (dep count x metric-sample count x ceiling), >= 500 cases ---
        DEP_COUNTS = [0, 1, 2, 5, 10, 20, 50, 100, 200, 350, 500]
        SAMPLE_COUNTS = [0, 1, 2, 5, 10, 50, 200, 1000, 5000, 10000]
        # The floor payload (0 deps, 0 samples) for this shape is ~571 bytes and grows to
        # ~640 with one metric present -- desired_state/actual_state/metrics_source are
        # fixed cost dependencies alone can never truncate away, same as cp1's own floor
        # for its envelope. Every ceiling below is measured above that floor; a ceiling
        # smaller than the floor is not a truncation problem, it is an unreachable ceiling
        # (nothing left to cut), which is a different, un-owned failure mode.
        CEILINGS = (700, 1000, 2000, 8000, 50000)

        ceilings_ok = True
        accounting_ok = True
        metrics_ok = True
        total_cases = 0
        last_payload = None
        for ndeps in DEP_COUNTS:
            deps = [f"component:default/dep-{i:04d}" for i in range(ndeps)]
            synth_catalog_entity(
                cat,
                "app-x",
                "group:default/platform",
                "chidionyema/app-x",
                deps,
                ASSET_PATH,
            )
            for nsamples in SAMPLE_COUNTS:
                samples = (
                    {"latency_ms": [float(i % 997) for i in range(nsamples)]}
                    if nsamples
                    else {}
                )
                for ceiling in CEILINGS:
                    total_cases += 1
                    cfg = {
                        "catalog_path": cat,
                        "estate_db_path": db,
                        "byte_ceiling": ceiling,
                    }
                    payload = ws.build_workload_state(
                        "app-x", cfg, metric_samples=samples
                    )
                    last_payload = payload
                    size = ws._json_bytes(payload)
                    if size > ceiling:
                        ceilings_ok = False
                        print(
                            f"      ndeps={ndeps} nsamples={nsamples} ceiling={ceiling} got {size} bytes"
                        )
                    kept = len(payload["dependencies"])
                    if payload["dependencies_truncated"]:
                        if (
                            payload["dependency_count_total"] - kept
                            != payload["dependencies_omitted"]
                            or kept >= ndeps
                        ):
                            accounting_ok = False
                    elif kept != ndeps or payload["dependencies_omitted"] != 0:
                        accounting_ok = False
                    if payload["dependency_count_total"] != ndeps:
                        accounting_ok = False
                    if nsamples:
                        m = payload["metrics"].get("latency_ms")
                        if m is None or m["count"] != nsamples:
                            metrics_ok = False

        check("cp2-cases-at-least-500", total_cases >= 500, f"only {total_cases} cases")
        check(
            "cp2-byte-ceiling", ceilings_ok, "a payload exceeded its configured ceiling"
        )
        check(
            "cp2-dependency-accounting",
            accounting_ok,
            "dependency_count_total/dependencies/omitted disagree",
        )
        check(
            "cp2-metrics-aggregated",
            metrics_ok,
            "aggregated count did not match sample count",
        )

        # --- incident: no raw log line, no per-sample timeseries array, ever ---
        def has_raw_array(payload):
            for k, v in payload.items():
                if isinstance(v, list) and k != "dependencies":
                    return True
            for agg in payload["metrics"].values():
                if not isinstance(agg, dict) or set(agg) - {
                    "min",
                    "max",
                    "mean",
                    "last",
                    "count",
                }:
                    return True
                if any(isinstance(v, list) for v in agg.values()):
                    return True
            return False

        check(
            "cp2-no-raw-arrays",
            last_payload is not None and not has_raw_array(last_payload),
            "the largest generated payload (500 deps, 10000 samples) leaked a raw array",
        )

        # A payload that quotes "10,000 log lines" verbatim would fail this the same way --
        # the tool has no log field at all (get_workload_logs is CP3), so the guarantee is
        # structural, not a filter that a differently-shaped source could slip past.
        check(
            "cp2-no-log-field",
            "logs" not in last_payload and "log_lines" not in last_payload,
        )

        # --- incident: found app, desired vs actual both present, one call ---
        synth_catalog_entity(
            cat,
            "app-x",
            "group:default/platform",
            "chidionyema/app-x",
            ["component:default/dep-0001"],
            ASSET_PATH,
        )
        found = ws.build_workload_state(
            "app-x", {"catalog_path": cat, "estate_db_path": db, "byte_ceiling": 8000}
        )
        check(
            "cp2-found-catalog-fields",
            found["found"] is True
            and found["owner"] == "group:default/platform"
            and found["repo"] == "chidionyema/app-x"
            and found["dependencies"] == ["component:default/dep-0001"],
            f"got {found}",
        )
        check(
            "cp2-found-desired-actual",
            found["desired_state"].get("loaded") == 1
            and found["actual_state"].get("health") == "green"
            and found["state_error"] is None,
            f"got desired={found['desired_state']} actual={found['actual_state']}",
        )

        # --- incident, both ways: an unknown app degrades, a known one does not ---
        unknown = ws.build_workload_state(
            "app-does-not-exist",
            {"catalog_path": cat, "estate_db_path": db, "byte_ceiling": 8000},
        )
        check(
            "cp2-unknown-app-degrades",
            unknown["found"] is False
            and unknown["catalog_error"] is not None
            and unknown["dependencies"] == []
            and unknown["desired_state"] == {}
            and unknown["actual_state"] == {},
            f"got {unknown}",
        )
        check(
            "cp2-known-app-not-degraded",
            found["found"] is True and found["catalog_error"] is None,
        )


def test_cp2_workload_state():
    """pytest entry: run the checks, then their verdict (crew#325 step 2)."""
    _run()
    assert not fail, "cp2-workload-state: a check above printed FAIL"  # noqa: S101


if __name__ == "__main__":
    _run()
    print("PASS  cp2-workload-state" if not fail else "FAIL  cp2-workload-state")
    sys.exit(1 if fail else 0)
