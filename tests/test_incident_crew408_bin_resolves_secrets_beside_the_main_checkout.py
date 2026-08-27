"""Incident crew#408, 2026-08-27: bin/idp-identity-apply run from a worktree under .claude/worktrees
looked for estate-secrets at .claude/worktrees/estate-secrets, because it resolved the vault as a
sibling of the checkout it ran from. Seven scripts carried the same default. The rule: a script
resolves estate-secrets beside the main checkout (git-common-dir), never beside $IDP. Rung 4."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SIBLING_OF_IDP = re.compile(r'\$\(dirname "\$IDP"\)/estate-secrets|\$IDP/\.\.\}?/estate-secrets')


def test_no_estate_script_resolves_secrets_beside_the_checkout_it_runs_from() -> None:
    bad = {f.name: SIBLING_OF_IDP.findall(f.read_text()) for f in sorted((ROOT / "bin").glob("idp-*"))}
    bad = {k: v for k, v in bad.items() if v}
    assert not bad, f"estate-secrets resolved beside $IDP (breaks under .claude/worktrees): {bad}"


def test_every_secrets_default_goes_through_main() -> None:
    users = [f for f in sorted((ROOT / "bin").glob("idp-*")) if "estate-secrets" in f.read_text()]
    assert users, "no script reads estate-secrets; the rule has nothing to guard"
    for f in users:
        s = f.read_text()
        if "ESTATE_SECRETS" in s:
            assert 'MAIN=$(dirname "$(git -C "$IDP" rev-parse --path-format=absolute --git-common-dir)")' in s, f.name
            assert "$MAIN" in s.split("MAIN=$(dirname", 1)[1], f.name


def test_main_resolves_to_the_main_checkout_from_a_worktree() -> None:
    # the expression itself, evaluated where this test runs: git-common-dir of a worktree is <main>/.git
    out = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "--path-format=absolute", "--git-common-dir"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    main = Path(out).parent
    assert (main / "bin").is_dir() and ".claude/worktrees" not in str(main), main
