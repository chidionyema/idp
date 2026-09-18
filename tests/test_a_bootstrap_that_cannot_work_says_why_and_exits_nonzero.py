"""A bootstrap that cannot do its job must say why, in one line, and exit non-zero.

Measured 2026-09-18, on a laptop whose estate-secrets vault holds only LITELLM_LAPTOP_KEY.yaml
(the state commit 76ba8be left it in when dev secrets moved to OCI Vault):

    $ bin/idp-oci-bootstrap
    $ echo $?
    100

No stdout. No stderr. Exit 100 is sops's own exit code for a missing file, propagated by
`set -euo pipefail` out of a `vget()` that ran `sops ... 2>/dev/null`. The guard two lines below
the call -- `|| { echo "BLIND vault lacks OCI_REGION / OCI_TENANCY_OCID"; exit 2; }` -- was dead
code that could never run, because the shell never got that far.

The founder hit this three times in a row, because the other script's only advice was to run
this one:

    $ bin/idp-oci-login
    BLIND oci     no API key in the vault yet; run bin/idp-oci-bootstrap
    $ bin/idp-oci-bootstrap
    $ bin/idp-oci-login
    BLIND oci     no API key in the vault yet; run bin/idp-oci-bootstrap

Two scripts pointing at each other, neither naming the real state. This grades the three
properties that make that impossible to repeat, and no prose:

  * a missing vault secret produces a BLIND line naming the secret AND a non-zero exit;
  * the exit code is not 100 (sops's code, which reads as success-adjacent to no one but is
    indistinguishable from a crash), it is the script's own 2;
  * neither script's output advises running the other one.

The last one is the guard against the loop itself: re-introducing "run bin/idp-oci-bootstrap"
into idp-oci-login's missing-key path is the regression, whether or not the message is pretty.
"""

from __future__ import annotations

import os
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOOTSTRAP = os.path.join(ROOT, "bin", "idp-oci-bootstrap")
LOGIN = os.path.join(ROOT, "bin", "idp-oci-login")


def _run(script: str, **env_extra: str) -> subprocess.CompletedProcess:
    """Run a bin/ script with no tty, exactly as an agent or a hook invokes it."""
    env = dict(os.environ, **env_extra)
    return subprocess.run(
        [script],
        capture_output=True,
        text=True,
        env=env,
        stdin=subprocess.DEVNULL,
        timeout=120,
        check=False,
    )


def test_a_missing_vault_secret_is_named_not_swallowed():
    """The regression: exit 100 with zero output. Both halves must hold."""
    p = _run(BOOTSTRAP)
    output = p.stdout + p.stderr

    # It must speak. Silence is the defect, not the exit code.
    assert output.strip(), (
        "bin/idp-oci-bootstrap produced no output at all. This is the exact defect: "
        "`set -e` plus `2>/dev/null` means a missing vault file kills the script before its "
        "own BLIND guard runs, and nobody -- human or agent -- is told anything."
    )

    # And it must name what is actually wrong, not merely fail.
    assert "BLIND" in output, f"expected a BLIND line naming the gap, got:\n{output}"
    assert "OCI_REGION" in output or "OCI_TENANCY" in output, (
        f"expected the missing secret to be named, got:\n{output}"
    )


def test_the_exit_code_is_the_scripts_own_and_not_sopss():
    """100 is sops failing. A reader cannot tell that from a crash; the script's own 2 is a verdict."""
    p = _run(BOOTSTRAP)
    assert p.returncode == 2, (
        f"expected exit 2 (the script's own BLIND), got {p.returncode}. "
        "Exit 100 is sops's missing-file code escaping through set -e, which is how a missing "
        "secret came to look like a crash with no message."
    )


def test_a_missing_vault_secret_does_not_take_the_whole_script_down():
    """vget must be callable for an optional secret without aborting the caller.

    This is why vget returns instead of exiting: OCI_TENANCY_NAME is legitimately optional, and
    before the fix a caller could not ask for it without the whole bootstrap dying at that line.
    """
    p = _run(BOOTSTRAP)
    output = p.stdout + p.stderr
    # All three of the first reads report themselves, rather than the first one killing the run.
    assert output.count("BLIND vault") >= 2, (
        "expected each missing required secret to report itself, not the first one to abort the "
        f"script. Got:\n{output}"
    )


def test_the_two_scripts_do_not_point_at_each_other():
    """The loop, guarded directly. Script A's advice must not be script B, and vice versa."""
    bootstrap = open(BOOTSTRAP, encoding="utf-8").read()
    login = open(LOGIN, encoding="utf-8").read()

    # Strip comments: an explanatory note naming the other script is fine and useful. What must
    # not survive is an *instruction to the reader* telling them to go run it.
    def code_lines(text: str) -> str:
        return "\n".join(
            line for line in text.splitlines() if not line.lstrip().startswith("#")
        )

    login_code = code_lines(login)
    assert "run bin/idp-oci-bootstrap" not in login_code, (
        "bin/idp-oci-login tells the reader to run bin/idp-oci-bootstrap. That is the loop: "
        "bootstrap reads the same missing vault files and stops at its first line, so the reader "
        "is sent back to a script that cannot help, forever."
    )

    bootstrap_code = code_lines(bootstrap)
    assert "run bin/idp-oci-login" not in bootstrap_code, (
        "bin/idp-oci-bootstrap tells the reader to run bin/idp-oci-login, whose missing-key path "
        "then sends them back here. Name the cause instead."
    )


def test_login_refuses_an_agent_without_advising_a_dead_end():
    """idp-oci-login's tty guard is correct and must stay; its message must route to a live road."""
    p = _run(LOGIN)
    output = p.stdout + p.stderr
    assert p.returncode == 2, f"expected exit 2, got {p.returncode}:\n{output}"
    assert "interactive terminal" in output, (
        f"the tty guard must still refuse an agent (Law: him, not agents). Got:\n{output}"
    )
    # The live road is Actions, which needs no laptop credential at all.
    assert "oke-check.yml" in output, (
        "an agent refused by the tty guard must be routed to the road that actually works for "
        f"it -- the Actions runner. Got:\n{output}"
    )
