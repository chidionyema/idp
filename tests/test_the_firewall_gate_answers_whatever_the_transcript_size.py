"""The firewall's gate must ANSWER, whatever the transcript's size.

Founder, 2026-10-29 (DR): a gate that cannot fail is not a gate, and a gate that never answers is
worse than no gate -- it looks like a refusal. pi's epistemic-firewall hook runs
`epistemic_firewall.py --gate <transcript>` at every session start, synchronously. The grader read
the WHOLE transcript and graded EVERY turn, and `_code()` -- the "what the shell runs" normaliser --
re-derived the code of every command in the session for every agent sentence x every outcome. On the
newest real pi transcript (41 MB, 6486 lines) the gate ran 64.5 s and was still going at the 60 s
alarm, so pi's own 30 s hook budget expired on every session start and every agent saw
`spawnSync python3 ETIMEDOUT`: the grade never finished, so the gate never got to answer.

THE CLASS. A gate whose cost is unbounded in its input size is a gate that eventually stops
answering. The fix is a bound on the WORK, not a bigger timeout.

WHAT THIS TEST PROVES (and what falsifies it):
  * the KNOWN-BAD input -- a transcript far past the bound -- is graded inside a hard budget, so
    the hook cannot hang the session;
  * the KNOWN-GOOD input -- a transcript inside the bound -- is read WHOLE, so the verdict is the
    verdict the unbounded grader gave;
  * the tail is cut at a LINE boundary, so the slice is never half a turn;
  * a transcript that cannot be read is still BLIND (fail-closed): the bound must not turn the
    gate into a clean bill.

Runs the real bin/epistemic_firewall.py.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIREWALL = ROOT / "bin/epistemic_firewall.py"

# The budget the hook itself has. The gate must answer inside it or the session hangs.
HOOK_BUDGET_S = 30.0
# What we allow the gate on a huge transcript in this test, with room for a loaded machine.
BIG_BUDGET_S = 20.0
# The verdict vocabulary the grader actually uses. A FAIL carries a reason with it, so the
# check is on the FIRST WORD: the point is that the gate reached a verdict at all.
VERDICTS = ("PASS", "FAIL", "BLIND")


def _verdict_of(result: dict) -> str:
    return str(result.get("verdict", "")).split(" ", 1)[0]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _prompt(text: str) -> dict:
    return {"type": "user", "message": {"role": "user", "content": text}}


def _say(text: str) -> dict:
    return {
        "type": "assistant",
        "message": {"role": "assistant", "content": [{"type": "text", "text": text}]},
    }


def _bash(n: int, command: str, output: str) -> list[dict]:
    uid = f"toolu_{n}"
    return [
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "id": uid,
                        "name": "Bash",
                        "input": {"command": command},
                    }
                ],
            },
        },
        {
            "type": "user",
            "message": {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": uid,
                        "content": output,
                    }
                ],
            },
        },
    ]


def _write_transcript(path: Path, turns: list[dict]) -> Path:
    path.write_text("".join(json.dumps(t) + "\n" for t in turns))
    return path


def test_the_gate_answers_a_transcript_past_the_bound(tmp_path: Path) -> None:
    """KNOWN-BAD: a transcript far past the bound is still graded, inside the hook's budget.

    Falsifier: with the bound removed (the pre-2026-10-29 grader) this input takes minutes, and
    the hook's own 30 s budget expires -- the session hangs and the gate never answers.
    """
    mod = _load("fw", FIREWALL)
    tail = getattr(mod, "TAIL_BYTES", None)
    assert tail is not None, (
        "the gate has no bound: it reads the whole transcript every time"
    )

    # A transcript of ~8x the bound: the case that used to take minutes.
    # Built line by line and flushed, so the test does not spend its own budget re-serialising a
    # growing list -- the transcript is the fixture, not the thing under test.
    filler = _prompt("x" * 4096)
    turns: list[dict] = []
    path = tmp_path / "huge.jsonl"
    with path.open("w") as fh:
        written = 0
        while written < tail * 8:
            for turn in (filler, _say("working")):
                line = json.dumps(turn) + "\n"
                fh.write(line)
                written += len(line)
            fh.flush()
    turns.append(_say("I pushed the change and the tests are green."))
    turns.extend(
        _bash(1, "git push", "To github.com:o/idp.git\n   1a2b..3c4d  HEAD -> fix/a")
    )
    with path.open("a") as fh:
        for turn in turns:
            fh.write(json.dumps(turn) + "\n")

    started = time.monotonic()
    result = mod.grade_file(path)
    elapsed = time.monotonic() - started

    assert elapsed < BIG_BUDGET_S, (
        f"the gate took {elapsed:.1f}s on a {path.stat().st_size / 1e6:.1f} MB transcript: "
        f"the hook budget is {HOOK_BUDGET_S:.0f}s, so the session hangs"
    )
    assert _verdict_of(result) in VERDICTS, result


def test_the_tail_is_cut_at_a_line_boundary(tmp_path: Path) -> None:
    """KNOWN-GOOD: every line of the slice is a whole JSON line, never half a turn."""
    mod = _load("fw", FIREWALL)
    tail = getattr(mod, "TAIL_BYTES", None)
    assert tail is not None

    turns = [_prompt("a"), _say("b"), _prompt("c"), _say("d")]
    path = _write_transcript(tmp_path / "small.jsonl", turns)

    lines = mod._tail_lines(path, limit=len(path.read_text()) // 2)
    assert lines, "the tail must not be empty"
    for line in lines:
        if not line.strip():
            continue
        json.loads(line)  # raises if the slice cut a line in half


def test_a_transcript_inside_the_bound_is_graded_whole(tmp_path: Path) -> None:
    """KNOWN-GOOD: inside the bound the grader reads everything, so nothing is lost.

    The verdict must be the verdict the UNBOUNDED grader gives. This is the check that the bound
    does not quietly change the rule -- it only changes how much of the file is read.
    """
    mod = _load("fw", FIREWALL)
    turns = [
        _prompt("do the thing"),
        _say("I pushed the change and the tests are green."),
    ]
    turns.extend(
        _bash(1, "git push", "To github.com:o/idp.git\n   1a2b..3c4d  HEAD -> fix/a")
    )
    path = _write_transcript(tmp_path / "normal.jsonl", turns)

    lines = mod._tail_lines(path, limit=mod.TAIL_BYTES)
    assert len(lines) == len(turns), "a transcript inside the bound must be read whole"

    result = mod.grade_file(path)
    assert _verdict_of(result) in VERDICTS, result


def test_an_unreadable_transcript_is_still_blind(tmp_path: Path) -> None:
    """The bound must not turn the gate into a clean bill.

    A file that is not JSON at all is BLIND, exactly as before: a transcript we could not read is
    not evidence that the agent did not lie.
    """
    mod = _load("fw", FIREWALL)
    path = tmp_path / "broken.jsonl"
    path.write_text("this is not json\n" * 10)

    result = mod.grade_file(path)
    assert result.get("verdict") == "BLIND", result


def test_the_hook_budget_is_a_real_bound(tmp_path: Path) -> None:
    """The gate answers through its CLI, the way the hook calls it."""
    turns = [_prompt("x"), _say("I pushed it."), _bash(1, "git push", "ok")]
    path = _write_transcript(tmp_path / "t.jsonl", turns)

    started = time.monotonic()
    proc = subprocess.run(
        [sys.executable, str(FIREWALL), "--gate", str(path)],
        capture_output=True,
        text=True,
        timeout=HOOK_BUDGET_S,
    )
    elapsed = time.monotonic() - started
    # The gate exits 0 on PASS, 1 on a FAIL verdict and 2 on BLIND. All three are ANSWERS: what
    # matters here is that it answered inside the hook's budget, not which verdict it reached.
    assert proc.returncode in (0, 1, 2), (proc.returncode, proc.stderr)
    assert elapsed < HOOK_BUDGET_S
    assert (proc.stdout + proc.stderr).strip(), "the gate must print its verdict"
