#!/usr/bin/env python3
"""The branch fence must survive a ref the remote refuses.

Between 2026-09-09 and 2026-09-22 `.github/workflows/branch-archive.yml` ran eight times
and deleted nothing. It was never wrong about the work -- every run printed
`archived 795 branch(es); kept 137` -- but it pushed every refspec in one `git push` with
`check=True`, so one refused ref raised and took the job down before a single branch went,
and `capture_output=True` swallowed git's reason. Seven weekly runs reported
`returned non-zero exit status 1` and no more, while 954 branches stayed.

This test builds a real remote carrying the exact mine that did it: an `archive/*` tag
already on the remote at a different sha. It fails if a refusal is ever again allowed to
cost more than its own branch.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load_fence():
    path = ROOT / "bin" / "idp-branch-archive"
    loader = importlib.machinery.SourceFileLoader("idp_branch_archive", str(path))
    spec = importlib.util.spec_from_loader("idp_branch_archive", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def run(*args: str, cwd: Path) -> str:
    return subprocess.run(
        args, cwd=cwd, capture_output=True, text=True, check=True
    ).stdout


@pytest.fixture()
def remote(tmp_path, monkeypatch):
    """A bare origin with three branches, one of which is already half-archived."""
    bare, work = tmp_path / "origin.git", tmp_path / "work"
    subprocess.run(["git", "init", "--bare", "-q", str(bare)], check=True)
    subprocess.run(["git", "init", "-q", "-b", "main", str(work)], check=True)
    run("git", "config", "user.email", "fence@test", cwd=work)
    run("git", "config", "user.name", "fence", cwd=work)
    run("git", "remote", "add", "origin", str(bare), cwd=work)
    (work / "f").write_text("1")
    run("git", "add", "f", cwd=work)
    run("git", "commit", "-qm", "one", cwd=work)
    run("git", "push", "-q", "origin", "main", cwd=work)

    shas = {}
    for name in ("alpha", "beta", "gamma"):
        run("git", "checkout", "-qb", name, "main", cwd=work)
        (work / "f").write_text(name)
        run("git", "commit", "-aqm", name, cwd=work)
        run("git", "push", "-q", "origin", name, cwd=work)
        shas[name] = run("git", "rev-parse", "HEAD", cwd=work).strip()
    run("git", "checkout", "-q", "main", cwd=work)

    # The mine. `archive/beta` exists on the remote pointing at main, not at beta's tip,
    # so pushing beta's tip to that name is a non-fast-forward the remote refuses -- the
    # shape the 2026-09-09 run left behind when it landed 33 tags and then died.
    main_sha = run("git", "rev-parse", "main", cwd=work).strip()
    run("git", "push", "-q", "origin", f"{main_sha}:refs/tags/archive/beta", cwd=work)

    monkeypatch.chdir(work)
    return work, shas


def remote_refs(work: Path, kind: str) -> list[str]:
    out = run("git", "ls-remote", f"--{kind}", "origin", cwd=work)
    return sorted(ln.split()[-1] for ln in out.splitlines() if ln.strip())


def test_a_refused_ref_is_data_not_an_exception(remote):
    """push() reports the remote's own words. A bare exit code is what hid this for weeks."""
    work, shas = remote
    fence = load_fence()
    refused = fence.push("origin", f"{shas['beta']}:refs/tags/archive/beta")
    assert refused, "the remote refused the ref and push() reported nothing"
    reason = " ".join(refused.values())
    assert "rejected" in reason.lower(), reason


def test_one_refused_ref_costs_only_its_own_branch(remote):
    """alpha and gamma must still be archived and deleted with beta's tag name taken."""
    work, shas = remote
    fence = load_fence()
    rows = [(n, shas[n], "test", f"archive/{n}") for n in ("alpha", "beta", "gamma")]
    deleted, refused = fence.apply("origin", rows)

    heads = remote_refs(work, "heads")
    tags = remote_refs(work, "tags")
    assert "refs/heads/alpha" not in heads, heads
    assert "refs/heads/gamma" not in heads, heads
    assert "refs/tags/archive/alpha" in tags, tags
    assert "refs/tags/archive/gamma" in tags, tags
    assert deleted >= 2, (deleted, refused)


def test_a_tag_already_on_the_remote_means_already_archived(remote):
    """The 33 tags the dead run landed are progress, not a trap: beta is deleted, not
    re-tagged and refused forever."""
    work, shas = remote
    fence = load_fence()
    rows = [("beta", shas["beta"], "test", "archive/beta")]
    deleted, refused = fence.apply("origin", rows)
    assert refused == {}, refused
    assert deleted == 1, deleted
    assert "refs/heads/beta" not in remote_refs(work, "heads")


def test_the_fence_never_pushes_atomically():
    """--atomic would restore the all-or-nothing failure this file exists to end."""
    source = (ROOT / "bin" / "idp-branch-archive").read_text()
    call = source.split("def push(", 1)[1].split("def ", 1)[0]
    assert '"--atomic"' not in call, (
        "--atomic makes one refused ref fail the whole batch"
    )
    assert '"--porcelain"' in call, "a refusal must come back as data"
    assert "check=True" not in call, "a rejected ref is a skip, not a death"


def test_batches_are_small_enough_to_bound_a_refusal():
    fence = load_fence()
    assert 1 <= fence.BATCH <= 25, fence.BATCH
