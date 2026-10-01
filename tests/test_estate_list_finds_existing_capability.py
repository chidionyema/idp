"""estate_list(query=...): an agent asks in plain words and gets what the estate already has,
intents and harv parts, best first, each with the exact estate_invoke call.

Why it exists (measured 2026-09-30 from ~/.estate/estate.db): 1822 intent runs over 537 intents,
387 of them run exactly once, and zero harv parts ever called for real work. Agents write a new
thing because nothing tells them the old one exists; with bash going away, estate_invoke is the
only door, so this lookup is the one they need before building anything.
"""

import importlib.util
import sqlite3
from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parents[1] / "mcp" / "plugins" / "estate_mcp.py"


@pytest.fixture()
def em(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("estate_mcp_under_test", PLUGIN)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    intents = tmp_path / "intents"
    intents.mkdir()
    (intents / "ci-status.yaml").write_text(
        "description: Structured CI/CD status for a PR or SHA.\n"
        "args:\n  pr: {help: pull request number}\nsteps:\n  - cmd: 'true'\n"
    )
    (intents / "check-pr-4764-ci.yaml").write_text(
        "description: Check PR 4764 CI status\nsteps:\n  - cmd: 'true'\n"
    )
    (intents / "flux-kick.yaml").write_text(
        "description: Reconcile a Flux kustomization now.\nsteps:\n  - cmd: 'true'\n"
    )
    (intents / "broken.yaml").write_text('description: "bad \\| escape"\n')
    monkeypatch.setattr(mod, "INTENTS", intents)

    ledger = tmp_path / "estate.db"
    con = sqlite3.connect(ledger)
    con.execute("CREATE TABLE intent_tickets (id TEXT, intent TEXT)")
    con.executemany(
        "INSERT INTO intent_tickets VALUES (?, ?)",
        [(str(i), "ci-status") for i in range(78)] + [("x", "check-pr-4764-ci")],
    )
    con.commit()
    con.close()
    monkeypatch.setattr(mod, "ESTATE_DB", ledger)

    harv = tmp_path / "harv"
    (harv / "registry").mkdir(parents=True)
    con = sqlite3.connect(harv / "registry" / "index.db")
    con.execute(
        "CREATE TABLE artifacts(manifest_id TEXT, name TEXT, version TEXT, class TEXT,"
        " tier TEXT, component TEXT, created INTEGER)"
    )
    con.executemany(
        "INSERT INTO artifacts VALUES (?, ?, ?, 'read', ?, 'b3:x', ?)",
        [
            ("m1", "base64-encode-u8", "0.23.1", "t1", 1),
            ("m2", "semver-comparator-parse-to-string", "1.0.28", "t2", 2),
            ("m3", "comp-flags", "0.9.1", "t2", 3),
            ("m4", "base64-encode-u8", "0.23.2", "t1", 4),
        ],
    )
    con.commit()
    con.close()
    monkeypatch.setenv("HARV_HOME", str(harv))
    return mod


def headings(text):
    return [line for line in text.splitlines() if line.startswith("## ")]


def test_a_harv_part_is_found_with_the_call_that_runs_it(em):
    out = em._estate_list({"query": "base64 encoding"})
    assert headings(out)[0].startswith(
        "## harv part base64-encode-u8 0.23.2 "
    )  # newest version
    assert '"verb": "run", "name": "base64-encode-u8"' in out


def test_the_reused_intent_ranks_above_the_one_off(em):
    first, second = headings(em._estate_list({"query": "ci status for a pr"}))[:2]
    assert first.startswith("## intent ci-status (run 78 time(s))")
    assert second.startswith("## intent check-pr-4764-ci (run 1 time(s))")
    assert (
        'estate_invoke {"intent": "ci-status", "args": {"pr": ...}}'
        in em._estate_list({"query": "ci status"})
    )


def test_stems_match_but_short_fragments_do_not(em):
    out = em._estate_list({"query": "compare"})
    assert "semver-comparator-parse-to-string" in out
    assert "comp-flags" not in out


def test_filler_words_match_nothing(em):
    assert "nothing in the estate matches" in em._estate_list({"query": "a for the of"})


def test_nothing_found_says_so_and_says_what_to_do(em):
    out = em._estate_list({"query": "xyzzy"})
    assert out.startswith('# nothing in the estate matches "xyzzy"')
    assert "build it once as an intent" in out


def test_a_missing_shelf_is_said_never_shown_as_no_parts(em, tmp_path, monkeypatch):
    monkeypatch.setenv("HARV_HOME", str(tmp_path / "no-such-shelf"))
    out = em._estate_list({"query": "flux kustomization"})
    assert "NOTE: no harv shelf at" in out and "harv parts are missing" in out
    assert headings(out)[0].startswith("## intent flux-kick")


def test_an_unreadable_shelf_is_said(em, tmp_path, monkeypatch):
    bad = tmp_path / "bad-harv"
    (bad / "registry").mkdir(parents=True)
    (bad / "registry" / "index.db").write_text("not a database")
    monkeypatch.setenv("HARV_HOME", str(bad))
    assert "unreadable" in em._estate_list({"query": "base64"})


def test_no_query_still_lists_every_readable_intent(em):
    out = em._estate_list({})
    assert out.startswith("# 3 intents available:")


def test_the_tool_tells_agents_to_search_before_building(em):
    (tool,) = [t for t in em.TOOL_DEFS if t["name"] == "estate_list"]
    assert "query" in tool["inputSchema"]["properties"]
    assert "before building" in tool["description"]


def test_the_library_path_comes_from_the_environment(tmp_path, monkeypatch):
    """The estate-mcp image has no ~/.estate; it sets ESTATE_INTENTS_DIR=/app/intents."""
    lib = tmp_path / "lib"
    lib.mkdir()
    (lib / "only-one.yaml").write_text("description: The one intent.\n")
    monkeypatch.setenv("ESTATE_INTENTS_DIR", str(lib))
    spec = importlib.util.spec_from_file_location("estate_mcp_env", PLUGIN)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.INTENTS == lib
    assert mod._estate_list({}).startswith("# 1 intents available:")


def test_the_image_ships_the_library_and_refuses_an_empty_one():
    dockerfile = (PLUGIN.parents[2] / "estate-mcp.Dockerfile").read_text()
    assert "COPY platform/estate/intents /app/intents" in dockerfile
    assert "ENV ESTATE_INTENTS_DIR=/app/intents" in dockerfile
    assert "assert n >= 50" in dockerfile
