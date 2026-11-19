"""Pure candidate contract tests. Real runtime/Greenlane bindings are separate."""
import json
import sys
from pathlib import Path

import pytest
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

# Import the actual estate modules, not duplicate test snippets.
import importlib.machinery
import importlib.util

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    loader = importlib.machinery.SourceFileLoader(name, str(ROOT / path))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    loader.exec_module(module)
    return module


contract = load("frontier_contract", "platform/estate/nsvee_enforcement.py")
ReceiptError = contract.ReceiptError
validate_admission_receipt = contract.validate_admission_receipt
binary_calibration = load("frontier_calibration", "platform/eval/judge_drift.py").binary_calibration
mutation_verdict = load("frontier_mutation", "bin/mutation-orchestrator").mutation_verdict
fixed_horizon_decision = load("frontier_comparison", "platform/eval/pareval_layer.py").fixed_horizon_decision


def canonical(receipt):
    return json.dumps({k: v for k, v in receipt.items() if k != "signature"}, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")


@pytest.fixture
def case():
    private = Ed25519PrivateKey.generate()
    public = private.public_key()
    expected = dict(repository="chidionyema/idp", base="a" * 40, head="b" * 40, tree="c" * 40, contract="d" * 64, policy="e" * 64, environment="f" * 64, instruction="I-1", fence=4, nonce="nonce-1", scope=["nsvee/engine.py"], max_ttl=120, builder="builder", verifiers=["qa"], nonce_unused=True, required_checks={"bdd": {"mode": "REQUIRED"}})
    receipt = {k: expected[k] for k in ("repository", "base", "head", "tree", "contract", "policy", "environment", "instruction", "fence", "nonce", "scope")}
    receipt.update(schema="estate.nsvee.admission/2", issued_at=10, expires_at=100, signer="qa", key_id="key-1", verdict="PASS", evidence_digest="0" * 64, checks={"bdd": {"status": "PASS", "executed": 2, "control": "PASS", "evidence": "1" * 64}})

    def sign(r):
        r["signature"] = private.sign(canonical(r)).hex()
        return r

    def authenticate(signer, key, payload, signature):
        if (signer, key) != ("qa", "key-1"):
            return False
        try:
            public.verify(bytes.fromhex(signature), payload)
        except (InvalidSignature, ValueError):
            return False
        return True

    return expected, sign(receipt), sign, authenticate


def test_valid(case):
    e, r, _, auth = case
    assert validate_admission_receipt(r, e, now=20, authenticate=auth) == r


@pytest.mark.parametrize("field,value", [("repository", "other/repo"), ("base", "0"*40), ("head", "0"*40), ("tree", "0"*40), ("contract", "0"*64), ("policy", "0"*64), ("environment", "0"*64), ("instruction", "I-other"), ("fence", 3), ("nonce", "other"), ("scope", []), ("signer", "builder"), ("key_id", "bad"), ("expires_at", 19), ("issued_at", 30), ("signature", "bad"), ("verdict", "FAIL"), ("schema", "old")])
def test_refuse_binding(case, field, value):
    e, r, sign, auth = case
    r[field] = value
    if field != "signature":
        sign(r)
    with pytest.raises(ReceiptError):
        validate_admission_receipt(r, e, now=20, authenticate=auth)


@pytest.mark.parametrize("field,value", [("executed", 0), ("executed", True), ("status", "SKIPPED"), ("status", "NEUTRAL"), ("control", "FAIL"), ("evidence", "")])
def test_bad_check(case, field, value):
    e, r, sign, auth = case
    r["checks"]["bdd"][field] = value
    with pytest.raises(ReceiptError):
        validate_admission_receipt(sign(r), e, now=20, authenticate=auth)


def test_tamper_and_replay(case):
    e, r, sign, auth = case
    for corrupt in (dict(r, checks={}), dict(r, evidence_digest="2"*64)):
        with pytest.raises(ReceiptError):
            validate_admission_receipt(corrupt, e, now=20, authenticate=auth)
    with pytest.raises(ReceiptError):
        validate_admission_receipt(r, dict(e, nonce_unused=False), now=20, authenticate=auth)


def test_auth_outage(case):
    e, r, _, _ = case
    def dead(*args):
        raise OSError("offline")
    with pytest.raises(ReceiptError):
        validate_admission_receipt(r, e, now=20, authenticate=dead)


def test_non_applicable_policy(case):
    e, r, sign, auth = case
    e["required_checks"]["docs"] = {"mode": "NOT_APPLICABLE"}
    r["checks"]["docs"] = dict(status="NOT_APPLICABLE", executed=0, control="NOT_APPLICABLE", evidence="2"*64)
    assert validate_admission_receipt(sign(r), e, now=20, authenticate=auth)


def test_calibration_imbalanced():
    result = binary_calibration([(1, 1)]*80 + [(0, 0)]*10 + [(1, 0)]*10)
    assert result["pe"] == pytest.approx(.74)
    assert result["kappa"] == pytest.approx((.9-.74)/(1-.74))
    assert result["false_accept_rate"] == .5


@pytest.mark.parametrize("rows", [[(1,1)]*50, [(0,0)]*50, [(None,1)], [(float("nan"),1)], [(1,1)]*10+[(0,0)]])
def test_calibration_unknown(rows):
    assert binary_calibration(rows)["status"] == "inconclusive"


def test_calibration_perfect():
    assert binary_calibration([(1,1)]*8+[(0,0)]*8)["kappa"] == 1


@pytest.mark.parametrize("status", ["TIMEOUT", "ERROR", "EQUIVALENT", "UNKNOWN", "SURVIVED"])
def test_mutant_nonpass(status):
    assert mutation_verdict(expected=["a"], results={"a": {"status": status}}) == ("FAIL" if status == "SURVIVED" else "INCONCLUSIVE")


def test_mutation_valid_and_missing():
    killed = dict(status="KILLED", baseline_passed=True, test_executed=True, failure_kind="ASSERTION")
    assert mutation_verdict(expected=["a"], results={"a": killed}) == "PASS"
    assert mutation_verdict(expected=[], results={}) == "INCONCLUSIVE"
    assert mutation_verdict(expected=["a","b"], results={"a": killed}) == "INCONCLUSIVE"
    assert mutation_verdict(expected=["a"], results={"a": dict(killed, test_executed=False)}) == "INCONCLUSIVE"


def comparison_case(n, a, b, margin=.2):
    plan = {str(i): "one" for i in range(n)}
    rows = [(k, "one", a, b) for k in plan]
    return rows, dict(planned_ids=plan, strata=["one"], margin=margin)


def test_fixed_horizon_waits():
    rows, args = comparison_case(300, 1, 0)
    assert fixed_horizon_decision(rows[:-1], **args)["decision"] == "NEED_MORE_EVIDENCE"
    assert fixed_horizon_decision(rows, **args)["decision"] == "A_BETTER"


def test_no_difference_is_not_equivalence():
    rows, args = comparison_case(10, .5, .5)
    assert fixed_horizon_decision(rows, **args)["decision"] == "INCONCLUSIVE"
    rows, args = comparison_case(1000, .5, .5)
    assert fixed_horizon_decision(rows, **args)["decision"] == "EQUIVALENT"


def test_comparison_rejects_duplicate():
    rows, args = comparison_case(20, .5, .5)
    assert fixed_horizon_decision([*rows, rows[0]], **args)["decision"] == "INCONCLUSIVE"


def test_nsvee_refuses_empty_tests():
    from nsvee.engine import verify

    class NeverRun:
        def run(self, *_args):
            raise AssertionError("missing test must not execute candidate")

    assert verify("pass", [], runner=NeverRun()).status == "EXHAUSTED"



def test_admission_prefix_pending_then_red_blocks_green_tip():
    from greenlane.github import GitHubBackend

    base, prefix, tip = "a" * 40, "b" * 40, "c" * 40
    refs = {"main": base, "queue/b1": tip}
    grades = {tip: ("green", ""), prefix: ("pending", "waiting")}
    pushes = []

    class Backend:
        def _ref(self, name):
            return refs.get(name, "")

        def checks(self, sha):
            return grades[sha]

        def git(self, *args):
            pushes.append(args)
            sha, ref = args[-1].split(":")
            refs[ref.removeprefix("refs/heads/")] = sha

    backend = Backend()
    members = [("lane/a", "x", prefix), ("lane/b", "y", tip)]
    grade = GitHubBackend.admission_checks
    assert grade(backend, "b1", base, tip, members)[0] == "pending"
    assert len(pushes) == 1
    assert grade(backend, "b1", base, tip, members)[0] == "pending"
    assert len(pushes) == 1
    grades[prefix] = ("red", "test failure")
    assert grade(backend, "b1", base, tip, members)[0] == "red"
    grades[prefix] = ("green", "")
    assert grade(backend, "b1", base, tip, members)[0] == "green"
    refs["main"] = "d" * 40
    assert grade(backend, "b1", base, tip, members)[0] == "red"


def test_new_pr_is_refused_before_post_on_remote_base_change():
    from greenlane.github import GitHubBackend

    class Backend:
        owner = "owner"
        LAND_WAIT_S = 1

        def gh(self, path, *args):
            assert not args, "must not write to GitHub on stale base"
            return []

        def _proof_body(self, *args):
            return "proof"

        def main(self):
            return "a" * 40

        def _ref(self, name):
            return "b" * 40 if name == "lane/a" else "c" * 40

        def _await_green(self, *args):
            pass

    with pytest.raises(RuntimeError, match="changed under proof"):
        GitHubBackend._ensure_pr(Backend(), "lane/a", "x", "b" * 40, "b" * 40)
