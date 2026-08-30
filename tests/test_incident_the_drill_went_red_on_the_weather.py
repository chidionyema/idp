"""Run 33234248201, 2026-08-29: the hydration drill reddened on a registry hiccup.

    docker failed to pull image 'ghcr.io/k3d-io/k3d-tools:5.9.0': TLS handshake timeout
    Cluster creation FAILED, all changes have been rolled back!

Eleven seconds in, no cluster, no receipt uploaded, and a required check red on a pull request
that had nothing to do with it. Its predecessor died the same way at 304s on
`k3d-estate-agent-0 failed to get ready`. Neither red says anything about whether this estate's
tree hydrates on a vanilla cluster, which is the only question crew#488's drill exists to answer.

The cost of the class is not the lost run. It is that a drill which reds on the weather teaches
every session to press re-run without reading the log, and the next session presses a real red
through the same way -- the reasoning already written into the k3s node-ready wait (crew#307).

So: every fetch this drill makes over the network gets a second chance, and a second consecutive
failure stays red and honest. These tests hold that, and they are written against the fetches
rather than against a list of run numbers, so a fetch added later is covered without an edit.
"""
import re
from pathlib import Path

import yaml

IDP = Path(__file__).resolve().parents[1]
DRILL = IDP / ".github" / "workflows" / "portability-drill.yml"
K3D_ACTION = IDP / ".github" / "actions" / "k3d-estate" / "action.yml"


def _steps() -> list[dict]:
    doc = yaml.safe_load(DRILL.read_text())
    return [s for job in doc["jobs"].values() for s in job.get("steps", []) or []]


def _run_lines() -> list[str]:
    """Every logical shell line the drill runs.

    Continuations are joined: `helm install ... \\` on one physical line and its flags on the
    next is one command, and a guard that reads the physical lines sees a command with no `||`
    and a fragment with no `helm` -- it would have to be satisfied by whichever half it happened
    to match, which is not grading anything.
    """
    out = []
    for s in _steps():
        buf = ""
        for raw in (s.get("run") or "").splitlines():
            ln = raw.strip()
            if not ln or ln.startswith("#"):
                continue
            buf += ln[:-1].rstrip() + " " if ln.endswith("\\") else ln
            if not ln.endswith("\\"):
                out.append(buf)
                buf = ""
        if buf:
            out.append(buf)
    return out


def test_the_incident_creating_the_cluster_gets_a_second_attempt():
    """The step that failed is attempted twice, and both attempts use the same arguments."""
    steps = _steps()
    uses = [s for s in steps if str(s.get("uses", "")).endswith("/k3d-estate")]
    assert len(uses) == 2, (
        "cluster creation must be attempted twice; a single attempt is what run 33234248201 "
        f"had, and it reddened on a TLS handshake: {[s.get('name') for s in steps]}"
    )
    first, second = uses
    assert first.get("continue-on-error") is True, "the first attempt must not fail the job on its own"
    assert first.get("id"), "the first attempt needs an id for the second to be gated on"
    assert f"steps.{first['id']}.outcome == 'failure'" in str(second.get("if", "")), (
        f"the second attempt must run only when the first failed, not unconditionally: {second.get('if')!r}"
    )


def test_the_two_attempts_cannot_drift_apart():
    """One source of arguments. Two copies of a `with:` block is one copy nobody updates."""
    assert K3D_ACTION.exists(), f"{K3D_ACTION} holds the cluster arguments for both attempts"
    doc = yaml.safe_load(K3D_ACTION.read_text())
    inner = [s for s in doc["runs"]["steps"] if "k3d-action" in str(s.get("uses", ""))]
    assert len(inner) == 1, doc["runs"]["steps"]
    assert "--config=platform/k3d/estate.yaml" in inner[0]["with"]["args"], inner[0]["with"]
    text = DRILL.read_text()
    assert "AbsaOSS/k3d-action" not in text, (
        "the workflow pins the upstream action directly again; the arguments now live in two "
        "places and the retry can silently create a different cluster from the first attempt"
    )


def test_every_curl_the_drill_makes_is_retried():
    bare = [ln for ln in _run_lines() if re.search(r"\bcurl\b", ln) and "--retry" not in ln]
    assert not bare, f"a curl with no --retry reds the drill on a transient: {bare}"


def test_every_image_and_chart_the_drill_pulls_is_retried():
    """helm and docker have no --retry flag, so the retry is the shell's."""
    lines = _run_lines()
    for pattern, what in ((r"helm install .*oci://", "a chart pulled from a registry"),
                          (r"^docker pull ", "an image pull")):
        hits = [ln for ln in lines if re.search(pattern, ln)]
        assert hits, f"{what}: nothing matched {pattern!r}; this guard has stopped grading"
        for ln in hits:
            assert "||" in ln or any(ln in other and "||" in other for other in lines), (
                f"{what} with no second attempt: {ln}"
            )


def test_docker_run_does_not_pull_implicitly():
    """`docker run` pulls a missing image and gives up on the first failure.

    The pull is therefore done as its own retried step. Without this the retry above can be
    added, the guard passes, and the implicit pull inside `docker run` is still the unretried
    one that fails -- a guard measuring the line next to the one that breaks.
    """
    lines = _run_lines()
    runs = [ln for ln in lines if ln.startswith("docker run ")]
    assert runs, "no `docker run` in the drill; this guard has stopped grading"
    pulled = {m.group(1) for ln in lines for m in [re.match(r"docker pull (\S+)", ln)] if m}
    for ln in runs:
        images = re.findall(r"\b((?:[\w.-]+/)*[\w.-]+:[\w.+-]+)\b", ln)
        remote = [i for i in images if "/" in i]
        for img in remote:
            assert img in pulled, f"{img} is pulled implicitly by `docker run` and never retried: {ln}"
