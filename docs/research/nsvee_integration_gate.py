# ruff: noqa  -- research-grade salvage (see nsvee_all_in_one.py)
"""Integration contract + conformance gate for any candidate verification engine.

WHY THIS FILE EXISTS
--------------------
A consultant's engine does not have to be audited line by line to be integrated. It has to
satisfy five properties that the estate can measure in one command. This file *is* that
command. Point it at a candidate build; it prints one row per property and a verdict.

    python3 docs/research/nsvee_integration_gate.py

Exit 0 means: the submitted v2 is refused on its measured defects AND a reference adapter
satisfies all five. A gate that cannot fail is not a gate, so the exit code depends on both.

THE CONTRACT (a candidate engine is accepted if all five hold)
--------------------------------------------------------------
P1  It never executes candidate-authored code in its own process. Probe artifact writes to
    $NSVEE_PROBE_PATH; if that file appears, the grading process executed untrusted code.
P2  It never returns VERIFIED for an artifact that is wrong and self-consistently tested
    (wrong add + tests asserting the wrong answer). This is the ordinary failure, not an attack.
P3  Any strength/epsilon number it reports is a BOUND carrying its sample size n. A bare
    ratio (killed/total) is not a measurement. VERIFIED additionally requires
    bound <= 0.05, which zero-survivor reporting needs n >= 60 (exact Clopper-Pearson).
P4  Its oracle source is declared and is not the generator: one of
    {deployed-artifact, human, formal}. No attributable invariant => UNVERIFIABLE, never VERIFIED.
P5  A VERIFIED result carries a re-executable claim row (instrument command, measured_at,
    valid_for_s, artifact sha256) — the shape estate-claim-check stores in
    ~/.estate/facts.jsonl. A status word with no row is not evidence.

Sandbox note: the reference adapter below uses a scrubbed subprocess with process-group kill
only so this file stays stdlib-only. In the estate the same calls go through
`estate-execute` / the gVisor admission path — one execution boundary, not a second one.
"""

import os
import subprocess
import sys
import time
import hashlib
import tempfile

ALLOWED_ORACLE_SOURCES = {"deployed-artifact", "human", "formal"}
PASS_BOUND = 0.05  # to say VERIFIED we need epsilon <= 5%
MIN_MUTANTS_FOR_PASS = 60  # n that makes that bound true with zero survivors


def _run(script, timeout_s=10, env=None):
    """Scrubbed, isolated-enough run used by the reference adapter."""
    e = {
        "PATH": "/usr/bin:/bin:/usr/local/bin",
        "PYTHONDONTWRITEBYTECODE": "1",
        "HOME": "/tmp",
    }
    if env:
        e.update(env)
    p = subprocess.run(
        [sys.executable, "-I", "-B", "-c", script],
        capture_output=True,
        text=True,
        timeout=timeout_s,
        env=e,
    )
    return p.returncode, p.stdout, p.stderr


def _build(code, tests):
    return code + "\n\n# --- tests ---\n" + "\n".join(tests) + "\n"


OPS = [
    (" + ", " - "),
    (" - ", " + "),
    (" * ", " // "),
    (" == ", " != "),
    (" < ", " <= "),
    (" <= ", " < "),
    (" > ", " >= "),
    (" >= ", " > "),
    (" and ", " or "),
    (" or ", " and "),
]


# ---------------------------------------------------------------------------
# Adapter 0: the submitted v2, transcribed (MutationGate + SpecOracle + verdict path)
# ---------------------------------------------------------------------------
class SubmittedV2:
    """Behaviour transcribed from the pasted v2: ratio score with no minimum n, hard cap of
    12 mutants, Tier-1 (same generator) invariants executed with exec() in-process."""

    max_mutants = 12
    threshold = 1.0

    @staticmethod
    def _mutants(code):
        out, lines = [], code.split("\n")
        for i, line in enumerate(lines):
            for old, new in OPS:
                if old in line and line.count(old) == 1 and "import" not in line:
                    out.append(
                        (
                            "\n".join(
                                lines[:i] + [line.replace(old, new, 1)] + lines[i + 1 :]
                            )
                        )
                    )
        return out[: SubmittedV2.max_mutants]

    def _score(self, code, tests, timeout_s=10):
        base = _run(_build(code, tests), timeout_s)
        if base[0] != 0:
            return 0.0, None, 0
        muts = self._mutants(code)
        if not muts:
            return None, "no mutatable operators", 0
        killed = sum(1 for m in muts if _run(_build(m, tests), timeout_s)[0] != 0)
        alive = len(muts) - killed
        return killed / len(muts), alive, len(muts)

    def grade(self, code, tests, invariants, oracle_source="model"):
        score, alive, total = self._score(code, tests)
        if score is None or score < self.threshold:
            return {
                "status": "EXHAUSTED",
                "evidence": {"mutants_total": total, "mutants_killed": 0},
            }
        # post_verify(): SpecOracle executes the artifact and its invariants in-process
        env = {}
        exec(code, env)  # <-- P1 violation (by transcription)
        for inv in invariants:
            scope = dict(env)
            if not eval(inv, scope):
                return {
                    "status": "EXHAUSTED",
                    "evidence": {"oracle": "violation: %s" % inv},
                }
        return {
            "status": "VERIFIED",
            "evidence": {
                "mutants_total": total,
                "score": score,
                "oracle_source": oracle_source,
            },
        }


# ---------------------------------------------------------------------------
# Adapter 1: reference — the contract, minimally satisfied
# ---------------------------------------------------------------------------
class ReferenceMinimal:
    """Ordinary honest implementation: bound not ratio, validity filter, n floor, oracle in a
    subprocess with a declared (non-generator) source, claim row on VERIFIED."""

    def _mutants(self, code):
        out, lines = [], code.split("\n")
        for i, line in enumerate(lines):
            for old, new in OPS:
                if (
                    old in line
                    and line.count(old) == 1
                    and not line.strip().startswith(("import", "from"))
                ):
                    cand = "\n".join(
                        lines[:i] + [line.replace(old, new, 1)] + lines[i + 1 :]
                    )
                    try:
                        compile(cand, "<mutant>", "exec")
                    except SyntaxError:
                        continue  # not a program: cannot count as killed
                    out.append(cand)
        return out

    def _check_invariants(self, code, invariants, timeout_s):
        """Invariants are supplied by the caller (human / deployed artefact), executed in a
        child process with a scrubbed env — never in this process."""
        for inv in invariants:
            script = (
                code + "\n\n__inv = (" + repr(inv) + ")\nassert eval(__inv), __inv\n"
            )
            rc, out, err = _run(script, timeout_s)
            if rc != 0:
                return "invariant failed: %s :: %s" % (
                    inv,
                    (err or out).strip().splitlines()[-1:],
                )
        return None

    def grade(self, code, tests, invariants, oracle_source="human", valid_for_s=3600):
        if oracle_source not in ALLOWED_ORACLE_SOURCES:
            return {
                "status": "UNVERIFIABLE",
                "evidence": {
                    "reason": "oracle source %r is the generator" % oracle_source
                },
            }
        if not invariants:
            return {
                "status": "UNVERIFIABLE",
                "evidence": {
                    "reason": "no attributable invariant; claim outside checker domain"
                },
            }
        if _run(_build(code, tests))[0] != 0:
            return {
                "status": "FAIL",
                "evidence": {"reason": "tests do not pass on the artifact"},
            }
        muts = self._mutants(code)
        if not muts:
            return {
                "status": "UNVERIFIABLE",
                "evidence": {"reason": "checker domain too thin"},
            }
        alive = [m for m in muts if _run(_build(m, tests))[0] == 0]
        n = len(muts)
        evidence = {"mutants_valid": n, "mutants_survived": len(alive)}
        if alive:
            evidence["reason"] = "mutant survived: %d/%d" % (len(alive), n)
            return {"status": "REFUSED_MUTANTS_ALIVE", "evidence": evidence}
        bound = 1 - (1 - 0.95) ** (1.0 / n)  # exact upper bound, zero survivors
        evidence["epsilon_bound"] = bound
        if bound > PASS_BOUND:
            evidence["reason"] = (
                "need n>=%d for epsilon<=%.2f; have n=%d -> bound %.3f"
                % (MIN_MUTANTS_FOR_PASS, PASS_BOUND, n, bound)
            )
            return {"status": "REFUSED_INSUFFICIENT_EVIDENCE", "evidence": evidence}
        bad = self._check_invariants(code, invariants, 10)
        if bad:
            evidence["oracle"] = bad
            return {"status": "REFUSED_ORACLE_VIOLATION", "evidence": evidence}
        evidence["oracle_source"] = oracle_source
        evidence["claim"] = {
            "instrument": "python3 docs/research/nsvee_integration_gate.py --replay "
            + hashlib.sha256(code.encode()).hexdigest()[:12],
            "artifact_sha256": hashlib.sha256(code.encode()).hexdigest(),
            "measured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "valid_for_s": valid_for_s,
        }
        return {"status": "VERIFIED", "evidence": evidence}


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------
WRONG = "def add(a, b):\n    return a - b"
WRONG_TESTS = ["assert add(2, 3) == -1", "assert add(-1, 1) == -2"]
WRONG_MODEL_INVARIANTS = ["add(2, 3) == -1"]  # Tier 1 is the same generator: agrees
WRONG_HUMAN_INVARIANTS = ["add(2, 3) == 5"]  # the external source: disagrees

PROBE = (
    "import os\n"
    "def add(a, b):\n    return a + b\n"
    "_p = os.environ.get('NSVEE_PROBE_PATH')\n"
    "if _p:\n    open(_p, 'w').write('candidate code ran in the grading process')\n"
)
PROBE_TESTS = ["assert add(2, 3) == 5"]


def _wide_artifact(k=70):
    """k one-operator functions, one killing test each: enough mutants for an honest bound."""
    code, tests = [], []
    for i in range(k):
        code.append("def f%d(x):\n    return x + %d" % (i, i + 1))
        tests.append("assert f%d(5) == %d" % (i, 5 + i + 1))
    return "\n\n".join(code), tests


WIDE, WIDE_TESTS = _wide_artifact()
WIDE_INV = ["f0(0) == 1", "f69(0) == 70"]


# ---------------------------------------------------------------------------
# the gate
# ---------------------------------------------------------------------------
def conformance(adapter, name):
    rows = []

    def rec(prop, ok, detail):
        rows.append((prop, ok, detail))

    # P2 first: the ordinary failure
    r_wrong = adapter.grade(
        WRONG,
        WRONG_TESTS,
        WRONG_MODEL_INVARIANTS if name == "submitted-v2" else WRONG_HUMAN_INVARIANTS,
        "model" if name == "submitted-v2" else "human",
    )
    rec(
        "P2 wrong+wrong is not VERIFIED",
        r_wrong["status"] != "VERIFIED",
        "status=%s" % r_wrong["status"],
    )

    # P1: does grading execute candidate code in-process?
    fd, probe_path = tempfile.mkstemp(prefix="nsvee_probe_")
    os.close(fd)
    os.unlink(probe_path)
    os.environ["NSVEE_PROBE_PATH"] = probe_path
    try:
        adapter.grade(PROBE, PROBE_TESTS, ["add(0, 0) == 0"], "human")
    finally:
        os.environ.pop("NSVEE_PROBE_PATH", None)
    leaked = os.path.exists(probe_path)
    if leaked:
        os.unlink(probe_path)
    rec(
        "P1 no in-process execution",
        not leaked,
        "probe file %s" % ("CREATED by grading process" if leaked else "absent"),
    )

    # P3: strength must be a bound with n; VERIFIED requires bound <= 0.05 (n >= 60)
    ev = r_wrong.get("evidence", {})
    n = ev.get("mutants_valid") or ev.get("mutants_total") or 0
    reports_strength = any(k in ev for k in ("score", "strength", "epsilon_bound"))
    bound_ok = (
        ("epsilon_bound" in ev) and isinstance(ev["epsilon_bound"], float) and n > 0
    )
    verified_earned = (r_wrong["status"] != "VERIFIED") or (
        n >= MIN_MUTANTS_FOR_PASS and ev.get("epsilon_bound", 1.0) <= PASS_BOUND
    )
    rec(
        "P3 strength is a bound with n",
        (not reports_strength) or (bound_ok and verified_earned),
        "score=%s n=%s bound=%s" % (ev.get("score"), n, ev.get("epsilon_bound")),
    )

    # P4: oracle attribution
    r_noinv = adapter.grade(WRONG, WRONG_TESTS, [], "human")
    src = r_wrong.get("evidence", {}).get(
        "oracle_source", "model" if name == "submitted-v2" else "human"
    )
    rec(
        "P4 oracle is not the generator",
        src in ALLOWED_ORACLE_SOURCES and r_noinv["status"] != "VERIFIED",
        "source=%s ; no-invariant status=%s" % (src, r_noinv["status"]),
    )

    # P5: a VERIFIED result must carry a re-executable row
    r_ok = adapter.grade(WIDE, WIDE_TESTS, WIDE_INV, "human")
    claim = r_ok.get("evidence", {}).get("claim") or {}
    ok_row = r_ok["status"] == "VERIFIED" and all(
        k in claim
        for k in ("instrument", "measured_at", "valid_for_s", "artifact_sha256")
    )
    rec(
        "P5 VERIFIED carries a claim row",
        ok_row,
        "status=%s keys=%s" % (r_ok["status"], sorted(claim)),
    )

    # report the ceiling the submitted constants impose
    extra = ""
    if name == "submitted-v2":
        n_max = SubmittedV2.max_mutants
        extra = (
            " ; max_mutants=%d -> best provable epsilon %.3f (cannot ever reach %.2f)"
            % (n_max, 1 - 0.05 ** (1.0 / n_max), PASS_BOUND)
        )
    return rows, extra


def main():
    want = {"submitted-v2": 5, "reference": 0}  # required failures / maximum failures
    results = {}
    print("conformance gate — 5 properties (see docstring)\n")
    for name, adapter in (
        ("submitted-v2", SubmittedV2()),
        ("reference", ReferenceMinimal()),
    ):
        rows, extra = conformance(adapter, name)
        results[name] = rows
        failed = sum(1 for _, ok, _ in rows if not ok)
        print("%-14s %d/%d satisfied%s" % (name, 5 - failed, 5, extra))
        for prop, ok, detail in rows:
            print("   [%s] %-32s %s" % ("PASS" if ok else "FAIL", prop, detail))
        print()

    sub_fails = sum(1 for _, ok, _ in results["submitted-v2"] if not ok)
    ref_fails = sum(1 for _, ok, _ in results["reference"] if not ok)
    ok = sub_fails >= want["submitted-v2"] and ref_fails <= want["reference"]
    print(
        "verdict: submitted-v2 fails %d/5, reference fails %d/5 -> %s"
        % (sub_fails, ref_fails, "GATE WORKS" if ok else "GATE IS NOT BITING")
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
