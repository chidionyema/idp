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


def test_every_secret_a_workflow_reads_has_a_life_cycle_row_or_is_declared_configuration():
    rows = _rows()
    config = set(re.findall(r"`(SEED_[A-Z0-9_]+)`", POLICY[POLICY.index("## Configuration that is not a credential"):]))
    missing = sorted(n for n in _names_in_workflows() if n not in rows and n not in config)
    assert not missing, f"no life-cycle row on credential-lifecycle.md for {missing} (crew#618)"


def test_every_row_fills_expiry_rotation_and_revocation():
    for name, cells in _rows().items():
        assert len(cells) == 8, f"{name}: {len(cells)} cells, want 8"
        for col, label in ((4, "expiry"), (5, "rotation"), (6, "revocation"), (7, "audit")):
            assert len(cells[col]) >= 4, f"{name}: {label} is empty"


def test_the_pr_body_rule_exists():
    rego = (ROOT / "policy/operating_model.rego").read_text()
    assert "rule=lifecycle_row" in rego and "credential-lifecycle.md" in rego
