"""Incident, 2026-08-29 (crew#307): two Kyverno validate rules, both written in the previous four
days and proved only against the estate's own YAML, took the portal down for hours — one judged a
DELETE it was never meant to see, one refused the cluster's own default StorageClass. Founder:
"we make the rules and we spend hours fighting the rules instead of just doing the right thing".

The rule about rules, enforced on the PR diff against the base branch:

1. A validate rule that is NEW in this PR, or whose body changed, must carry
   `failureAction: Audit`. It runs against real traffic first.
2. Flipping a rule to Enforce is its own PR: the only change to that rule is the failureAction
   line, and a comment on that line names the audit run that was clean, e.g.
   `failureAction: Enforce   # audit: https://github.com/<org>/<repo>/actions/runs/<id>`.

Rules untouched by the PR are not judged; the 13 Enforce rules on main today stand.
"""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
POLICY_DIRS = ("platform/edge", "platform/scheduling")
AUDIT_RECEIPT = re.compile(r"#\s*audit:\s*\S+")


def _base_ref() -> str:
    base = os.environ.get("GITHUB_BASE_REF", "").strip()
    return f"origin/{base}" if base else "origin/main"


def _git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True).stdout


def _rules(text: str) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for doc in yaml.safe_load_all(text):
        if not isinstance(doc, dict) or doc.get("kind") not in ("ClusterPolicy", "Policy"):
            continue
        for rule in doc.get("spec", {}).get("rules", []):
            if "validate" in rule:
                out[f"{doc['metadata']['name']}/{rule['name']}"] = rule
    return out


def _rule_line(text: str, rule_name: str) -> str:
    """The failureAction line that belongs to `rule_name` (first one after its `- name:` line)."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if re.match(rf"\s*-\s*name:\s*{re.escape(rule_name)}\s*$", line):
            for later in lines[i + 1:]:
                if "failureAction:" in later:
                    return later
                if re.match(r"\s*-\s*name:", later):
                    break
    return ""


def _changed_policy_files() -> list[str]:
    names = _git("diff", "--name-only", f"{_base_ref()}...HEAD").split()
    return [n for n in names if n.startswith(POLICY_DIRS) and n.endswith(".yaml")]


def _judgements() -> list[tuple[str, str]]:
    """(rule, defect) for every rule this PR adds or changes that breaks the rule about rules."""
    defects = []
    for f in _changed_policy_files():
        head = (ROOT / f).read_text() if (ROOT / f).exists() else ""
        base = _git("show", f"{_base_ref()}:{f}")
        new_rules, old_rules = _rules(head), _rules(base)
        for key, rule in new_rules.items():
            action = rule["validate"].get("failureAction", "Enforce")
            old = old_rules.get(key)
            body_new = {k: v for k, v in rule.items()}
            body_new["validate"] = {k: v for k, v in rule["validate"].items() if k != "failureAction"}
            body_old = None
            if old:
                body_old = {k: v for k, v in old.items()}
                body_old["validate"] = {k: v for k, v in old["validate"].items() if k != "failureAction"}
            if old is None or body_new != body_old:
                if action != "Audit":
                    defects.append((key, "new or changed validate rule must enter as failureAction: Audit"))
                continue
            old_action = old["validate"].get("failureAction", "Enforce")
            if old_action != "Enforce" and action == "Enforce":
                line = _rule_line(head, rule["name"])
                if not AUDIT_RECEIPT.search(line):
                    defects.append((key, "flip to Enforce must name the clean audit run: "
                                         "`failureAction: Enforce   # audit: <run url>`"))
    return defects


def test_no_validate_rule_in_this_pr_arrives_as_enforce_or_flips_without_an_audit_receipt():
    defects = _judgements()
    assert not defects, "\n".join(f"{k}: {why}" for k, why in defects)


@pytest.mark.parametrize(
    "head, base, expect",
    [
        # a brand-new rule as Enforce is refused
        ("rules:\n  - name: r\n    match: {any: [{resources: {kinds: [Pod]}}]}\n    validate:\n      failureAction: Enforce\n      pattern: {a: b}\n",
         "rules: []\n", 1),
        # the same rule as Audit is fine
        ("rules:\n  - name: r\n    match: {any: [{resources: {kinds: [Pod]}}]}\n    validate:\n      failureAction: Audit\n      pattern: {a: b}\n",
         "rules: []\n", 0),
        # a flip with a receipt is fine; without one is refused
        ("rules:\n  - name: r\n    validate:\n      failureAction: Enforce   # audit: https://x/actions/runs/1\n      pattern: {a: b}\n",
         "rules:\n  - name: r\n    validate:\n      failureAction: Audit\n      pattern: {a: b}\n", 0),
        ("rules:\n  - name: r\n    validate:\n      failureAction: Enforce\n      pattern: {a: b}\n",
         "rules:\n  - name: r\n    validate:\n      failureAction: Audit\n      pattern: {a: b}\n", 1),
        # an untouched Enforce rule is not judged
        ("rules:\n  - name: r\n    validate:\n      failureAction: Enforce\n      pattern: {a: b}\n",
         "rules:\n  - name: r\n    validate:\n      failureAction: Enforce\n      pattern: {a: b}\n", 0),
    ],
)
def test_the_judge_itself(monkeypatch, tmp_path, head, base, expect):
    wrap = "apiVersion: kyverno.io/v1\nkind: ClusterPolicy\nmetadata: {name: p}\nspec:\n  "
    head_doc = wrap + head.replace("\n", "\n  ")
    base_doc = wrap + base.replace("\n", "\n  ")
    (tmp_path / "platform" / "edge").mkdir(parents=True)
    (tmp_path / "platform" / "edge" / "p.yaml").write_text(head_doc)
    import sys
    me = sys.modules[__name__]   # tests/ has no __init__.py: a dotted target patches a second copy of this module
    monkeypatch.setattr(me, "ROOT", tmp_path)
    monkeypatch.setattr(me, "_git", lambda *a: "platform/edge/p.yaml\n" if a[0] == "diff" else base_doc)
    assert len(_judgements()) == expect
