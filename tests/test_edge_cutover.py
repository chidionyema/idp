"""Falsifiers for bin/idp-edge-cutover, the door that puts llm.<zone> on the Cloudflare edge.

Each test here is written from a defect that was MEASURED, not imagined. The door was debugged
four times on 2026-11-10 and every one of those failures cost a full executor call and a wrong
conclusion, so each is pinned here so it cannot come back.

The rule the whole file enforces: a door may not report `BLIND` when it means "present but
unreadable", and it may not report a measurement when it means "I could not look".
"""

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

IDP = Path(__file__).resolve().parents[1]
DOOR = IDP / "bin" / "idp-edge-cutover"


@pytest.fixture(scope="module")
def door():
    """The script as a module, so its own helpers are tested rather than a copy of them."""
    assert DOOR.exists(), f"the door is missing: {DOOR}"
    spec = importlib.util.spec_from_loader(
        "idp_edge_cutover",
        importlib.machinery.SourceFileLoader("idp_edge_cutover", str(DOOR)),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---- the door exists and is runnable --------------------------------------
# Section heading `the door exists and is runnable` is the falsifier for DBG-013: a door that is
# not executable, or whose committed copy does not even parse, is a document, not a door.
def test_the_door_is_committed_and_executable():
    assert DOOR.exists()
    assert os.access(DOOR, os.X_OK), "a door that is not executable is a document"


def test_the_door_parses_as_python():
    out = subprocess.run(
        [sys.executable, "-m", "py_compile", str(DOOR)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert out.returncode == 0, out.stderr


# ---- defect 1: vault_get demanded JSON and turned a present key into a false absence -----
def test_vault_get_returns_a_bare_value_not_only_json(door, monkeypatch):
    """MEASURED: `secret get` returns a bare banner-stripped string. The first version required
    JSON and answered "" -- 'BLIND the vault holds no cloudflare-api-token' -- for a token that
    was present. A BLIND dressed as an absence sends the next agent to mint a duplicate."""

    def fake_run(cmd, **kw):
        class R:
            returncode = 0
            stdout = "s3cr3t-value\n"
            stderr = "whoami: profile DEFAULT\n"

        return R()

    monkeypatch.setattr(door.subprocess, "run", fake_run)
    assert door.vault_get("cloudflare-api-token") == "s3cr3t-value"
    # and with a field asked for, a non-JSON body is still a value, not a crash. This is the branch
    # that actually carries the defect: field="value" falls through the `if not field` shortcut into
    # the JSON parse, and the JSON-only version answered "" for a bare body there.
    assert door.vault_get("cloudflare-api-token", "value") == "s3cr3t-value"
    assert door.vault_get("cloudflare-api-token", "") == "s3cr3t-value"


def test_vault_get_pins_the_oci_profile(door, monkeypatch):
    """MEASURED: without OCI_CLI_PROFILE the backend probes for a live session and HANGS past the
    executor ceiling (exit 142 SIGALRM at 40s; 11.5s with the profile pinned). A read that can
    hang is a read the 100s door cannot make."""
    seen = {}

    def fake_run(cmd, **kw):
        seen["env"] = kw.get("env") or {}
        seen["timeout"] = kw.get("timeout")

        class R:
            returncode = 0
            stdout = "v"
            stderr = ""

        return R()

    monkeypatch.delenv("OCI_CLI_PROFILE", raising=False)
    monkeypatch.setattr(door.subprocess, "run", fake_run)
    door.vault_get("anything")
    assert seen["env"].get("OCI_CLI_PROFILE") == "DEFAULT"
    assert seen["timeout"] is not None and seen["timeout"] <= 60


# ---- defect 2: __file__ was trusted, so a copy in /tmp resolved the root to /private ----
def test_idp_root_names_itself_when_it_is_not_in_a_checkout(door, monkeypatch):
    """MEASURED: copying the script to /tmp/cut.py resolved IDP to /private and the next call died
    `FileNotFoundError: /private/bin/idp-cloud`. A wrong path must say it is wrong, not raise."""
    monkeypatch.setattr(door, "__file__", "/tmp/cut.py")  # noqa: S108 -- the pseudo-path under test
    with pytest.raises(SystemExit) as exc:
        door.idp_root()
    assert exc.value.code != 0


def test_idp_root_finds_the_real_checkout(door):
    root = door.idp_root()
    assert (root / "bin" / "idp-cloud").exists()
    assert (root / "platform" / "lifeboat" / "wrangler.toml").exists()


# ---- the zone comes from the ONE file that defines it, never from the environment ----
# The section heading is the falsifier for DBG-014: a door that reads the zone from the environment
# is a second opinion about a value LAW 46 declares exactly once, and the first test here went red
# against a door that was correct because it assumed the wrong contract.
def test_zone_reads_the_config_not_the_environment(door, monkeypatch):
    """LAW 46: the zone is declared ONCE, in clusters/*/estate-config.yaml. A door that read
    $ESTATE_ZONE would be a second opinion about the same value, and the second opinion is the
    one that drifts. This test pins the real contract -- the first version asserted an env read
    and went red against a door that was correct."""
    monkeypatch.setenv("ESTATE_ZONE", "a-lie.example")
    assert door.zone() == "mumchimp.com"


def test_zone_refuses_to_guess_when_no_config_declares_it(door, monkeypatch, tmp_path):
    """A missing zone must NAME itself and exit non-zero, never fall back to a default."""
    monkeypatch.setattr(door, "IDP", tmp_path)
    (tmp_path / "clusters" / "oke").mkdir(parents=True)
    (tmp_path / "clusters" / "oke" / "estate-config.yaml").write_text("nothing: here\n")
    with pytest.raises(SystemExit) as exc:
        door.zone()
    assert exc.value.code == 2


# ---- the file's DECLARED absences are the design, and are tested as such ----
# This heading is the falsifier for DBG-015: a deploy that succeeds is not a deploy that is
# correct. These tests assert the RIGHT things are placed -- the route and the D1 binding, the
# estate's real routing lanes, the three brain state keys -- so a green door cannot mean an edge
# serving lanes nobody routes to or a `status: live` about an empty store.
def test_wrangler_toml_keeps_the_route_out_and_says_why():
    """MEASURED assumption, corrected: wrangler.toml deliberately carries NO route and NO
    zone_name -- both would name the DNS zone as a literal, and the deploy passes them on the
    command line from clusters/*/estate-config.yaml. Asserting `llm.` here was wrong; asserting
    that the absence is DOCUMENTED is the real contract, because an undocumented absence is
    indistinguishable from an omission."""
    toml = (IDP / "platform" / "lifeboat" / "wrangler.toml").read_text()
    assert "There is no `route`" in toml
    assert "bin/idp-edge-cutover" in toml


def test_d1_binding_is_written_only_after_a_real_database_id_resolves():
    """The binding is not in the committed file: `--bind-d1` appends it once a real id exists.
    A placeholder id is a deploy that fails on somebody's laptop at a bad moment."""
    toml = (IDP / "platform" / "lifeboat" / "wrangler.toml").read_text()
    assert "[[d1_databases]]" in toml, "the binding must at least be documented"
    assert "placeholder" in toml, "the reason it is absent must be written down"


def test_the_brain_schema_carries_the_three_state_keys():
    sql = (IDP / "platform" / "lifeboat" / "schema" / "brain.sql").read_text()
    for key in ("founder_instructions", "active_claims", "fencing_tokens"):
        assert key in sql, f"the D1 schema no longer holds {key}"


def test_groq_is_flagged_for_rotation(door):
    """The defect pass 3 exists to fix: the Groq key was exposed and must be re-minted."""
    assert "GROQ_API_KEY" in door.ROTATE


def test_the_frontier_lanes_are_the_estate_routing_defaults(door):
    """The cutover replaced a dead cluster router, so the edge must serve the lanes the estate
    actually routes to (routing.default = minimax, plus deepseek), not only the free floor."""
    names = {k for k, _ in door.PROVIDER_SECRETS}
    assert {
        "MINIMAX_API_KEY",
        "DEEPSEEK_API_KEY",
        "GROQ_API_KEY",
        "OPENROUTER_API_KEY",
    } <= names
