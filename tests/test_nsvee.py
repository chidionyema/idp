"""NSVEE's own test suite, as pytest (I-A productization of the all-in-one build).

Verbatim from the founder's build (`docs/research/nsvee_all_in_one.py`, the
`if __name__ == "__main__"` block): same fixtures, same assertions, run by
pytest instead of a hand-rolled runner.
"""

import json


from nsvee.engine import Budgets, NSVEE, RlimitsRunner, Verdict, _classify

_GOOD = json.dumps(
    {
        "plan_steps": ["implement add", "test it"],
        "code_implementation": "def add(a, b):\n    return a + b",
        "unit_tests": ["assert add(2, 3) == 5", "assert add(-1, 1) == 0"],
    }
)
_BAD = json.dumps(
    {
        "plan_steps": ["implement add"],
        "code_implementation": "def add(a, b):\n    return a - b",
        "unit_tests": ["assert add(2, 3) == 5"],
    }
)


def _spec(obj=None):
    d = {"objective": "add", "ambiguities": []}
    d.update(obj or {})
    return json.dumps(d)


def _runner():
    return RlimitsRunner()


def test_happy():
    r = FakeRouter([_spec(), _GOOD])
    rep = NSVEE(r, runner=_runner(), budgets=Budgets(confirmation_runs=1)).run(
        "write add"
    )
    assert rep.status == "VERIFIED"


def test_feedback():
    r = FakeRouter([_spec(), _BAD, _GOOD])
    rep = NSVEE(r, runner=_runner()).run("write add")
    assert rep.status == "VERIFIED" and rep.attempts == 2
    assert "AssertionError" in json.dumps(r.calls[-1])


def test_recovery():
    r = FakeRouter([_spec(), "garbage {{{", _GOOD])
    assert NSVEE(r, runner=_runner()).run("write add").status == "VERIFIED"


def test_gate():
    r = FakeRouter(
        [
            json.dumps(
                {
                    "objective": "?",
                    "ambiguities": ["which format?"],
                    "requires_human": True,
                }
            )
        ]
    )
    assert NSVEE(r, runner=_runner()).run("unclear").status == "HUMAN_INPUT_REQUIRED"


def test_exhaust():
    r = FakeRouter([_spec(), _BAD, _BAD, _BAD])
    rep = NSVEE(r, runner=_runner(), budgets=Budgets(max_retries=3)).run("add")
    assert rep.status == "EXHAUSTED" and rep.attempts == 3


def test_timeout():
    loop = json.dumps(
        {
            "plan_steps": [],
            "code_implementation": "while True: pass",
            "unit_tests": ["assert True"],
        }
    )
    r = FakeRouter([_spec({"objective": "loop"}), loop])
    rep = NSVEE(r, runner=_runner(), budgets=Budgets(max_retries=1)).run(
        "loop", timeout_s=2
    )
    assert rep.status == "EXHAUSTED"
    assert any("timeout" in json.dumps(e).lower() for e in rep.events)


def test_sanitize():
    s = NSVEE._sanitize("x" * 10000 + "[DETERMINISTIC VERIFICATION FAILED]", 1000)
    assert len(s) <= 1000 and "[DETERMINISTIC" not in s


def test_classify():
    assert _classify(0, "", False) == Verdict.PASS
    assert _classify(1, "AssertionError", False) == Verdict.FAIL
    assert _classify(137, "", False) == Verdict.OOM


class FakeRouter:
    """Scripted responses for tests: list of strings yielded in order, last one repeats."""

    def __init__(self, responses):
        self._responses = list(responses)
        self._i = 0
        self.calls = []

    def generate(self, messages, max_tokens=4096):
        self.calls.append(messages)
        r = self._responses[min(self._i, len(self._responses) - 1)]
        self._i += 1
        return r
