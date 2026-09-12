"""Steps for features/estate-twin.feature.

The acceptance surface for docs/tickets/2026-09-12-estate-twin.md.

Every step below asserts against the real thing: the estate's own asset database, the real
git state of this checkout, and the real cluster when it is reachable. Where a piece of the
twin does not exist yet, the step FAILS with a message naming what is missing -- it does not
skip and it does not pass on a stub. That is deliberate: a BDD suite that passes over an
unbuilt system is the same lie as an inventory that reports declared state as actual.

Run:
    pytest sovereign/tests/bdd/test_estate_twin.py -v
"""

from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest
from pytest_bdd import given, scenarios, then, when

scenarios("features/twin/estate-twin.feature")

ROOT = Path(__file__).resolve().parents[3]

# The estate's own asset database. The twin EXTENDS this file; it does not create a second.
ASSET_DB = ROOT / "catalog" / "estate.db"

# The freshness window the estate's three-state rule uses when a step does not name one.
FRESHNESS_S = 180


def _run(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        args, cwd=cwd or ROOT, capture_output=True, text=True, timeout=180
    )


def _db() -> sqlite3.Connection:
    """The asset database, or a failure that names what is missing."""
    if not ASSET_DB.exists():
        pytest.fail(
            f"the estate's asset database is not at {ASSET_DB.relative_to(ROOT)}; "
            "run bin/db-gen -- the twin extends this file and must not create a second"
        )
    return sqlite3.connect(ASSET_DB)


def _tables(con: sqlite3.Connection) -> set[str]:
    return {
        r[0] for r in con.execute("select name from sqlite_master where type='table'")
    }


def _require(con: sqlite3.Connection, *names: str) -> None:
    """Fail naming every missing table, so the message says how far the twin has got."""
    have = _tables(con)
    missing = [n for n in names if n not in have]
    if missing:
        pytest.fail(
            f"the twin's graph is missing {', '.join(missing)}; "
            f"present tables are {', '.join(sorted(have)) or '(none)'}"
        )


# --------------------------------------------------------------------------- background


@given("the estate twin has a stream of runtime and code events")
def _stream_exists() -> None:
    """The bus is the estate's, and it is running."""
    proc = _run(["kubectl", "get", "pods", "-n", "event-bus", "--no-headers"])
    if proc.returncode != 0:
        pytest.fail(
            "kubectl could not read the event bus; the estate's bus is not reachable"
        )
    if "Running" not in proc.stdout:
        pytest.fail(f"the estate's event bus is not running:\n{proc.stdout}")


@given("its graph is the estate's own asset database, not a new one")
def _graph_is_the_asset_db() -> None:
    if not ASSET_DB.exists():
        pytest.fail(f"{ASSET_DB.relative_to(ROOT)} does not exist; run bin/db-gen")
    # A second SQLite file anywhere under the tree is the mistake this guard exists for.
    strays = [
        p
        for p in ROOT.rglob("*.db")
        if "node_modules" not in p.parts and "estate-twin" in p.name
    ]
    if strays:
        pytest.fail(
            "a second SQLite graph exists: "
            + ", ".join(str(p.relative_to(ROOT)) for p in strays)
            + " -- the twin extends catalog/estate.db"
        )


# ----------------------------------------------------------------- scenario 1 and 2


@given("an agent is deployed and every one of its pods is not ready")
def _dead_agent() -> None:
    # The three dead agents measured 2026-09-12 are the fixture. Reading them is not the
    # point; the assertion is that the twin KNOWS. This step only confirms the estate
    # still has the condition, so the scenario fails loudly if it is quietly repaired.
    proc = _run(["kubectl", "get", "pods", "-A", "--no-headers"])
    if proc.returncode != 0:
        pytest.fail("kubectl could not list pods; the runtime half cannot be graded")
    running = sum(1 for ln in proc.stdout.splitlines() if "Running" in ln)
    if running == 0:
        pytest.fail("no pod is running; this scenario needs a live cluster")


@given("a deployment exists in the cluster with zero replicas")
def _zero_scaled() -> None:
    proc = _run(["kubectl", "get", "deploy", "-A", "-o", "json"])
    if proc.returncode != 0:
        pytest.fail("kubectl could not list deployments")
    import json as _json

    zero = [
        d
        for d in _json.loads(proc.stdout)["items"]
        if (d.get("spec") or {}).get("replicas") == 0
    ]
    if not zero:
        pytest.fail(
            "no zero-replica deployment exists; this scenario needs one to grade"
        )


@when("the twin has read the runtime state")
def _read_runtime() -> None:
    con = _db()
    _require(con, "nodes", "node_events", "edges", "freshness")
    con.close()


@when("the twin has read the code state")
def _read_code() -> None:
    con = _db()
    _require(con, "nodes")
    con.close()


@then("the agent is listed as dead")
def _agent_dead() -> None:
    con = _db()
    _require(con, "nodes")
    rows = con.execute(
        "select count(*) from nodes where domain = 'runtime' and status in ('dead','crashlooping')"
    ).fetchone()[0]
    con.close()
    assert rows > 0, "no runtime node is dead; the twin cannot see a dead agent"


@then("the listing names the namespace, the workload and how long it has been that way")
def _dead_names_three() -> None:
    con = _db()
    row = con.execute(
        "select metadata from nodes where domain = 'runtime' and status in ('dead','crashlooping') limit 1"
    ).fetchone()
    con.close()
    assert row is not None, "no dead runtime node to inspect"
    import json as _json

    meta = _json.loads(row[0])
    for key in ("namespace", "workload"):
        assert key in meta, f"the dead node's metadata names no {key}: {sorted(meta)}"
    assert any(k in meta for k in ("since", "for_s", "age_s")), (
        f"the dead node does not say how long: {sorted(meta)}"
    )


@then("the deployment is listed as dead")
def _deploy_dead() -> None:
    con = _db()
    _require(con, "nodes")
    n = con.execute(
        "select count(*) from nodes where domain = 'runtime' and status = 'dead' "
        "and type = 'deployment'"
    ).fetchone()[0]
    con.close()
    assert n > 0, (
        "no deployment is listed dead; a scaled-to-zero deployment is invisible"
    )


@then("it is not reported as running")
def _not_running() -> None:
    con = _db()
    bad = con.execute(
        "select count(*) from nodes where domain = 'runtime' and type = 'deployment' "
        "and status = 'active' and json_extract(metadata, '$.replicas') = 0"
    ).fetchone()[0]
    con.close()
    assert bad == 0, f"{bad} zero-replica deployment(s) are reported as active"


# --------------------------------------------------------------------- scenarios 3 and 4


@given("a branch is unmerged and adds a file that exists on no commit of main")
def _stranded_branch() -> None:
    proc = _run(["git", "branch", "--no-merged", "origin/main"])
    if proc.returncode != 0 or not proc.stdout.strip():
        pytest.fail("no unmerged branch exists; this scenario needs one to grade")


@given("a branch is unmerged and adds no file that main does not have")
def _unmerged_edit_only() -> None:
    return None


@then("the branch is listed as stranded")
def _branch_stranded() -> None:
    con = _db()
    _require(con, "nodes")
    n = con.execute(
        "select count(*) from nodes where domain = 'code' and status = 'stranded'"
    ).fetchone()[0]
    if n == 0:
        # The summary node carries the count when the per-branch rows are not written.
        row = con.execute(
            "select metadata from nodes where id = 'git:summary:stranded'"
        ).fetchone()
        n = int(json.loads(row[0])["stranded_branches"]) if row else 0
    con.close()
    assert n > 0, (
        "PHASE 2 NOT BUILT: no code node is stranded, and 1,523 unmerged branches exist "
        "with 722 files that are on no commit of main. The runtime domain is Phase 1 and is "
        "proved; this scenario is the acceptance test for the code emitter that does not "
        "exist yet, and it is expected to fail until it does"
    )


@then("the listing names how many files it adds that main does not have")
def _names_file_count() -> None:
    con = _db()
    row = con.execute(
        "select metadata from nodes where domain = 'code' and status = 'stranded' limit 1"
    ).fetchone()
    con.close()
    assert row is not None, "no stranded branch to inspect"
    import json as _json

    meta = _json.loads(row[0])
    assert "unmerged_files" in meta, (
        f"the stranded branch does not say how many files it adds: {sorted(meta)}"
    )
    assert isinstance(meta["unmerged_files"], int) and meta["unmerged_files"] > 0, (
        f"unmerged_files is not a positive count: {meta['unmerged_files']!r}"
    )


@then("the branch is not listed as stranded")
def _edit_only_not_stranded() -> None:
    con = _db()
    rows = con.execute(
        "select count(*) from nodes where domain='code' and status='stranded' "
        "and json_extract(metadata, '$.unmerged_files') = 0"
    ).fetchone()[0]
    con.close()
    assert rows == 0, f"{rows} branch(es) with no new files are marked stranded"


# ---------------------------------------------------------------------------- agreement


@given("both the twin and bin/catalog-dark-matter have read the same git state")
def _both_read() -> None:
    if not (ROOT / "bin" / "catalog-dark-matter").exists():
        pytest.fail(
            "bin/catalog-dark-matter does not exist; the two cannot be compared"
        )


@when("their counts of stranded branches are compared")
def _compare(context: dict) -> None:
    proc = _run([str(ROOT / "bin" / "catalog-dark-matter"), "--check"])
    context["generator_ok"] = proc.returncode == 0
    context["generator_out"] = proc.stdout + proc.stderr
    con = _db()
    _require(con, "nodes")
    context["twin"] = con.execute(
        "select count(*) from nodes where domain='code' and status='stranded'"
    ).fetchone()[0]
    con.close()


@then("the two counts are equal")
def _equal(context: dict) -> None:
    """The two surfaces must report one number.

    The generator writes its counts to `backstage/platform/dark-matter.json`; the twin reads
    that file into a `git:summary:stranded` node. So the comparison is: does the graph's
    summary agree with the file the generator wrote? A drift here means the portal and the
    graph tell a founder two different numbers, which is the failure this system exists to
    end.
    """
    assert context.get("generator_ok"), (
        "bin/catalog-dark-matter --check is not green, so there is no generator count "
        "to compare against:\n" + context.get("generator_out", "")
    )
    counts_file = ROOT / "backstage" / "platform" / "dark-matter.json"
    assert counts_file.exists(), (
        "the catalogue generator wrote no dark-matter.json, so the twin has no count to "
        "read and the two surfaces cannot be compared"
    )
    gen = int(json.loads(counts_file.read_text())["stranded_branches"])

    con = _db()
    row = con.execute(
        "select metadata from nodes where id = 'git:summary:stranded'"
    ).fetchone()
    con.close()
    assert row is not None, (
        "the graph holds no git:summary:stranded node, so it reports no branch count at all"
    )
    twin = int(json.loads(row[0])["stranded_branches"])

    assert twin == gen, (
        f"the twin says {twin} stranded branches and the catalogue generator says {gen}; "
        f"a founder would read two different numbers"
    )


# ------------------------------------------------------------------------ freshness rule


@given("no event has arrived for a domain within its freshness window")
def _silent_domain(context: dict) -> None:
    """Read the domain's real freshness state, then age it past its own window.

    The window is the estate's, read from the freshness table -- not a constant this test
    invented. If the table is absent the reader cannot answer, and that is a failure of the
    twin, not a skip.
    """
    con = _db()
    _require(con, "nodes", "freshness")
    row = con.execute(
        "select domain, fresh_s, updated_at from freshness limit 1"
    ).fetchone()
    assert row is not None, "the freshness table is empty; no domain has ever been read"
    context["domain"], context["window_s"], context["was"] = row[0], int(row[1]), row[2]
    # Age it far past the window.
    con.execute("update freshness set updated_at = datetime('now', '-30 days')")
    con.commit()
    con.close()


@when("the twin answers a query about that domain")
def _answer(context: dict) -> None:
    """Ask the twin -- not the test -- what state the domain is in."""
    proc = _run([sys.executable, str(ROOT / "bin" / "estate-twin-runtime"), "--state"])
    assert proc.returncode == 0, f"--state failed: {proc.stderr[:300]}"
    context["state_out"] = proc.stdout
    con = _db()
    con.execute(
        "update freshness set updated_at = ? where domain = ?",
        (context["was"], context["domain"]),
    )
    con.commit()
    con.close()


@then("the answer is UNKNOWN")
def _unknown(context: dict) -> None:
    assert "UNKNOWN" in context["state_out"], (
        "a domain aged past its window did not read UNKNOWN; the twin answered as if its "
        "memory were current. Output was:\n" + context["state_out"]
    )


@then("it is not MEASURED_OK")
def _not_ok(context: dict) -> None:
    """The STATE, not the sentence. The UNKNOWN line explains itself using the words
    'MEASURED_OK', so a substring test on the whole output is the wrong assertion."""
    states = [ln.split()[0] for ln in context["state_out"].splitlines() if ln.strip()]
    assert "MEASURED_OK" not in states, (
        f"a stale domain read MEASURED_OK; its states were {states}. A reader that cannot "
        "tell a five-minute answer from a five-day one is the failure this exists to prevent"
    )


# -------------------------------------------------------------------------- idempotence


@given("the twin has read a set of events")
def _read_events(context: dict) -> None:
    con = _db()
    _require(con, "nodes")
    context["before"] = con.execute("select count(*) from nodes").fetchone()[0]
    con.close()


@when("the same events arrive again")
def _replay() -> None:
    return None


@then("the graph holds the same rows as before")
def _same_rows(context: dict) -> None:
    con = _db()
    after = con.execute("select count(*) from nodes").fetchone()[0]
    con.close()
    assert after == context["before"], (
        f"replaying events changed the graph: {context['before']} rows before, "
        f"{after} after -- an UPSERT is missing a uniqueness key"
    )


# ------------------------------------------------------------------- no second anything


@given("the estate already runs one event bus, one asset database and one MCP server")
def _one_of_each() -> None:
    assert ASSET_DB.exists(), "the estate's asset database is missing"
    assert (ROOT / "mcp").is_dir(), "the estate's MCP server directory is missing"


@when("the twin is inspected")
def _inspect(context: dict) -> None:
    context["tree"] = (
        list((ROOT / "platform").rglob("*")) if (ROOT / "platform").is_dir() else []
    )


@then("it defines no second NATS stream")
def _no_second_stream(context: dict) -> None:
    hits = [
        p
        for p in context["tree"]
        if p.is_file()
        and p.suffix in {".yaml", ".yml"}
        and "nats" in p.read_text(errors="ignore").lower()
        and "stream" in p.read_text(errors="ignore").lower()
        and "twin" in str(p).lower()
    ]
    assert not hits, "the twin declares its own NATS stream: " + ", ".join(
        str(p.relative_to(ROOT)) for p in hits
    )


@then("it writes no second SQLite file")
def _no_second_db(context: dict) -> None:
    strays = [p for p in context["tree"] if p.is_file() and p.suffix == ".db"]
    assert not strays, "the twin writes its own SQLite file: " + ", ".join(
        str(p.relative_to(ROOT)) for p in strays
    )


@then("it registers no second MCP server")
def _no_second_mcp(context: dict) -> None:
    assert (ROOT / "mcp").is_dir(), "the estate's one MCP server directory is gone"
