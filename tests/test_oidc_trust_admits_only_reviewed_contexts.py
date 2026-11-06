"""The estate's cloud identity is reachable only from reviewed contexts, never from a lane.

2026-11-06: the identity domain's trust admitted `sub eq <repo prefix>*` -- every job of this
repository on every ref. Lane branches forked before #7743 still carry a push-triggered
greenlane.yml, and GitHub runs a push from the PUSHED branch's YAML: 50 greenlane runs on lane/*
pushes in one hour that day, each able to mint the estate App's token. The declared contexts live
in platform/github/oidc-trust.json; this suite proves the list is complete for every workflow that
exchanges a token, that no lane or queue ref can ever be in it, and that the App token refuses to
mint outside it before the vault is read.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
SPEC = json.loads((ROOT / "platform/github/oidc-trust.json").read_text())
DECLARED = {c["context"] for c in SPEC["contexts"]}
TRUST = ROOT / "bin/idp-oidc-trust"
EXCHANGE = re.compile(r"oci-token-exchange-action|\./\.github/actions/github-app-token")


def _contexts(path: Path) -> set[str]:
    """The `sub` contexts a workflow's triggers produce (GitHub OIDC reference)."""
    on = yaml.safe_load(path.read_text()).get(True) or {}
    if isinstance(on, str):
        on = {on: None}
    elif isinstance(on, list):
        on = {k: None for k in on}
    out = set()
    for event, cfg in on.items():
        if event in ("pull_request", "pull_request_target"):
            out.add("pull_request")
        elif event == "push":
            branches = (cfg or {}).get("branches") if isinstance(cfg, dict) else None
            for b in branches or ["<any branch>"]:
                out.add(f"ref:refs/heads/{b}")
        elif event == "workflow_call":
            continue  # its callers' contexts are counted where they are declared
        else:
            # schedule, workflow_dispatch, workflow_run, check_run, issue_comment,
            # repository_dispatch: the default branch's definition runs
            out.add("ref:refs/heads/main")
    return out


def _exchangers() -> dict[str, set[str]]:
    found = {}
    for p in sorted((ROOT / ".github/workflows").glob("*.yml")):
        if EXCHANGE.search(p.read_text()):
            found[p.name] = _contexts(p)
    return found


def test_every_workflow_that_exchanges_a_token_runs_only_in_declared_contexts():
    found = _exchangers()
    assert len(found) >= 20, f"the scan found {len(found)} workflows; it is not reading them"
    missing = {w: sorted(c - DECLARED) for w, c in found.items() if c - DECLARED}
    assert not missing, (
        "these workflows trade a token in a context the trust will refuse; declare the context "
        f"in platform/github/oidc-trust.json with its reason, or move the trigger: {missing}"
    )


def test_no_lane_or_queue_ref_can_ever_be_declared():
    assert set(SPEC["never"]) >= {"ref:refs/heads/lane/", "ref:refs/heads/queue/"}
    for c in DECLARED:
        assert not any(c.startswith(n) for n in SPEC["never"]), c
        assert "*" not in c, f"a wildcard is how the trust admitted every ref: {c}"


def _allowed(event: str, ref: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "GITHUB_EVENT_NAME": event, "GITHUB_REF": ref}
    return subprocess.run(
        [str(TRUST), "allowed"], capture_output=True, text=True, env=env
    )


@pytest.mark.parametrize(
    "event,ref,rc",
    [
        ("schedule", "refs/heads/main", 0),
        ("workflow_run", "refs/heads/main", 0),
        ("pull_request", "refs/pull/7/merge", 0),
        ("pull_request_target", "refs/heads/main", 0),
        ("push", "refs/heads/flux/image-updates", 0),
        ("push", "refs/heads/lane/stale-before-7743", 3),
        ("push", "refs/heads/queue/b4782", 3),
        ("workflow_dispatch", "refs/heads/lane/x", 3),
        ("workflow_dispatch", "refs/heads/probe/anything", 3),
    ],
)
def test_the_context_decision(event, ref, rc):
    p = _allowed(event, ref)
    assert p.returncode == rc, p.stdout + p.stderr


def test_the_rules_are_one_exact_rule_per_context_never_a_wildcard():
    p = subprocess.run(
        [str(TRUST), "rules", "repo:o@1/idp@2:"], capture_output=True, text=True
    )
    rules = json.loads(p.stdout)
    assert rules == [f"sub eq repo:o@1/idp@2:{c['context']}" for c in SPEC["contexts"]]
    assert not any(r.endswith("*") for r in rules)


def test_the_app_token_refuses_a_lane_before_it_reads_the_vault():
    env = {
        **os.environ,
        "GITHUB_ACTIONS": "true",
        "GITHUB_EVENT_NAME": "push",
        "GITHUB_REF": "refs/heads/lane/stale",
        "PATH": "/usr/bin:/bin",  # no oci, no sops: any vault read would fail differently
    }
    p = subprocess.run(
        [str(ROOT / "bin/idp-github-app"), "token", "platform-engineer"],
        capture_output=True,
        text=True,
        env=env,
    )
    assert p.returncode == 3, p.stdout + p.stderr
    assert "REFUSED oidc-trust" in p.stderr
    assert p.stdout == "", "nothing that could be taken for a token reaches stdout"


def test_the_bootstrap_has_no_wildcard_rule_left():
    text = (ROOT / "bin/idp-oci-bootstrap").read_text()
    assert 'sub eq ${SUB_PREFIX}*"' not in text
    assert text.count("bin/idp-oidc-trust\" rules") == 2


def test_apply_proves_main_still_exchanges_and_restores_the_old_rules_if_not():
    text = TRUST.read_text()
    body = text[text.index("apply() {") : text.index("exchange_code() {")]
    assert "exchange_code" in body and "previous rules restored" in body
    assert body.index("PATCH") < body.index("exchange_code") < body.index("restored")
    wf = (ROOT / ".github/workflows/oidc-trust.yml").read_text()
    assert "OIDC_CLIENT_IDENTIFIER: ${{ secrets.OIDC_CLIENT_IDENTIFIER }}" in wf
