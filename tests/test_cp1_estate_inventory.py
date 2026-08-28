#!/usr/bin/env python3
"""cp1 estate inventory tool: property + incident tests (crew#216 CP1).

Rungs, per ~/AGENTS.md "How to test":
  property  the byte ceiling holds over many synthetic catalog sizes and ceilings
            (features/self-aware-platform/cp1_inventory_tool.feature: "summarised
            by default, under a byte ceiling").
  incident  staleness is disclosed, proved both ways (a stale fixture and a fresh
            one), and a missing STATE.md degrades instead of raising -- named for
            scenario 3, "A stale snapshot is disclosed, not hidden".
  static    scenario 2's own assertion -- the tool's source contains no subprocess
            call, no os.system, no shell=True -- run directly against the shipped
            file rather than mocked.

Run directly: python3 tests/test_cp1_estate_inventory.py (needs pyyaml; .venv/bin/python
has it). Wired into bin/idp-ci. Exit 0 pass, 1 fail.
"""
import datetime as dt
import os
import random
import re
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "mcp", "plugins"))
import estate_inventory as ei  # noqa: E402

fail = False


def check(name, cond, detail=""):
    global fail
    if cond:
        print(f"ok    {name}")
    else:
        fail = True
        print(f"FAIL  {name}  {detail}")


# --- scenario 2: the source never shells out --------------------------------
# The module's own docstring narrates the guarantee in prose ("no subprocess call, no
# os.system, no shell=True"), which would trip a naive scan of its own description. The
# leading docstring is stripped first, same shape as bin/idp-ci's hardcode_scan skipping
# comment lines, so the check is against code, not against a sentence describing the code.
SRC_PATH = os.path.join(ROOT, "mcp", "plugins", "estate_inventory.py")
with open(SRC_PATH, encoding="utf-8") as fh:
    src = fh.read()
code_only = re.sub(r'^"""(?:[^"]|"(?!""))*"""', "", src, count=1)
check("cp1-no-shellout-in-prose", code_only != src)  # the docstring really was stripped
SHELLOUT_RE = re.compile(
    r"^\s*(import subprocess\b|from subprocess\b)|subprocess\.(run|Popen|call|check_output|check_call)\(|os\.system\(|shell\s*=\s*True",
    re.M,
)
check("cp1-no-shellout", not SHELLOUT_RE.search(code_only))
# Proved both ways (LAW 38): the same pattern must fire on real shell-out code, not
# just fail to fire on prose.
check("cp1-no-shellout-guard-discriminates",
      bool(SHELLOUT_RE.search("import subprocess\nsubprocess.run(['ls'], shell=True)\n")))


def synth_catalog(n, path):
    docs = []
    for i in range(n):
        docs.append(
            "---\napiVersion: backstage.io/v1alpha1\nkind: Component\nmetadata:\n"
            f"  name: entity-{i:05d}\n  annotations:\n"
            f"    github.com/project-slug: chidionyema/repo-{i:05d}\n"
            "spec:\n  owner: group:default/platform\n"
        )
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(docs))


def synth_state_md(path, generated: dt.datetime):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(
            f"# Estate snapshot\n\n**Generated {generated.strftime('%Y-%m-%d %H:%M')} UTC** "
            "by `scripts/estate-snapshot`.\n"
        )


def _run():
    """The scenario. Runs once, when the test (or __main__) asks, never on import:
    measured 2026-08-27, on import it cost pytest collection 81s/24s (crew#513)."""
    global fail
    with tempfile.TemporaryDirectory() as td:
        cat = os.path.join(td, "catalog-info.yaml")
        st = os.path.join(td, "STATE.md")
        now = dt.datetime(2026, 8, 25, 12, 0, tzinfo=dt.timezone.utc)

        # --- property: many (entity count x ceiling) pairs, payload never exceeds ceiling ---
        synth_state_md(st, now - dt.timedelta(minutes=5))
        rng = random.Random(0)
        ceilings_ok = True
        counts_ok = True
        for n in [0, 1, 5, 50, 200, 1000, 5000]:
            synth_catalog(n, cat)
            for ceiling in (500, 2000, 8000, 50000):
                cfg = {"catalog_path": cat, "state_md_path": st,
                       "byte_ceiling": ceiling, "stale_minutes": 90}
                payload = ei.build_inventory(cfg, now=now)
                size = ei._json_bytes(payload)
                if size > ceiling:
                    ceilings_ok = False
                    print(f"      n={n} ceiling={ceiling} got {size} bytes")
                kept = len(payload["entities"])
                if payload["entities_truncated"]:
                    if payload["entity_count_total"] - kept != payload["entities_omitted"] or kept >= n:
                        counts_ok = False
                elif kept != n or payload["entities_omitted"] != 0:
                    counts_ok = False
                if payload["entity_count_total"] != n:
                    counts_ok = False
        check("cp1-byte-ceiling", ceilings_ok, "a payload exceeded its configured ceiling")
        check("cp1-entity-accounting", counts_ok, "entity_count_total/entities/omitted disagree")

        # --- incident, both ways: a stale snapshot is disclosed, a fresh one is not ---
        synth_catalog(3, cat)
        synth_state_md(st, now - dt.timedelta(minutes=200))  # 200 > default 90-minute threshold
        stale_payload = ei.build_inventory(
            {"catalog_path": cat, "state_md_path": st, "byte_ceiling": 8000, "stale_minutes": 90}, now=now)
        synth_state_md(st, now - dt.timedelta(minutes=5))
        fresh_payload = ei.build_inventory(
            {"catalog_path": cat, "state_md_path": st, "byte_ceiling": 8000, "stale_minutes": 90}, now=now)
        check("cp1-stale-disclosed", stale_payload["snapshot_stale"] is True
              and stale_payload["snapshot_age_minutes"] == 200.0
              and len(stale_payload["entities"]) == 3,
              f"got {stale_payload['snapshot_stale']} / {stale_payload['snapshot_age_minutes']}")
        check("cp1-fresh-not-stale", fresh_payload["snapshot_stale"] is False
              and fresh_payload["snapshot_age_minutes"] == 5.0,
              f"got {fresh_payload['snapshot_stale']} / {fresh_payload['snapshot_age_minutes']}")

        # --- a missing STATE.md degrades (an error field), never raises, never hides the catalog ---
        missing_payload = ei.build_inventory(
            {"catalog_path": cat, "state_md_path": os.path.join(td, "absent.md"),
             "byte_ceiling": 8000, "stale_minutes": 90}, now=now)
        check("cp1-missing-state-md-degrades", missing_payload["snapshot_error"] is not None
              and missing_payload["snapshot_stale"] is False
              and len(missing_payload["entities"]) == 3,
              f"got error={missing_payload['snapshot_error']!r}")


def test_cp1_estate_inventory():
    """pytest entry: run the checks, then their verdict (crew#325 step 2)."""
    _run()
    assert not fail, "cp1-estate-inventory: a check above printed FAIL"


if __name__ == "__main__":
    _run()
    print("PASS  cp1-estate-inventory" if not fail else "FAIL  cp1-estate-inventory")
    sys.exit(1 if fail else 0)
