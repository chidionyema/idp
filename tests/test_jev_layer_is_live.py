"""The Jev layer must be REACHABLE and must LEAVE A ROW, or "no evidence of use" is the truth.

WHY THESE TESTS EXIST (measured 2026-10-18, founder: "we have a jev layer but I don't see
evidence of use"). Both statements were true at once and neither was a lie:

  1. `mcp/plugins/jev.py` could not be imported by the only python3 on the laptop
     (`/usr/bin/python3`, 3.9.6). `answer: str | None` is evaluated in the class body at import
     time without `from __future__ import annotations`, so loading the module raised TypeError.
     `bin/idp-affected` and `bin/idp-pr-risk` both died inside `_load_jev()` before making a
     single decision, and `sovereign/tests/bdd/test_jev_layer.py` could not even be collected
     locally. CI stayed green because the runners carry 3.12 -- a green gate over a layer that
     was dead on the machine that runs it.

  2. `ESTATE_DB_PATH` defaulted to `/data/estate.db`, which does not exist on the laptop, so
     `_upsert` hit its BLIND except and every decision was dropped. The Fleet page reads
     `catalog/estate.db`; `jev_decisions` was empty there and absent from `~/.estate/estate.db`.
     A layer whose rows land on no surface is indistinguishable from a layer that never ran.

  3. `bin/idp-pr-risk-gate` -- the push-time caller -- was invoked by NOTHING. `rg -n
     pr-risk-gate .githooks/ scripts/` returned nothing, so no push had ever consulted the layer.

Each test below fails against the code as it was and passes against the code as it is.
"""

from __future__ import annotations

import ast
import importlib.util
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
JEV = REPO / "mcp" / "plugins" / "jev.py"
FLEET_DB = REPO / "catalog" / "estate.db"


def _load():
    """Load the plugin by path, exactly as bin/idp-affected and bin/idp-pr-risk do."""
    spec = importlib.util.spec_from_file_location("jev_live_under_test", JEV)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["jev_live_under_test"] = module
    spec.loader.exec_module(module)
    return module


def test_module_declares_string_annotations() -> None:
    """`from __future__ import annotations` is what lets python3.9 import this module.

    Checked structurally, not by running 3.9: CI's interpreter is 3.12, where the missing
    future import is invisible. The next test runs the real system python anyway.
    """
    tree = ast.parse(JEV.read_text(encoding="utf-8"))
    futures = [
        node
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module == "__future__"
    ]
    assert any(
        alias.name == "annotations" for node in futures for alias in node.names
    ), (
        "mcp/plugins/jev.py must start with `from __future__ import annotations`: without it "
        "the module raises TypeError on import under python 3.9 (the laptop's only python3)"
    )


@pytest.mark.skipif(
    not Path("/usr/bin/python3").exists(), reason="no /usr/bin/python3 on this machine"
)
def test_the_estates_own_interpreter_can_import_the_module() -> None:
    """The interpreter that runs the hooks must be able to load the layer, not just CI's."""
    out = subprocess.run(  # noqa: S603 -- argv is fixed, the interpreter path is /usr/bin/python3
        [
            "/usr/bin/python3",
            "-c",
            "import importlib.util as u, sys;"
            f"s = u.spec_from_file_location('j', {str(JEV)!r});"
            "m = u.module_from_spec(s); sys.modules['j'] = m; s.loader.exec_module(m);"
            "print(m.ESTATE_DB_PATH)",
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert out.returncode == 0, out.stderr


def test_default_db_is_the_database_the_fleet_page_reads(monkeypatch) -> None:
    """A row the founder cannot see is a row that was not written.

    The default must be the Fleet page's database. `bin/serve-fleetview` is read here rather
    than trusted as prose: if the board's default moves, this test says so.
    """
    for var in ("ESTATE_DB_PATH", "ESTATE_DB", "IDP"):
        monkeypatch.delenv(var, raising=False)
    jev = _load()

    assert Path(jev.ESTATE_DB_PATH) == FLEET_DB
    board = (REPO / "bin" / "serve-fleetview").read_text(encoding="utf-8")
    assert "catalog/estate.db" in board, (
        "bin/serve-fleetview no longer defaults to catalog/estate.db; jev.py's default and the "
        "board's must not diverge or Jev's decisions land nowhere the founder looks"
    )


def test_an_unreachable_layer_still_records_the_consultation(
    tmp_path: Path, monkeypatch
) -> None:
    """No key is not "no decision made": it is a decision to ESCALATE, and it is recorded.

    This is the evidence the founder asked for. It proves the layer is consulted and that the
    consultation is durable; it does NOT prove the layer answered -- see the assertion on
    `confidence is None`, which is what an unlit vendor key looks like from the outside.
    """
    db = tmp_path / "estate.db"
    monkeypatch.setenv("ESTATE_DB", str(db))
    monkeypatch.delenv("ESTATE_DB_PATH", raising=False)
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    jev = _load()

    result = jev.jev_noul(
        repo="idp",
        layer="hook",
        decision_id="regression:unreachable",
        context={"probe": "is the layer reachable"},
        question="Is the Jev layer reachable from this process?",
    )

    assert result["escalated"] is True
    rows = (
        sqlite3.connect(db)
        .execute(
            "SELECT repo, layer, decision_id, confidence, escalated FROM jev_decisions"
        )
        .fetchall()
    )
    assert rows == [("idp", "hook", "regression:unreachable", None, 1)]


def test_pre_push_consults_the_decision_layer() -> None:
    """The push-time caller must be CALLED. It was not, which is why nothing was recorded.

    `bin/idp-pr-risk-gate` already refuses at `high` only, and already reports "no condition
    could be scored (layer unreachable)" instead of blocking on a blind check -- so wiring it
    in cannot turn a correct push red. Without this, the scorer is dead code.
    """
    hook = (REPO / ".githooks" / "pre-push").read_text(encoding="utf-8")
    assert "idp-pr-risk-gate" in hook, (
        ".githooks/pre-push must consult bin/idp-pr-risk-gate (--advise); otherwise nothing "
        "ever asks the decision layer about a change before it leaves the laptop"
    )

    gate = REPO / "bin" / "idp-pr-risk-gate"
    assert gate.is_file()
    assert gate.stat().st_mode & 0o111, "bin/idp-pr-risk-gate is not executable"
