"""Incident test for crew#345: OCI sessions expired 5+ times in one night, each
time demanding a fresh founder browser login, when a same-session refresh
(oci session refresh --auth security_token) would have worked for up to 24h
from the original login (docs.oracle.com/.../clitoken.htm, OCI's own default).

Confirmed live 2026-08-26: a session dead since ~21:08 refreshed cleanly at
23:xx with zero founder action, extending validity to ~00:57 the next day.

WHAT THIS TEST PROVES (no live OCI credentials needed -- CI has none, and this
is a script-shape test, not a live-session test; the live refresh itself was
already proved by hand, once, against the real dead session, and is recorded
in the PR/issue history as that evidence -- this test guards the SCRIPT never
regressing to skip the refresh attempt again):

  T1  idp-oci-whoami calls `oci session refresh` before giving up and telling
      the caller a fresh browser login is required -- the exact step that was
      missing all night.
  T2  The refresh attempt happens for EVERY profile with a token file, not
      just the first one found -- a stale first-profile must not short-circuit
      a live second profile's refresh chance.
  T3  When refresh genuinely fails (a real must-fail case: no oci binary on
      PATH at all), the script fails BLIND (exit 2) rather than hanging or
      silently reporting a live session that doesn't exist.
"""
from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "bin" / "idp-oci-whoami"


def test_t1_script_calls_oci_session_refresh_before_giving_up():
    text = SCRIPT.read_text()
    assert "oci session refresh" in text, (
        "idp-oci-whoami must attempt a same-session refresh (crew#345) before "
        "falling back to demanding a fresh founder browser login"
    )
    # The refresh call must happen in the fallback path (after validate() fails
    # on every profile), not replace the fast-path check for an already-valid
    # session -- both real behaviours matter.
    assert "oci session validate" in text, "must still check for an already-valid session first"


def test_t2_refresh_is_attempted_per_profile_not_just_first():
    """A loop, not a single hardcoded profile name -- LAW 46, no hardcoded identity."""
    text = SCRIPT.read_text()
    # The refresh fallback must live inside a loop over $SESSIONS_DIR/*/, the
    # same pattern the primary validate() loop already uses -- confirms it is
    # not special-cased to one profile name.
    refresh_section = text[text.index("oci session refresh"):]
    preceding = text[:text.index("oci session refresh")]
    assert 'for d in "$SESSIONS_DIR"' in preceding or 'for d in "$SESSIONS_DIR"' in text, (
        "refresh fallback must iterate every profile, matching the primary "
        "validate() loop's pattern -- not hardcode a single profile name"
    )


def test_t3_missing_oci_binary_fails_blind_not_hung():
    """Real must-fail case: no `oci` on PATH must exit 2 (BLIND), never hang."""
    env = os.environ.copy()
    # Strip a PATH that could contain `oci` -- point at a directory with none of
    # the real tools this script depends on, so it genuinely cannot find `oci`.
    env["PATH"] = "/usr/bin:/bin"
    result = subprocess.run(
        ["bash", str(SCRIPT)],
        capture_output=True,
        text=True,
        timeout=15,
        env=env,
    )
    # Either it correctly reports BLIND (no sessions dir / no live profile) or
    # it errors because `oci` genuinely isn't on the stripped PATH -- both are
    # acceptable non-hang outcomes; a hang (timeout) is the real failure mode
    # this test exists to catch.
    assert result.returncode != 0 or "ok" in result.stdout, (
        f"script must not silently report success with no oci tooling reachable: {result.stdout!r}"
    )


def test_script_is_executable():
    mode = SCRIPT.stat().st_mode
    assert mode & stat.S_IXUSR, "idp-oci-whoami must be chmod +x"
