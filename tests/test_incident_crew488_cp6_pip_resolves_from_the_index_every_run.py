"""crew#488 CP6: every CI job that pip-installs restores a wheel cache, or is named here with why.

Measured on origin/main b426a4d before this change: 7 workflows installed `oci-cli` at 14 sites and
not one of them cached a wheel, so every run downloaded the same ~40 MB of wheels again. The eight
oke-check jobs of run 33217075374 spent 33/38/38/43/35/33/35/39 s on it, verify-drill 33215196600
36 s, trace-drill 33215194366 39 s, vault-seed 33122872248 39 s, login-drill 33217988021 71 s,
conscience 33204945289 4 s + 40 s, estate-escrow 33208893050 46 s -- 569 s of runner time per sweep
spent re-downloading what the previous run already had.

The rule this guards is not "oci-cli is cached". It is the class: a job that runs `pip install` and
sets python up with actions/setup-python must pass `cache: pip` with a `cache-dependency-path` that
matches at least one file, because a key that hashes nothing restores nothing and reads green.

Rung 4, incident test.
"""
import glob
import os
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"

# A job may install without setup-python only with a reason, and the reason is graded by a human
# reading this line, never by the absence of an entry. A new uncached job fails the test.
NO_SETUP_PYTHON = {
    "operating-model-gate.yml::operating-model-gate":
        "A reusable workflow: it checks the CALLER repo out to `.` and idp to `.idp`, so any "
        "cache-dependency-path it names resolves inside whichever repo called it (hermes-v2, crew, "
        "idp) and matches no file in two of the three. One `pip install -q pyyaml` on the runner's "
        "preinstalled python costs less than a setup-python step, and a key that matches nothing "
        "would be a cache that never hits while reading as though it did.",
}


def _jobs():
    for path in sorted(WORKFLOWS.glob("*.y*ml")):
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(doc, dict):
            continue
        for name, job in (doc.get("jobs") or {}).items():
            steps = [s for s in (job.get("steps") or []) if isinstance(s, dict)]
            yield path, name, steps


def _installs(steps):
    return [s for s in steps if "pip install" in str(s.get("run") or "")]


def _setups(steps):
    return [s for s in steps if "actions/setup-python@" in str(s.get("uses") or "")]


def test_a_job_that_pip_installs_restores_a_wheel_cache():
    uncached = []
    for path, name, steps in _jobs():
        if not _installs(steps):
            continue
        setups = _setups(steps)
        if not setups:
            key = "%s::%s" % (path.name, name)
            assert key in NO_SETUP_PYTHON, (
                "%s runs pip install with no actions/setup-python step, so no wheel cache can be "
                "restored. Give it one with cache: pip, or name it in NO_SETUP_PYTHON with the "
                "reason it cannot have one." % key)
            continue
        for step in setups:
            if (step.get("with") or {}).get("cache") != "pip":
                uncached.append("%s::%s -> %s" % (path.name, name, step.get("name") or step["uses"]))
    assert uncached == [], (
        "these setup-python steps precede a pip install and set no wheel cache; every run "
        "re-downloads what the last one had: %s" % uncached)


@pytest.mark.parametrize("path", sorted(WORKFLOWS.glob("*.y*ml")), ids=lambda p: p.name)
def test_every_cache_key_hashes_at_least_one_file_that_exists(path):
    """A cache-dependency-path matching nothing is silent green: setup-python warns and moves on,
    the cache never hits, and the workflow looks cached to anyone reading the yaml."""
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        pytest.skip("not a workflow")
    for name, job in (doc.get("jobs") or {}).items():
        steps = [s for s in (job.get("steps") or []) if isinstance(s, dict)]
        # The key is hashed from the workspace, not the repo: a job that checks this repo out
        # under `path: idp` writes `idp/.github/...` (catalog-render run 33224632189, 2026-08-29).
        checkout = [s for s in steps if str(s.get("uses", "")).startswith("actions/checkout")
                    and "repository" not in (s.get("with") or {})]
        prefix = ((checkout[0].get("with") or {}).get("path") or "") if checkout else ""
        for step in steps:
            if (step.get("with") or {}).get("cache") != "pip":
                continue
            dep = (step.get("with") or {}).get("cache-dependency-path")
            assert dep, "%s::%s caches pip and names no cache-dependency-path" % (path.name, name)
            for pattern in str(dep).split():
                if prefix:
                    assert pattern.startswith(prefix + "/"), (
                        "%s::%s hashes %r but its checkout lives under %s/: the key would hash "
                        "nothing" % (path.name, name, pattern, prefix))
                    pattern = pattern[len(prefix) + 1:]
                assert glob.glob(os.path.join(str(ROOT), pattern)), (
                    "%s::%s hashes %r, which matches no file in the repository: the key would be "
                    "constant and the cache would never hold what the job installs"
                    % (path.name, name, pattern))


def _requires(req: Path):
    """The other requirements files `req` pulls in with `-r`, resolved as pip resolves them:
    relative to the file that names them."""
    out = []
    for line in req.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line.startswith("-r "):
            out.append((req.parent / line[3:].strip()).resolve())
    return out


def test_a_key_hashes_every_requirements_file_its_install_actually_reads():
    """The transitive half of the rule above, and it bit this very branch.

    `.github/requirements/conscience.txt` and `login-drill.txt` each begin `-r oci-cli.txt`, so the
    wheels those jobs install change when oci-cli.txt changes. Both first shipped hashing only
    their own file: the key would have stayed constant while the install moved, restoring a stale
    cache and reading exactly like a key that tracked it. That is the same silent-green shape this
    file exists to refuse, so it is asserted rather than remembered."""
    missing = []
    for path, name, steps in _jobs():
        for step in _setups(steps):
            with_ = step.get("with") or {}
            if with_.get("cache") != "pip":
                continue
            hashed = {(ROOT / pattern).resolve()
                      for pattern in str(with_.get("cache-dependency-path") or "").split()}
            for req in list(hashed):
                if not req.is_file():
                    continue
                for pulled in _requires(req):
                    if pulled not in hashed:
                        missing.append("%s::%s hashes %s but not %s, which %s pulls in with -r"
                                       % (path.name, name, req.name, pulled.name, req.name))
    assert missing == [], (
        "these keys hash a requirements file but not everything it reads, so the cache goes stale "
        "without the key changing: %s" % missing)
