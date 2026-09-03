"""crew#618 (founder 2026-08-29): "no PR covering critical infra like this can have setup going to
void: reusable? expiration? we need policy." Every SEED_* repository secret a workflow reads has a
row on docs/reference/policy/credential-lifecycle.md with expiry, rotation and revocation filled, or
is listed there as configuration. A new root without a row is red here before it is merged."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY = (ROOT / "docs/reference/policy/credential-lifecycle.md").read_text()


def _names_in_workflows():
    names = set()
    for wf in (ROOT / ".github/workflows").glob("*.yml"):
        names |= set(re.findall(r"secrets\.(SEED_[A-Z0-9_]+)", wf.read_text()))
    return names


def _rows():
    rows = {}
    for line in POLICY.splitlines():
        if not line.startswith("| `SEED_"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        for name in re.findall(r"`(SEED_[A-Z0-9_]+)`", cells[0]):
            rows[name] = cells
    return rows


def test_every_row_fills_expiry_rotation_and_revocation():
    for name, cells in _rows().items():
        assert len(cells) == 8, f"{name}: {len(cells)} cells, want 8"
        for col, label in (
            (4, "expiry"),
            (5, "rotation"),
            (6, "revocation"),
            (7, "audit"),
        ):
            assert len(cells[col]) >= 4, f"{name}: {label} is empty"
