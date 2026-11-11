"""The no-override FMEA guard: a failure mode without a real test cannot land."""

from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "bin" / "failure-mode-gate"
PRE_COMMIT = ROOT / ".githooks" / "pre-commit"
PRE_PUSH = ROOT / ".githooks" / "pre-push"


def run(service: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [str(GATE), *args, str(service)],
        capture_output=True,
        text=True,
        cwd=ROOT,
        timeout=20,
    )


def manifest(service: Path, test_cell: str) -> None:
    service.mkdir(parents=True)
    (service / "FAILURE_MODES.md").write_text(
        "| ID | Failure | Expected | Test |\n"
        "|---|---|---|---|\n"
        f"| F-X-1 | process dies | resume safely | {test_cell} |\n"
    )


def test_a_named_test_that_does_not_exist_is_refused(tmp_path):
    service = tmp_path / "service"
    manifest(service, "`resume_after_death`")
    (service / "src").mkdir()
    (service / "src" / "lib.rs").write_text("#[test]\nfn another_test() {}\n")

    result = run(service)

    assert result.returncode == 1
    assert "missing test resume_after_death" in result.stderr


def test_a_failure_mode_without_a_test_cell_is_refused(tmp_path):
    service = tmp_path / "service"
    manifest(service, "—")

    result = run(service)

    assert result.returncode == 1
    assert "F-X-1 has no test" in result.stderr


def test_a_real_rust_test_satisfies_the_row(tmp_path):
    service = tmp_path / "service"
    manifest(service, "`resume_after_death`")
    (service / "src").mkdir()
    (service / "src" / "lib.rs").write_text(
        "#[cfg(test)]\nmod tests {\n"
        "    #[test]\n"
        "    fn resume_after_death() {}\n"
        "}\n"
    )

    result = run(service)

    assert result.returncode == 0
    assert "ok failure-modes" in result.stdout


def test_there_is_no_override_or_ignore_flag(tmp_path):
    service = tmp_path / "service"
    manifest(service, "—")

    result = run(service, "--allow-missing")

    assert result.returncode == 2
    assert "unknown argument" in result.stderr


def test_commit_and_push_hooks_install_the_guard_without_an_override():
    pre_commit = PRE_COMMIT.read_text()
    pre_push = PRE_PUSH.read_text()

    assert "bin/failure-mode-gate" in pre_commit
    assert "cargo fmt --all -- --check" in pre_commit
    assert "cargo clippy" in pre_commit
    assert "-- -D warnings" in pre_commit
    assert "cargo test" in pre_commit
    assert "bin/failure-mode-gate" in pre_push
    assert "--allow-missing" not in pre_commit
    assert "IDP_SKIP_FAILURE_MODE_GATE" not in pre_commit
