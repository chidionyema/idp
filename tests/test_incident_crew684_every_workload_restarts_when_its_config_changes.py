"""crew#684 (2026-08-30) and idp#955 before it: a rotated Secret never reached a running pod, and
three separate hand-kept lists claimed it would.

The estate said "this workload restarts when the Secret it reads changes" in the only place that
cannot hold an invariant: a list of names a person maintains. `secret.reloader.stakater.com/reload:
"a,b,c"` on hermes-agent omitted the Langfuse Secret the day that Secret was added; the same
annotation on healthchecks and on the portal sat in namespaces Reloader was not watching, so it did
nothing at all. Each was guarded by a test in this directory that asserted the list equalled the
list -- "an assertion a developer can green by editing the expectation is not a control ... controls
have to sit outside the blast radius of the thing they guard" (founder, 2026-08-30, 4ca529a0.md).

Those per-workload assertions are deleted. This file replaces all of them, and it is deliberately
the only one: a control that names a specific service is O(n) rot, an estate-wide one is O(1)
(founder, 2026-08-30, c08d08d9.md). Nothing below names healthchecks, litellm or the portal. The
table is discovered from git, so a workload added tomorrow is graded by the same rows.

The control itself is platform/edge/require-auto-reload.yaml, a Kyverno mutation, one rung lower
than a test: it makes the annotation a property of admission rather than of whoever wrote the
manifest. This file grades that the tree and the control agree, and that the control is watched
refusing the pre-fix state on every run.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "platform" / "edge" / "require-auto-reload.yaml"
ROW = ROOT / "platform" / "reloader" / "reloader.yaml"
KUSTOMIZATION = ROOT / "platform" / "edge" / "kustomization.yaml"
BAD = ROOT / "tests" / "fixtures" / "reloader" / "hand-kept-list.bad.yaml"

AUTO = "reloader.stakater.com/auto"
REASON = "idp.platform/reload-opt-out-reason"
WORKLOAD_KINDS = {"Deployment", "StatefulSet", "DaemonSet"}


def _docs(path: Path) -> list[dict]:
    return [
        d
        for d in yaml.safe_load_all(path.read_text(encoding="utf-8"))
        if isinstance(d, dict)
    ]


def _policy_rule(name: str) -> dict:
    policy = next(d for d in _docs(POLICY) if d.get("kind") == "ClusterPolicy")
    return next(r for r in policy["spec"]["rules"] if r["name"] == name)


def excluded_namespaces() -> set[str]:
    """Read the exemption from the policy, never from a copy of it kept here.

    Two lists of the same namespaces, one in the control and one in its test, is the defect this
    file exists to end. The policy is the single writer; the table below asks it.
    """
    rule = _policy_rule("workload-reloads-on-its-own-config")
    return {
        ns
        for entry in rule["exclude"]["any"]
        for ns in (entry["resources"].get("namespaces") or [])
    }


def workloads() -> list[tuple[str, str, str, dict]]:
    """Every workload the estate ships as YAML, discovered from git.

    platform/ and clusters/ are the trees Flux applies; a fixture under tests/ is not a workload
    the cluster runs and a chart's own templates are not in git, which is why the control that
    covers those is a mutation at admission and not this table.
    """
    files = subprocess.run(
        ["git", "ls-files", "platform", "clusters"],
        capture_output=True,
        text=True,
        check=True,
        cwd=ROOT,
    ).stdout.split()
    skip = excluded_namespaces()
    found = []
    for rel in files:
        if not rel.endswith((".yaml", ".yml")):
            continue
        text = (ROOT / rel).read_text(encoding="utf-8")
        if not any(f"kind: {k}" in text for k in WORKLOAD_KINDS):
            continue
        for doc in yaml.safe_load_all(text):
            if not isinstance(doc, dict) or doc.get("kind") not in WORKLOAD_KINDS:
                continue
            meta = doc.get("metadata") or {}
            if (meta.get("namespace") or "") in skip:
                continue
            found.append(
                (rel, doc["kind"], meta.get("name", "?"), meta.get("annotations") or {})
            )
    return found


TABLE = workloads()
IDS = [f"{rel}::{kind}/{name}" for rel, kind, name, _ in TABLE]


def test_the_table_found_the_estate_and_not_an_empty_list() -> None:
    """A discovery that finds nothing passes every row below and grades nothing (LAW 28).

    The floor is emptiness, not a census. It was `>= 20` until 2026-09-05, when moving commerce
    off its own Postgres and onto the estate's one database (crew#623) deleted a StatefulSet and
    took the count to 19 -- correct work, refused by a number that goes stale every time the
    estate legitimately gains or loses a workload (LAW 38). What this row is actually for is the
    case the docstring names: a glob that matches nothing, which would pass every row below.
    """
    assert TABLE, "no workloads discovered under platform/ -- the glob found nothing"


def test_the_watcher_watches_every_namespace_and_only_workloads_that_opted_in() -> None:
    """crew#684 in one line: an annotation in an unwatched namespace is inert, and inert reads
    exactly like working. A list of watched namespaces is the same defect as a list of Secret
    names, so there is no list -- one watcher, every namespace, opt-in by annotation."""
    values = next(d for d in _docs(ROW) if d.get("kind") == "HelmRelease")["spec"][
        "values"
    ]
    reloader = values["reloader"]
    assert reloader["watchGlobally"] is True, reloader
    assert reloader["namespaces"] == [], (
        "chart 2.2.16 values.yaml: a non-empty `namespaces` is scoped mode and builds a Role per "
        "named namespace instead of the ClusterRole global mode needs"
    )
    assert reloader["autoReloadAll"] is False, (
        "watching every namespace is not rolling every workload: only the annotation opts in"
    )
    assert reloader["reloadOnCreate"] is True, (
        "a Secret that already existed when Reloader arrived emits no update (crew#506 CP4)"
    )


def test_the_control_is_a_mutation_the_cluster_applies_not_a_line_in_a_manifest() -> (
    None
):
    """A workload nobody has written yet must be correct too, which a repository test cannot do."""
    rule = _policy_rule("workload-reloads-on-its-own-config")
    patch = rule["mutate"]["patchStrategicMerge"]["metadata"]["annotations"]
    assert patch == {f"+({AUTO})": "true"}, (
        "the `+()` add-if-absent anchor is what makes an explicit opt-out survive the mutation"
    )
    assert sorted(rule["match"]["any"][0]["resources"]["kinds"]) == sorted(
        WORKLOAD_KINDS
    )
    resources = yaml.safe_load(KUSTOMIZATION.read_text(encoding="utf-8"))["resources"]
    assert "require-auto-reload.yaml" in resources, (
        "a policy in no kustomization is a policy the cluster never holds (crew#341: "
        "secrets-not-from-env-vars sat unreferenced for two days)"
    )


def test_the_control_refuses_the_state_it_was_written_for(tmp_path: Path) -> None:
    """The proof obligation, run on every gate rather than once by its author.

    Founder, 2026-08-30 (c08d08d9.md): "a control must be demonstrated failing against the pre-fix
    state before the task can close ... a control nobody has watched fail is not known to work".
    The fixture is the pre-fix healthchecks Deployment, verbatim from commit 5a151c2b.
    """
    if not shutil.which("kyverno"):
        pytest.skip(
            "BLIND: kyverno CLI not on PATH; the control was not watched refusing anything"
        )
    out = subprocess.run(
        ["kyverno", "apply", str(POLICY), "--resource", str(BAD), "--remove-color"],
        capture_output=True,
        text=True,
    ).stdout
    assert "no-hand-kept-reload-list" in out, out
    summary = [line for line in out.splitlines() if line.startswith("pass:")]
    assert summary, out
    counts = {
        k.strip(): int(v) for k, v in (kv.split(": ") for kv in summary[-1].split(","))
    }
    assert counts["fail"] == 1, out

    good = tmp_path / "fixed.yaml"
    good.write_text(
        BAD.read_text(encoding="utf-8").replace(
            'secret.reloader.stakater.com/reload: "healthchecks"',
            f'{AUTO}: "true"',
        ),
        encoding="utf-8",
    )
    out = subprocess.run(
        ["kyverno", "apply", str(POLICY), "--resource", str(good), "--remove-color"],
        capture_output=True,
        text=True,
    ).stdout
    summary = [line for line in out.splitlines() if line.startswith("pass:")]
    counts = {
        k.strip(): int(v) for k, v in (kv.split(": ") for kv in summary[-1].split(","))
    }
    assert counts["fail"] == 0, out
