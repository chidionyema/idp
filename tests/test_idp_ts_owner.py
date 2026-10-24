"""The commit hook's typecheck asks the project about its own files, and says what it skipped.

Measured 2026-10-23: three `git commit` calls touching extensions/estate-capabilities/index.ts were
SIGTERMed at the executor door's 100s ceiling, each throwing its staged work away, because the hook
started `bin/idp-backstage-tsc` -- a whole-workspace `tsc --noEmit` -- for any staged .ts file.
backstage/tsconfig.json includes only `packages/*` and `plugins/*` under backstage/, so the
typecheck could not see the file it was started for, and does not finish inside the door's ceiling.

bin/idp-ts-owner is the selection, kept out of the hook's control flow so it can be graded here
without a node_modules, a worktree or a git index.
"""

from __future__ import annotations

import pathlib
import subprocess

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "bin" / "idp-ts-owner"


def _owner(*paths: str) -> list[str]:
    out = subprocess.run(
        [str(SCRIPT), *paths], capture_output=True, text=True, check=True, timeout=20
    )
    return [ln for ln in out.stdout.splitlines() if ln]


def _owner_stdin(paths: list[str]) -> list[str]:
    out = subprocess.run(
        [str(SCRIPT)],
        input="\n".join(paths) + "\n",
        capture_output=True,
        text=True,
        check=True,
        timeout=20,
    )
    return [ln for ln in out.stdout.splitlines() if ln]


def test_backstage_packages_and_plugins_are_owned():
    paths = [
        "backstage/packages/app/src/App.tsx",
        "backstage/plugins/catalog-backend-module-estate-projection/src/index.ts",
    ]
    assert _owner(*paths) == paths


def test_a_pi_extension_is_not_the_backstage_project_s_file():
    """The exact file whose commit could not be made through the door."""
    assert _owner("extensions/estate-capabilities/index.ts") == []


def test_a_mixed_stage_keeps_only_the_project_s_own_files():
    staged = [
        "extensions/estate-capabilities/index.ts",
        "backstage/plugins/fleetview-backend/src/plugin.ts",
        "bin/idp-ts-owner",
        "docs/x.md",
    ]
    assert _owner_stdin(staged) == ["backstage/plugins/fleetview-backend/src/plugin.ts"]


def test_nothing_staged_is_not_an_error():
    assert _owner_stdin([]) == []


def test_the_hook_uses_the_owner_check():
    """The hook must route its typecheck decision through this door, not re-derive it inline."""
    hook = (SCRIPT.parents[1] / ".githooks" / "pre-commit").read_text()
    assert "bin/idp-ts-owner" in hook
    assert 'if [ -n "$staged_ts_owned" ]' in hook
