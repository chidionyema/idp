"""idp#3525 CP5 -- code-review-record evidence for OFF-02, GRIND-01,
DARWIN-01 and ORCH-01.

Each of these four REQs' own METHOD is "config review" or "code review
record", not a runtime test of a capability that does not exist. Each
test below is exactly that record made mechanical: it holds today's
honest state (built / not built / partially matched) and fails the
moment the spec or the requirements files start asserting something
this repository does not actually have -- or, just as importantly, the
day one of these gaps is actually closed and the spec text needs to
catch up.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SPEC = REPO_ROOT / "docs/specs/2026-09-15-asymmetric-compute-leverage-spec-v0.1.md"


def _spec_text() -> str:
    return SPEC.read_text()


def _section(text: str, req: str) -> str:
    """The REQ's own statement block, not an earlier passing mention of
    its id (e.g. line 30's "once GRIND-01/DARWIN-01 land."). The spec
    states each REQ at the start of a line, `"{req} The ..."`."""
    marker = f"\n{req} "
    return text.split(marker, 1)[1].split("\n\n", 1)[0]


# ---------------------------------------------------------------------------
# OFF-02 -- execute_python (CPU-sandbox tool) is a NAMED GAP, not a built
# tool. Confirmed by grep: it appears only in the spec and in
# docs/evidence/, never as a defined function anywhere in the codebase.
# ---------------------------------------------------------------------------


def test_off_02_gap_is_recorded_in_the_spec() -> None:
    section = _section(_spec_text(), "OFF-02")
    status = "recorded" if "NAMED GAP" in section else "missing"
    assert status == "recorded"


def test_off_02_execute_python_does_not_exist_as_a_built_tool() -> None:
    """If someone builds it, this assertion starts failing -- that is
    the signal to move OFF-02's status in the spec, not a defect in
    this test."""
    hits = []
    for path in REPO_ROOT.rglob("*.py"):
        if (
            "/tests/" in str(path)
            or path.name.startswith("test_")
            or path == Path(__file__)
        ):
            continue
        try:
            text = path.read_text()
        except (OSError, UnicodeDecodeError):
            continue
        if re.search(r"\bdef execute_python\b", text):
            hits.append(str(path.relative_to(REPO_ROOT)))
    assert hits == [], (
        f"execute_python is now defined; OFF-02 must move off NAMED GAP: {hits}"
    )


# ---------------------------------------------------------------------------
# GRIND-01 -- the overnight grind worker: confirmed absent against repo
# queue primitives, exactly as the spec's own traceability matrix
# already records it ("Pillar 3 Grind Tool CronJob worker -> GRIND-01
# (NAMED GAP)").
# ---------------------------------------------------------------------------


def test_grind_01_gap_is_recorded_in_the_spec() -> None:
    section = _section(_spec_text(), "GRIND-01")
    status = "recorded" if ("NAMED" in section and "GAP" in section) else "missing"
    assert status == "recorded"


def test_grind_01_no_overnight_grind_worker_exists_yet() -> None:
    """Code review record (2026-09-15): grepped
    overnight|grind_worker|GrindWorker|Pillar 3 across every .py/.yaml
    file in the repo. The two textual hits that came back --
    platform/prospector/store-db-backup.yaml (an unrelated daily SQLite
    backup CronJob) and platform/jit/broker/telegram.py (the JIT
    broker's morning approval digest, whose docstring literally says
    "overnight") -- were read in full and are both unrelated: neither
    runs a queue worker gated on a deterministic test passing, neither
    enforces a 4h wall-clock ceiling tied to that gate, and neither runs
    context compaction every 20 turns. The repo's other wall-clock-
    shaped hits (verifier.py's sandbox timeout, jit_provisioning.py's
    Apple 24h licensing floor, bin/budget_governor.py's 60s execution
    boundary) are unrelated ceilings for unrelated things. No
    GrindWorker/grind_worker symbol exists anywhere. This test fails
    the day that changes, which is the point: it is the mechanical half
    of the code review, not a stand-in for the fault-injection test
    GRIND-01 still needs once a real worker exists."""
    hits = []
    for path in REPO_ROOT.rglob("*"):
        if (
            path.suffix not in (".py", ".yaml", ".yml")
            or ".git" in path.parts
            or path == Path(__file__)
        ):
            continue
        try:
            text = path.read_text()
        except (OSError, UnicodeDecodeError):
            continue
        if re.search(r"\b(GrindWorker|grind_worker)\b", text):
            hits.append(str(path.relative_to(REPO_ROOT)))
    assert hits == [], (
        f"a grind worker now exists; GRIND-01 must move off NAMED GAP: {hits}"
    )


def test_grind_01_named_false_positive_files_are_confirmed_unrelated() -> None:
    """The two files a keyword grep for GRIND-01 surfaces are not the
    grind worker -- record why, so a future grep does not have to
    re-read them to find out again."""
    telegram = (REPO_ROOT / "platform/jit/broker/telegram.py").read_text()
    assert "overnight" in telegram.lower()
    assert "digest" in telegram  # the morning summary function, not a worker
    assert "def digest(" in telegram

    backup = (REPO_ROOT / "platform/prospector/store-db-backup.yaml").read_text()
    assert "CronJob" in backup
    assert "store-db-backup" in backup  # a daily SQLite backup, not a grind worker


# ---------------------------------------------------------------------------
# DARWIN-01 -- sovereign/shadow/distill.py really runs a generate ->
# eval -> auto-deploy loop (train -> grade -> route, with a receipt
# either way), but it is not the *weekly*, multi-*variant* loop the REQ
# names: one local model per task_class, not several candidates compared
# against each other, and nothing schedules it. Stays UNCONFIRMED / gap,
# exactly as the spec's own traceability matrix already records it
# ("Pillar 4 Darwin Machines meta-optimizer -> DARWIN-01 (UNCONFIRMED ->
# gap)").
# ---------------------------------------------------------------------------


def test_darwin_01_gap_is_recorded_in_the_spec() -> None:
    text = _spec_text()
    section = _section(text, "DARWIN-01")
    status = (
        "recorded" if ("NAMED GAP" in section or "UNCONFIRMED" in text) else "missing"
    )
    assert status == "recorded"


def test_darwin_01_distill_has_a_real_generate_eval_deploy_loop() -> None:
    """Confirmed by reading sovereign/shadow/distill.py in full: train()
    runs the configured LoRA job, grade() runs a deterministic
    normalized-match grader (no model judges another model), route()
    flips the LiteLLM route table at or above distill.route_accuracy and
    writes a receipt whether it flips or not. This half of DARWIN-01 is
    real, not a gap."""
    distill = (REPO_ROOT / "sovereign/shadow/distill.py").read_text()
    required = (
        "def train(",
        "def grade(",
        "def route(",
        "def run(",
        "flipped",
        "receipts_mod.append(",
    )
    missing = [name for name in required if name not in distill]
    assert missing == [], (
        f"distill.py no longer matches the train/grade/route/receipt loop; "
        f"re-review DARWIN-01: missing {missing}"
    )


def test_darwin_01_distill_is_not_yet_the_weekly_multi_variant_loop() -> None:
    """What distill.py does not do: generate multiple *variants* to
    compare (it trains exactly one local model per task_class from the
    queue, not several candidates), and nothing schedules it -- `sb
    distill` is a CLI command a person or an external job invokes, and
    no CronJob anywhere under platform/ names distill. Until one does,
    DARWIN-01 stays UNCONFIRMED / gap, per the spec's own traceability
    line, not "existing capability"."""
    scheduled = []
    for path in (REPO_ROOT / "platform").rglob("*.y*ml"):
        try:
            text = path.read_text()
        except (OSError, UnicodeDecodeError):
            continue
        if "distill" in text.lower() and "cronjob" in text.lower():
            scheduled.append(str(path.relative_to(REPO_ROOT)))
    assert scheduled == [], (
        f"a weekly schedule for distill now exists ({scheduled}); DARWIN-01 "
        "should move from UNCONFIRMED to confirmed-real in the spec"
    )


# ---------------------------------------------------------------------------
# ORCH-01 -- dependency manifests carry no second orchestration
# framework, and branching really is real Temporal, not CrewAI/LangGraph.
# ---------------------------------------------------------------------------

REQUIREMENTS_FILES = (
    "sovereign/requirements.txt",
    "sovereign/requirements-dev.txt",
    "bin/rca_worker/requirements.txt",
)

FORBIDDEN_FRAMEWORKS = frozenset(("crewai", "langgraph"))


def _declared_packages(path: Path) -> frozenset[str]:
    """Parse a requirements.txt and return the set of declared package names."""
    pkgs: set[str] = set()
    for line in path.read_text().splitlines():
        line = line.split("#", 1)[0].strip()
        if not line or line.startswith("-"):
            continue
        m = re.match(r"^([A-Za-z0-9_.-]+)", line)
        if m:
            pkgs.add(m.group(1).lower())
    return frozenset(pkgs)


def test_orch_01_dependency_manifests_have_no_second_orchestration_framework() -> None:
    checked = 0
    for rel in REQUIREMENTS_FILES:
        path = REPO_ROOT / rel
        if not path.exists():
            continue
        checked += 1
        declared = _declared_packages(path)
        intersection = declared & FORBIDDEN_FRAMEWORKS
        assert intersection == frozenset(), (
            f"{rel} declares {intersection}; ORCH-01 requires an explicit REQ first"
        )
    if checked == 0:
        raise AssertionError(
            "none of the known requirements files exist; re-check ORCH-01's manifest list"
        )


def test_orch_01_branching_uses_real_temporal_child_workflows_not_a_second_framework() -> (
    None
):
    branching = (REPO_ROOT / "sovereign/shadow/branching.py").read_text()
    workflow = (REPO_ROOT / "sovereign/shadow/workflow.py").read_text()
    assert "from temporalio.client import Client" in branching
    assert "start_child_workflow" in workflow
    for forbidden in FORBIDDEN_FRAMEWORKS:
        assert forbidden not in branching.lower()
        assert forbidden not in workflow.lower()
