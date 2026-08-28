"""Incident 2026-08-28 (crew#570 CP1, oke-check run 33172282641). robusta-runner sat in
`Init:CrashLoopBackOff` across four successive pods for hours, and six Flux kustomizations
(monitoring, monitoring-rules, chaos and the rest of that chain) sat not-Ready behind it. The
kubelet had logged exactly one line of cause, and only ever under `--previous`, because a
crash-looping container is between attempts for most of any window you look in:

    cp: preserving times for '/venv-writable/.': Operation not permitted

The chain: platform/robusta/robusta.yaml sets pod `fsGroup: 1000`, so the kubelet chowns the
emptyDir to root:1000 mode 0775 -- group-writable, but the *owner* is still uid 0. The chart's
init container (robusta 0.48.0 templates/runner.yaml:79-84) runs `cp -a`, which is
`-dR --preserve=all`, so it calls utimensat() on the destination directory. utimensat with
explicit times requires the caller to be the owner or to hold CAP_FOWNER; that container is
uid 1000 with `capabilities: { drop: [ALL] }` -- our own hardening -- so it is neither. cp exits
non-zero and the init container dies.

The class of mistake, which is what this file grades: *a container this estate hardens running a
command that needs a capability the hardening dropped.* Preserving timestamps or ownership on a
copy is the common instance -- `cp -a`, `cp -p`, `tar -p`, `rsync -a` all ask the kernel for a
privilege that restricted-PSS workloads do not have. The fix is always to stop asking for the
attribute, never to add the capability back: restoring CAP_FOWNER to satisfy a copy flag trades
the estate's posture for a file mtime.

Scope note (LAW 38 -- a guard that refuses correct work is an outage): a container that explicitly
declares `runAsUser: 0` genuinely owns the files it copies, so preserving metadata is correct work
there and is allowed. Everything else under platform/ is refused.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
PLATFORM = ROOT / "platform"

CONTAINER_KEYS = ("containers", "initContainers", "ephemeralContainers")

# Each entry: (regex over the joined command, what the kernel is being asked for).
PRIVILEGED_METADATA_FLAGS = (
    (re.compile(r"\bcp\s+(?:-\w*\s+)*-\w*a"), "cp -a is -dR --preserve=all: it utimensat()s and chown()s the destination"),
    (re.compile(r"\bcp\s+(?:-\w*\s+)*-\w*p"), "cp -p preserves timestamps and ownership"),
    (re.compile(r"\bcp\b[^|;&]*--preserve(?!=mode\b)(?!=links\b)"), "cp --preserve asks for attributes a dropped capability owns"),
    (re.compile(r"\btar\s+(?:-\w*\s+)*-?\w*p"), "tar -p restores permissions and ownership from the archive"),
    (re.compile(r"\brsync\s+(?:-\w*\s+)*-\w*[aot]"), "rsync -a/-o/-t preserve ownership and times"),
)


def _yaml_docs(text: str):
    try:
        return [d for d in yaml.safe_load_all(text) if isinstance(d, (dict, list))]
    except yaml.YAMLError:
        return []


def _walk(node, containers):
    """Collect every container spec, including ones inside embedded kustomize patch strings."""
    if isinstance(node, dict):
        for key, value in node.items():
            if key in CONTAINER_KEYS and isinstance(value, list):
                for item in value:
                    if isinstance(item, dict) and "name" in item:
                        containers.append(item)
            _walk(value, containers)
    elif isinstance(node, list):
        for item in node:
            _walk(item, containers)
    elif isinstance(node, str) and "kind:" in node and "spec:" in node:
        # A Flux postRenderer patch is a whole manifest carried as a string. The robusta init
        # container this file exists for lives *only* here, so not descending would grade nothing.
        for doc in _yaml_docs(node):
            _walk(doc, containers)


def _platform_containers():
    found = []
    for path in sorted(PLATFORM.rglob("*.yaml")) + sorted(PLATFORM.rglob("*.yml")):
        containers: list = []
        for doc in _yaml_docs(path.read_text()):
            _walk(doc, containers)
        for container in containers:
            found.append((path.relative_to(ROOT), container))
    return found


def _shell(container) -> str:
    parts = list(container.get("command") or []) + list(container.get("args") or [])
    return " ".join(str(p) for p in parts)


def _runs_as_root(container) -> bool:
    return (container.get("securityContext") or {}).get("runAsUser") == 0


def test_the_platform_actually_declares_containers_to_grade() -> None:
    """Without this the whole file passes vacuously the day the walk stops finding anything."""
    containers = _platform_containers()
    assert len(containers) >= 10, f"only {len(containers)} containers found under platform/ -- the walk is broken, not the estate"


def test_the_robusta_init_container_is_in_scope() -> None:
    """The one this incident was about lives inside a postRenderer patch string, not a manifest."""
    named = [(p, c) for p, c in _platform_containers() if c.get("name") == "setup-venv"]
    assert named, "setup-venv was not found: the walk no longer descends into postRenderer patches"
    assert any(_shell(c) for _, c in named), "setup-venv was found but carries no command to grade"


@pytest.mark.parametrize("pattern,why", PRIVILEGED_METADATA_FLAGS, ids=lambda v: getattr(v, "pattern", "")[:24])
def test_no_hardened_container_asks_the_kernel_to_preserve_file_metadata(pattern, why) -> None:
    offenders = []
    for path, container in _platform_containers():
        if _runs_as_root(container):
            continue
        shell = _shell(container)
        if shell and pattern.search(shell):
            offenders.append(f"{path}: container {container.get('name')!r}: {shell.strip()[:120]}")
    assert not offenders, (
        f"{why}. A restricted-PSS container (drop: [ALL], non-root) gets EPERM and dies in a "
        f"crash-loop whose only log line is under --previous. Drop the attribute, do not add the "
        f"capability back:\n  " + "\n  ".join(offenders)
    )


def test_the_fix_did_not_quietly_add_the_capability_back() -> None:
    """The other way to make the cp succeed, and the one that costs the estate its posture."""
    offenders = []
    for path, container in _platform_containers():
        caps = ((container.get("securityContext") or {}).get("capabilities") or {})
        added = {str(c).upper().removeprefix("CAP_") for c in (caps.get("add") or [])}
        # NET_BIND_SERVICE is the single addition restricted PSS permits.
        forbidden = added - {"NET_BIND_SERVICE"}
        if forbidden:
            offenders.append(f"{path}: container {container.get('name')!r} adds {sorted(forbidden)}")
    assert not offenders, (
        "restricted PSS permits adding NET_BIND_SERVICE and nothing else:\n  " + "\n  ".join(offenders)
    )
