"""T-7 (ADR 0044): every action has a decider, and the register must be honest.

The estate's question is "why cannot a machine or a decision model do this?". The answer
lives in one store (`policy/agent-decisions.json`), and the gate (`bin/registry-gate`,
invariant I-6) refuses a declaration that lies.

Every test here carries the case that must trip it. A gate that cannot fail is not a gate,
and a test that executes nothing is not a test.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
DOOR = REPO / "bin" / "capability-index"
GATE = REPO / "bin" / "registry-gate"
REGISTER = REPO / "policy" / "agent-decisions.json"


def load_door():
    spec = importlib.util.spec_from_loader(
        "capability_index",
        importlib.machinery.SourceFileLoader("capability_index", str(DOOR)),
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def door(tmp_path, monkeypatch):
    module = load_door()
    monkeypatch.setattr(module, "KEY_PATH", tmp_path / "registry.key")
    monkeypatch.setattr(module, "DB_PATH", tmp_path / "registry.db")
    return module


def register(entries, roles=("founder",)):
    return {"schema_version": 1, "roles": list(roles), "decisions": list(entries)}


def write_register(tmp_path, monkeypatch, payload) -> Path:
    path = tmp_path / "agent-decisions.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    monkeypatch.setenv("ESTATE_DECISIONS", str(path))
    return path


# --------------------------------------------------------------------------------------
# the derivation: the mode an intent's own source implies


def test_the_derivation_reads_the_steps_and_not_the_description(door):
    """A description that names a model is not a model call. Only the steps decide."""
    machine = "name: x\ndescription: calls an llm to help\nsteps:\n  - cmd: echo hi\n"
    model = "name: x\ndescription: plain\nsteps:\n  - cmd: curl http://llm/v1/chat/completions\n"
    judgment = (
        "name: x\ndescription: plain\nsteps:\n  - cmd: ./ask-the-founder.sh\n"
        "    note: manual approval by the founder\n"
    )
    assert door.derive_intent_mode(machine) == "machine"
    assert door.derive_intent_mode(model) == "model"
    assert door.derive_intent_mode(judgment) == "judgment"


def test_the_committed_register_is_honest(door, tmp_path):
    """The estate's own register must pass its own gate. If this fails, the gate is wrong."""
    ctx = door.Context(idp=REPO, home=tmp_path)
    verdict = door.decision_violations(ctx)
    assert verdict["violations"] == [], verdict["violations"]


def test_the_committed_register_names_only_modes_the_estate_understands():
    payload = json.loads(REGISTER.read_text(encoding="utf-8"))
    for entry in payload["decisions"]:
        assert entry["mode"] in ("machine", "model", "judgment"), entry


# --------------------------------------------------------------------------------------
# I-6: every clause, with the case that trips it


def _violations(
    door, tmp_path, monkeypatch, payload, known=("cap:intent/lane-submit",)
):
    write_register(tmp_path, monkeypatch, payload)
    ctx = door.Context(idp=REPO, home=tmp_path)
    return door.decision_violations(ctx, known_caps=set(known))["violations"]


def test_a_mode_that_does_not_exist_is_refused(door, tmp_path, monkeypatch):
    violations = _violations(
        door,
        tmp_path,
        monkeypatch,
        register(
            [
                {
                    "id": "dec:x",
                    "decision": "d",
                    "mode": "vibes",
                    "decided_by": "cap:intent/lane-submit",
                }
            ]
        ),
    )
    assert [v["clause"] for v in violations] == ["I-6.mode"]


def test_a_judgement_without_irreducibility_is_refused(door, tmp_path, monkeypatch):
    violations = _violations(
        door,
        tmp_path,
        monkeypatch,
        register(
            [
                {
                    "id": "dec:x",
                    "decision": "d",
                    "mode": "judgment",
                    "irreducibility": "i-was-not-sure",
                    "justification": "z" * 80,
                    "decided_by": "founder",
                }
            ]
        ),
    )
    assert "I-6.irreducibility" in [v["clause"] for v in violations]


def test_a_judgement_that_shrugs_is_refused(door, tmp_path, monkeypatch):
    violations = _violations(
        door,
        tmp_path,
        monkeypatch,
        register(
            [
                {
                    "id": "dec:x",
                    "decision": "d",
                    "mode": "judgment",
                    "irreducibility": "novel",
                    "justification": "not sure",
                    "decided_by": "founder",
                }
            ]
        ),
    )
    assert "I-6.justification" in [v["clause"] for v in violations]


def test_a_judgement_with_no_role_is_refused(door, tmp_path, monkeypatch):
    violations = _violations(
        door,
        tmp_path,
        monkeypatch,
        register(
            [
                {
                    "id": "dec:x",
                    "decision": "d",
                    "mode": "judgment",
                    "irreducibility": "novel",
                    "justification": "z" * 80,
                    "decided_by": "the intern",
                }
            ]
        ),
    )
    assert "I-6.judgment-role" in [v["clause"] for v in violations]


def test_a_model_the_estate_does_not_run_is_refused(door, tmp_path, monkeypatch):
    violations = _violations(
        door,
        tmp_path,
        monkeypatch,
        register(
            [
                {
                    "id": "dec:x",
                    "decision": "d",
                    "mode": "model",
                    "decided_by": "model:the-committee",
                }
            ]
        ),
    )
    assert "I-6.model-decider" in [v["clause"] for v in violations]


def test_a_machine_decider_the_estate_does_not_have_is_refused(
    door, tmp_path, monkeypatch
):
    violations = _violations(
        door,
        tmp_path,
        monkeypatch,
        register(
            [
                {
                    "id": "dec:x",
                    "decision": "d",
                    "mode": "machine",
                    "decided_by": "cap:intent/does-not-exist",
                }
            ]
        ),
    )
    assert "I-6.machine-decider" in [v["clause"] for v in violations]


def test_the_same_decision_id_twice_is_refused(door, tmp_path, monkeypatch):
    entry = {
        "id": "dec:twice",
        "decision": "d",
        "mode": "machine",
        "decided_by": "cap:intent/lane-submit",
    }
    violations = _violations(
        door, tmp_path, monkeypatch, register([entry, dict(entry)])
    )
    assert "I-6.unique-id" in [v["clause"] for v in violations]


def test_an_honest_register_is_accepted(door, tmp_path, monkeypatch):
    violations = _violations(
        door,
        tmp_path,
        monkeypatch,
        register(
            [
                {
                    "id": "dec:ok",
                    "decision": "d",
                    "mode": "machine",
                    "decided_by": "cap:intent/lane-submit",
                },
                {
                    "id": "dec:ok2",
                    "decision": "d",
                    "mode": "judgment",
                    "irreducibility": "value-tradeoff",
                    "justification": "two goods the estate cannot rank without a person",
                    "decided_by": "founder",
                },
            ]
        ),
    )
    assert violations == []


def test_undeclared_judgement_residue_is_a_finding_not_a_refusal(
    door, tmp_path, monkeypatch
):
    """Residue nobody wrote down is reported. Refusing it would refuse correct work."""
    write_register(tmp_path, monkeypatch, register([]))
    ctx = door.Context(idp=REPO, home=tmp_path)
    verdict = door.decision_violations(ctx, known_caps=set())
    assert verdict["violations"] == []
    assert isinstance(verdict["findings"], list)


# --------------------------------------------------------------------------------------
# the gate itself


def test_the_gate_fails_a_register_that_lies(tmp_path):
    """The real gate, on a register that claims a capability the estate does not have."""
    lying = tmp_path / "agent-decisions.json"
    lying.write_text(
        json.dumps(
            register(
                [
                    {
                        "id": "dec:lying",
                        "decision": "a decision handed to a capability that does not exist",
                        "mode": "machine",
                        "decided_by": "cap:intent/does-not-exist",
                    }
                ]
            ),
            indent=2,
        ),
        encoding="utf-8",
    )
    env = dict(os.environ)
    env["ESTATE_DECISIONS"] = str(lying)
    proc = subprocess.run(
        [sys.executable, str(GATE), "--json"],
        cwd=REPO,
        env=env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode != 0, proc.stdout
    payload = json.loads(proc.stdout)
    clauses = [v["clause"] for v in payload["decisions"]["violations"]]
    assert "I-6.machine-decider" in clauses, payload["failures"]
    assert any(f.startswith("I-6:") for f in payload["failures"])


def test_the_gate_accepts_the_committed_register():
    proc = subprocess.run(
        [sys.executable, str(GATE), "--json"], cwd=REPO, capture_output=True, text=True
    )
    payload = json.loads(proc.stdout)
    assert payload["decisions"]["violations"] == [], payload["decisions"]["violations"]
