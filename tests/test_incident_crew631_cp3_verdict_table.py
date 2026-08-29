"""crew#631 CP3: the verdict table is append-only in the Backstage Postgres; the prover INSERTs,
agent_role only SELECTs. The SQL is pure and graded here; the tool's psql door is a fake."""

import importlib.machinery
import importlib.util
import json
import os
import re
import stat
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
IDP = os.path.dirname(HERE)
sys.path.insert(0, IDP)
from probes import store as S  # noqa: E402


def test_schema_grants_insert_to_prover_select_to_agent_and_refuses_update_delete():
    sql = S.SCHEMA_SQL
    assert re.search(r"GRANT INSERT, SELECT ON verdicts TO prover", sql)
    assert re.search(r"GRANT SELECT ON verdicts TO agent_role", sql)
    assert (
        "UPDATE"
        not in sql.split("GRANT SELECT ON verdicts TO agent_role")[0].split(
            "REVOKE ALL"
        )[1]
    )
    assert "BEFORE UPDATE OR DELETE OR TRUNCATE" in sql and "append-only" in sql
    assert "CHECK (outcome IN ('PASS','FAIL','BLOCKED','ERROR'))" in sql


def test_insert_runs_as_prover_never_updates_and_quotes():
    v = {
        "verdict_id": "v'1",
        "check_id": "c",
        "target": "t",
        "commit_sha": "s",
        "outcome": "FAIL",
        "completed_at": "2026-08-29T15:00:00Z",
        "prover_id": "p",
        "prover_run_id": "1",
        "assertions": [],
    }
    sql = S.insert_sql(v)
    assert sql.startswith("SET ROLE prover;")
    assert "ON CONFLICT (verdict_id) DO NOTHING" in sql and "UPDATE" not in sql
    assert "'v''1'" in sql and json.dumps(v, sort_keys=True).replace("'", "''") in sql
    assert S.list_sql(5, "c").startswith(
        "SET ROLE agent_role;"
    ) and "LIMIT 5" in S.list_sql(5, "c")
    assert S.refuse_sql().startswith("SET ROLE agent_role;\nINSERT")


def _tool(tmp_path, stdout, rc):
    """A fake bin/idp-kube that records the SQL it was fed and answers as told."""
    fake = tmp_path / "bin"
    fake.mkdir()
    (fake / "idp-kube").write_text(
        f"#!/bin/sh\ncat > {tmp_path}/sql.txt\nprintf '%s' '{stdout}'\nexit {rc}\n"
    )
    (fake / "idp-kube").chmod(0o755)
    for name in ("idp-verdict",):
        (fake / name).symlink_to(os.path.join(IDP, "bin", name))
    return fake


def test_store_reports_a_landed_row_and_blind_when_the_pod_answers_no(
    tmp_path, monkeypatch
):
    v = {
        "verdict_id": "v1",
        "check_id": "c",
        "target": "t",
        "commit_sha": "s",
        "outcome": "PASS",
        "completed_at": "2026-08-29T15:00:00Z",
        "prover_id": "p",
        "prover_run_id": "1",
    }
    (tmp_path / "verdict.json").write_text(json.dumps(v))
    loader = importlib.machinery.SourceFileLoader(
        "idp_verdict", os.path.join(IDP, "bin", "idp-verdict")
    )
    spec = importlib.util.spec_from_loader("idp_verdict", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    calls = []

    def psql(sql, timeout=120):
        calls.append(sql)
        return (
            (0, "1\n", "")
            if "INSERT" in sql and "prover" in sql
            else (1, "", "ERROR:  permission denied for table verdicts")
        )

    monkeypatch.setattr(mod, "psql", psql)
    assert mod.main(["store", str(tmp_path / "verdict.json")]) == 0
    assert calls[-1].startswith("SET ROLE prover;")

    def psql_down(sql, timeout=120):
        return 2, "", "OSError: no cluster"

    monkeypatch.setattr(mod, "psql", psql_down)
    assert mod.main(["store", str(tmp_path / "verdict.json")]) == 2
    assert mod.main(["list"]) == 2

    def psql_refuse(sql, timeout=120):
        if "agent_role" in sql:
            return 1, "", "ERROR:  permission denied for table verdicts"
        return 1, "", "ERROR:  verdicts is append-only: UPDATE refused"

    monkeypatch.setattr(mod, "psql", psql_refuse)
    assert mod.main(["refuse-test"]) == 0
    monkeypatch.setattr(mod, "psql", lambda sql, timeout=120: (0, "UPDATE 3", ""))
    assert mod.main(["refuse-test"]) == 1, "an accepted INSERT/UPDATE must be red"


def test_the_prover_stores_the_verdict_after_the_artifact():
    wf = open(os.path.join(IDP, ".github/workflows/verdict-langfuse.yml")).read()
    assert "bin/idp-verdict schema" in wf and "bin/idp-verdict store verdict.json" in wf
    assert wf.index("upload-artifact") < wf.index("bin/idp-verdict store")
