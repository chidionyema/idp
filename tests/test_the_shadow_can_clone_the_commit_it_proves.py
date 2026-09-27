"""The shadow cluster must be able to clone the commit it is asked to prove.

Incident: 2026-09-27. Every PR that touched platform/ went red on shadow-verify with
source-controller's "unable to clone 'http://host.k3d.internal:9418/idp': object not found".
actions/checkout of a SHA leaves HEAD detached with no refs/heads, and a commit-only clone
(Flux's go-git) fetches refs/heads/* only -- so the commit under test was never reachable. The C git
client follows a detached HEAD, so it cannot show the defect; the go-git before/after is in the PR.

This runs the real served-tree HTTP server from bin/idp-shadow over an actions/checkout-shaped
tree, and clones it the way the GitRepository now asks: branch SHADOW_BRANCH pinned to the head.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import socket
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SHADOW = REPO / "bin" / "idp-shadow"


def load_shadow():
    loader = importlib.machinery.SourceFileLoader("idp_shadow", str(SHADOW))
    spec = importlib.util.spec_from_loader("idp_shadow", loader)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def git(*argv, cwd):
    return subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", *argv],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def checkout_shaped_tree(tmp: Path) -> tuple[Path, str]:
    """A remote with main and a PR branch, fetched the way actions/checkout does for a SHA."""
    origin = tmp / "origin"
    origin.mkdir()
    git("init", "-q", "-b", "main", cwd=origin)
    git("commit", "-q", "--allow-empty", "-m", "base", cwd=origin)
    git("checkout", "-q", "-b", "feat", cwd=origin)
    git("commit", "-q", "--allow-empty", "-m", "head under test", cwd=origin)
    head = git("rev-parse", "HEAD", cwd=origin)
    tree = tmp / "srv" / "idp"
    tree.mkdir(parents=True)
    git("init", "-q", cwd=tree)
    git("fetch", "-q", str(origin), "+refs/heads/*:refs/remotes/origin/*", cwd=tree)
    git("checkout", "-q", "--detach", head, cwd=tree)
    assert git("for-each-ref", "refs/heads", cwd=tree) == ""
    return tree, head


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def serve(shadow, base: Path, port: int) -> subprocess.Popen:
    backend = (
        subprocess.check_output(["git", "--exec-path"], text=True).strip()
        + "/git-http-backend"
    )
    p = subprocess.Popen(
        [sys.executable, "-c", shadow._HTTP_GIT_SERVER, backend, str(base), str(port)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(50):
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", port)) == 0:
                return p
        time.sleep(0.1)
    p.kill()
    raise AssertionError("served-tree server never listened")


def reachable(url: str, head: str, dest: Path, branch: str | None) -> bool:
    argv = ["git", "clone", "-q", "--no-checkout"]
    if branch:
        argv += ["--single-branch", "--branch", branch]
    r = subprocess.run([*argv, url, str(dest)], capture_output=True, text=True)
    if r.returncode != 0:
        return False
    return (
        subprocess.run(
            ["git", "-C", str(dest), "cat-file", "-e", head + "^{commit}"]
        ).returncode
        == 0
    )


def test_the_shadow_names_its_head_on_a_branch_and_clones_that_branch(
    tmp_path, monkeypatch
):
    shadow = load_shadow()
    tree, head = checkout_shaped_tree(tmp_path)
    port = free_port()
    server = serve(shadow, tree.parent, port)
    try:
        url = f"http://127.0.0.1:{port}/idp"
        monkeypatch.setattr(shadow, "REPO", str(tree))
        shadow.name_head(head)
        heads = subprocess.run(
            ["git", "ls-remote", "--heads", url], capture_output=True, text=True
        ).stdout.split()
        assert heads == [head, f"refs/heads/{shadow.SHADOW_BRANCH}"]
        assert reachable(url, head, tmp_path / "clone", shadow.SHADOW_BRANCH)
    finally:
        server.kill()


def test_the_gitrepository_is_pinned_to_the_commit_on_the_named_branch(monkeypatch):
    shadow = load_shadow()
    applied = []

    def fake_run(argv, input=None, **kw):
        applied.append(input)
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(shadow, "name_head", lambda head: None)
    monkeypatch.setattr(shadow.subprocess, "run", fake_run)
    monkeypatch.setattr(shadow, "sh", lambda *a, **k: None)
    shadow.flux_source("a" * 40)
    ref = json.loads(applied[0])["spec"]["ref"]
    assert ref == {"branch": shadow.SHADOW_BRANCH, "commit": "a" * 40}
