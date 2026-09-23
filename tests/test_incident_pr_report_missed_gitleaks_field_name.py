"""Incident, 2026-08-27 (crew#539, idp#485): `.github/workflows/vault-seed.yml` gained the line
`put k8sgpt key=<NAME>_LLM_API_KEY` (spelled with a placeholder here: the literal form fails the
gate this test guards, which it did on idp#497 itself). It names a vault FIELD, but gitleaks reads
`key=<UPPER>_API_KEY` as a generic-api-key, so the security-scan job went red on the PR and,
because CI fetched every ref, on every other open PR (idp#479, #486-#492) until idp#494 made
the scan HEAD-only. The line had passed bin/pr-report, which ran conftest and nothing else.

LAW 45: the local gate now runs the same detector over the lines a PR adds. These tests feed
bin/idp-pr-secrets the exact incident line and the fix that landed, and check pr-report and the
gate workflow both carry the step. Rung 4: the incident shape is refused, the fixed shape passes.
"""

import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "bin" / "idp-pr-secrets"

needs_gitleaks = pytest.mark.skipif(
    shutil.which("gitleaks") is None,
    reason="gitleaks not on PATH (brew install gitleaks)",
)


def _run(path: Path) -> subprocess.CompletedProcess:
    return subprocess.run([str(TOOL), str(path)], capture_output=True, text=True)


@needs_gitleaks
def test_incident_line_is_refused_before_the_pr_exists(tmp_path: Path) -> None:
    added = tmp_path / "pr-added.txt"
    # assembled, not written literally: the literal line would fail this repo's own gate (idp#497)
    incident = "+          put k8sgpt key=" + "K8SGPT_LLM_" + "API_KEY\n"
    added.write_text(incident)
    r = _run(added)
    assert r.returncode == 1, r.stdout + r.stderr
    assert r.stdout.startswith("FAIL    secrets   gitleaks found 1 leak(s)")


@needs_gitleaks
def test_fixed_field_name_passes(tmp_path: Path) -> None:
    added = tmp_path / "pr-added.txt"
    added.write_text(
        "+          put k8sgpt key=K8SGPT_KEY\n+  SEED_K8SGPT_KEY: ${{ secrets.SEED_K8SGPT_KEY }}\n"
    )
    r = _run(added)
    assert r.returncode == 0, r.stdout + r.stderr
    assert r.stdout.startswith("ok      secrets   gitleaks"), r.stdout
    assert "2 added lines" in r.stdout


def test_missing_gitleaks_is_blind_never_a_pass(tmp_path: Path) -> None:
    added = tmp_path / "pr-added.txt"
    added.write_text("+anything\n")
    # a PATH holding bash and nothing else: the tool must say BLIND, not pass, not crash
    (tmp_path / "bin").mkdir()
    (tmp_path / "bin" / "bash").symlink_to(shutil.which("bash"))
    r = subprocess.run(
        [str(TOOL), str(added)],
        capture_output=True,
        text=True,
        env={"PATH": str(tmp_path / "bin")},
    )
    assert r.returncode == 2
    assert r.stdout.startswith("BLIND   secrets   gitleaks not on PATH")


def test_pr_report_runs_the_secrets_step_and_exits_on_blind() -> None:
    src = (ROOT / "bin" / "pr-report").read_text()
    assert 'idp-pr-secrets" "$REPORTS/pr-added-scan.txt"' in src
    assert '[ "$src" -eq 2 ] && exit 2' in src
    assert "rule=no_secret_added" in src


def test_gate_workflow_installs_the_same_pinned_gitleaks() -> None:
    gate = (ROOT / ".github" / "workflows" / "operating-model-gate.yml").read_text()
    scan = (ROOT / ".github" / "actions" / "security-scan" / "action.yml").read_text()
    pin = re.search(r"gitleaks/releases/download/(v[\d.]+)/", scan).group(1)
    sha = re.search(r"([0-9a-f]{64})  \S*gitleaks\.tgz", scan).group(1)
    assert f"gitleaks/releases/download/{pin}/" in gate, (
        "gate installs a different gitleaks than security-scan"
    )
    assert sha in gate, "gate does not verify the same sha256 as security-scan"


def test_checksum_manifests_are_not_scanned_for_secrets() -> None:
    """idp#901: a go.sum `h1:` hash was read as a generic-api-key (stdin mode drops the path gitleaks'
    default allowlist keys on) and reddened the gate. The secret scan skips checksum manifests; rego
    still reads every added line from pr-added.txt."""
    src = (ROOT / "bin" / "pr-report").read_text()
    assert "pr-added-scan.txt" in src and '--rawfile a "$REPORTS/pr-added.txt"' in src
    prog = re.search(r"skip_sums='(.*)'\n", src).group(1)
    diff = "+++ b/platform/messaging/go.sum\n+github.com/x v1 h1:AAAA=\n+++ b/bin/x\n+echo kept\n"
    out = subprocess.run(
        ["awk", prog], input=diff, capture_output=True, text=True, check=True
    ).stdout
    assert out == "+echo kept\n"
