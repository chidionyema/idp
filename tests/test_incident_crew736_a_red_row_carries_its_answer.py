"""crew#736 (founder 2026-08-31 09:41Z): a red parity row that prints nothing is a ghost check.

`sa-blind-elsewhere` was red on all 17 otto-parity runs since idp#1013 and printed nothing, so a
broken command and a real kube-system leak read the same; `estate-mcp-answers` died in its own
code (KeyError) instead of naming the missing config. Every branch of every Otto row now prints
its answer, the cluster's bindings naming Otto's account are listed, and the `otto-lockdown`
playbook exists in the script and on the workflow's menu.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PB = (ROOT / "bin" / "idp-oke-break-glass").read_text(encoding="utf-8")
WF = (ROOT / ".github" / "workflows" / "oke-check.yml").read_text(encoding="utf-8")


def row(name: str) -> str:
    """The row's text up to the next row or eye (a row may span lines)."""
    m = re.search(
        rf"^  step {re.escape(name)} (.*?)(?=^  (?:step|show|show_redacted) |^}}$)",
        PB,
        re.M | re.S,
    )
    assert m, f"row {name} missing"
    return m.group(1)


def test_the_kube_system_row_prints_yes_no_or_blind():
    r = row("sa-blind-elsewhere")
    assert "2>&1" in r, "stderr was thrown away, so an error printed nothing"
    assert "kube-system secrets:" in r
    assert "no*) exit 0" in r
    assert "yes*)" in r and "LEAK" in r
    assert "BLIND" in r, (
        "an answer that is neither yes nor no must say the check is blind"
    )


def test_bindings_naming_otto_are_listed_cluster_wide():
    r = row("bindings-outside-namespace")
    assert "rolebindings,clusterrolebindings -A" in r
    assert "bindings outside" in r


def test_the_estate_rows_name_what_is_missing():
    assert "no 'estate-state:' line" in row("estate-state-read-at-start")
    assert 'c[\\"mcp_servers\\"]' not in PB, "a KeyError is not an answer"
    assert "has no mcp_servers.estate.url" in PB


def test_the_lockdown_playbook_exists_and_is_reversible():
    assert "pb_otto_lockdown()" in PB
    assert "  otto-lockdown) pb_otto_lockdown ;;" in PB
    body = PB.split("pb_otto_lockdown() {", 1)[1].split("\n}\n", 1)[0]
    assert "flux suspend kustomization" in body, "Flux would scale it back up"
    assert "--replicas=0" in body
    assert "delete clusterrolebinding" in body and "delete rolebinding" in body
    assert "own-namespace" in body, "the binding rbac.yaml ships must survive"
    opts = re.search(r"playbook:.*?options: \[(.*?)\]", WF, re.S).group(1)
    assert "otto-lockdown" in opts.split(", ")


def test_the_lockdown_has_its_undo_and_the_undo_waits_for_the_gateway():
    """LAW 16: otto-lockdown suspends the Flux row and scales to zero; otto-restore resumes the
    row and does not say done until the gateway rollout answers."""
    assert "  otto-restore) pb_otto_restore ;;" in PB
    body = re.search(r"^pb_otto_restore\(\) \{(.*?)^\}", PB, re.M | re.S).group(1)
    assert "flux resume kustomization" in body
    assert "rollout status deploy/hermes-agent-gateway" in body
    opts = re.search(r"playbook:.*?options: \[(.*?)\]", WF, re.S).group(1)
    assert "otto-restore" in opts.split(", ")
    listed = re.search(r'--list\) echo "(.*?)"', PB).group(1).split()
    assert "otto-restore" in listed and "otto-lockdown" in listed
