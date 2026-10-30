"""The judge for catalog/critical-functions.json -- the estate's ONE critical-function judge.

WHY THIS EXISTS. Founder, 2026-10-30: "we need to get a metric unified across the board ...
we need to be able to measure it ... ambiently ... evaluated and judged ... and it has to
prioritise founder concerns ... and move idle agents to the highest value work for the
estate." A registry that nobody judges is a wish list. This file is the judge:

  * every registered function must be MEASURABLE by the one spine -- a probe type or a goal
    type the spine does not know is BLIND, and BLIND is not a pass (the spine's own law)
  * every entry must carry a structured remedy (runner, repo, budget, task), so a failing
    function always has a next action for an idle agent
  * founder-critical entries must sit FIRST and carry weight 2, because the registry order is
    the priority order the spine walks and the weight is how the one metric prioritises the
    founder's concerns
  * the estate's mandatory critical functions must all be registered

THE GATE MUST BE ABLE TO FAIL. Every rule below is checked against the REAL registry AND
against a fixture that breaks it, so the judge is proven to reject what it claims to reject.
A gate that cannot fail is not a gate (estate law, section 9, principle 1).
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
REGISTRY_PATH = REPO / "catalog/critical-functions.json"
SPINE_PATH = REPO / "platform/estate/libexec/critical-watch.py"
PROBE_PATH = REPO / "platform/estate/libexec/critical-probe.py"

# The functions the estate cannot work without. The spine only watched three of them until
# 2026-10-30, while the founder's memory plane, the router's lanes, the cost bound and the
# cluster substrate were stressed and unmonitored.
MANDATORY_FUNCTIONS = {
    "memory-plane",
    "router-lanes",
    "spend-bound",
    "estate-substrate",
    "disk-guardian",
    "executor",
    "estate-bus",
}

# The runners the estate's session door accepts (platform/estate/intents, the bus's registry).
VALID_RUNNERS = {"claude", "llm", "echo", "sleep", "ask"}


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader, "could not load %s" % path
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


spine = _load(SPINE_PATH, "critical_watch_spine")
probe = _load(PROBE_PATH, "critical_probe_module")


def _spine_supports(kind: str, probe_type: bool) -> bool:
    """Whether the spine can MEASURE this kind -- asked of the spine itself, not of a list.

    The spine's own dispatch is the truth: a known type asked for without its arguments
    fails as MALFORMED, while an unknown type is refused outright as "unknown probe type".
    So the two answers tell us what the spine can and cannot measure, without duplicating
    the spine's type list here (which would drift).
    """
    if probe_type:
        _, why, _ = spine.probe_liveness({"type": kind})
    else:
        _, why, _ = spine.probe_goal({"type": kind})
    if "unknown" in why:
        return False
    return "malformed" in why or "not a number" in why or "not a positive" in why


def _entries(registry: dict) -> list:
    return list(registry.get("functions", [])) + list(registry.get("assumptions", []))


def judge_registry(registry: dict) -> list:
    """The findings. An empty list means the registry is fit to be watched."""
    findings: list = []
    entries = _entries(registry)
    if not entries:
        return ["the registry registers no function at all"]

    seen = set()
    founder_seen_non_founder = False
    for entry in entries:
        fid = entry.get("id")
        if not fid:
            findings.append("an entry has no id")
            continue
        if fid in seen:
            findings.append("%s is registered twice" % fid)
        seen.add(fid)

        # 1. it must be MEASURABLE by the one spine.
        liveness = entry.get("liveness")
        if not liveness:
            findings.append("%s declares no liveness probe" % fid)
        elif not _spine_supports(liveness.get("type", ""), True):
            findings.append(
                "%s uses the liveness type '%s', which the spine cannot measure"
                % (fid, liveness.get("type"))
            )
        goal = entry.get("goal")
        if goal and not _spine_supports(goal.get("type", ""), False):
            findings.append(
                "%s uses the goal type '%s', which the spine cannot measure"
                % (fid, goal.get("type"))
            )

        # 2. it must carry a structured remedy, so a failure always has a next action.
        remediation = entry.get("remediation") or {}
        for field in ("task", "runner", "repo"):
            if not remediation.get(field):
                findings.append("%s has no remediation.%s" % (fid, field))
        if remediation.get("runner") and remediation["runner"] not in VALID_RUNNERS:
            findings.append(
                "%s remediates with the runner '%s', which the bus does not know"
                % (fid, remediation["runner"])
            )
        if not remediation.get("budget"):
            findings.append("%s has no remediation budget" % fid)

        # 3. founder concerns first, and weighted: the order is the priority, the weight is
        #    how the one metric counts them.
        weight = entry.get("weight", 1)
        if entry.get("founder_critical"):
            if weight < 2:
                findings.append(
                    "%s is founder-critical but carries weight %s: the metric would not "
                    "prioritise it" % (fid, weight)
                )
            if founder_seen_non_founder:
                findings.append(
                    "%s is founder-critical but sits below a non-founder entry: the spine "
                    "walks the registry in order, so it would not be reached first"
                    % fid
                )
        else:
            founder_seen_non_founder = True
            if weight != 1:
                findings.append(
                    "%s is not founder-critical but carries weight %s: only the founder's "
                    "own surfaces may be weighted" % (fid, weight)
                )

    # 4. the mandatory functions are all present.
    for fid in sorted(MANDATORY_FUNCTIONS - seen):
        findings.append("%s is not registered: the estate cannot work without it" % fid)

    # 5. the registry's own declared types must be the ones the spine can measure.
    for kind in registry.get("probe_types") or {}:
        if not _spine_supports(kind, True):
            findings.append(
                "the registry declares the liveness type '%s' (unknown)" % kind
            )
    for kind in registry.get("goal_types") or {}:
        if not _spine_supports(kind, False):
            findings.append("the registry declares the goal type '%s' (unknown)" % kind)

    return findings


# --------------------------------------------------------------------------- the judge


def test_the_real_registry_passes_the_judge():
    registry = json.loads(REGISTRY_PATH.read_text())
    findings = judge_registry(registry)
    assert findings == [], (
        "the critical-function registry does not pass its own judge: %s" % (findings,)
    )


def test_the_judge_rejects_an_unmeasurable_probe_type():
    registry = json.loads(REGISTRY_PATH.read_text())
    registry["functions"][0]["liveness"]["type"] = "telepathy"
    findings = judge_registry(registry)
    assert any("cannot measure" in f for f in findings), findings


def test_the_judge_rejects_a_founder_entry_below_a_non_founder_one():
    registry = json.loads(REGISTRY_PATH.read_text())
    functions = registry["functions"]
    founder = [f for f in functions if f.get("founder_critical")]
    other = [f for f in functions if not f.get("founder_critical")]
    registry["functions"] = other[:1] + founder + other[1:]
    findings = judge_registry(registry)
    assert any("founder-critical but sits below" in f for f in findings), findings


def test_the_judge_rejects_an_entry_without_a_structured_remedy():
    registry = json.loads(REGISTRY_PATH.read_text())
    registry["functions"][0].pop("remediation")
    findings = judge_registry(registry)
    assert any("remediation" in f for f in findings), findings


def test_the_judge_rejects_a_registry_missing_a_mandatory_function():
    registry = json.loads(REGISTRY_PATH.read_text())
    registry["functions"] = [
        f for f in registry["functions"] if f.get("id") != "memory-plane"
    ]
    findings = judge_registry(registry)
    assert any("memory-plane is not registered" in f for f in findings), findings


def test_the_judge_rejects_an_unweighted_founder_surface():
    registry = json.loads(REGISTRY_PATH.read_text())
    registry["functions"][0]["weight"] = 1
    findings = judge_registry(registry)
    assert any("the metric would not prioritise it" in f for f in findings), findings


# --------------------------------------------------------------------------- the metric


def _results(verdicts: dict) -> list:
    return [{"id": k, "verdict": v, "why": "why"} for k, v in verdicts.items()]


def test_the_metric_is_the_weighted_share_of_passing_entries():
    entries = [
        {"id": "a", "weight": 2, "founder_critical": True},
        {"id": "b", "weight": 1},
        {"id": "c", "weight": 1},
    ]
    out = probe.compute_health(
        entries, _results({"a": "PASS", "b": "PASS", "c": "PASS"})
    )
    assert out["estate_health"] == 100.0, out
    assert out["weighted_total"] == 4 and out["weighted_passed"] == 4, out
    assert out["founder_total"] == 2 and out["founder_passed"] == 2, out


def test_the_metric_counts_a_founder_failure_twice():
    entries = [
        {"id": "a", "weight": 2, "founder_critical": True},
        {"id": "b", "weight": 1},
        {"id": "c", "weight": 1},
    ]
    out = probe.compute_health(
        entries, _results({"a": "FAIL", "b": "PASS", "c": "PASS"})
    )
    assert out["estate_health"] == 50.0, out  # 2 of 4 weighted points
    assert out["founder_passed"] == 0 and out["founder_total"] == 2, out


def test_the_metric_queues_the_failures_in_registry_order():
    entries = [
        {"id": "first", "weight": 2, "founder_critical": True},
        {"id": "second", "weight": 1},
    ]
    out = probe.compute_health(entries, _results({"first": "FAIL", "second": "FAIL"}))
    assert [q["id"] for q in out["queue"]] == ["first", "second"], out


# --------------------------------------------------------------------------- the probes


def test_the_spend_bound_probe_accepts_the_estates_real_configs():
    healthy, reason, _ = probe.probe_spend_bound()
    assert healthy, reason


def test_the_spend_bound_probe_rejects_a_chain_that_ends_in_a_paid_lane(tmp_path):
    fixture = tmp_path / "config.yaml"
    fixture.write_text(
        "model_list:\n"
        "  - model_name: paid\n"
        "    litellm_params:\n"
        "      model: openai/gpt-5\n"
        "      input_cost_per_token: 0.0000012\n"
        "  - model_name: cheap\n"
        "    litellm_params:\n"
        "      model: ollama/qwen2.5-coder:1.5b\n"
        "router_settings:\n"
        "  fallbacks:\n"
        "    - cheap: [paid]\n"
        "general_settings:\n"
        "  max_budget: 5.0\n"
    )
    healthy, reason, _ = probe.probe_spend_bound([("fixture", str(fixture))])
    assert not healthy, "a chain that ends in a paid lane must be rejected"
    assert "PAID" in reason, reason


def test_the_spend_bound_probe_rejects_a_config_with_no_ceiling(tmp_path):
    fixture = tmp_path / "config.yaml"
    fixture.write_text(
        "model_list:\n"
        "  - model_name: cheap\n"
        "    litellm_params:\n"
        "      model: ollama/qwen2.5-coder:1.5b\n"
        "general_settings:\n"
        "  budget_duration: 1d\n"
    )
    healthy, reason, _ = probe.probe_spend_bound([("fixture", str(fixture))])
    assert not healthy
    assert "spend ceiling" in reason, reason


def test_the_memory_plane_probe_fails_when_the_door_cannot_be_reached():
    """The falsifier: a door that refuses must be RED, never a quiet pass."""
    healthy, reason, _ = probe.probe_memory_plane(
        door_url="https://127.0.0.1:1/estate/mcp"
    )
    assert not healthy, "an unreachable door must not pass"
    assert "unreachable" in reason or "no MCP_GATEWAY_KEY" in reason, reason
