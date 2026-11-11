"""The installed pi extensions and the repo copy must be the same bytes.

Every pi extension this estate runs is installed in ``~/.pi/agent/extensions/``. Before this
test existed, nine of the fourteen installed extensions were in no git repository at all --
including three enforcement hooks (``00-shift-left-enforcer``, ``epistemic-firewall-hook``,
``estate-protocol-gate``). Enforcement that exists only in a home directory has no review, no
CI and no backup, and the estate cannot say what behaviour an agent on another machine runs.

``~/.estate`` looked like it tracked some of them. It does not: its only remote is a local
path into this repo's ``.git`` and ``git ls-files memory/extensions/`` returns 0. A directory
that looks versioned and is not is the failure this file catches.

Two copies of one layer is how a layer drifts (AGENTS.md section 6), so the repo copy is the
source of record and this test fails when the installed copy is edited alone.
"""

import hashlib
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
EXTENSIONS = REPO / "extensions"

TRACKED = (
    "00-shift-left-enforcer.ts",
    "epistemic-firewall-hook.ts",
    "estate-commands.ts",
    "fleetview-directives.ts",
    "read-shunt.ts",
    "active-focus-memory/index.ts",
    "estate-protocol-gate/index.ts",
    "pi-governance/index.ts",
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _installed_root() -> Path:
    return Path.home() / ".pi" / "agent" / "extensions"


@pytest.mark.parametrize("rel", TRACKED)
def test_the_extension_is_in_the_repo(rel: str) -> None:
    """A missing file here means an extension the estate runs has no source of record."""
    path = EXTENSIONS / rel
    assert path.is_file(), f"extensions/{rel} is not in the repo"
    assert path.stat().st_size > 0, f"extensions/{rel} is empty"
    body = path.read_text(errors="replace")
    assert body.strip(), f"extensions/{rel} has no content"
    # An extension is a module: it must export the entry point the runtime looks for.
    assert re.search(r"export\s+default|export\s+(async\s+)?function", body), (
        f"extensions/{rel} exports no entry point -- it would not load as an extension"
    )


@pytest.mark.parametrize("rel", TRACKED)
def test_the_installed_copy_is_the_repo_copy(rel: str) -> None:
    """Drift between the installed extension and the repo is the defect, whichever side moved."""
    repo = EXTENSIONS / rel
    installed = _installed_root() / rel
    assert repo.is_file(), f"extensions/{rel} is not in the repo"
    if not installed.exists():
        pytest.skip(f"{rel} is not installed on this machine")
    assert _sha(repo) == _sha(installed), (
        f"{rel}: the installed pi extension differs from the repo copy. "
        "Copy the repo version into ~/.pi/agent/extensions/, or land the installed change."
    )
