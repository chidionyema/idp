"""The compiled FLOW -> DOF -> LEGION -> KARMA engine, proved by its own cargo tests.

The workspace lives in crates/meridian-estate-engine. The root pytest suite is the one runner
the estate's CI already executes, so it is the door that makes a red unit in the engine block a
merge: this test runs the workspace's own `cargo test` and, once the army binary exists, requires
its sentinel line. A workspace member that is missing is simply not run yet; a member that is
present and red fails here.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "crates" / "meridian-estate-engine"
SENTINEL = "optimus.estate.karma_dof_legion_flow_unified=1"


def _cargo() -> str:
    found = shutil.which("cargo") or str(Path.home() / ".cargo" / "bin" / "cargo")
    if Path(found).exists():
        return found
    if os.environ.get("CI"):
        pytest.fail("cargo is missing on a CI runner: the engine cannot be proved")
    pytest.skip("cargo is not installed on this machine")


def _run(args: list[str], tmp_path: Path) -> subprocess.CompletedProcess:
    env = {**os.environ, "CARGO_TARGET_DIR": str(tmp_path / "target")}
    return subprocess.run(
        [_cargo(), *args],
        cwd=ENGINE,
        env=env,
        capture_output=True,
        text=True,
        timeout=900,
        check=False,
    )


@pytest.mark.skipif(
    not (ENGINE / "Cargo.toml").exists(), reason="engine workspace not landed"
)
def test_engine_workspace_tests_pass(tmp_path: Path) -> None:
    # Cargo.lock lands with the last member; once it exists the build must not drift from it.
    flags = ["--locked"] if (ENGINE / "Cargo.lock").exists() else []
    done = _run(["test", "--workspace", *flags], tmp_path)
    assert done.returncode == 0, done.stdout[-3000:] + done.stderr[-3000:]
    assert "test result: ok" in done.stdout


@pytest.mark.skipif(
    not (ENGINE / "crates" / "meridian-army" / "src" / "main.rs").exists(),
    reason="army binary not landed",
)
def test_army_prints_unified_sentinel(tmp_path: Path) -> None:
    done = _run(["run", "-q", "--locked", "-p", "meridian-army"], tmp_path)
    assert done.returncode == 0, done.stderr[-3000:]
    assert done.stdout.strip() == SENTINEL


# --- live mode: the engine deciding against the estate's own capability registry ---------------

REGISTRY = ROOT / "catalog" / "estate-capability-registry.json"
ARMY_PRESENT = (ENGINE / "crates" / "meridian-army" / "src" / "main.rs").exists()


def _live(args: list[str], target: Path) -> subprocess.CompletedProcess:
    # _run puts the target dir under its first argument's "target"; reuse one build for all tests.
    return _run(
        ["run", "-q", "--locked", "-p", "meridian-army", "--", *args], target.parent
    )


@pytest.fixture(scope="module")
def live_target(tmp_path_factory: pytest.TempPathFactory) -> Path:
    base = tmp_path_factory.mktemp("engine-live")
    (base / "target").mkdir()
    return base / "target"


def _decide(intent: str, registry: Path, live_target: Path) -> dict:
    done = _live(["--registry", str(registry), "--intent", intent], live_target)
    assert done.returncode == 0, done.stdout + done.stderr[-2000:]
    lines = done.stdout.strip().splitlines()
    assert len(lines) == 1, f"exactly one log line expected, got {lines}"
    return json.loads(lines[0])


@pytest.mark.skipif(not ARMY_PRESENT, reason="army binary not landed")
def test_army_decides_against_the_real_registry(live_target: Path) -> None:
    records = json.loads(REGISTRY.read_text())["records"]
    # An independent oracle: this test counts the file itself, never the engine's own arithmetic.
    verified = sum(
        1 for r in records if (r.get("health") or {}).get("state") == "verified"
    )
    out = _decide("agent invoke the failed critical function", REGISTRY, live_target)
    assert out["event"] == "meridian.flow.decision"
    assert out["registry_capabilities"] + out["registry_skipped"] == len(records)
    assert out["registry_verified"] == verified
    # Every capability in this registry is declared today. A declared route is reported with its
    # path and is never presented as running; when the registry verifies one, this flips to REUSE.
    allowed = (
        {"DECLARED_NOT_VERIFIED"}
        if verified == 0
        else {"DECLARED_NOT_VERIFIED", "REUSE_VERIFIED"}
    )
    assert out["decision"] in allowed
    assert out["capability"] == "cap:intent/agent-invoke" or verified > 0
    assert out["target_paths"] or out["decision"] != "DECLARED_NOT_VERIFIED"


@pytest.mark.skipif(not ARMY_PRESENT, reason="army binary not landed")
def test_army_says_implement_new_when_nothing_matches(live_target: Path) -> None:
    out = _decide("zzqx unmatchable gibberish plorp", REGISTRY, live_target)
    assert out["decision"] == "IMPLEMENT_NEW" and out["capability"] is None


@pytest.mark.skipif(not ARMY_PRESENT, reason="army binary not landed")
@pytest.mark.parametrize(
    "case",
    ["missing", "garbage", "empty-records", "empty-intent", "no-args-to-flag"],
)
def test_army_fails_closed_on_untrusted_input(
    case: str, tmp_path: Path, live_target: Path
) -> None:
    bad = tmp_path / "r.json"
    args = ["--registry", str(bad), "--intent", "agent invoke"]
    if case == "garbage":
        bad.write_text("not json")
    elif case == "empty-records":
        bad.write_text('{"records": []}')
    elif case == "empty-intent":
        args = ["--registry", str(REGISTRY), "--intent", "   "]
    elif case == "no-args-to-flag":
        args = ["--registry"]
    done = _live(args, live_target)
    assert done.returncode == 2, done.stdout + done.stderr[-1500:]
    assert (
        json.loads(done.stdout.strip().splitlines()[-1])["event"]
        == "meridian.flow.refused"
    )
