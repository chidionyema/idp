"""A patch that stamps nothing rolls nothing, and says so in no output anyone reads.

The estate's 154 NetworkPolicy objects judge a pod only if Calico wired it. Calico wins the CNI
race -- 10-calico.conflist sorts before 10-flannel.conflist in /etc/cni/net.d -- so every pod
created from now on is judged and every pod created before is not. Measured 2026-09-08: 108
running pods still on flannel against 39 on Calico, so the fences are decoration for three
quarters of the estate.

The roll is a pull request rather than a permission. Changing a pod-template annotation changes
the pod template, so Flux performs the rollout: no token, no drain, no founder tap, and reverting
the value reverts the roll. A drain was measured and refused -- two nodes, 144 running pods, a
110-pod ceiling on each, so one node's pods do not fit on the other and a third node is capacity
we are not buying.

What this grades is the built output, because the failure mode is silence. A strategic-merge patch
whose target does not exist is an error kustomize reports, but a patch that lands on the workload
and not on its pod template is not: the file reads like a roll, the build is byte-identical, and
nothing restarts. So the assertion is made against `kubectl kustomize`, at the path Kubernetes
actually compares when it decides whether a rollout is needed.
"""

import os
import subprocess

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLATFORM = os.path.join(ROOT, "platform")

# The pod-template annotation whose value is the generation of the roll.
STAMP = "idp.internal/cni-generation"

ROLLABLE = {"Deployment", "StatefulSet", "DaemonSet"}


def _kustomizations():
    """Every directory that stamps the roll, read off the files rather than a hand-kept list."""
    found = set()
    for dirpath, _, filenames in os.walk(PLATFORM):
        if "kustomization.yaml" not in filenames:
            continue
        with open(
            os.path.join(dirpath, "kustomization.yaml"), encoding="utf-8"
        ) as handle:
            if STAMP in handle.read():
                found.add(dirpath)
    return sorted(found)


def _declared(directory):
    """The (kind, name) pairs the kustomization says it is rolling."""
    with open(
        os.path.join(directory, "kustomization.yaml"), encoding="utf-8"
    ) as handle:
        doc = yaml.safe_load(handle) or {}
    declared = set()
    for entry in doc.get("patches") or []:
        body = entry.get("patch")
        if not isinstance(body, str) or STAMP not in body:
            continue
        patch = yaml.safe_load(body)
        declared.add((patch["kind"], patch["metadata"]["name"]))
    return declared


def _built(directory):
    """kind/name -> the pod-template annotations Kubernetes will be handed."""
    result = subprocess.run(
        [
            "kubectl",
            "kustomize",
            directory,
        ],  # kubectl-local-intended: a local render, no cluster
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"{directory} does not build:\n{result.stderr}"
    templates = {}
    for doc in yaml.safe_load_all(result.stdout):
        if not isinstance(doc, dict) or doc.get("kind") not in ROLLABLE:
            continue
        template = ((doc.get("spec") or {}).get("template") or {}).get("metadata") or {}
        templates[(doc["kind"], doc["metadata"]["name"])] = (
            template.get("annotations") or {}
        )
    return templates


def test_the_roll_is_declared_somewhere():
    """A rule with no subjects passes for the wrong reason."""
    directories = _kustomizations()
    assert directories, (
        f"no kustomization stamps {STAMP}; the roll is not declared anywhere"
    )


def test_every_stamped_workload_carries_the_stamp_in_the_built_output():
    """The patch has to reach spec.template.metadata.annotations, not just the workload."""
    missing = []
    for directory in _kustomizations():
        built = _built(directory)
        for kind, name in sorted(_declared(directory)):
            annotations = built.get((kind, name))
            if annotations is None:
                missing.append(f"{directory}: {kind}/{name} is not in the build at all")
            elif STAMP not in annotations:
                missing.append(
                    f"{directory}: {kind}/{name} builds without {STAMP} on its pod template, "
                    "so nothing restarts"
                )
    assert not missing, "the roll would be silent for:\n" + "\n".join(missing)


def test_the_generation_is_one_value_across_the_estate():
    """Two generations in flight means half a roll, and no way to read where it stopped."""
    values = {}
    for directory in _kustomizations():
        for (kind, name), annotations in _built(directory).items():
            if STAMP in annotations:
                values.setdefault(annotations[STAMP], []).append(
                    f"{directory}:{kind}/{name}"
                )
    assert len(values) == 1, (
        "the roll is at more than one generation, so nobody can say what has rolled: "
        + "; ".join(
            f"{value} -> {len(where)} workload(s)"
            for value, where in sorted(values.items())
        )
    )
