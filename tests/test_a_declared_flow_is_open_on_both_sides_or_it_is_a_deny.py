"""A namespace fence is two default-denies facing each other.

A packet from A to B survives only if A declares `egress: [B]` and B declares
`ingress_from: [A]`. Half a declaration reads like an allowance in allowances.yaml and is a
deny on the wire, which is the one shape of fence defect nothing could see.

It bit the estate on 2026-09-07: estate-db admitted llm, llm never named estate-db, and the
router could not roll -- every new pod died in Prisma's startup health check with
`httpx.ConnectError: All connection attempts failed`, while two pods older than the fence went
on serving against a ConfigMap Flux had already pruned. The fence had been lying for as long
as the declaration had been half-written.
"""

import importlib.util
import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
ALLOWANCES = ROOT / "platform" / "ns-fences" / "allowances.yaml"

# The generator is a script, not a package, and workspace loads it by path -- so does this
# (LAW 45, the defs_validate row of AGENTS.md).
_spec = importlib.util.spec_from_loader(
    "idp_ns_fence_gen",
    importlib.machinery.SourceFileLoader(
        "idp_ns_fence_gen", str(ROOT / "bin" / "idp-ns-fence-gen")
    ),
)
gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen)


def test_the_estate_declares_no_flow_on_one_side_only():
    flows = yaml.safe_load(ALLOWANCES.read_text())["flows"]
    assert gen.one_sided(flows) == []


def test_an_egress_nobody_admits_is_refused():
    complaints = gen.one_sided(
        {
            "a": {"egress": ["b"]},
            "b": {"ingress_from": []},
        }
    )
    assert len(complaints) == 1
    assert "a" in complaints[0] and "b" in complaints[0]


def test_an_admission_nobody_declared_is_refused():
    complaints = gen.one_sided(
        {
            "a": {"egress": []},
            "b": {"ingress_from": ["a"]},
        }
    )
    assert len(complaints) == 1


def test_both_halves_declared_is_allowed():
    assert (
        gen.one_sided(
            {
                "a": {"egress": ["b"]},
                "b": {"ingress_from": ["a"]},
            }
        )
        == []
    )


def test_the_collector_edge_is_not_graded():
    """policy_docs grants every namespace egress to the collector for LAW 50 whether it asked
    or not, so neither half of that edge is ever declared and its absence proves nothing."""
    assert (
        gen.one_sided(
            {
                "a": {"egress": [gen.SINK]},
                gen.SINK: {"ingress_from": []},
            }
        )
        == []
    )


def test_a_namespace_outside_the_flows_map_is_not_graded():
    """estate-db-style targets that exist but declare nothing are somebody else's fence."""
    assert gen.one_sided({"a": {"egress": ["not-in-this-file"]}}) == []
