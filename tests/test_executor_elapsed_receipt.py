"""The executor records what it measured, so a bound can be learned instead of guessed.

These are the falsifiers for the elapsed-time receipt: a receipt that leaks a value, a receipt
that is missing when the job died, a receipt that cannot be read by the resolver, or a resolver
that learns from a job the ceiling killed. Each one fails loudly if the seam breaks.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

EXECUTOR = Path(__file__).resolve().parents[1] / "platform" / "executor"
if str(EXECUTOR) not in sys.path:
    sys.path.insert(0, str(EXECUTOR))

import bounds  # noqa: E402
import receipts  # noqa: E402
import run  # noqa: E402


def test_shape_ignores_values_but_not_flags() -> None:
    """Same command, different values -> one shape (so durations pool). Different flags -> two."""
    a = receipts.command_shape(
        ["python3", "-m", "pytest", "tests/test_x.py", "-k", "alpha"]
    )
    b = receipts.command_shape(
        ["python3", "-m", "pytest", "tests/test_y.py", "-k", "beta"]
    )
    c = receipts.command_shape(
        ["python3", "-m", "pytest", "tests/test_x.py", "-k", "alpha"]
    )
    d = receipts.command_shape(["python3", "-m", "pytest", "--json", "tests/test_x.py"])
    assert a == b
    assert a == c
    assert a != d


def test_shape_never_carries_a_value() -> None:
    secret = "hunter2-super-secret-token"  # noqa: S105 - a fake value, and the point is that it never lands
    shape = receipts.command_shape(["deploy", "--token", secret, "--env", "prod"])
    assert secret not in shape
    assert "prod" not in shape
    assert "deploy" in shape


def test_flag_values_are_redacted_but_flag_names_are_kept() -> None:
    shape = receipts.command_shape(["curl", "--header", "Authorization: Bearer x"])
    assert "Authorization" not in shape
    assert "--header" in shape
    assert "curl" in shape


def test_successful_job_writes_a_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(run, "RUNS", tmp_path)
    rc = run.supervise(
        "ok-job", 30, [sys.executable, "-c", "print('hello')"], str(tmp_path)
    )
    assert rc == 0
    data = json.loads(
        receipts.receipt_path(tmp_path, "ok-job").read_text(encoding="utf-8")
    )
    assert data["exit_code"] == 0
    assert data["killed_at_ceiling"] is False
    assert data["elapsed_sec"] >= 0
    assert data["ceiling_sec"] == 30
    assert data["repo"] == str(tmp_path)


def test_a_job_killed_at_the_ceiling_says_so(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(run, "RUNS", tmp_path)
    argv = [sys.executable, "-c", "import time; time.sleep(30)"]
    run.supervise("slow-job", 1, argv, str(tmp_path))
    data = json.loads(
        receipts.receipt_path(tmp_path, "slow-job").read_text(encoding="utf-8")
    )
    assert data["killed_at_ceiling"] is True
    assert data["exit_code"] == run.CEILING_EXIT
    assert data["elapsed_sec"] >= 1


def test_a_command_that_cannot_start_still_leaves_a_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(run, "RUNS", tmp_path)
    run.supervise("ghost-job", 5, ["/nonexistent/definitely-not-here"], str(tmp_path))
    data = json.loads(
        receipts.receipt_path(tmp_path, "ghost-job").read_text(encoding="utf-8")
    )
    assert data["exit_code"] == 127
    assert data["killed_at_ceiling"] is False


def test_read_receipts_skips_a_corrupt_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(run, "RUNS", tmp_path)
    run.supervise("good-job", 30, [sys.executable, "-c", "pass"], str(tmp_path))
    (tmp_path / "broken.receipt.json").write_text("{not json", encoding="utf-8")
    (tmp_path / "wrong.receipt.json").write_text(
        '{"schema": "other"}', encoding="utf-8"
    )
    found = receipts.read_receipts(tmp_path)
    assert [r["argv0"] for r in found] == [Path(sys.executable).name]


def test_the_resolver_can_learn_from_a_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The seam is real: what the executor writes is what the resolver reads."""
    monkeypatch.setattr(run, "RUNS", tmp_path)
    argv = [sys.executable, "-c", "import time; time.sleep(0.2)"]
    for name in ("learn-1", "learn-2"):
        run.supervise(name, 30, argv, str(tmp_path))
    learned = [
        bounds.Receipt(
            shape=r["shape"],
            elapsed_sec=r["elapsed_sec"],
            exit_code=r["exit_code"],
            killed_at_ceiling=r["killed_at_ceiling"],
            repo=r["repo"],
        )
        for r in receipts.read_receipts(tmp_path)
    ]
    measured = bounds.measured_bound(learned, learned[0].shape, repo=str(tmp_path))
    assert measured is not None
    assert 0 <= measured <= 30
    resolution = bounds.resolve(
        "standard", receipts=learned, shape=learned[0].shape, repo=str(tmp_path)
    )
    assert resolution.state == bounds.ALLOW
    assert resolution.evidence == "measured"
    assert resolution.seconds is not None
    assert resolution.seconds >= bounds.MIN_CEILING_SEC


def test_a_ceiling_kill_is_not_evidence_that_a_bigger_ceiling_would_have_worked(
    tmp_path: Path,
) -> None:
    killed = bounds.Receipt(
        shape="sha256:x",
        elapsed_sec=100.0,
        exit_code=124,
        killed_at_ceiling=True,
        repo=str(tmp_path),
    )
    assert bounds.measured_bound([killed], "sha256:x", repo=str(tmp_path)) is None
