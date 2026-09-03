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


def test_the_two_attempts_cannot_drift_apart():
    """One source of arguments. Two copies of a `with:` block is one copy nobody updates."""
    assert K3D_ACTION.exists(), (
        f"{K3D_ACTION} holds the cluster arguments for both attempts"
    )
    doc = yaml.safe_load(K3D_ACTION.read_text())
    inner = [s for s in doc["runs"]["steps"] if "k3d-action" in str(s.get("uses", ""))]
    assert len(inner) == 1, doc["runs"]["steps"]
    assert "--config=platform/k3d/estate.yaml" in inner[0]["with"]["args"], inner[0][
        "with"
    ]
    text = DRILL.read_text()
    assert "AbsaOSS/k3d-action" not in text, (
        "the workflow pins the upstream action directly again; the arguments now live in two "
        "places and the retry can silently create a different cluster from the first attempt"
    )
