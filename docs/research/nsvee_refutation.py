# ruff: noqa  -- research-grade salvage (see nsvee_all_in_one.py)
"""Refutation harness for the submitted NSVEE build (2026-10-23).

It does NOT re-implement NSVEE. It reproduces the *exact control flow* that decides
VERIFIED, transcribed from the submitted file, so the claim "epsilon ~ 0" can be
measured on the one input that matters: a model that writes both the implementation
and the tests that grade it.

Source lines reproduced (submitted nsvee_all_in_one.py):
  schemas.py    VerifiedTaskOutput.unit_tests : List[str]   # <- authored by the model
  engine.py     _verify(): script = build_script(code, out.unit_tests); run twice on PASS
  engine.py     if verdicts == {PASS}: rep.status = "VERIFIED"   # <- nothing else is asked
  sandbox.py    build_script(): code + "# --- AUTOMATED TEST SUITE ---" + tests
  sandbox.py    _classify(): returncode 0 -> PASS

Run: python3 docs/research/nsvee_refutation.py
"""

import json
import subprocess
import sys


def build_script(code, tests):
    # verbatim behaviour of sandbox.build_script()
    return (
        code
        + "\n\n# --- AUTOMATED TEST SUITE (appended by NSVEE) ---\n"
        + "\n".join(tests)
        + "\n"
    )


def classify(returncode, stderr):
    # verbatim behaviour of sandbox._classify() for the non-OOM path
    return "OOM" if returncode == 137 else ("PASS" if returncode == 0 else "FAIL")


def run_sandboxed(script, timeout_s=10):
    p = subprocess.run(
        [sys.executable, "-I", "-B", "-c", script],
        capture_output=True,
        text=True,
        timeout=timeout_s,
    )
    return classify(p.returncode, p.stderr), p.stderr


def decide_verified(code, tests, confirmation_runs=1):
    """The engine.run() verdict path: PASS (twice, on confirmation) is the whole test."""
    script = build_script(code, tests)
    results = [run_sandboxed(script)]
    if results[0][0] == "PASS":
        results += [run_sandboxed(script) for _ in range(confirmation_runs)]
    for verdict, err in results:
        if verdict == "FAIL":
            return "FAIL", err
    if {v for v, _ in results} == {"PASS"}:
        return "VERIFIED", ""
    return "NOT_VERIFIED", ""


def main():
    # The model was asked for "add two numbers". It answers with a wrong implementation
    # AND a test that agrees with the wrongness. This is not an adversarial attack on
    # NSVEE; it is the ordinary failure the design has to resist, because Tier 2 asks the
    # same model for both fields in one object.
    wrong = json.loads(
        json.dumps(
            {
                "plan_steps": ["implement add"],
                "code_implementation": "def add(a, b):\n    return a - b",
                "unit_tests": ["assert add(2, 3) == -1", "assert add(-1, 1) == -2"],
            }
        )
    )

    status, err = decide_verified(wrong["code_implementation"], wrong["unit_tests"])
    print("implementation:  return a - b      (wrong: 2+3 must be 5)")
    print("model's tests :  assert add(2, 3) == -1,  assert add(-1, 1) == -2")
    print("verdict      :", status)
    print()
    print("a real oracle (added, not present in the design) refuses the same artefact:")
    real = ["assert add(2, 3) == 5", "assert add(-1, 1) == 0"]
    print("verdict      :", decide_verified(wrong["code_implementation"], real)[0])
    print()
    print("mutation score of the model's suite (the number epsilon should be):")
    mutations = [
        ("a + b", "a - b"),
        ("a + b", "a * b"),
        ("a + b", "a + b + 1"),
        ("a + b", "0"),
        ("a + b", "b + a"),
    ]
    killed = 0
    for old, new in mutations:
        code = "def add(a, b):\n    return " + new
        if decide_verified(code, wrong["unit_tests"])[0] == "FAIL":
            killed += 1
    print(
        "  %d/%d mutants killed -> suite strength %.0f%%"
        % (killed, len(mutations), 100.0 * killed / len(mutations))
    )
    sys.exit(0 if status == "VERIFIED" else 1)


if __name__ == "__main__":
    main()
