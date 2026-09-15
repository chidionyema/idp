"""GOV-02 (idp#3525 CP8, spec section 6): "Autonomous actions that spend money SHALL
inherit the destructive capability class: quorum + hardware signature (COST-02). No
separately invented authority."

ACCEPT, verbatim: "capability classifier maps tier-activation to destructive class."
METHOD: config review.

CP1's COST-02 already built the one activation path (sovereign/engine/paid_compute.py):
`test_provision_paid_compute_is_classified_destructive` there proves the classifier maps
`provision_paid_compute` to `destructive`, and `activate()`'s own control flow makes an
unsigned call reach `provision()` architecturally impossible. GOV-02 restates that REQ at
the governance level and adds one more thing to prove: that this is still the *only* money-
spending activation path in the tree -- "no separately invented authority" is a claim about
the rest of the codebase, not just about this one file.
"""

from __future__ import annotations

import ast
from pathlib import Path

from sovereign import config
from sovereign.engine import ops, paid_compute

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def test_tier_activation_inherits_the_destructive_capability_class() -> None:
    """GOV-02's own ACCEPT line, unit-level: the classifier maps the one tier-activation
    op this estate defines to destructive, which is what carries quorum + hardware
    signature -- the same assertion CP1's COST-02 test makes, restated at CP8 as the
    governance-level REQ that names it."""
    spec = ops.classify(paid_compute.PROVISION_ACTION)
    assert spec.classification == ops.DESTRUCTIVE
    assert spec.needs_quorum
    assert spec.needs_hardware_signature


def test_provision_paid_compute_op_name_is_declared_only_in_the_destructive_list() -> (
    None
):
    """The op must not also appear in nondestructive/engine/intake/shadow -- an op
    classified two ways is a separately invented authority for whichever caller reaches
    the more permissive class."""
    other_lists = {
        "nondestructive": config.OPS_NONDESTRUCTIVE,
        "engine": getattr(config, "OPS_ENGINE", []),
        "intake": getattr(config, "OPS_INTAKE", []),
        "shadow": getattr(config, "OPS_SHADOW", []),
    }
    for list_name, values in other_lists.items():
        assert paid_compute.PROVISION_ACTION not in {v.lower() for v in values}, (
            f"{paid_compute.PROVISION_ACTION!r} also declared {list_name!r}; "
            "an op cannot be both destructive and something more permissive"
        )


def _defines_a_second_activation_path(py_file: Path) -> list[str]:
    """Function definitions named like an activation entrypoint, outside
    paid_compute.py itself. A second `def activate_*` / `def provision_*` elsewhere is
    exactly the "separately invented authority" GOV-02 forbids -- money-spending should
    have one gate, not one a reviewer has to go looking for."""
    tree = ast.parse(py_file.read_text())
    return [
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and (node.name.startswith("activate") or node.name.startswith("provision"))
    ]


def test_no_second_activation_path_exists_outside_paid_compute() -> None:
    """GOV-02: "no separately invented authority." Money-spending activation is
    architecturally singular -- one function, sovereign/engine/paid_compute.py:activate()
    -- not a policy someone could bypass by writing a second one."""
    offenders: dict[str, list[str]] = {}
    for py_file in (REPO_ROOT / "sovereign").rglob("*.py"):
        if (
            py_file.name.startswith("test_")
            or py_file == REPO_ROOT / "sovereign/engine/paid_compute.py"
        ):
            continue
        names = _defines_a_second_activation_path(py_file)
        if names:
            offenders[str(py_file.relative_to(REPO_ROOT))] = names
    assert offenders == {}
