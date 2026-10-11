"""The shadow stands in for the estate database, and proves it before workloads wait on it.

Incident: every DB-backed path (llm, temporal, unified-memory-server, hindsight...) resolves
estate-rw.estate-db.svc.cluster.local:5432. Production serves that name with CloudNativePG;
the shadow installs no operator and no cluster, so those workloads found nothing, never
converged, and burned the deadline -- or the path was never meaningfully verifiable at all.

The stand-in is the same move as the vault stand-in: it stands in for the ESTATE (the
server, its roles, its databases), never for the change. Every role and database is the
one the head's own databases.yaml declares; every password is the vault stand-in's
placeholder, which is exactly the value the vault stand-in writes into the Secret the
workload mounts. A stand-in that cannot be laid fails the run: a shadow that cannot raise
its own dependencies proves nothing about the change.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def load_shadow():
    loader = importlib.machinery.SourceFileLoader(
        "idp_shadow", str(REPO / "bin" / "idp-shadow")
    )
    spec = importlib.util.spec_from_loader("idp_shadow", loader)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def test_the_seed_is_read_from_the_head_not_from_a_table_in_the_script():
    shadow = load_shadow()
    rows = shadow.database_rows()
    # temporal-visibility the Database is temporal_visibility the schema: the spec name,
    # not metadata's, is the one Postgres gets.
    by = {r[0]: r for r in rows}
    assert by["temporal_visibility"] == ("temporal_visibility", "temporal", [])
    # Every extension the seed declares is carried, in the database that declares it.
    assert by["hindsight"][2] == ["vector", "pg_trgm"]
    assert by["via_negativa"][2] == ["vector"]
    assert by["memory"][2] == ["vector"]
    assert by["quad_ledger"][2] == []
    # temporal owns two databases: the role is minted once, the databases twice.
    assert len(rows) == 17
    assert len({owner for _d, owner, _e in rows}) == 16


def test_the_image_is_what_production_pins_not_what_the_script_guesses():
    shadow = load_shadow()
    assert (
        shadow.db_image()
        == "ghcr.io/chidionyema/postgres-partman:18.1-postgres-partman"
    )


def test_the_seed_script_is_guarded_not_blind():
    shadow = load_shadow()
    sql = shadow.db_sql(shadow.database_rows())
    assert sql.count("CREATE DATABASE") == 17
    assert sql.count("CREATE ROLE") == 16  # temporal once, though it owns two databases
    assert sql.count("CREATE EXTENSION") == 5  # vector x4, pg_trgm x1
    for db, owner, _e in shadow.database_rows():
        assert f'CREATE DATABASE "{db}" OWNER "{owner}"' in sql, (db, owner)
    assert "shadow-vault-stand-in" in sql  # the vault stand-in's placeholder, verbatim


def test_the_service_is_named_what_the_workloads_resolve():
    shadow = load_shadow()
    kinds = {
        (o["kind"], o["metadata"].get("name"), o["metadata"].get("namespace"))
        for o in shadow.db_standin_objects()
    }
    assert ("Service", "estate-rw", "estate-db") in kinds
    assert ("Namespace", "estate-db", None) in kinds
    deploy = next(o for o in shadow.db_standin_objects() if o["kind"] == "Deployment")
    container = deploy["spec"]["template"]["spec"]["containers"][0]
    assert container["image"] == shadow.db_image()
    env = {e["name"]: e["value"] for e in container["env"]}
    assert env["POSTGRES_SUPERUSER_PASSWORD"] == shadow.VAULT_PLACEHOLDER
    assert "ssl=on" in container["args"][0]  # unified-memory connects sslmode=require


def test_only_paths_that_point_at_the_database_get_the_stand_in():
    shadow = load_shadow()
    assert shadow.db_needs_standin(["platform/llm"]) is True
    assert shadow.db_needs_standin(["platform/secrets"]) is False


def test_a_stand_in_that_cannot_be_laid_fails_the_run(monkeypatch):
    shadow = load_shadow()

    def dead_apply(cmd, input=None, capture_output=None, text=None, timeout=None):
        return subprocess.CompletedProcess(cmd, 1, "", "no such namespace estate-db")

    monkeypatch.setattr(shadow.subprocess, "run", dead_apply)
    assert "could not lay the database stand-in" in shadow.stand_in_database()


def test_a_postgres_that_never_becomes_ready_fails_the_run(monkeypatch):
    shadow = load_shadow()

    def apply_ok(cmd, input=None, capture_output=None, text=None, timeout=None):
        return subprocess.CompletedProcess(cmd, 0, "deploy configured", "")

    def never_ready(cmd, check=None, timeout=None):
        return subprocess.CompletedProcess(cmd, 1, "", "timed out waiting")

    monkeypatch.setattr(shadow.subprocess, "run", apply_ok)
    monkeypatch.setattr(shadow, "kube", never_ready)
    assert "never became available" in shadow.stand_in_database()


def test_a_postgres_that_refuses_the_seed_fails_the_run(monkeypatch):
    shadow = load_shadow()

    class Fake:
        def __init__(self, code, out="", err=""):
            self.returncode, self.stdout, self.stderr = code, out, err

    calls = []

    def fake_run(cmd, input=None, capture_output=None, text=None, timeout=None, **_kw):
        calls.append((cmd, input))
        if cmd[:2] == ["kubectl", "apply"]:
            return Fake(0, "namespace/estate-db created", "")
        if "wait" in cmd:
            return Fake(0, "deployment condition met", "")
        return Fake(1, "", 'ERROR:  extension "vector" is not available')

    monkeypatch.setattr(shadow.subprocess, "run", fake_run)
    verdict = shadow.stand_in_database()
    assert "refused the estate's seed" in verdict
    assert "vector" in verdict
    seeded = [inp for cmd, inp in calls if cmd[:2] == ["kubectl", "-n"]][-1]
    assert 'CREATE DATABASE "temporal_visibility"' in seeded


def test_a_healthy_stand_in_says_so_and_lies_about_nothing(monkeypatch, capsys):
    shadow = load_shadow()

    class Fake:
        def __init__(self, code, out="", err=""):
            self.returncode, self.stdout, self.stderr = code, out, err

    seeded = []

    def fake_run(cmd, input=None, capture_output=None, text=None, timeout=None, **_kw):
        if cmd[:2] == ["kubectl", "apply"]:
            return Fake(0, "created", "")
        if "wait" in cmd:
            return Fake(0, "deployment condition met", "")
        seeded.append(input)
        return Fake(0, "CREATE ROLE", "")

    monkeypatch.setattr(shadow.subprocess, "run", fake_run)
    assert shadow.stand_in_database() is None
    assert 'CREATE DATABASE "memory" OWNER "memory"' in seeded[0]
    assert "database stand-in estate-db/estate-rw seeded" in capsys.readouterr().out


def test_the_apply_is_a_document_stream_never_a_json_array(monkeypatch):
    """Greenlane 38096348716: kubectl refuses a top-level JSON array with "invalid
    object to validate", so every full shadow run died 53s into verify."""
    shadow = load_shadow()

    class Fake:
        def __init__(self, code, out="", err=""):
            self.returncode, self.stdout, self.stderr = code, out, err

    applied = []

    def fake_run(cmd, input=None, capture_output=None, text=None, timeout=None, **_kw):
        if cmd[:2] == ["kubectl", "apply"]:
            applied.append(input)
            return Fake(0, "created", "")
        return Fake(0, "deployment condition met", "")

    monkeypatch.setattr(shadow.subprocess, "run", fake_run)
    assert shadow.stand_in_database() is None
    (manifest,) = applied
    docs = [json.loads(d) for d in manifest.split("\n---\n")]
    kinds = [d["kind"] for d in docs]
    assert kinds == ["Namespace", "Deployment", "Service"]
    assert docs[1]["metadata"]["name"] == shadow.DB_STAND_IN
    # Available must mean serving (greenlane 38118221613: the seed exec raced initdb
    # and found no socket), so the deployment carries a real readiness probe.
    (container,) = docs[1]["spec"]["template"]["spec"]["containers"]
    assert container["readinessProbe"]["exec"]["command"][-1].startswith("pg_isready")
