"""crew#639, 2026-08-31: main went red on a download, not on a defect.

`bin/idp-messaging-demo all` failed with `embedded postgres: no version found
matching 16.9.0` on main at 9f66ae52. That artefact was published and answered
200 on Maven Central in the same minute, the metadata listed 16.4.0 through
16.15.0, and the dedicated messaging-demo job had passed with identical code on
two branches minutes earlier. So the failure was a transient fetch reported as a
code failure -- a red that told every session the wrong thing and blocked every
merge behind it, because the merge guard refuses to merge onto a red main.

The class, not the instance: the embedded Postgres binaries were the only
download in ci.yml with neither a retry nor a cache. Every curl in the same
workflow already carried `--retry`. These tests hold both halves of the fix --
the fetch retries when the cache is cold, and CI keeps the cache so the warm
path never reaches the network -- and the curl rule, so the next download added
to this workflow cannot arrive bare.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CI = ROOT / ".github" / "workflows" / "ci.yml"
LOCAL_GO = ROOT / "platform" / "messaging" / "local" / "local.go"

# The jobs that actually run the demo, and so pay for the download.
DEMO_JOBS = ("messaging-demo", "bdd-suites")
CACHE_PATH = "~/.cache/idp-messaging-demo/postgres-16"


def _jobs(text: str) -> dict[str, str]:
    """ci.yml split into job name -> job body, by two-space indentation."""
    starts = [
        (m.group(1), m.start())
        for m in re.finditer(r"^  ([A-Za-z0-9_-]+):[ \t]*$", text, re.M)
    ]
    out = {}
    for i, (name, pos) in enumerate(starts):
        end = starts[i + 1][1] if i + 1 < len(starts) else len(text)
        out[name] = text[pos:end]
    return out


def test_the_postgres_start_retries_a_cold_cache_fetch():
    src = LOCAL_GO.read_text()
    assert "func startPostgres(" in src, (
        "the embedded Postgres start must go through startPostgres, which is where the "
        "retry lives. A bare pg.Start() is the shape that took main red."
    )
    assert "pgAttempts" in src and "pgBackoff" in src, (
        "the retry must be bounded and named. An unbounded retry against a down mirror "
        "is a hang, not a fix (crew#678: bounded attempts, cool-off, visible state)."
    )
    m = re.search(r"pgAttempts\s*=\s*(\d+)", src)
    assert m, "pgAttempts must be a literal the reader can see"
    attempts = int(m.group(1))
    assert 2 <= attempts <= 5, (
        f"pgAttempts is {attempts}. One attempt is the bug; more than five turns a real "
        "break into a long red instead of a fast one."
    )


def test_every_job_that_runs_the_demo_caches_the_binaries():
    jobs = _jobs(CI.read_text())
    for name in DEMO_JOBS:
        assert name in jobs, f"{name} is no longer a job in ci.yml; this guard is stale"
        assert CACHE_PATH in jobs[name], (
            f"job {name} runs the messaging demo but does not cache {CACHE_PATH}. "
            "Cold, every run downloads Postgres over the network and one bad minute at "
            "Maven Central is a red main for everybody."
        )


def test_no_download_in_ci_is_bare():
    """The class: a fetch in this workflow retries, or it is a flake waiting to fire."""
    bare = []
    for n, line in enumerate(CI.read_text().splitlines(), 1):
        s = line.strip()
        if not re.search(r"\bcurl\b", s) or s.startswith("#"):
            continue
        if "--retry" in s:
            continue
        bare.append(f"{n}: {s[:110]}")
    assert not bare, (
        "these curls reach the network with no retry; add --retry 5 --retry-all-errors "
        "--retry-delay 2 like the ones beside them:\n" + "\n".join(bare)
    )
