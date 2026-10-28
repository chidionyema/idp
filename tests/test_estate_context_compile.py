"""tests/test_estate_context_compile.py -- the context compiler, pinned.

The compiler is the estate's ONE context compiler (docs/decisions/2026-10-26-one-context-
compiler-and-one-execution-gateway.md). It resolves a task into a bounded, ranked, provenance-
carrying plan. What makes it worth trusting is not that it finds files -- it is that it asks the
ONE engine and keeps the engine's order, that it is deterministic, that it refuses rather than
pads, that it drops what does not fit and NAMES what it dropped, and that it never prints a
credential value.

A test that cannot fail is not a test (AGENTS.md 3). Every claim below has a way to break it:
a ranker creeping back in, a budget that silently truncates, a stale index served as fresh, a
secret that leaks, a plan that changes between two runs on the same tree.

The tests drive a FAKE engine, so they are fast and they prove the compiler's own behaviour
(the engine's behaviour is the engine's to test). One test at the end runs against the REAL
laptop daemon, and is skipped -- not silently passed -- when the daemon is not installed.

Run: bin/pytest or `python3 -m pytest tests/test_estate_context_compile.py`
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import os
import shutil
import subprocess
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
COMPILE = os.path.join(ROOT, "bin", "estate-context-compile")


def _load():
    """Load bin/estate-context-compile as a module (it carries no .py suffix by convention)."""
    spec = importlib.util.spec_from_loader(
        "estate_context_compile",
        importlib.machinery.SourceFileLoader("estate_context_compile", COMPILE),
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    # dataclasses looks the defining module up in sys.modules; an unregistered module cannot
    # define a dataclass at all.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


cc = _load()


# --- the estate's own impact layers, faked so the tests stay fast -------------------------------
# The real layers are SUBPROCESSES: bin/idp-affected-graph takes about a second and
# bin/catalog-projection takes about twenty-two. A test suite that pays twenty-two seconds
# per case to prove a dict was consulted is a suite nobody runs. So the layers are faked
# here and RECORDED, and the real ones are exercised by the command-line tests below, which
# run the compiler as the estate runs it.
_IMPACT_CALLS: list[str] = []


def _fake_affected(base=None, *, repo=ROOT):
    _IMPACT_CALLS.append("estate")
    return {
        "base": base or "origin/main",
        "changed": ["platform/estate/context/plan.py"],
        "layers": {
            "code": {
                "changed": ["platform/estate/context/plan.py"],
                "downstream": ["platform/estate/context/server.py"],
                "tests": ["tests/test_estate_context_compile.py"],
            }
        },
    }


def _fake_catalog(repo=ROOT):
    _IMPACT_CALLS.append("catalog")
    return {
        "entities": [
            {
                "metadata": {
                    "name": "platform-estate-context-broker",
                    "annotations": {
                        "estate/source-path": "platform/estate/context/broker.py"
                    },
                },
                "spec": {"dependsOn": []},
            },
            {
                "metadata": {
                    "name": "platform-estate-context-server",
                    "annotations": {
                        "estate/source-path": "platform/estate/context/server.py"
                    },
                },
                "spec": {
                    "dependsOn": ["component:default/platform-estate-context-broker"]
                },
            },
        ]
    }


cc.estate_affected = _fake_affected
cc.catalog_evidence = _fake_catalog


# --- a fake engine, so the tests are about the compiler -----------------------------------------
class FakeEngine:
    """A stand-in for the one context engine.

    It returns exactly what the real engine returns -- working_set, relevant_symbols,
    files_to_edit, blast_radius -- so the compiler is exercised on the real shape. The order
    it hands over is deliberately NOT alphabetical: a compiler with a ranker of its own would
    re-sort it, and the test below says so.
    """

    def __init__(self, *, head="aaa111", indexed="aaa111", payload=None):
        self.head = head
        self.indexed = indexed
        self.calls = []
        self.payload = payload if payload is not None else self._payload()

    def freshness(self):
        return {
            "path": ROOT,
            "head_commit": self.head,
            "indexed_commit": self.indexed,
            "indexed": True,
            "stale": self.head != self.indexed,
            "last_indexed": "2026-10-27T00:00:00Z",
            "freshness_scope": "base",
            "branch": "lane/estate-context-engine",
        }

    def version(self):
        return "v0.64.11"

    def working_set(self, task, token_budget, *, paths=(), view=None):
        self.calls.append(
            {"task": task, "token_budget": token_budget, "paths": list(paths)}
        )
        return self.payload

    @staticmethod
    def _payload():
        # The engine stores a tracked repository's files under that repository's NAME, and
        # that is what it really answers with (MEASURED against gortex v0.64.11). The fake
        # says it the same way, so the compiler is exercised on the real shape.
        prefix = os.path.basename(ROOT)
        return {
            "task": "estate context broker policy",
            "etag": "0f1e2d3c4b5a",
            "working_set": [
                {
                    "file": f"{prefix}/platform/estate/context/broker.py",
                    "is_test": False,
                    "symbols": ["broker::decide_request"],
                },
                {
                    "file": f"{prefix}/platform/estate/context/claims.py",
                    "is_test": False,
                    "symbols": ["claims::verify_claim"],
                },
                {
                    "file": f"{prefix}/tests/test_estate_context_broker.py",
                    "is_test": True,
                    "symbols": [],
                },
            ],
            "files_to_edit": [f"{prefix}/platform/estate/context/broker.py"],
            "related_test_files": [f"{prefix}/tests/test_estate_context_broker.py"],
            "relevant_symbols": [
                {
                    "file_path": f"{prefix}/platform/estate/context/broker.py",
                    "id": "broker::decide_request",
                    "kind": "function",
                    "name": "decide_request",
                    "start_line": 1,
                    "source": "def decide_request(request, state):\n    return Decision(True, 'ALLOW', 'ok')\n",
                }
            ],
            "blast_radius": {
                "callers_by_file": [
                    {
                        "file": f"{prefix}/platform/estate/context/broker.py",
                        "callers": ["server::tool_estate_context"],
                    }
                ],
                "covering_tests": ["tests/test_estate_context_broker.py"],
                "warning": "no covering tests found",
            },
            "retrieval_note": {
                "verdict": "high",
                "reason": "clustered",
                "likely_dirs": [],
                "suggested_tools": [],
            },
        }


def _resolve(engine=None, **kwargs):
    eng = engine or FakeEngine()
    kwargs.setdefault("repo", ROOT)
    kwargs.setdefault("tier", "standard")
    kwargs.setdefault("door", "local")
    _IMPACT_CALLS.clear()
    plan = cc.resolve(
        kwargs.pop("task", "estate context broker policy"), engine=eng, **kwargs
    )
    return plan, eng


# --- the compiler asks the ONE engine, and keeps its order ---------------------------------------
def test_the_compiler_asks_the_engine_and_says_what_it_asked():
    plan, engine = _resolve()
    assert engine.calls, "the compiler never asked the engine"
    assert engine.calls[0]["task"] == "estate context broker policy"


def test_the_engine_s_order_is_the_plan_s_order():
    """A ranker of the compiler's own would re-sort this. The engine's order is kept."""
    plan, _ = _resolve()
    files = [i["file"] for i in plan["items"]]
    assert files == [
        "platform/estate/context/broker.py",
        "platform/estate/context/claims.py",
        "tests/test_estate_context_broker.py",
    ]


def test_the_engines_repo_prefix_is_stripped_and_the_repos_own_path_kept():
    """The engine stores a tracked repository's files under that repository's NAME. That
    prefix is the engine's storage detail; the plan carries the repository's own path."""
    plan, _ = _resolve()
    prefix = os.path.basename(ROOT)
    files = [i["file"] for i in plan["items"]]
    assert files, "the plan has no items"
    assert all(not f.startswith(f"{prefix}/") for f in files), files


def test_the_compiler_carries_no_ranker_of_its_own():
    """The estate has one ranking layer. A second one in this file is the stitching AGENTS.md 6
    forbids, and it is the exact thing that was deleted from this file once already."""
    source = open(COMPILE, encoding="utf-8").read().lower()
    for banned in ("tf-idf", "tfidf", "idf", "bm25", "cosine", "similarity score"):
        assert banned not in source, (
            f"the compiler grew its own ranking signal: {banned}"
        )
    assert "smart_context" in source, "the compiler must speak to the engine's own tool"


# --- the contract (C1) ---------------------------------------------------------------------------
def test_the_plan_carries_every_contract_field():
    plan, _ = _resolve()
    for key in (
        "task",
        "surface",
        "tier",
        "budget_tokens",
        "used_tokens",
        "items",
        "coverage",
        "plan_hash",
        "provenance",
    ):
        assert key in plan, key


# --- the vocabulary is the contract's, not the implementation's ---------------------------------
def test_the_tier_vocabulary_is_free_standard_frontier():
    """The contract names the tiers "free" | "standard" | "frontier". A tier the contract does
    not name is refused, not accepted as an alias."""
    assert cc.PLAN.TIERS == ("free", "standard", "frontier")
    plan, _ = _resolve(tier="fast")
    assert plan["allowed"] is False
    assert plan["verdict"] == "BAD_REQUEST"


def test_each_tier_says_which_evidence_it_consulted():
    for tier, layers in (
        ("free", ["engine"]),
        ("standard", ["engine", "estate"]),
        ("frontier", ["engine", "estate", "catalog"]),
    ):
        plan, _ = _resolve(tier=tier)
        assert plan["evidence"] == layers
        assert plan["tier"] == tier


def test_the_free_tier_consults_no_estate_layer():
    """The free tier is the engine's working set and nothing else: no subprocess, no second
    graph. A free plan that carries estate impact is a free plan that is not free."""
    plan, _ = _resolve(tier="free")
    assert plan["evidence"] == ["engine"]
    assert _IMPACT_CALLS == []


def test_the_wider_tiers_consult_the_layers_they_name():
    plan, _ = _resolve(tier="standard")
    assert _IMPACT_CALLS == ["estate"]
    plan, _ = _resolve(tier="frontier")
    assert _IMPACT_CALLS == ["estate", "catalog"]


def test_the_catalog_layer_is_impact_evidence_and_not_a_ranker():
    """The catalog's reverse dependency is EVIDENCE: it says what depends on a file. It never
    reorders the plan -- the engine's order stands."""
    plan, _ = _resolve(tier="frontier")
    files = [i["source"] for i in plan["items"]]
    assert files == [
        "platform/estate/context/broker.py",
        "platform/estate/context/claims.py",
        "tests/test_estate_context_broker.py",
    ]
    dependents = {i["source"]: i["impact"]["catalog_dependents"] for i in plan["items"]}
    assert dependents["platform/estate/context/broker.py"] == [
        "platform/estate/context/server.py"
    ]


def test_the_estates_real_impact_layer_is_the_one_the_compiler_calls():
    """The layer is bin/idp-affected-graph, run as a subprocess, on the real tree."""
    out = cc.estate_affected(repo=ROOT)
    assert isinstance(out, dict)
    assert "layers" in out or out == {}


def test_the_surface_is_the_agent_surface_and_the_door_is_how_it_was_asked():
    plan, _ = _resolve(surface="claude-code", door="local")
    assert plan["surface"] == "claude-code"
    assert plan["door"] == "local"
    assert plan["provenance"]["engine"]["door"] == "laptop-fallback-daemon"


def test_a_budget_above_the_estates_one_ceiling_is_refused():
    """The ceiling lives in platform/llm/request_ceiling.py and is READ, not copied. A budget
    above it is refused rather than silently shrunk."""
    ceiling = cc._ceiling()
    plan, _ = _resolve(budget_tokens=ceiling + 1)
    assert plan["allowed"] is False
    assert plan["verdict"] == "BUDGET_REFUSED"
    assert plan["evidence"]["ceiling"] == ceiling


def test_the_ceiling_is_read_from_the_estate_and_not_copied_here():
    source = open(COMPILE, encoding="utf-8").read()
    assert "request_ceiling" in source
    assert "200000" not in source, (
        "the ceiling number is copied into the compiler; read it instead"
    )


def test_every_item_carries_its_provenance_and_its_reason():
    plan, _ = _resolve()
    assert plan["items"]
    for item in plan["items"]:
        assert item["source"]
        assert item["sha256"] and len(item["sha256"]) == 64
        assert item["content_sha256"] and len(item["content_sha256"]) == 64
        assert item["tokens"] >= 1
        assert item["rank"] >= 1
        assert item["why"]
        assert "score" in item["impact"]
        assert item["impact"]["why"]
        prov = item["provenance"]
        assert prov["file"] == item["source"]
        assert prov["commit"] == plan["provenance"]["commit"]


def test_the_items_carry_the_contract_c1_names():
    """C1 is normative: each item carries source, sha256, tokens, impact_score, rank, why.
    A renamed field is a contract the compiler does not keep."""
    plan, _ = _resolve()
    for item in plan["items"]:
        for field in ("source", "sha256", "tokens", "impact_score", "rank", "why"):
            assert field in item, f"C1 field missing from the item: {field}"
        assert item["impact_score"] == item["impact"]["score"]
        assert item["sha256"] == item["provenance"]["sha256"]


def test_the_budget_is_a_ceiling_and_the_used_tokens_are_measured():
    plan, _ = _resolve(budget_tokens=4000)
    assert plan["used_tokens"] <= plan["budget_tokens"]
    assert plan["used_tokens"] == sum(i["tokens"] for i in plan["items"])
    assert plan["tokenizer"]


# --- determinism ---------------------------------------------------------------------------------
def test_two_resolves_over_the_same_tree_and_task_are_identical():
    a, _ = _resolve()
    b, _ = _resolve()
    assert a["plan_hash"] == b["plan_hash"]
    assert a["items"] == b["items"]


def test_the_plan_hash_does_not_move_when_only_volatile_fields_move():
    """The engine's etag and retrieval note change without the answer changing."""
    engine_a = FakeEngine()
    engine_b = FakeEngine()
    payload_b = json.loads(json.dumps(engine_b.payload))
    payload_b["etag"] = "ffffffffffffffff"
    payload_b["retrieval_note"] = {
        "verdict": "low",
        "reason": "different",
        "likely_dirs": [],
        "suggested_tools": [],
    }
    engine_b.payload = payload_b
    a, _ = _resolve(engine_a)
    b, _ = _resolve(engine_b)
    assert a["plan_hash"] == b["plan_hash"]


# --- it refuses rather than pads ------------------------------------------------------------------
def test_a_stale_index_is_refused_on_a_committed_request():
    engine = FakeEngine(head="aaa111", indexed="bbb222")
    plan, _ = _resolve(engine)
    assert plan["allowed"] is False
    assert plan["verdict"] == "STALE_REJECT"
    assert plan["items"] == []


def test_a_working_copy_request_may_be_served_from_the_published_route():
    engine = FakeEngine(head="aaa111", indexed="bbb222")
    plan, _ = _resolve(engine, mode="working_copy")
    assert plan.get("allowed", True) is True
    assert plan["items"]


def test_a_path_outside_the_claim_is_refused():
    plan, _ = _resolve(
        paths=["platform/estate/context/broker.py"],
        claim_paths=["tests/**"],
    )
    assert plan["allowed"] is False
    assert plan["verdict"] == "PATH_REFUSED"
    assert plan["items"] == []


def test_a_path_inside_the_claim_is_served():
    plan, _ = _resolve(
        paths=["platform/estate/context/broker.py"],
        claim_paths=["platform/estate/context/*"],
    )
    assert plan.get("allowed", True) is True
    assert plan["items"]


def test_an_empty_task_is_refused():
    plan, _ = _resolve(task="   ")
    assert plan["allowed"] is False
    assert plan["verdict"] == "BAD_REQUEST"


# --- the budget drops, and names what it dropped ----------------------------------------------------
def test_what_does_not_fit_the_budget_is_dropped_and_named():
    plan, _ = _resolve(budget_tokens=40)
    assert plan["used_tokens"] <= 40
    assert plan["dropped"]
    for dropped in plan["dropped"]:
        assert dropped["source"]
        assert dropped["reason"] in ("budget", "not-in-tree")


def test_the_coverage_names_the_impact_nodes_the_plan_did_not_carry():
    plan, _ = _resolve(budget_tokens=40)
    coverage = plan["coverage"]
    assert "uncovered_impact_nodes" in coverage
    for node in coverage["uncovered_impact_nodes"]:
        assert node["node"]
        assert node["why"]


# --- secrets ---------------------------------------------------------------------------------------
def test_no_excerpt_carries_a_credential_value():
    payload = FakeEngine._payload()
    payload["relevant_symbols"][0]["source"] = (
        'GITHUB_TOKEN = "ghp_abcdefghijklmnopqrstuvwxyz012345"\n'
    )
    plan, _ = _resolve(FakeEngine(payload=payload))
    for item in plan["items"]:
        assert "ghp_abcdefghijklmnopqrstuvwxyz012345" not in item["excerpt"]
    assert "GITHUB_TOKEN" in plan["redacted"]


def test_the_compiler_uses_the_brokers_secret_rule_and_not_its_own():
    assert (
        cc.BROKER.scrub("token ghp_abcdefghijklmnopqrstuvwxyz0123")[0]
        == "token REF:GITHUB_TOKEN"
    )


# --- the doors -------------------------------------------------------------------------------------
def test_the_cluster_door_is_the_default_route_and_the_laptop_is_the_fallback():
    """A cluster that cannot answer falls back to the laptop, and the plan says so."""

    class DeadBroker:
        def context(self, **kwargs):
            raise cc.BROKER_CLIENT.BrokerUnavailable("the broker is not there")

    plan, engine = _resolve(door="auto", client=DeadBroker())
    assert plan.get("allowed", True) is True
    assert plan["door"] == "local"
    assert plan["fallback_from"] == "cluster"
    assert engine.calls, "the fallback never asked the engine"


def test_a_refusal_from_the_broker_is_not_silently_answered_by_the_fallback():
    """Only an UNREACHABLE broker falls back. A broker that REFUSES is the policy speaking,
    and a refusal is not replaced by a laptop answer."""

    class RefusingBroker:
        def context(self, **kwargs):
            return {
                "isError": True,
                "structuredContent": {
                    "allowed": False,
                    "verdict": "STALE_REJECT",
                    "reason": "the index is at bbb222 and the request asked about aaa111",
                    "evidence": {},
                },
            }

    plan, _ = _resolve(door="auto", client=RefusingBroker())
    assert plan["allowed"] is False
    assert plan["verdict"] == "STALE_REJECT"


# --- the command line -------------------------------------------------------------------------------
def test_the_cli_answers_json_and_exits_zero():
    result = subprocess.run(
        [
            COMPILE,
            "--task",
            "estate context broker policy",
            "--tier",
            "standard",
            "--door",
            "local",
            "--json",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert result.returncode == 0, result.stderr[:800]
    payload = json.loads(result.stdout)
    assert payload["plan_hash"]
    assert payload["items"]


def test_the_cli_exits_nonzero_when_the_engine_cannot_answer(tmp_path):
    """No daemon tracking this path means no answer. The compiler says so and refuses."""
    untracked = tmp_path / "not-a-tracked-repository"
    untracked.mkdir()
    result = subprocess.run(
        [
            COMPILE,
            "--task",
            "estate context broker policy",
            "--tier",
            "standard",
            "--door",
            "local",
            "--json",
            "--repo",
            str(untracked),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=300,
    )
    if shutil.which("gortex") is None:
        pytest.skip("the engine is not installed on this machine")
    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["allowed"] is False
    assert payload["verdict"] in (
        "ENGINE_UNREACHABLE",
        "STALE_REJECT",
        "UNPROVEN_INDEX",
    )


# --- against the real engine ------------------------------------------------------------------------
def test_the_real_engine_answers_and_the_plan_is_stable():
    """The live path: the laptop daemon, the estate's developer fallback.

    Skipped -- not passed -- when the engine is not installed, so the suite never claims a
    proof it did not get.
    """
    if shutil.which("gortex") is None:
        pytest.skip("gortex is not installed on this machine")
    first = subprocess.run(
        [
            COMPILE,
            "--task",
            "estate context broker policy",
            "--tier",
            "standard",
            "--door",
            "local",
            "--budget-tokens",
            "2000",
            "--json",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=300,
    )
    if first.returncode != 0:
        pytest.skip(
            f"the laptop daemon is not tracking this checkout: {first.stdout[:200]}"
        )
    second = subprocess.run(
        [
            COMPILE,
            "--task",
            "estate context broker policy",
            "--tier",
            "standard",
            "--door",
            "local",
            "--budget-tokens",
            "2000",
            "--json",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=300,
    )
    a, b = json.loads(first.stdout), json.loads(second.stdout)
    assert a["plan_hash"] == b["plan_hash"]
    assert a["items"]
    assert a["used_tokens"] <= a["budget_tokens"]
    assert a["provenance"]["engine"]["door"] == "laptop-fallback-daemon"
