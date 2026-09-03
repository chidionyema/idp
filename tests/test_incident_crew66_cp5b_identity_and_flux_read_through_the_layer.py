"""crew#66 CP5b: bin/idp-identity-apply and bin/idp-flux-bootstrap stop naming the oci CLI for vault
reads; they go through bin/idp-cloud (one primitive layer). The IDCS SCIM door in identity-apply is
left as `oci raw-request` because that is the identity provider's own API, not a vault read. Rule
(rung 4): the script exits 2 with `BLIND   <noun> <first stderr line>` when the layer exits
non-zero, never treats an empty value as success."""

from __future__ import annotations

import re
import stat
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IDENTITY = (ROOT / "bin" / "idp-identity-apply").read_text()
FLUX = (ROOT / "bin" / "idp-flux-bootstrap").read_text()


# ------------------------------------------------------------------------------------------- runtime


def _fake(b: Path, name: str, body: str) -> None:
    f = b / name
    f.write_text("#!/usr/bin/env bash\n" + body)
    f.chmod(f.stat().st_mode | stat.S_IEXEC)


def test_identity_layer_exit_split_blinds(tmp_path: Path) -> None:
    """A layer exit 3 (Split: ACTIVE in more than one vault) on the first describe is BLIND, not a
    silent empty value. The script must exit 2 with `BLIND   identity <why>` on stdout."""
    idp = tmp_path / "idp"
    idp.mkdir()
    fake_bin = idp / "bin"
    fake_bin.mkdir()
    _fake(
        fake_bin,
        "idp-cloud",
        """
case "$1 $2" in
  "secret describe")
    echo "Split: secret $3 is ACTIVE in more than one vault of the compartment" >&2
    exit 3;;
esac
echo "unexpected: $*" >&2; exit 9""",
    )
    src = (ROOT / "bin" / "idp-identity-apply").read_text()
    # extract from `err_id="${TMPDIR:-/tmp}/identity-id.err"` through the closing of the second case.
    # the script's first layer call is on `oauth2-proxy-client-id`; a Split there must BLIND.
    m = re.search(
        r'(err_id="\$\{TMPDIR:-/tmp\}/identity-id\.err"; : > "\$err_id"\n.*?case "\$rc_sec" in\n.*?\)\s*\n)',
        src,
        re.S,
    )
    assert m, "the identity-apply BLIND-on-layer-error block could not be located"
    block = m.group(1)
    r = subprocess.run(
        ["bash", "-c", f'IDP="{idp}"\n{block}'], capture_output=True, text=True
    )
    assert r.returncode == 2, (r.stdout, r.stderr)
    assert "BLIND" in r.stdout
    assert "identity" in r.stdout
    # REWORK idp#476 (09cd04a6): both describes run before either rc is checked, so a shared stderr
    # file would print client-secret's line for a client-id BLIND. The line must name client-id.
    assert "oauth2-proxy-client-id is ACTIVE" in r.stdout, r.stdout
    assert "client-secret" not in r.stdout, r.stdout


def test_flux_layer_exit_split_blinds(tmp_path: Path) -> None:
    """A layer exit 3 (Split) on `secret list --vault` is BLIND, not a count of 0; the script must
    exit 2 with `BLIND   flux <why>` on stdout."""
    idp = tmp_path / "idp"
    idp.mkdir()
    fake_bin = idp / "bin"
    fake_bin.mkdir()
    _fake(
        fake_bin,
        "idp-cloud",
        """
case "$1 $2 $3" in
  "secret list --vault")
    echo "Split: vault CUR is unreadable" >&2
    exit 3;;
esac
echo "unexpected: $*" >&2; exit 9""",
    )
    src = (ROOT / "bin" / "idp-flux-bootstrap").read_text()
    # the block runs from the `if [ -n "$VAULT_ID" ] && [ -n "$CUR" ] && [ "$CUR" != "$VAULT_ID" ];`
    # header through its closing `fi`, the part of the script that exercises the layer for the
    # current vault's secret count and reacts to the exit code.
    m = re.search(
        r'(if \[ -n "\$VAULT_ID" \] && \[ -n "\$CUR" \] && \[ "\$CUR" != "\$VAULT_ID" \]; then.*?\nfi\n)',
        src,
        re.S,
    )
    assert m, "the flux-bootstrap vault-switch block could not be located"
    block = m.group(1)
    r = subprocess.run(
        [
            "bash",
            "-c",
            f'IDP="{idp}"; VAULT_ID=ocid1.vault.new; CUR=ocid1.vault.old\n{block}',
        ],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 2, (r.stdout, r.stderr)
    assert "BLIND" in r.stdout
    assert "flux" in r.stdout
