#!/usr/bin/env python3
"""The three real errors from the 2026-10-23 session, encoded as a test suite.

Each test is one way an agent produced a confident wrong number, and it asserts
that the checker refuses it. If any of these pass silently, the guarantee is
false.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1] / "bin" / "estate-claim-check"


def run(*args: str, store: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(TOOL), "--store", str(store), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def write_rows(store: Path, rows: list[dict]) -> None:
    store.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


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


def test_an_empty_store_passes_but_says_it_is_not_a_proof(tmp_path):
    p = run("verify", store=tmp_path / "missing.jsonl")
    assert p.returncode == 0
    assert "not a proof" in p.stdout
