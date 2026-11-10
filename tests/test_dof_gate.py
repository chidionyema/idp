"""bin/dof-gate: while a critical service is down, only its repair may land. Each test can fail."""

import importlib.machinery
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_loader = importlib.machinery.SourceFileLoader(
    "dof_gate", str(ROOT / "bin" / "dof-gate")
)
_spec = importlib.util.spec_from_loader("dof_gate", _loader)
gate = importlib.util.module_from_spec(_spec)
_loader.exec_module(gate)

REGISTRY = json.loads((ROOT / "catalog" / "dof-registry.json").read_text())
ROUTER_DOWN = [{"id": "llm-router", "issue": 7332}]


def test_no_incident_admits_anything():
    assert gate.evaluate(REGISTRY, [], "feat: x", ["README.md"])["admitted"]


def test_unrelated_low_effect_work_keeps_an_authorised_path_during_outage():
    """Explicit safe docs/tests can progress, but unknown source effects cannot."""
    d = gate.evaluate(
        REGISTRY,
        ROUTER_DOWN,
        "docs: no runtime effect",
        ["docs/specs/instruction-flow.md", "tests/test_accounting.py"],
    )
    assert d["admitted"], f"safe work has no admissible path: {d.get('reason')}"


def test_unclassified_source_cannot_claim_runtime_independence_from_its_path():
    d = gate.evaluate(REGISTRY, ROUTER_DOWN, "feat: unknown effects", ["web/app.tsx"])
    assert not d["admitted"], "arbitrary source has no proven low-effect contract"


def test_a_resolving_commit_inside_scope_is_admitted():
    assert gate.evaluate(
        REGISTRY,
        ROUTER_DOWN,
        "fix\n\nGenesis-Resolves: llm-router",
        ["clusters/oke/pool.yaml"],
    )["admitted"]


def test_a_resolving_commit_that_strays_is_refused():
    d = gate.evaluate(
        REGISTRY,
        ROUTER_DOWN,
        "fix\n\nGenesis-Resolves: llm-router",
        ["clusters/a.yaml", "web/app.tsx"],
    )
    assert not d["admitted"] and d["files"] == ["web/app.tsx"]


def test_claiming_a_service_that_is_not_down_is_refused():
    assert not gate.evaluate(
        REGISTRY, ROUTER_DOWN, "Genesis-Resolves: otto", ["clusters/a.yaml"]
    )["admitted"]


def test_the_gate_cannot_unlock_itself():
    d = gate.evaluate(
        REGISTRY, ROUTER_DOWN, "Genesis-Resolves: llm-router", ["bin/dof-gate"]
    )
    assert not d["admitted"]


def test_blind_inventory_cannot_mint_self_repair_authority_from_trailers():
    blind = [{"id": "dof-probe", "issue": None}]
    for paths in (
        ["README.md"],
        ["docs/specs/safe.md"],
        ["bin/dof-gate"],
        ["catalog/dof-registry.json"],
        ["tests/test_dof_gate.py"],
        [".github/workflows/ci.yml"],
    ):
        for message in ("feat: x", "Genesis-Resolves: dof-probe"):
            result = gate.evaluate(REGISTRY, blind, message, paths)
            assert not result["admitted"], (message, paths, result)
            assert result["required_trailer"] is None
            assert result["unblocker"]["kind"] == "authenticated-recovery"


def test_mixed_safe_and_unsafe_commit_must_not_use_truthy_partial_safe_list():
    for unsafe in (
        ".github/workflows/ci.yml",
        "web/app.tsx",
        "bin/dof-gate",
        "platform/otto-gateway/deploy.yaml",
    ):
        result = gate.evaluate(
            REGISTRY,
            ROUTER_DOWN,
            "docs: partly safe",
            ["docs/specs/safe.md", unsafe],
        )
        assert not result["admitted"], (unsafe, result)
        assert result["unblocker"]["split_out"] == ["docs/specs/safe.md"]


def test_repair_trailer_never_overrides_immutable_dof_control():
    for path in REGISTRY["immutableWhileRed"]:
        result = gate.evaluate(
            REGISTRY, ROUTER_DOWN, "Genesis-Resolves: llm-router", [path]
        )
        assert not result["admitted"], (path, result)


# --- Scope-aware deadlock breaker (idp#7787) ---------------------------------
# The governing invariant: every P0 objective keeps an authorised path to progress.
# A broken service constrains operations that DEPEND on it, not unrelated safe work.

SAFE_DOCS = ["docs/specs/2026-11-08-temporal-automation-machinery.md"]
# A surface that belongs to OTTO, not the router: repairing the router must not authorise it.
PRIVILEGED = ["platform/otto-gateway/deploy.yaml"]


def test_independent_safe_work_is_admitted_while_an_unrelated_service_is_down():
    """POSITIVE: non-substrate work must keep moving during an unrelated outage.

    Fails today: refused with 'files outside llm-router repairScope'.
    """
    d = gate.evaluate(REGISTRY, ROUTER_DOWN, "docs: specify the kernel", SAFE_DOCS)
    assert d["admitted"], f"independent safe work was refused: {d.get('reason')}"


def test_a_privileged_surface_owned_by_another_component_is_refused():
    """NEGATIVE: a repair trailer must not become a universal key to the substrate.

    Fails today: every component's repairScope is the unbounded '@substrate' alias, so
    claiming to repair the router also authorises otto's gateway.
    """
    d = gate.evaluate(
        REGISTRY, ROUTER_DOWN, "fix\n\nGenesis-Resolves: llm-router", PRIVILEGED
    )
    assert not d["admitted"], (
        "a surface owned by another component was admitted under a foreign incident"
    )


def test_repair_scope_narrows_to_the_component_being_repaired():
    """NEGATIVE: repairing the router must not authorise otto's or the doors' surfaces."""
    scope, _ = gate.scope_of(REGISTRY, "llm-router")
    assert scope, "a component with an empty repairScope repairs nothing"
    assert len(scope) < len(REGISTRY["substrateScope"]), (
        "repairScope equals the whole substrate: one incident unlocks every deploy surface"
    )


def test_repair_of_the_failing_component_is_still_admitted():
    """POSITIVE: narrowing must not break genuine repair, the whole point of the lease."""
    scope, _ = gate.scope_of(REGISTRY, "llm-router")
    in_scope = scope[0].replace("/**", "/probe.yaml").replace("*", "probe")
    d = gate.evaluate(
        REGISTRY, ROUTER_DOWN, "fix\n\nGenesis-Resolves: llm-router", [in_scope]
    )
    assert d["admitted"], f"a genuine repair was refused: {d.get('reason')}"


def test_the_gate_reports_the_smallest_safe_unblocker_when_work_is_deadlocked():
    """POSITIVE: a refusal must name an executable next action, not just say no.

    Fails today: 'files outside repairScope' leaves the author with no admissible path.
    """
    d = gate.evaluate(REGISTRY, ROUTER_DOWN, "docs: unrelated", SAFE_DOCS)
    if not d["admitted"]:
        u = d.get("unblocker")
        assert u, "a deadlocked author is told no, but not how to proceed"
        assert u["split_out"] == SAFE_DOCS, (
            "the unblocker must name the paths that can proceed"
        )
        assert u["repair_trailer"] == "Genesis-Resolves: llm-router"


def test_a_repeated_failure_with_unchanged_preconditions_is_not_admitted_twice():
    """NEGATIVE: the same failing change must not be re-admitted, or it loops forever.

    Fails today: no dedupe key exists, so an identical re-push is decided identically
    and can be retried indefinitely without a changed precondition.
    """
    first = gate.evaluate(
        REGISTRY,
        ROUTER_DOWN,
        "fix\n\nGenesis-Resolves: llm-router",
        PRIVILEGED + ["otto/x.yaml"],
    )
    assert not first["admitted"]
    assert first.get("dedupe_key"), (
        "a refusal carries no dedupe key, so an identical retry is indistinguishable from a new attempt"
    )
    # The same attempt decides identically: identity is stable, so a loop is detectable.
    again = gate.evaluate(
        REGISTRY,
        ROUTER_DOWN,
        "fix\n\nGenesis-Resolves: llm-router",
        PRIVILEGED + ["otto/x.yaml"],
    )
    assert again["dedupe_key"] == first["dedupe_key"]


def test_an_empty_commit_depends_on_nothing_and_proceeds():
    """POSITIVE: a commit touching no paths cannot depend on a broken service."""
    d = gate.evaluate(REGISTRY, ROUTER_DOWN, "docs: empty", [])
    assert d["admitted"], f"a no-op commit was refused: {d.get('reason')}"


def test_glob_is_anchored():
    assert gate.glob_match("clusters/**", "clusters/a/b.yaml")
    assert not gate.glob_match("clusters/**", "clustersx/a.yaml")
    assert gate.glob_match("bin/idp-oke-*", "bin/idp-oke-rebuild")
    assert not gate.glob_match("bin/idp-oke-*", "bin/x/idp-oke-rebuild")


def test_founder_control_modes_and_explicit_suspension():
    assert gate.control_mode(REGISTRY) == "disabled"
    assert gate.control_mode({}) == "enforced"
    assert gate.control_mode({"control": {"mode": "unknown"}}) == "enforced"
    for mode in ("disabled", "observe", "enforced"):
        assert gate.control_mode({"control": {"mode": mode}}) == mode
    result = gate.suspended_result(REGISTRY)
    assert result["ok"] is True
    assert result["enforcement"] == "DISABLED"
    assert result["open_incidents"] is None
    assert result["other_security_checks"] == "UNCHANGED"


def test_scope_exemption_preserves_unaffected_incidents():
    incidents = [{"id": "otto", "issue": 7333}, {"id": "llm-router", "issue": 7334}]
    registry = dict(REGISTRY)
    registry["control"] = {"suspendedComponents": ["otto"]}
    assert gate.active_incidents(registry, incidents) == [incidents[1]]
    registry["control"] = {"suspendedComponents": "otto"}
    assert gate.active_incidents(registry, incidents) == incidents


def test_blind_inventory_remains_visible_during_scope_change():
    blind = [{"id": "dof-probe", "issue": None}]
    registry = dict(REGISTRY)
    registry["control"] = {"suspendedComponents": ["dof-probe"]}
    assert gate.active_incidents(registry, blind) == blind
