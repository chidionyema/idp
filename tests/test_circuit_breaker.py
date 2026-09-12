"""The circuit breaker proved both ways: it locks proved repetition, and never correct work.

Founder, 2026-09-12: "write the interceptor to hash the outputs and throw the 423 Locked
exception at N=3."

The real case, taken from 2026-09-12: six pull requests failed with the same three perl-base
CVEs. Their logs differ -- different positions, different stacks -- so a raw hash of the output
would never have matched. The fingerprint is the CVE set, which is the same on all six.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def brk():
    """The module under test. bin/ has no .py suffix, so it is loaded by path."""
    tool = ROOT / "bin" / "idp-circuit-breaker"
    loader = importlib.machinery.SourceFileLoader("breaker", str(tool))
    spec = importlib.util.spec_from_file_location("breaker", str(tool), loader=loader)
    assert spec and spec.loader, f"could not load {tool}"
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# The measured failure, as two different pull requests printed it: same CVEs, different shape.
LOG_A = """
2026-09-12T19:09:31.2278369Z Total: 3 (CRITICAL: 3)
│ perl-base │ CVE-2026-13221 │ CRITICAL │ fixed │ 5.40.1-6 │ 5.40.1-6+deb13u1 │
│ perl-base │ CVE-2026-42496 │ CRITICAL │ fixed │ 5.40.1-6 │ 5.40.1-6+deb13u1 │
│ perl-base │ CVE-2026-8376  │ CRITICAL │ fixed │ 5.40.1-6 │ 5.40.1-6+deb13u1 │
"""
LOG_B = """
2026-09-12T19:50:53.7606151Z Total: 3 (CRITICAL: 3)
│ perl-base │ CVE-2026-8376  │ CRITICAL │ fixed │ 5.40.1-6 │ 5.40.1-6+deb13u1 │
│ perl-base │ CVE-2026-13221 │ CRITICAL │ fixed │ 5.40.1-6 │ 5.40.1-6+deb13u1 │
│ perl-base │ CVE-2026-42496 │ CRITICAL │ fixed │ 5.40.1-6 │ 5.40.1-6+deb13u1 │
│   at /usr/lib/perl/base.pm:118:9                                  │
"""


class TestItLocksProvedRepetition:
    def test_one_finding_is_not_locked(self, brk):
        """Flow is preserved for a single target: diagnosis must stay free."""
        b = brk.Breaker()
        b.observe(LOG_A, "pr-1")
        assert b.check(LOG_A, "pr-2")["locked"] is False

    def test_two_findings_are_not_locked(self, brk):
        """N=3 means three. Two is a coincidence."""
        b = brk.Breaker()
        b.observe(LOG_A, "pr-1")
        b.observe(LOG_A, "pr-2")
        assert b.check(LOG_A, "pr-3")["locked"] is False

    def test_three_identical_findings_lock_the_primitive(self, brk):
        b = brk.Breaker()
        for t in ("pr-1", "pr-2", "pr-3"):
            b.observe(LOG_A, t)
        v = b.check(LOG_A, "pr-4")
        assert v["locked"] is True
        assert v["status"] == 423

    def test_it_is_not_decorative(self, brk):
        """After the lock the fourth target is refused, not merely noted."""
        b = brk.Breaker()
        for t in ("pr-1", "pr-2", "pr-3"):
            b.observe(LOG_A, t)
        assert b.check(LOG_A, "pr-4")["locked"] is True

    def test_the_lock_message_names_the_lever(self, brk):
        """A wall with no door is an outage: the refusal must say what to do instead."""
        b = brk.Breaker()
        for t in ("pr-1", "pr-2", "pr-3"):
            b.observe(LOG_A, t)
        v = b.check(LOG_A, "pr-4")
        assert v["lever"], "the lock named no lever"
        assert "merge-when-green" in v["lever"] or "one fix" in v["lever"]


class TestItNeverRefusesCorrectWork:
    def test_nine_different_findings_never_lock(self, brk):
        """The R38 case: nine targets, nine causes, all of them workable."""
        b = brk.Breaker()
        for i in range(1, 10):
            b.observe(
                f"failure number {i}: something unique to target {i}", f"target-{i}"
            )
        for i in range(1, 10):
            assert (
                b.check(
                    f"failure number {i}: something unique to target {i}", f"t-{i}"
                )["locked"]
                is False
            )

    def test_a_new_target_with_a_new_finding_is_not_locked(self, brk):
        """The lock is scoped by fingerprint, so a new cause stays fully open."""
        b = brk.Breaker()
        for t in ("pr-1", "pr-2", "pr-3"):
            b.observe(LOG_A, t)
        other = "Total: 1 (CRITICAL: 1)\n│ openssl │ CVE-2026-99999 │ CRITICAL │"
        assert b.check(other, "pr-9")["locked"] is False

    def test_a_different_fingerprint_on_a_locked_target_is_allowed(self, brk):
        """The lock is on the finding, never on the target or the tool."""
        b = brk.Breaker()
        for t in ("pr-1", "pr-2", "pr-3"):
            b.observe(LOG_A, t)
        assert (
            b.check("both fast-gate legs failed on this branch", "pr-1")["locked"]
            is False
        )


class TestTheFingerprint:
    def test_the_fingerprint_is_order_independent(self, brk):
        """LOG_A and LOG_B list the same three CVEs in a different order, with extra noise."""
        assert brk.fingerprint(LOG_A) == brk.fingerprint(LOG_B)

    def test_the_fingerprint_ignores_log_noise(self, brk):
        """A stack frame and a line:col difference are not a different cause."""
        assert brk.fingerprint(LOG_A) == brk.fingerprint(
            LOG_B + "\n   at other.pm:1:1\n"
        )

    def test_the_fingerprint_separates_different_causes(self, brk):
        a = "CVE-2026-13221"
        b = "CVE-2026-99999"
        assert brk.fingerprint(a) != brk.fingerprint(b)

    def test_a_finding_with_no_cve_still_fingerprints(self, brk):
        """Coarse, and the tests say so: unrelated text must not collide with a CVE finding."""
        assert brk.fingerprint("a git conflict on bin/x").startswith("sha:")
        assert brk.fingerprint("a git conflict on bin/x") != brk.fingerprint(LOG_A)


class TestTheTwoBugsEnforcementFound:
    """Both were found by trying to ENFORCE the breaker, and neither was caught in-process.

    An in-process test builds one Breaker object, so state that fails to persist across processes
    and a file that cannot be executed both pass. That is the difference between a rule in CI and a
    guard a session cannot walk past, and it is why enforcement found what the unit tests did not.
    """

    def test_the_record_rebuilds_the_lock_in_a_fresh_process(self, brk, tmp_path):
        """Each CLI invocation is a NEW process. The lock is derived from the record, not stored.

        Measured 2026-09-12: replaying observe rows without re-running the threshold left a fresh
        process reporting locked: false on a pattern that was already proved, so the enforcement
        was blind exactly when it mattered.
        """
        store = tmp_path / "b.jsonl"
        first = brk.Breaker(store=store)
        for t in ("pr-1", "pr-2", "pr-3"):
            first.observe("CVE-2026-13221 CVE-2026-42496", t)
        # a second object, as a second process would build
        second = brk.Breaker(store=store)
        assert second.check("CVE-2026-42496 CVE-2026-13221", "pr-4")["locked"] is True

    def test_the_tool_is_executable(self):
        """A file with no shebang cannot be run as a program, so a caller silently gets nothing.

        Measured 2026-09-12: bin/idp-circuit-breaker was marked executable and started with a
        docstring, so spawnSync returned no output and the extension reported "not locked" for a
        pattern that was proved. The unit tests never ran it as a program.
        """
        tool = ROOT / "bin" / "idp-circuit-breaker"
        assert tool.read_text().startswith("#!"), (
            "no shebang, so it cannot be executed directly"
        )
        assert tool.stat().st_mode & 0o111, "not executable"
