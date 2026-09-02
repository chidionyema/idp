"""2026-09-02, the run 33618879684 follow-up. With namespace labels finally reaching the offline
judge, every latent verdict surfaced -- and 30+ of them were misses of ONE Audit rule
(require-priority-class/platform-workload-names-a-class), which admission logs as a PolicyReport
row and ADMITS. The judge called them FAIL, which would have turned most estate PRs red for a
thing the cluster permits: run 33618879684 mirrored, red-where-admission-is-green instead of
green-where-admission-is-red.

The vendor fact underneath (measured, kyverno CLI v1.19.0): `kyverno apply --audit-warn` decides
at POLICY granularity. A policy that mixes Enforce and Audit rules counts a failing Audit rule as
`fail`; the same rule alone in its own policy counts `warn`. Admission decides per RULE. So
bin/lib/kyverno_policy_set.py splits every mixed policy before the CLI sees it: the enforce half
keeps the original name (PolicyExceptions written for Enforce rules keep matching), the audit
half gets `-audit-rules`.

The same pass dedupes by name, last copy wins: bin/idp-kyverno-render appended the 11 estate
policies twice (bin/idp-kyverno-own-policies from raw files, then the clusters/oke renders with
no cross-check), and every estate-policy verdict printed doubled.
"""

import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bin" / "lib"))
from kyverno_policy_set import shape, split_policy  # noqa: E402

RENDER = (ROOT / "bin" / "idp-kyverno-render").read_text()


def _policy(name, rules):
    return {
        "apiVersion": "kyverno.io/v1",
        "kind": "ClusterPolicy",
        "metadata": {"name": name},
        "spec": {"rules": rules},
    }


def _rule(name, action, kind="Deployment"):
    return {
        "name": name,
        "match": {"any": [{"resources": {"kinds": [kind]}}]},
        "validate": {
            "failureAction": action,
            "message": "needs a label",
            "pattern": {"metadata": {"labels": {"x": "?*"}}},
        },
    }


MIXED = _policy(
    "exp-mixed",
    [
        _rule("unrelated-enforce", "Enforce", kind="StatefulSet"),
        _rule("needs-label", "Audit"),
    ],
)

RESOURCE = textwrap.dedent("""\
    apiVersion: apps/v1
    kind: Deployment
    metadata: {name: d, namespace: default}
    spec:
      selector: {matchLabels: {a: b}}
      template:
        metadata: {labels: {a: b}}
        spec: {containers: [{name: c, image: docker.io/library/busybox:1}]}
""")

needs_cli = pytest.mark.skipif(
    shutil.which("kyverno") is None,
    reason="kyverno CLI not installed; ci.yml installs it before bin/idp-ci",
)


def _apply(tmp_path, policies):
    pol = tmp_path / "pol.yaml"
    pol.write_text(yaml.safe_dump_all(policies))
    res = tmp_path / "res.yaml"
    res.write_text(RESOURCE)
    out = subprocess.run(
        ["kyverno", "apply", str(pol), "--resource", str(res), "--audit-warn"],
        capture_output=True,
        text=True,
    ).stdout
    return [line for line in out.splitlines() if line.startswith("pass:")][-1]


@needs_cli
def test_the_vendor_fact_a_mixed_policy_counts_an_audit_miss_as_fail(tmp_path):
    """The measurement the split exists for. If a kyverno upgrade makes this pass per-rule,
    this test goes red and the split can retire -- which is the point."""
    assert "fail: 1, warn: 0" in _apply(tmp_path, [MIXED])


@needs_cli
def test_the_split_set_counts_the_same_miss_as_warn(tmp_path):
    """The other angle (LAW 15): the shaped set reads the miss the way admission acts on it."""
    assert "fail: 0, warn: 1" in _apply(tmp_path, shape([MIXED]))


def test_the_enforce_half_keeps_the_name_exceptions_match():
    halves = split_policy(MIXED)
    assert [p["metadata"]["name"] for p in halves] == [
        "exp-mixed",
        "exp-mixed-audit-rules",
    ]
    assert [r["name"] for r in halves[0]["spec"]["rules"]] == ["unrelated-enforce"]
    assert [r["name"] for r in halves[1]["spec"]["rules"]] == ["needs-label"]


def test_a_single_mode_policy_is_left_alone():
    for action in ("Enforce", "Audit"):
        pure = _policy("pure", [_rule("r1", action), _rule("r2", action)])
        assert split_policy(pure) == [pure]


def test_duplicate_policies_dedupe_and_the_last_copy_wins():
    """The clusters/oke render is appended after the raw file and is the bytes Flux applies."""
    raw = _policy("twice", [_rule("r", "Enforce")])
    rendered = _policy("twice", [_rule("r", "Audit")])
    shaped = [d for d in shape([raw, rendered]) if d["metadata"]["name"] == "twice"]
    assert len(shaped) == 1
    assert shaped[0]["spec"]["rules"][0]["validate"]["failureAction"] == "Audit"


def test_the_render_script_shapes_the_set_before_judging():
    assert 'kyverno_policy_set.py" "$S/policies.yaml"' in RENDER
    assert "--audit-warn" in RENDER
