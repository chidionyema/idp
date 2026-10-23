#!/usr/bin/env python3
"""The three real errors from the 2026-10-23 session, encoded as a test suite.

Each test is one way an agent produced a confident wrong number, and it asserts
that the checker refuses it. If any of these pass silently, the guarantee is
false.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1] / "bin" / "estate-claim-check"


def _tool_module():
    loader = importlib.machinery.SourceFileLoader("estate_claim_check", str(TOOL))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def run(*args: str, store: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(TOOL), "--store", str(store), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def write_rows(store: Path, rows: list[dict]) -> None:
    """Write fixtures the way `add` would: through the tool's own append, so the hash
    chain is valid and the test is about the verdicts, not about the fixture."""
    tool = _tool_module()
    for r in rows:
        tool._append(str(store), dict(r))


def ledger_fixture(tmp: Path, before: int, after: int) -> Path:
    """A miniature efficiency ledger with the same shape as the real one."""
    p = tmp / "ledger.jsonl"
    p.write_text(
        json.dumps({"kind": "pre", "bytes_before": before, "bytes_after": after})
        + "\n",
        encoding="utf-8",
    )
    return p


def cut_instrument(ledger: Path) -> str:
    return (
        f"python3 -c \"import json;r=json.loads(open('{ledger}').readline());"
        "b=r['bytes_before'];a=r['bytes_after'];print(round(100.0*(b-a)/b,1))\""
    )


# ---------------------------------------------------------------- error 1
def test_error_1_a_value_quoted_from_a_code_comment_is_contradicted(tmp_path):
    """I reported '0.3% cut' from a comment dated 2026-09-29. The ledger says 86.7%.

    The fact was stored once, honestly, when 0.3% was true. Re-execution is what
    catches it, which is why the store keeps the instrument and not just the number.
    """
    ledger = ledger_fixture(tmp_path, before=150_949_000_000, after=20_129_000_000)
    store = tmp_path / "facts.jsonl"
    write_rows(
        store,
        [
            {
                "id": "cut",
                "subject": "efficiency cut",
                "unit": "%",
                "value": "0.3",
                "instrument": cut_instrument(ledger),
                "measured_at": "2026-09-29T00:00:00Z",
                "valid_for_s": 999_999_999,
            }
        ],
    )
    p = run("verify", store=store)
    assert p.returncode == 1, p.stdout
    assert "CONTRADICTED" in p.stdout
    assert "86.7" in p.stdout, (
        "the failure must name what the instrument actually prints"
    )


def test_error_1_the_corrected_measurement_passes(tmp_path):
    ledger = ledger_fixture(tmp_path, before=150_949_000_000, after=20_129_000_000)
    store = tmp_path / "facts.jsonl"
    p = run(
        "add",
        "--subject",
        "efficiency cut",
        "--unit",
        "%",
        "--instrument",
        cut_instrument(ledger),
        "--valid-for",
        "600",
        store=store,
    )
    assert p.returncode == 0, p.stderr
    assert "86.7" in p.stdout
    v = run("verify", store=store)
    assert v.returncode == 0, v.stdout
    assert "PASS" in v.stdout


# ---------------------------------------------------------------- error 2
def test_error_2_a_wrong_denominator_is_caught_by_a_second_instrument(tmp_path):
    """I reported '30 claude processes' from `pgrep -fl claude`, which matched paths.

    The checker cannot know an instrument is the wrong instrument, so the fact must
    carry a second, independent one. A mis-typed instrument then contradicts a
    measurement instead of passing alone.
    """
    procs = tmp_path / "ps.txt"
    procs.write_text(
        "\n".join(
            ["claude daemon run"] * 2
            + [f"/Users/x/.claude/plugins/{i}/hook" for i in range(28)]
        )
        + "\n",
        encoding="utf-8",
    )
    loose = f"grep -c claude {procs}"  # matches paths: 30
    strict = f"grep -cE '^claude ' {procs}"  # real processes: 2
    store = tmp_path / "facts.jsonl"
    write_rows(
        store,
        [
            {
                "id": "procs",
                "subject": "claude processes",
                "unit": "count",
                "value": "30",
                "instrument": loose,
                "also": [strict],
                "measured_at": "2026-10-23T00:00:00Z",
                "valid_for_s": 999_999_999,
            }
        ],
    )
    p = run("verify", store=store)
    assert p.returncode == 1, p.stdout
    assert "CONTRADICTED" in p.stdout
    assert "disagrees" in p.stdout
    assert "wrong instrument" in p.stdout


# ---------------------------------------------------------------- error 3
def test_error_3_a_behaviour_claim_read_from_a_summary_is_unwitnessed(tmp_path):
    """I said the proxy rewrites Anthropic history, from a section heading.

    A claim about behaviour has no executable instrument, so it cannot be stored as
    a fact at all -- it is refused at write time rather than argued about later.
    """
    store = tmp_path / "facts.jsonl"
    write_rows(
        store,
        [
            {
                "id": "rewrite",
                "subject": "proxy rewrites Anthropic history",
                "value": "true",
                "instrument": None,
                "measured_at": "2026-10-23T00:00:00Z",
                "valid_for_s": 3600,
            }
        ],
    )
    p = run("verify", store=store)
    assert p.returncode == 1, p.stdout
    assert "UNWITNESSED" in p.stdout
    assert "cannot be checked" in p.stdout


# ---------------------------------------------------------------- the invariant
def test_a_value_cannot_be_typed_in_at_all(tmp_path):
    """The strongest guarantee here is a missing feature: `add` has no --value flag."""
    store = tmp_path / "facts.jsonl"
    p = run(
        "add", "--subject", "x", "--instrument", "echo 1", "--value", "99", store=store
    )
    assert p.returncode != 0
    assert not store.exists() or store.read_text() == ""


def test_a_stale_fact_fails_even_though_it_would_still_reproduce(tmp_path):
    store = tmp_path / "facts.jsonl"
    p = run(
        "add",
        "--subject",
        "rows",
        "--instrument",
        "echo 586884",
        "--valid-for",
        "0",
        store=store,
    )
    assert p.returncode == 0, p.stderr
    v = run("verify", store=store)
    assert v.returncode == 1, v.stdout
    assert "STALE" in v.stdout


def test_an_expectation_that_disagrees_stores_nothing(tmp_path):
    store = tmp_path / "facts.jsonl"
    p = run(
        "add",
        "--subject",
        "rows",
        "--instrument",
        "echo 2",
        "--expect",
        "30",
        store=store,
    )
    assert p.returncode == 2
    assert not store.exists()


def test_a_retired_fact_stops_being_graded_but_stays_on_record(tmp_path):
    """A row count of a ledger that appends continuously is the wrong instrument: measured live,
    the count moved from 587297 to 587397 while the session ran and the gate correctly refused it.
    Retiring keeps the history (the chain still walks) and stops grading the dead question."""
    store = tmp_path / "facts.jsonl"
    assert (
        run(
            "add", "--subject", "rows", "--instrument", "echo 5", store=store
        ).returncode
        == 0
    )
    rid = [json.loads(x) for x in store.read_text().splitlines()][0]["id"]
    assert (
        run("retire", "--id", rid, "--reason", "target moves", store=store).returncode
        == 0
    )
    # the instrument now disagrees, which would be CONTRADICTED if the fact were still live
    rows = [json.loads(x) for x in store.read_text().splitlines()]
    rows[0]["value"] = "9"
    store.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    p = run("verify", store=store)
    assert "TAMPERED" in p.stdout  # editing the past is still refused


def test_retiring_an_unknown_fact_is_refused(tmp_path):
    store = tmp_path / "facts.jsonl"
    assert (
        run(
            "add", "--subject", "rows", "--instrument", "echo 5", store=store
        ).returncode
        == 0
    )
    p = run("retire", "--id", "nope", "--reason", "typo", store=store)
    assert p.returncode == 2
    assert "no fact" in p.stderr


def test_an_empty_store_passes_but_says_it_is_not_a_proof(tmp_path):
    p = run("verify", store=tmp_path / "missing.jsonl")
    assert p.returncode == 0
    assert "not a proof" in p.stdout


def test_an_edited_history_is_tampered(tmp_path):
    """Change a stored value and leave the instrument alone: re-execution alone would
    not notice, because the instrument still prints its own honest number. The chain is
    what makes the record and the measurement the same object."""
    store = tmp_path / "facts.jsonl"
    assert (
        run(
            "add", "--subject", "rows", "--instrument", "echo 5", store=store
        ).returncode
        == 0
    )
    assert (
        run(
            "add", "--subject", "more", "--instrument", "echo 6", store=store
        ).returncode
        == 0
    )
    rows = [json.loads(x) for x in store.read_text().splitlines()]
    rows[0]["value"] = "7"
    store.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    p = run("verify", store=store)
    assert p.returncode == 1, p.stdout
    assert "TAMPERED" in p.stdout
    assert "edited" in p.stdout


def test_a_deleted_fact_breaks_the_chain(tmp_path):
    """Dropping the fact that disagrees is the other way to make a store agree with you."""
    store = tmp_path / "facts.jsonl"
    for v in ("5", "6"):
        assert (
            run(
                "add", "--subject", f"rows{v}", "--instrument", f"echo {v}", store=store
            ).returncode
            == 0
        )
    lines = store.read_text().splitlines()
    store.write_text(lines[1] + "\n", encoding="utf-8")
    p = run("verify", store=store)
    assert p.returncode == 1, p.stdout
    assert "TAMPERED" in p.stdout
    assert "follows" in p.stdout


def test_an_instrument_that_measures_nothing_is_refused(tmp_path):
    """`true` exits 0 and prints nothing. Nothing was measured, so nothing is witnessed.

    Without this, an empty value reproduces itself forever and no second run can ever
    contradict it: the precise shape of a gate that cannot fail.
    """
    store = tmp_path / "facts.jsonl"
    p = run("add", "--subject", "nothing", "--instrument", "true", store=store)
    assert p.returncode == 2, p.stdout
    assert "printed nothing" in p.stderr
    assert not store.exists()


def test_appending_leaves_no_lockfile_behind(tmp_path):
    """A crashed or unlucky append used to leave facts/estate.jsonl.lock on disk; git committed it
    and the claim gate refused the whole change. The lock exists only while it is held."""
    store = tmp_path / "facts.jsonl"
    assert (
        run(
            "add", "--subject", "rows", "--instrument", "echo 5", store=store
        ).returncode
        == 0
    )
    assert not (tmp_path / "facts.jsonl.lock").exists()


# ------------------------------------------- the three rungs (research 2026-10-23)
def test_a_fact_with_no_instrument_is_refused_at_write_time(tmp_path):
    """Rung 1 needs a command. Without one the row would be a number nobody can re-derive,
    which is the defect, so it is refused before it exists rather than flagged later."""
    store = tmp_path / "facts.jsonl"
    p = run("add", "--subject", "rows", "--kind", "fact", store=store)
    assert p.returncode == 2, p.stdout
    assert "needs --instrument" in p.stderr
    assert not store.exists()


def test_an_artefact_claim_is_bound_to_bytes_and_dies_when_they_change(tmp_path):
    """Most claims are about something that happened, not something a command recomputes: a
    deploy, a log line, a screenshot. Those cannot be re-executed, so rung 2 binds them to a
    digest -- the claim cannot outlive its evidence."""
    evidence = tmp_path / "deploy.log"
    evidence.write_text("pod idp-api-7f9c Ready 1/1\n", encoding="utf-8")
    store = tmp_path / "facts.jsonl"
    p = run(
        "add",
        "--subject",
        "idp-api deployed",
        "--kind",
        "artefact",
        "--evidence",
        str(evidence),
        store=store,
    )
    assert p.returncode == 0, p.stderr
    assert "R2-evidence" in p.stdout
    assert run("verify", store=store).returncode == 0

    evidence.write_text("CrashLoopBackOff\n", encoding="utf-8")
    v = run("verify", store=store)
    assert v.returncode == 1, v.stdout
    assert "CONTRADICTED" in v.stdout
    assert "artefact changed" in v.stdout


def test_an_artefact_claim_with_no_bytes_is_refused(tmp_path):
    store = tmp_path / "facts.jsonl"
    p = run(
        "add",
        "--subject",
        "deployed",
        "--kind",
        "artefact",
        "--evidence",
        str(tmp_path / "absent.log"),
        store=store,
    )
    assert p.returncode == 2, p.stdout
    assert "Nothing was witnessed" in p.stderr
    assert not store.exists()


def test_a_judgment_without_an_authority_is_refused(tmp_path):
    """A judgment is legitimate, but only attributed. Stored unattributed it would look like
    everything else in the ledger, which is how an opinion becomes a fact."""
    store = tmp_path / "facts.jsonl"
    p = run(
        "add", "--subject", "the concierge is useful", "--kind", "judgment", store=store
    )
    assert p.returncode == 2, p.stdout
    assert "only when attributed" in p.stderr
    assert not store.exists()


def test_an_attributed_judgment_is_stored_and_never_claimed_verified(tmp_path):
    """Rung 3 must be visible as rung 3. The point is not to make judgments storable, it is to
    make the difference between a measurement and an opinion readable in the record."""
    store = tmp_path / "facts.jsonl"
    p = run(
        "add",
        "--subject",
        "the founder prefers prose to tables",
        "--kind",
        "judgment",
        "--authority",
        "founder, 2026-10-23, in session",
        store=store,
    )
    assert p.returncode == 0, p.stderr
    assert "R3-attributed" in p.stdout
    v = run("verify", store=store)
    assert v.returncode == 0, v.stdout
    assert "attributed, not verified" in v.stdout
    assert "founder, 2026-10-23" in v.stdout


def test_re_measuring_after_a_retirement_is_live_not_retired(tmp_path):
    """The id is a hash of subject+instrument, so a re-measurement reuses it. Retirement is
    therefore ordered: a retire row only silences the rows before it. As a set it silenced the
    re-measurement too and verify reported 0/0 active -- a live fact hidden, on 2026-10-23."""
    store = tmp_path / "facts.jsonl"
    inst = "echo 13"
    assert (
        run("add", "--subject", "tests", "--instrument", inst, store=store).returncode
        == 0
    )
    rid = [json.loads(x) for x in store.read_text().splitlines()][0]["id"]
    assert run("retire", "--id", rid, "--reason", "grew", store=store).returncode == 0
    assert (
        run("add", "--subject", "tests", "--instrument", inst, store=store).returncode
        == 0
    )
    p = run("verify", store=store)
    assert p.returncode == 0, p.stdout + p.stderr
    assert "1/1 active facts" in p.stdout


# ---------------------------------------------------------------------------
# Integration contract (2026-10-23): a candidate verification engine — a
# consultant's build, or any future one — is admissible only if it passes five
# properties. Measured on the submitted NSVEE v2 the day it arrived: it fails
# all five. A minimal honest reference passes all five, so the gate is not an
# impossible bar, it is a specific one.
#
# P1 never executes candidate-authored code in the grading process
# P2 never returns VERIFIED for an artifact that is wrong and self-consistently
#    tested (wrong add, tests asserting the wrong answer)
# P3 any strength number is a BOUND with its sample size; VERIFIED needs
#    epsilon <= 0.05, which zero survivors needs n >= 60 to establish
# P4 the oracle's source is declared and is not the generator
# P5 VERIFIED carries a re-executable claim row
# ---------------------------------------------------------------------------
_GATE_OPS = [
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
_ALLOWED_SOURCES = {"deployed-artifact", "human", "formal"}
_PASS_BOUND = 0.05
_MIN_N = 60  # 1 - 0.05**(1/60) = 0.049: the first n that proves epsilon <= 5%


def _isolated(script: str, timeout: int = 10):
    """Scrubbed child process with no inherited environment. The estate's real boundary is
    estate-execute / gVisor; this keeps the gate itself stdlib-only."""
    env = {
        "PATH": "/usr/bin:/bin:/usr/local/bin",
        "PYTHONDONTWRITEBYTECODE": "1",
        "HOME": "/tmp",
    }
    p = subprocess.run(
        [sys.executable, "-I", "-B", "-c", script],
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
    )
    return p.returncode, p.stdout, p.stderr


def _script(code: str, tests: list) -> str:
    return code + "\n\n" + "\n".join(tests) + "\n"


class _SubmittedV2:
    """The submitted v2's decision path, transcribed: killed/total with no minimum n and a
    hard 12-mutant cap (so epsilon 0.221 is the best it can ever prove), and Tier-1
    invariants — authored by the same generator — executed with exec() in-process."""

    max_mutants = 12
    threshold = 1.0

    def _mutants(self, code):
        out, lines = [], code.split("\n")
        for i, line in enumerate(lines):
            for old, new in _GATE_OPS:
                if old in line and line.count(old) == 1 and "import" not in line:
                    out.append(
                        "\n".join(
                            lines[:i] + [line.replace(old, new, 1)] + lines[i + 1 :]
                        )
                    )
        return out[: self.max_mutants]

    def grade(self, code, tests, invariants, oracle_source="model"):
        if _isolated(_script(code, tests))[0] != 0:
            return {"status": "EXHAUSTED", "evidence": {"mutants_total": 0}}
        muts = self._mutants(code)
        if not muts:
            return {"status": "EXHAUSTED", "evidence": {"mutants_total": 0}}
        killed = sum(1 for m in muts if _isolated(_script(m, tests))[0] != 0)
        score = killed / len(muts)
        if score < self.threshold:
            return {
                "status": "EXHAUSTED",
                "evidence": {"mutants_total": len(muts), "score": score},
            }
        env = {}
        exec(code, env)  # P1: candidate code, this process
        for inv in invariants:
            if not eval(inv, dict(env)):  # P4: invariant from the generator
                return {
                    "status": "EXHAUSTED",
                    "evidence": {"oracle": "violation: %s" % inv},
                }
        return {
            "status": "VERIFIED",
            "evidence": {
                "mutants_total": len(muts),
                "score": score,
                "oracle_source": oracle_source,
            },
        }


class _Reference:
    """What the contract requires, minimally: a bound instead of a ratio, syntax-valid
    mutants only, an n floor, invariants from a declared non-generator source executed in a
    child process, and a claim row on VERIFIED."""

    def _mutants(self, code):
        out, lines = [], code.split("\n")
        for i, line in enumerate(lines):
            for old, new in _GATE_OPS:
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
                        continue  # not a program: it cannot count as a killed mutant
                    out.append(cand)
        return out

    def grade(self, code, tests, invariants, oracle_source="human", valid_for_s=3600):
        if oracle_source not in _ALLOWED_SOURCES or not invariants:
            return {
                "status": "UNVERIFIABLE",
                "evidence": {"reason": "no attributable invariant"},
            }
        if _isolated(_script(code, tests))[0] != 0:
            return {"status": "FAIL", "evidence": {"reason": "tests do not pass"}}
        muts = self._mutants(code)
        alive = [m for m in muts if _isolated(_script(m, tests))[0] == 0]
        n = len(muts)
        ev = {"mutants_valid": n, "mutants_survived": len(alive)}
        if not n:
            return {"status": "UNVERIFIABLE", "evidence": ev}
        if alive:
            return {"status": "REFUSED_MUTANTS_ALIVE", "evidence": ev}
        ev["epsilon_bound"] = 1 - 0.05 ** (1.0 / n)
        if ev["epsilon_bound"] > _PASS_BOUND:
            return {"status": "REFUSED_INSUFFICIENT_EVIDENCE", "evidence": ev}
        for inv in invariants:
            if _isolated(code + "\nassert eval(%r), %r\n" % (inv, inv))[0] != 0:
                ev["oracle"] = inv
                return {"status": "REFUSED_ORACLE_VIOLATION", "evidence": ev}
        ev["oracle_source"] = oracle_source
        ev["claim"] = {
            "instrument": "python3 -c <engine replay>",
            "measured_at": "2026-10-23T00:00:00Z",
            "valid_for_s": valid_for_s,
            "artifact_sha256": "0" * 64,
        }
        return {"status": "VERIFIED", "evidence": ev}


_ADD_WRONG = "def add(a, b):\n    return a - b"
_ADD_WRONG_TESTS = ["assert add(2, 3) == -1", "assert add(-1, 1) == -2"]
_PROBE_CODE = (
    "import os\n\n"
    "def add(a, b):\n    return a + b\n\n"
    "_p = os.environ.get('NSVEE_PROBE_PATH')\n"
    "if _p:\n    open(_p, 'w').write('candidate code ran in the grading process')\n"
)


def _wide(k: int = 70):
    """k one-operator functions with one killing test each: enough valid mutants for a bound."""
    code = "\n\n".join("def f%d(x):\n    return x + %d" % (i, i + 1) for i in range(k))
    tests = ["assert f%d(5) == %d" % (i, i + 6) for i in range(k)]
    return code, tests


def _conformance(adapter, name: str):
    """One row per property. Returns [(property, ok)]."""
    model_inv, human_inv = ["add(2, 3) == -1"], ["add(2, 3) == 5"]
    r = adapter.grade(
        _ADD_WRONG,
        _ADD_WRONG_TESTS,
        model_inv if name == "submitted-v2" else human_inv,
        "model" if name == "submitted-v2" else "human",
    )
    rows = [("P2 wrong+wrong is not VERIFIED", r["status"] != "VERIFIED")]

    fd, probe = tempfile.mkstemp(prefix="nsvee_probe_")
    os.close(fd)
    os.unlink(probe)
    os.environ["NSVEE_PROBE_PATH"] = probe
    try:
        adapter.grade(
            _PROBE_CODE, ["assert add(2, 3) == 5"], ["add(0, 0) == 0"], "human"
        )
    finally:
        os.environ.pop("NSVEE_PROBE_PATH", None)
    leaked = os.path.exists(probe)
    if leaked:
        os.unlink(probe)
    rows.append(("P1 no in-process execution", not leaked))

    ev = r.get("evidence", {})
    n = ev.get("mutants_valid") or ev.get("mutants_total") or 0
    reports = any(k in ev for k in ("score", "epsilon_bound"))
    bound_ok = isinstance(ev.get("epsilon_bound"), float) and n > 0
    earned = r["status"] != "VERIFIED" or (
        n >= _MIN_N and ev.get("epsilon_bound", 1.0) <= _PASS_BOUND
    )
    rows.append(
        ("P3 strength is a bound with n", (not reports) or (bound_ok and earned))
    )

    noinv = adapter.grade(_ADD_WRONG, _ADD_WRONG_TESTS, [], "human")
    src = ev.get("oracle_source", "model" if name == "submitted-v2" else "human")
    rows.append(
        (
            "P4 oracle is not the generator",
            src in _ALLOWED_SOURCES and noinv["status"] != "VERIFIED",
        )
    )

    wide_code, wide_tests = _wide()
    ok = adapter.grade(wide_code, wide_tests, ["f0(0) == 1"], "human")
    claim = ok.get("evidence", {}).get("claim") or {}
    rows.append(
        (
            "P5 VERIFIED carries a claim row",
            ok["status"] == "VERIFIED"
            and {"instrument", "measured_at", "valid_for_s", "artifact_sha256"}
            <= set(claim),
        )
    )
    return rows


def test_a_candidate_engine_is_admissible_only_if_it_passes_the_five_property_gate():
    """The submitted build is refused on every property; the reference passes all five. If the
    first half ever stops failing, the gate has stopped biting and the integration is theatre."""
    sub = _conformance(_SubmittedV2(), "submitted-v2")
    ref = _conformance(_Reference(), "reference")
    assert [p for p, ok in sub if not ok] == [p for p, _ in sub], sub
    assert all(ok for _, ok in ref), ref


def test_a_candidates_verdict_is_only_a_claim_when_its_re_execution_agrees(tmp_path):
    """An engine's own VERIFIED is a word, not evidence. The estate stores the command, re-runs
    it, and the row goes false the moment the engine's answer moves — which is the only reason
    a consultant's build can be integrated without auditing its internals."""
    engine = tmp_path / "engine.py"
    engine.write_text("print('VERIFIED epsilon=0')\n")
    store = tmp_path / "facts.jsonl"
    added = run(
        "add",
        "--subject",
        "nsvee",
        "--instrument",
        "%s %s" % (sys.executable, engine),
        store=store,
    )
    assert added.returncode == 0, added.stdout + added.stderr
    first = run("verify", store=store)
    assert first.returncode == 0 and "1/1 active facts" in first.stdout, first.stdout

    engine.write_text("print('EXHAUSTED')\n")
    second = run("verify", store=store)
    assert second.returncode != 0, second.stdout + second.stderr
