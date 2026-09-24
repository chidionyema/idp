"""Secret headroom is published before it blocks a deploy, never discovered from a refusal.

STANDARD 6, docs/reference/policy/enterprise-operating-model.md. Incident 2026-09-18: OKE's
resource-leak webhook refused every create because the cluster held 2,650 Secrets against a
2,000 limit. Thirty Flux objects went NotReady -- Backstage, Crossplane, commerce, otto-gateway,
prospector, via-negativa among them -- and the first thing in the estate that said so was a
failed Helm upgrade. Nothing reported the count.

`bin/idp-cluster-state` now reads `secret_count` from the receipt and `secret_limit` from
`estate-defaults.yaml`, and grades four states. This suite pins all four, because the value of
the row is entirely in the distinction between them:

  over the ceiling   FAIL, naming the arithmetic and the consequence (the webhook refuses
                     every new resource) -- this is the state that cost a day
  above steady-state  warn, not FAIL: a warning the platform acts on, not an outage
  under target       ok
  zero or absent     FAIL, never clean -- 0 Secrets in a cluster this size means the READ
                     failed, not that none exist. The estate's oldest rule (LAW 28, no dead
                     instrument) applied to a count.

The block is exercised by extracting it verbatim from the script and running it against
synthetic receipts, which is why the harness lives here rather than in the rule: the script
itself fetches its receipt from Object Storage, so a full run needs an OCI session and would
make this suite unrunable on the machine that most needs it.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "bin" / "idp-cluster-state"

# The HGC section, bounded by the comment that introduces it and the secret-freshness check
# that follows it. Extracted rather than imported because the script is bash with an embedded
# Python block, not a module.
_START = "# HGC (docs/reference/policy/enterprise-operating-model.md"
_END = 'if "secret_stale_consumers" not in kv2'


def _block() -> str:
    src = SCRIPT.read_text()
    return src[src.index(_START) : src.index(_END)]


def _run(secret_count: int | None, *, limit: int | None = None) -> tuple[int, str]:
    """Run the HGC block against a synthetic receipt. Returns (rc, output)."""
    kv2: dict = {
        "ok": True,
        "secret_stale_consumers": 0,
        "cpu_used_pct": 10,
        "cpu_req_pct": 20,
        "mem_used_pct": 30,
        "mem_req_pct": 40,
    }
    # `secret_count` absent vs zero are different states and both must be gradeable.
    if secret_count is not None:
        kv2["secret_count"] = secret_count
    if limit is not None:
        kv2["secret_limit"] = limit

    prelude = f'''
import json, os, re, sys
sys.path.insert(0, "{REPO / "bin" / "lib"}")


def _yaml_default(section, key):
    # The real helper, re-stated: the script's own copy is defined above the extracted block
    # and reads estate-defaults.yaml by regex so the reader never opens a vendor dashboard.
    path = os.path.join("{REPO}", "estate-defaults.yaml")
    try:
        text = open(path, encoding="utf-8", errors="replace").read()
    except OSError:
        return None
    m = re.search(r"(?m)^[ \t]+" + re.escape(key) + r"[ \t]*:[ \t]*([0-9]+)[ \t]*$", text)
    return int(m.group(1)) if m else None


line1 = "ok nodes=3 ready=3"
kv2 = json.loads(os.environ["KV2"])
rest = json.dumps(kv2)
'''
    # NOTE: string concatenation, never %-formatting. The first version of this harness used
    # `HARNESS % (...)`, which silently consumed the `%` in the block's own f-strings and ran a
    # mangled copy -- every state reported silence and the suite looked like the code was broken.
    p = subprocess.run(
        [sys.executable, "-c", prelude + _block()],
        capture_output=True,
        text=True,
        env={**os.environ, "KV2": json.dumps(kv2)},
        timeout=60,
        check=False,
    )
    return p.returncode, p.stdout + p.stderr


def test_over_the_ceiling_fails_and_names_the_consequence():
    """The state that cost a day: 2,650 against 2,000, refusal named, the fix named."""
    rc, out = _run(2650)
    assert rc == 1, f"over the ceiling must FAIL, got rc={rc}:\n{out}"
    assert "secret-headroom" in out
    assert "2,650" in out and "2,000" in out, "the arithmetic must be visible"
    assert "132%" in out, "and the percentage, so the overshoot is legible at a glance"
    assert "resource-leak webhook" in out, "name the mechanism that refuses"
    assert "spec.maxHistory" in out, "and the fix, which is the pruning"


def test_above_steady_state_warns_but_does_not_fail():
    """A warning is not an outage. A guard that fails here would block the work that prunes."""
    rc, out = _run(1800)
    assert rc == 0, f"a warn must not be fatal, got rc={rc}:\n{out}"
    assert "warn" in out
    assert "1,800" in out and "1,500" in out


def test_under_target_is_ok():
    rc, out = _run(1200)
    assert rc == 0
    assert out.strip().startswith("ok"), out
    assert "1,200" in out and "2,000" in out


def test_a_zero_count_fails_rather_than_reporting_healthy():
    """LAW 28 applied to a count: 0 Secrets in a cluster this size means the READ failed.

    This is the failure the whole row exists to prevent -- a reader that cannot see the estate
    must say so rather than report a clean one (the same rule `drift-blind` enforces elsewhere).
    """
    rc, out = _run(0)
    assert rc == 1, f"a zero count must FAIL, got rc={rc}:\n{out}"
    assert "NOT graded" in out or "not graded" in out, (
        "and it must say the headroom was not graded, so nobody reads a zero as healthy"
    )


def test_an_absent_count_fails_and_names_standard_6():
    """A receipt written before this row existed is FAIL, never clean -- the crew#584 rule."""
    rc, out = _run(None)
    assert rc == 1, f"an absent count must FAIL, got rc={rc}:\n{out}"
    assert "secret_count" in out
    assert "standard 6" in out or "HGC" in out, (
        "name the standard so the cause is checkable"
    )


def test_the_ceiling_comes_from_the_repo():
    """HGC obligation 1: the number is in the repo, not in a vendor dashboard.

    Asserted by reading estate-defaults.yaml, so a change to the ceiling is a visible diff in a
    reviewed file rather than a console edit nobody can see.
    """
    text = (REPO / "estate-defaults.yaml").read_text()
    assert "secret_limit:" in text
    assert "secret_steady_state_max:" in text
    assert "capacity:" in text, "and it lives under a named section"
    # The specific numbers the incident justifies.
    assert "secret_limit: 2000" in text
    assert "secret_steady_state_max: 1500" in text, (
        "the steady-state target must sit below the ceiling with room for a deploy burst"
    )


def test_the_receipts_own_limit_wins_when_it_carries_one():
    """A collector that reports its own ceiling is authoritative over the file default."""
    rc, out = _run(3000, limit=4000)
    assert rc == 0, (
        f"3000/4000 is under the ceiling the receipt declares, got rc={rc}:\n{out}"
    )
    assert "4,000" in out, "the receipt's limit must be the one used"


def test_the_row_runs_before_secret_freshness():
    """Ordering: headroom is a capacity fact and must be reported even when staleness also fails.

    `secret-freshness` exits non-zero on a stale consumer, so a headroom check placed after it
    would be invisible exactly when the cluster is under pressure -- which is when it is needed.
    """
    src = SCRIPT.read_text()
    assert src.index(_START) < src.index(_END), (
        "the headroom block must precede the secret-freshness check"
    )
