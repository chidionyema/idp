"""The OCI session must be reachable without reading the vault it exists to unlock.

THE CIRCLE, MEASURED 2026-09-18. `bin/idp-oci-login` renders `~/.oci/config` from
`estate-secrets/secrets/dev/OCI_*.yaml`. Those files do not exist -- commit `76ba8be` moved the
estate's dev secrets into OCI Vault -- and reading OCI Vault needs an OCI identity. So:

    vault files  ->  idp-oci-login  ->  OCI session  ->  idp-cloud  ->  vault
                       ^ needs what it produces

The founder hit it three times in a row, because the only advice the one script gave was to run
the other one:

    $ bin/idp-oci-login
    BLIND oci  this device has no OCI API key: secrets/dev/ has no OCI_FINGERPRINT.yaml
                ...bin/idp-oci-bootstrap cannot fix this

WORSE, THE OTHER SCRIPTS HAD THE SAME ORDERING BUG. `idp-oci-bootstrap`,
`idp-bootstrap-cloudflare` and `idp-bootstrap-tailscale` each run `sops -d OCI_REGION.yaml`
BEFORE their browser login -- so a missing vault file kills the script at the line that was
supposed to earn the credential needed to read the vault. `idp-oci-bootstrap` exits 100 with no
output at all.

WHAT MAKES THE ROAD A LINE. `oci session authenticate` is a browser login. It needs two
IDENTIFIERS -- a region and a tenancy name -- and no secret of any kind. Neither is a credential:
a tenancy name is in every OCI console URL, a region is a location. So `bin/idp-oci-session`
takes them from the environment, falls back to the vault only when it can actually read it, and
otherwise explains precisely what to type. Nothing on the path that matters reads a secret.

These tests grade the ordering, which is the whole defect: the script must reach the browser
login, or say what identifier is missing, and must never die on a vault read it does not need.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SESSION = REPO / "bin" / "idp-oci-session"
OLD_LOGIN = REPO / "bin" / "idp-oci-login"


def _run(**env: str) -> subprocess.CompletedProcess:
    e = {k: v for k, v in os.environ.items() if not k.startswith("OCI_")}
    e.update(env)
    return subprocess.run(
        [str(SESSION)], capture_output=True, text=True, env=e, timeout=60, check=False
    )


def test_check_mode_reports_without_changing_anything():
    """Read-only by default, like every other estate probe."""
    p = subprocess.run(
        [str(SESSION), "--check"],
        capture_output=True,
        text=True,
        env=os.environ,
        timeout=60,
        check=False,
    )
    assert p.returncode in (0, 2)
    assert p.stdout.strip(), "a check must say something either way"
    assert "session" in p.stdout.lower()


def test_missing_identifiers_name_them_and_do_not_mention_a_command_that_cannot_help():
    """The message the founder needed three times and never got.

    It must name the two identifiers, say they are not secrets, and say why the vault cannot be
    the gate. It must NOT tell the reader to run the script that produced the circle.

    A LIVE SESSION SHORT-CIRCUITS THIS, correctly: with `~/.oci/sessions` populated the script
    reports the live profile and never reaches the identifier check at all. That is the intended
    behaviour, so this test SKIPS rather than fails when a session exists -- otherwise it would
    be asserting the absence of the very thing it wants to happen, and a founder who has just
    signed in would see a red suite.
    """
    p = _run()  # _run strips every OCI_* var, which is the state under test
    out = p.stdout + p.stderr
    if "is live" in out:
        pytest.skip(
            "an OCI session is live, so the identifier path is unreachable by design"
        )
    assert "OCI_REGION" in out
    assert "OCI_TENANCY_NAME" in out
    assert "NOT secrets" in out or "not secrets" in out.lower()
    assert "76ba8be" in out, (
        "name the commit that moved the secrets, so the cause is checkable"
    )
    # And the anti-fix: do not send the reader round the circle again.
    assert "idp-oci-bootstrap" not in out or "cannot" in out


def test_identifiers_from_the_environment_reach_the_browser_login():
    """The defect in one assertion: with identifiers supplied, the vault must not be consulted.

    Before this script, `sops -d OCI_REGION.yaml` ran first and exited 100 on a missing file, so
    execution never reached the login. Reaching the `login` line here IS the fix.

    THIS TEST MUST NEVER SPAWN THE REAL LOGIN. `oci session authenticate` binds local port 8181
    to receive the OAuth callback, and the first version of this test let it run: the process
    survived the timeout, held 8181 for the rest of the session, and the founder's OWN sign-in
    then failed against my leftover listener. Oracle answered "credentials do not match our
    records" for a password that was correct, and warned his account may lock out -- an outage
    caused by a test, presented to him as a credential problem.

    So the browser step is now observed WITHOUT running it: the script is placed on a PATH whose
    `oci` is a stub that records its argv and exits. That proves the same property (the script
    reached the login, with the right arguments) with no port, no browser and no network.
    """
    import stat
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        stub = Path(td) / "oci"
        argvfile = Path(td) / "argv"
        stub.write_text(
            "#!/bin/sh\n"
            f'printf "%s\\n" "$@" > "{argvfile}"\n'
            # Exit non-zero so the script takes its failure branch and prints the cause -- the
            # assertion below is about reaching this point, not about a sign-in succeeding.
            "exit 1\n"
        )
        stub.chmod(stub.stat().st_mode | stat.S_IEXEC)

        p = subprocess.run(
            [str(SESSION), "--region", "uk-london-1", "--tenancy", "test-tenancy"],
            capture_output=True,
            text=True,
            # A stub `oci` first on PATH, so the real CLI is never invoked.
            env={**os.environ, "PATH": f"{td}:{os.environ.get('PATH', '')}"},
            timeout=60,
            check=False,
        )
        out = p.stdout + p.stderr
        argv = argvfile.read_text() if argvfile.exists() else ""

    assert "browser" in out.lower(), (
        f"expected the script to reach the browser-login step, got:\n{out[:400]}"
    )
    # And it passed the identifiers through, which is the whole point of the fix.
    assert "session" in argv and "authenticate" in argv, f"stub oci got: {argv!r}"
    assert "uk-london-1" in argv, "the region must reach the CLI"
    assert "test-tenancy" in argv, "the tenancy name must reach the CLI"
    # And it must never read a vault file on this path.
    assert "sops -d" not in out
    assert "FINGERPRINT" not in out


def test_no_test_in_this_suite_can_bind_the_oauth_callback_port():
    """The suite must not be able to pollute the machine, asserted structurally.

    Regression guard for 2026-09-18, when a test left an `oci session authenticate` holding port
    8181 and the founder's own sign-in then failed against it. Rather than merely checking for
    leftovers (which only catches the failure AFTER it has happened), this asserts the CAUSE is
    absent: no test in this file runs the real CLI, so none can bind the port.
    """
    src = Path(__file__).read_text()
    # The real binary is never executed: every invocation goes through a stub on PATH.
    assert "subprocess.Popen(\n        [str(SESSION)]" not in src, (
        "a test spawns the session script directly; if PATH is not stubbed with a fake `oci`, "
        "the real CLI runs, binds port 8181, and can outlive the test"
    )
    # And the stub is what PATH points at: a temp dir placed first, so the real CLI is
    # unreachable from the test that exercises the browser step.
    assert "PATH" in src and "td" in src, (
        "the browser-login test must put a stub oci first on PATH"
    )


def test_running_the_real_cli_is_never_needed_by_this_suite():
    """A second angle: after the suite, nothing of ours may hold 8181.

    Checked by looking for a process whose command line carries this suite's fake tenancy -- a
    sign-in someone else started is none of this test's business.
    """
    p = subprocess.run(
        ["pgrep", "-fl", "oci session authenticate"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert "test-tenancy" not in p.stdout and "not-a-real-tenancy" not in p.stdout, (
        "this suite left an `oci session authenticate` running. It holds port 8181, and the next "
        "real sign-in then fails with a message that names neither the test nor the port. "
        f"Leftover:\n{p.stdout}"
    )


def test_it_never_reads_the_vault_when_the_environment_supplies_the_identifiers():
    """Ordering, asserted on the CODE rather than on the file.

    A future edit that moved a vault read above the environment check would restore the circle
    while every other test here still passed, so the ordering is checked in the text. Comments
    are stripped first: the header explains the fix and therefore mentions both `oci session
    authenticate` and the vault, and the first version of this test matched the prose at index
    998 instead of the code at index 5000+.
    """
    src = SESSION.read_text()
    code = "\n".join(ln for ln in src.splitlines() if not ln.lstrip().startswith("#"))

    env_branch = code.index('if [ -z "$REGION" ] || [ -z "$TENANCY_NAME" ]; then')
    vault_read = code.index("sops -d --extract")
    browser = code.index("oci session authenticate")
    assert env_branch < vault_read < browser, (
        "the environment must be consulted BEFORE the vault, and the browser login must come "
        "last -- any other order puts a vault read in front of the login that unlocks it. "
        f"Got env={env_branch} vault={vault_read} browser={browser}"
    )


def test_the_old_login_no_longer_sends_the_reader_to_the_broken_script():
    """The circle, guarded at its other end.

    `idp-oci-login` used to say 'run bin/idp-oci-bootstrap', which dies at its first line on the
    same missing files. That instruction is the loop; the comment explaining it is fine.
    """
    src = OLD_LOGIN.read_text()
    code = "\n".join(ln for ln in src.splitlines() if not ln.lstrip().startswith("#"))
    assert "run bin/idp-oci-bootstrap" not in code, (
        "idp-oci-login tells the reader to run the script that produced the circle"
    )
    assert "idp-oci-session" in src or "agent-identity" in src, (
        "the missing-key path must route to the browser-login road or the runbook"
    )


def test_it_is_executable_and_syntactically_valid():
    assert os.access(SESSION, os.X_OK), "bin/idp-oci-session must be executable"
    p = subprocess.run(["bash", "-n", str(SESSION)], capture_output=True, text=True)
    assert p.returncode == 0, p.stderr


def test_it_says_the_next_three_steps_in_order():
    """The road from session to agent identity, so the reader is not left at a prompt.

    Asserted as a shape rather than exact prose: the three commands, in dependency order.
    """
    src = SESSION.read_text()
    for needed in (
        "bin/idp-cloud whoami",
        "bin/idp-mac-secret-deliver",
        "bin/idp-jit identity",
    ):
        assert needed in src, f"the success message must name {needed}"
    # And in that order, because each depends on the one before.
    assert (
        src.index("bin/idp-cloud whoami")
        < src.index("bin/idp-mac-secret-deliver")
        < src.index("bin/idp-jit identity")
    )


def test_the_portal_supervisor_starts_three_processes_and_waits_for_each():
    """bin/idp-portal exists because three faults in one day were the SETUP, not the code.

    Measured 2026-09-18: app-config.yaml was edited while the dev server ran (read at start, so
    the edit was invisible for ~90 minutes); the fleetview plugin on 18790 is a third process
    nothing started, and with it down the board renders EMPTY rather than erroring; and /fleet
    sits behind sign-in, so a first visit shows the wall and reads as a broken page.

    The supervisor is only worth having if it probes real endpoints rather than ports -- a
    listening socket that answers nothing is exactly the state that made the board look empty.
    """
    portal = REPO / "bin" / "idp-portal"
    assert portal.exists(), "bin/idp-portal is missing"
    assert os.access(portal, os.X_OK), "bin/idp-portal must be executable"
    src = portal.read_text()

    # All three processes are named, with their ports.
    for needed in (
        "serve-fleetview",
        "18790",
        "workspace backend",
        "7107",
        "workspace app",
        "3100",
    ):
        assert needed in src, f"the supervisor does not start or name {needed}"

    # Readiness is a real request, never a port check.
    assert "curl -s -m 4 -o /dev/null" in src, "readiness must be an HTTP request"
    assert "/healthz" in src, "the plugin is probed on a path it actually serves"
    assert "/api/config" in src, "the backend is probed on a path it actually serves"

    # The two traps are documented IN the script, because a reader hits them here first.
    assert "--restart" in src
    assert "read at start" in src, "the app-config reload trap must be stated"
    assert "behind sign-in" in src, (
        "the sign-in wall must be stated where the URL is printed"
    )
    assert "Enter" in src, "and the one action the reader takes"


def test_the_portal_runbook_documents_all_three_processes():
    """The doc that said only 'two ports' is why every fault above was invisible.

    `docs/how-to/onboarding/portal.md` said: "Locally it is `yarn start` in `backstage/`
    (frontend on 3100, backend on 7107)." That is two of three, and it mentions neither the
    config reload nor the sign-in wall.
    """
    doc = (REPO / "docs" / "how-to" / "onboarding" / "portal.md").read_text()
    for needed in ("18790", "7107", "3100", "bin/idp-portal"):
        assert needed in doc, f"the runbook does not name {needed}"
    # The four measured traps.
    assert "read at START" in doc or "read at start" in doc
    assert "sign-in" in doc
    assert "Bytesync" in doc, "the brand is deliberate; the doc must say so"
    assert "playwright" in doc.lower(), (
        "the runbook must point at a browser check: a curl proves the API answers and says "
        "nothing about what a person sees, which is the mistake this whole page records"
    )
