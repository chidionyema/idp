"""The three Backstage layers are separate things and must stay separate.

Founder, 2026-11-12: "need to soearate it fomr what isnt used".

Three different things were being called "Backstage" and conflated into one decision. Each has a
different caller, a different cost, and a different verdict:

  1. THE DOWNLOAD  -- a node_modules tree with no importer. 2.4 GB, no caller. DELETED, REFUSED.
  2. THE SOURCE    -- 505 tracked files, 2 MB, imported 181 times by the estate app. Has a caller
                      (Genesis workers, the /fleet surface). KEPT.
  3. THE BUILD     -- packages/app/dist + node_modules. Untracked, git-ignored, rebuilt by the
     OUTPUT           Dockerfile. 214 MB. DELETED; `yarn install && yarn build:all` restores it.

This test fails if a future change lets any two of those collapse again -- by tracking a build
artifact, by deleting the source, or by un-refusing the download.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BACKSTAGE = REPO / "backstage"
APP = BACKSTAGE / "packages" / "app"


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=BACKSTAGE, capture_output=True, text=True, check=True
    ).stdout


# --- layer 2: the source has a caller, so it stays -------------------------------------------


def test_the_estate_app_source_is_present() -> None:
    """The 218 tracked source files that mount the estate modules into the app."""
    tracked = _git("ls-files", "packages/app/src").splitlines()
    assert len(tracked) > 100, f"app source shrank to {len(tracked)} files"
    assert (APP / "src" / "App.tsx").is_file()


def test_genesis_backend_is_present_because_genesis_lives_inside_it() -> None:
    """PR #7987 (Genesis) touches only paths under this directory.

    Deleting it would delete the Genesis platform, which is why "purge backstage/"
    cannot be done on the reasoning that installed the 2.4 GB download.
    """
    fleetview = BACKSTAGE / "plugins" / "fleetview-backend"
    assert fleetview.is_dir(), "Genesis (fleetview-backend) is gone"
    assert (fleetview / "src" / "fleetview_backend" / "routes.py").is_file()


def test_the_app_really_imports_the_backstage_framework() -> None:
    """The correction this file exists to keep: it IS a Backstage app.

    The root package.json carries only 4 @backstage/* entries; the per-package
    manifests carry 32 each, and the source imports them well over a hundred times.
    A future reader who checks only the root will conclude "not really backstage"
    and reach for the delete key.
    """
    for manifest in (APP / "package.json", BACKSTAGE / "packages/backend/package.json"):
        assert manifest.is_file(), f"{manifest} is missing"
        declared = re.findall(r'"(@backstage/[a-z0-9-]+)"', manifest.read_text())
        assert len(set(declared)) >= 20, (
            f"{manifest.relative_to(REPO)} declares only {len(set(declared))} @backstage/* "
            "dependencies -- this no longer looks like a real Backstage app, so the "
            "reason for keeping the framework needs re-measuring"
        )

    imported = set()
    for path in APP.glob("src/**/*.ts*"):
        imported.update(re.findall(r"@backstage/[a-z0-9-]+", path.read_text(errors="ignore")))
    assert len(imported) >= 8, f"app source imports only {len(imported)} @backstage packages"


# --- layer 3: build output is not source -----------------------------------------------------


def test_the_build_output_is_not_tracked() -> None:
    """dist/ and node_modules/ are derived; a commit of either is the regression."""
    for rel in ("packages/app/dist", "packages/app/node_modules", "node_modules"):
        tracked = _git("ls-files", rel).strip()
        assert tracked == "", f"{rel} is tracked ({len(tracked.splitlines())} files): build output"


def test_the_build_output_is_git_ignored_so_it_cannot_be_committed_by_accident() -> None:
    for rel in ("packages/app/dist", "packages/app/node_modules"):
        proc = subprocess.run(
            ["git", "check-ignore", "-q", rel], cwd=BACKSTAGE, capture_output=True
        )
        assert proc.returncode == 0, f"{rel} is not git-ignored, so a stray `git add -A` tracks it"


def test_the_dockerfile_still_rebuilds_what_was_deleted() -> None:
    """Proves the 214 MB we deleted is genuinely derived, not a hand-made artifact.

    If `yarn build:all` ever stops producing packages/app/dist, deleting it locally
    would have removed something the image needed and could not regenerate.
    """
    dockerfile = (BACKSTAGE / "Dockerfile").read_text()
    assert "yarn build:all" in dockerfile, (
        "the Dockerfile no longer runs `yarn build:all`; the deleted dist/ would not be rebuilt"
    )


# --- layer 1: the download stays refused -----------------------------------------------------


def test_a_backstage_install_is_still_refused() -> None:
    """The one gate that closes the founder's request: it never comes back."""
    door = REPO / "bin" / "backstage-refused"
    assert door.is_file(), "the refusal door is gone"
    for argv in (
        ["install", "backstage"],
        ["yarn", "add", "@backstage/cli"],
        ["git", "clone", "https://github.com/backstage/backstage"],
    ):
        proc = subprocess.run([str(door), *argv], capture_output=True, text=True)
        assert proc.returncode == 1, f"{argv} was allowed through the door"


# --- the record ------------------------------------------------------------------------------


def test_the_addendum_records_the_correction_instead_of_hiding_it() -> None:
    """A record that deletes its own errors teaches nobody."""
    record = (REPO / "docs/decisions/2026-11-12-backstage-source-is-not-a-download.md").read_text()
    assert "Correction, same day" in record
    assert "181" in record, "the import count that proves it IS a Backstage app"
    assert "214 MB" in record, "the reclaimed derived-artifact figure"
    assert "4,361 MB" in record, "the measured free space after the deletion"
