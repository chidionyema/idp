"""Shared fixtures for the Sovereign Bus acceptance suite (R39).

The feature files under `features/sovereign-bus/` are the acceptance criteria.
This module is what makes them executable: pytest-bdd binds each Scenario to
step functions, and `bin/idp-ci` runs the result. There is no second runner.

Why pytest-bdd and not a hand-written Gherkin reader (LAW 43): the repository
already carries 35 `.feature` files in Gherkin, and pytest-bdd is the mature
tool that parses Gherkin, binds steps, and reports an unbound step as a test
failure. The tool rejected is `behave`, because it brings its own runner and
its own reporting, and `bin/idp-ci` would then have two test runners to keep
in step.

Conventions for the five other builders writing step definitions here
----------------------------------------------------------------------
* One module per feature, named `test_cp<N>.py`, binding the whole feature:

      from pytest_bdd import scenarios
      scenarios("features/sovereign-bus/cp31_fsm_budget.feature")

  The path is the feature's path in this repository. `bdd_features_base_dir`
  in `sovereign/pytest.ini` is the repository root, so no module holds an
  absolute path and none needs `../..` counting (LAW 46).

* Until your steps land, mark the module pending with your requirement number
  and workstream, and nothing else:

      pytestmark = pytest.mark.pending("R31", owner="W3")

  Pending scenarios are skipped and counted. Delete the mark in the same
  commit that lands the steps -- once it is gone, a step with no definition
  fails the suite, which is the point.

* Steps go in the same `test_cp<N>.py` module. A step that more than one
  feature needs goes here in `conftest.py` instead, so it is bound once.

* Steps drive real code. Mock only at a true external boundary: a model API,
  Touch ID hardware, Telegram. Everything else -- the DAG, receipts, budget,
  the FSM -- runs for real against the temporary estate these fixtures build.

* Carry state between steps in the `context` dict, or return a value with
  `target_fixture=` when the value is what the next step is about.

Branch policy (crew#219 R39/R41, AGENTS.md [merge])
---------------------------------------------------
`dev` is permissive: a pending feature is skipped and counted. `main` is
strict: with SB_BDD_STRICT=1 in the environment every pending feature is a
failure, and so is a pending mark with no owner or owner "unclaimed".
`.github/workflows/ci.yml` sets the variable from the pull request's base
branch, so the same suite is the gate on both branches and only the
verdict on a skip changes. The fixture directory
sovereign/tests/fixtures/bdd/pending_unclaimed is the must-fail half of
that guard, and sovereign/tests/bdd/test_branch_policy.py runs it both ways.
"""
from __future__ import annotations

import importlib
import os
import re
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterator

import pytest

# The repository root: this file is sovereign/tests/bdd/conftest.py.
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


# ---------------------------------------------------------------------------
# Pending features: declared, skipped, and counted. A rule nobody can be
# stopped by is a wish, so the count is printed rather than left implicit.
# ---------------------------------------------------------------------------


# A Gherkin tag line is one or more @tags: `@cp12 @v2 @branch-budget-10pct`.
_TAG_LINE_RE = re.compile(r"^[ \t]*(@\S+(?:[ \t]+@\S+)*)[ \t]*$", re.MULTILINE)


def pytest_configure(config: pytest.Config) -> None:
    """Register every `@tag` the feature files carry as a pytest marker.

    pytest-bdd turns a Gherkin tag into a pytest marker, and `--strict-markers`
    refuses one that is not registered. Listing them by hand in pytest.ini
    would mean a builder adding `@cp36` to a feature breaks collection for
    everyone else, so they are read from the features instead. `--strict-markers`
    still does its real job: catching a typo in a mark written in Python.
    """
    for feature in sorted(REPO_ROOT.glob("features/**/*.feature")) + sorted(
        (REPO_ROOT / "sovereign" / "tests" / "fixtures" / "bdd").glob("**/*.feature")
    ):
        for line in _TAG_LINE_RE.findall(feature.read_text()):
            for tag in (t.lstrip("@") for t in line.split()):
                config.addinivalue_line("markers", f"{tag}: Gherkin tag, declared in {feature.name}")


STRICT_ENV = "SB_BDD_STRICT"
UNCLAIMED = "unclaimed"


def strict_branch_policy() -> bool:
    """True when this run is the gate for a strict branch (AGENTS.md
    [merge].strict_branches, today `main`)."""
    return os.environ.get(STRICT_ENV, "").strip().lower() in ("1", "true", "yes", "on")


def pending_verdict(mark: pytest.Mark, strict: bool) -> tuple[str, str]:
    """("skip" | "fail", reason) for one pending mark under one policy.
    Pure, so test_branch_policy.py can check the rule without a subprocess
    as well as with one."""
    req = mark.args[0] if mark.args else "?"
    owner = str(mark.kwargs.get("owner") or "")
    if not strict:
        return "skip", f"{req}: steps not bound yet, owner {owner or '?'}"
    if not owner or owner == UNCLAIMED:
        return "fail", f"{req}: pending mark has no owner (got {owner or 'none'!r}); a strict branch needs a named workstream"
    return "fail", f"{req}: steps not bound yet (owner {owner}); pending is not allowed on a strict branch"


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    pending: dict[str, str] = {}
    strict = strict_branch_policy()
    for item in items:
        mark = item.get_closest_marker("pending")
        if mark is None:
            continue
        req = mark.args[0] if mark.args else "?"
        owner = mark.kwargs.get("owner", "?")
        pending[item.nodeid.split("::")[0]] = f"{req} ({owner})"
        verdict, reason = pending_verdict(mark, strict)
        if verdict == "skip":
            item.add_marker(pytest.mark.skip(reason=reason))
    config.stash[_PENDING] = pending


def pytest_runtest_setup(item: pytest.Item) -> None:
    mark = item.get_closest_marker("pending")
    if mark is None or not strict_branch_policy():
        return
    verdict, reason = pending_verdict(mark, strict=True)
    if verdict == "fail":
        pytest.fail(reason, pytrace=False)


_PENDING: pytest.StashKey[dict[str, str]] = pytest.StashKey()


def pytest_terminal_summary(terminalreporter: Any, exitstatus: int, config: pytest.Config) -> None:
    pending = config.stash.get(_PENDING, {})
    if not pending:
        return
    mode = "strict: each one fails" if strict_branch_policy() else "permissive: each one skips"
    terminalreporter.write_sep("-", f"{len(pending)} feature(s) pending step definitions ({mode})")
    for path, who in sorted(pending.items()):
        terminalreporter.write_line(f"  pending  {path}  {who}")


# ---------------------------------------------------------------------------
# A temporary estate. Every fixture below hangs off this one, so a scenario
# never reads or writes the founder's real ~/.estate.
# ---------------------------------------------------------------------------


@pytest.fixture
def estate_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """ESTATE_HOME pointed at a temporary directory, with `sovereign.config`
    re-resolved against it. ESTATE_ENV is pointed at a file that does not
    exist so no real credential from the founder's estate.env can reach a
    test."""
    home = tmp_path / "estate"
    (home / "sovereign").mkdir(parents=True)
    monkeypatch.setenv("ESTATE_HOME", str(home))
    monkeypatch.setenv("ESTATE_ENV", str(tmp_path / "absent" / "estate.env"))
    # The secret store is the other credential source (config._vault_get);
    # point it at nothing too, or the real LiteLLM key reaches every test.
    monkeypatch.setenv("ESTATE_SECRETS", str(tmp_path / "absent" / "estate-secrets"))
    monkeypatch.setenv("HOME", str(tmp_path / "fakehome"))
    (tmp_path / "fakehome").mkdir(exist_ok=True)
    # Touch ID and the macOS Keychain are true external boundaries. With
    # trust.backend left on "auto" a receipt written on this Mac would read
    # the founder's real Keychain item; software_key keeps every signature a
    # scenario makes inside the temporary estate. A scenario that needs the
    # enclave (cp29) pins secure_enclave itself and fakes the swift helper.
    monkeypatch.setenv("SB_TRUST_BACKEND", "software_key")
    config = importlib.import_module("sovereign.config")
    importlib.reload(config)
    yield home
    # Leave the module resolved against the real estate for anything that
    # imports it after this test.
    importlib.reload(config)


@pytest.fixture
def config(estate_home: Path):
    """`sovereign.config`, resolved against the temporary estate."""
    return importlib.import_module("sovereign.config")


@pytest.fixture
def dag_root(estate_home: Path, config) -> Path:
    """The Merkle DAG node directory for this scenario, empty and real."""
    root = Path(config.get("sidecar.dag_dir").value)
    root.mkdir(parents=True, exist_ok=True)
    return root


@pytest.fixture
def receipts_path(estate_home: Path, config) -> Path:
    """Where this scenario's receipt chain is appended."""
    path = Path(config.get("receipts.path").value)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


# ---------------------------------------------------------------------------
# A fake clock. Time is an input, not an ambient fact: cp26 predicts three
# steps ahead, cp27 stops three branches "within 10 seconds", cp31 halts after
# Langfuse has been unreachable for 5 minutes. None of those may be tested by
# sleeping.
# ---------------------------------------------------------------------------


@dataclass
class FakeClock:
    """A clock a scenario moves by hand. `now` is wall time, `monotonic` is
    the elapsed-time source; both advance together and only when told to."""

    epoch: float = 1_756_000_000.0  # a fixed instant, so receipts are reproducible
    elapsed: float = 0.0

    def now(self) -> float:
        return self.epoch + self.elapsed

    def monotonic(self) -> float:
        return self.elapsed

    def advance(self, seconds: float) -> float:
        if seconds < 0:
            raise ValueError("a clock does not run backwards; use a new fixture")
        self.elapsed += seconds
        return self.now()

    def install(self, monkeypatch: pytest.MonkeyPatch, module: Any) -> None:
        """Point a module's `time.time` / `time.monotonic` at this clock."""
        monkeypatch.setattr(module.time, "time", self.now, raising=False)
        monkeypatch.setattr(module.time, "monotonic", self.monotonic, raising=False)


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


# ---------------------------------------------------------------------------
# A budget with the locking the spec asks for. cp31: "two activities spend
# from one budget at the same time -- the final balance equals start minus
# both spends, never negative". That is a compare-and-swap, so the fixture
# implements one rather than a plain integer, and a test that spends
# concurrently against it is testing the rule and not a mock.
# ---------------------------------------------------------------------------


class Overdrawn(Exception):
    """A spend that would take the balance below zero. The session halts."""


@dataclass
class FakeBudget:
    """Optimistic-locking token budget (spec §4.3).

    `version` increments on every accepted write, so a caller that read a
    stale balance loses the race and retries instead of overdrawing.
    """

    balance: int
    version: int = 0
    spent: int = 0
    refills: list[int] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def spend(self, tokens: int) -> int:
        if tokens < 0:
            raise ValueError("a spend is not a refill")
        with self._lock:
            if tokens > self.balance:
                raise Overdrawn(f"spend {tokens} exceeds balance {self.balance}")
            self.balance -= tokens
            self.spent += tokens
            self.version += 1
            return self.balance

    def try_spend(self, tokens: int, seen_version: int) -> int | None:
        """Compare-and-swap: returns the new balance, or None if another
        writer moved the budget since `seen_version` was read."""
        with self._lock:
            if seen_version != self.version:
                return None
            if tokens > self.balance:
                raise Overdrawn(f"spend {tokens} exceeds balance {self.balance}")
            self.balance -= tokens
            self.spent += tokens
            self.version += 1
            return self.balance

    def refill(self, tokens: int, *, signed: bool = False) -> int:
        """A refill is a signed act (spec §4.3: "session awaits signed
        refill"). An unsigned refill is refused here so a scenario cannot
        pass by topping up without a signature."""
        if not signed:
            raise PermissionError("signature required: a refill is a founder act")
        with self._lock:
            self.balance += tokens
            self.refills.append(tokens)
            self.version += 1
            return self.balance

    @property
    def exhausted(self) -> bool:
        return self.balance <= 0


@pytest.fixture
def budget() -> Callable[[int], FakeBudget]:
    """Factory: `budget(2000)` is "a session with budget 2k tokens"."""
    return lambda tokens: FakeBudget(balance=int(tokens))


# ---------------------------------------------------------------------------
# The captured-messages sink. Ghost is the default (cp23) and almost every
# feature asserts that nothing was sent, so silence has to be observable.
# Telegram is a true external boundary, so this is the one place a scenario
# is allowed to see a fake.
# ---------------------------------------------------------------------------


@dataclass
class Message:
    channel: str
    text: str
    kind: str = "message"


@dataclass
class MessageSink:
    """Everything a scenario would have pushed to the founder."""

    sent: list[Message] = field(default_factory=list)

    def send(self, channel: str, text: str, kind: str = "message") -> Message:
        msg = Message(channel=channel, text=text, kind=kind)
        self.sent.append(msg)
        return msg

    # -- assertions the scenarios read as English ---------------------------
    def count(self, kind: str | None = None) -> int:
        return len([m for m in self.sent if kind is None or m.kind == kind])

    def assert_silent(self) -> None:
        assert self.sent == [], f"expected Ghost silence, got {self.sent!r}"

    def assert_exactly_one(self) -> Message:
        assert len(self.sent) == 1, f"expected exactly one message, got {len(self.sent)}: {self.sent!r}"
        return self.sent[0]


@pytest.fixture
def messages() -> MessageSink:
    return MessageSink()


# ---------------------------------------------------------------------------
# A real git repository. cp24 asserts a receipt names "a git commit hash that
# exists in the repo" and cp24's undo moves HEAD to that commit's parent, so
# the repository under test has to be a real one.
# ---------------------------------------------------------------------------


@pytest.fixture
def scratch_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "scratch"
    repo.mkdir()
    env = {**os.environ, "GIT_CONFIG_GLOBAL": str(tmp_path / "gitconfig"), "GIT_CONFIG_SYSTEM": os.devnull}
    run = lambda *a: subprocess.run(["git", *a], cwd=repo, env=env, check=True, capture_output=True)
    run("init", "-q", "-b", "main")
    run("config", "user.email", "bdd@example.invalid")
    run("config", "user.name", "bdd")
    (repo / "README.md").write_text("scratch\n")
    run("add", "README.md")
    run("commit", "-qm", "root commit")
    return repo


# ---------------------------------------------------------------------------
# `bin/sb`, run against the temporary estate. Many scenarios read
# `When I run "bin/sb ..."`, and running the real entrypoint is what makes
# those acceptance tests rather than unit tests of an internal function.
# ---------------------------------------------------------------------------


@dataclass
class SbResult:
    argv: list[str]
    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0

    def json(self) -> Any:
        import json

        return json.loads(self.stdout)


@pytest.fixture
def sb(estate_home: Path, tmp_path: Path) -> Callable[..., SbResult]:
    """Run `bin/sb <args>` with ESTATE_HOME pointed at the scenario's estate."""

    def _run(*args: str, cwd: Path | None = None, timeout: int = 60) -> SbResult:
        # bin/sb builds sovereign/.venv on first use (a pip install). When
        # that venv is absent -- a fresh worktree, CI -- run the same
        # entrypoint, `python -m sovereign.cli`, under this interpreter,
        # which already has sovereign/requirements.txt installed.
        venv_python = REPO_ROOT / "sovereign" / ".venv" / "bin" / "python"
        if venv_python.exists():
            argv = [str(REPO_ROOT / "bin" / "sb"), *args]
        else:
            argv = [sys.executable, "-m", "sovereign.cli", *args]
        proc = subprocess.run(
            argv,
            cwd=str(cwd or REPO_ROOT),
            env={**os.environ, "ESTATE_HOME": str(estate_home), "PYTHONPATH": str(REPO_ROOT)},
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return SbResult(argv=argv, returncode=proc.returncode, stdout=proc.stdout, stderr=proc.stderr)

    return _run


# ---------------------------------------------------------------------------
# Step-to-step state. pytest-bdd's own answer is `target_fixture=`, which is
# right when the value IS the subject of the next step. This dict is for
# everything else, so a builder does not have to invent a fixture per noun.
# ---------------------------------------------------------------------------


@pytest.fixture
def context() -> dict[str, Any]:
    return {}
