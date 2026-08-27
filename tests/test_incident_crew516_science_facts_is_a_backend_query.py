"""Incident 2026-08-27 (crew#516 CP5, LAW 50): the science lane's only writer was a launchd tick on
the founder's Mac (`com.founder.sciencecollect`), skipped three times that day under load 55, and
its 41 stores are 31 Mac home paths, so a cluster copy of the script would read nothing. Rule
(rung 4, incident test): the cluster grades the science lane by querying the collector's backend
(platform/science/science-facts.yaml): one or more sources with rows in the window is ok; a backend
that answers with no science row is FAIL and names the attribute it looked for; a backend that
cannot be queried is BLIND, never ok. The Flux row, the oke-check job and the reader are wired, so
the receipt is read the way cluster-state and telemetry-coverage are."""
import pathlib
import types
from datetime import datetime, timezone

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "platform" / "science" / "science-facts.yaml"
NOW = datetime(2026, 8, 27, 15, 0, tzinfo=timezone.utc)


def _collector():
    docs = [d for d in yaml.safe_load_all(MANIFEST.read_text()) if d]
    cm = next(d for d in docs if d["kind"] == "ConfigMap")
    mod = types.ModuleType("collect")
    exec(compile(cm["data"]["collect.py"], "collect.py", "exec"), mod.__dict__)
    return mod


def test_incident_crew516_backend_query_grades_both_ways():
    mod = _collector()
    rows = [("spend", "12", "2026-08-27 14:50:00"), ("ships", "3", "2026-08-27 09:00:00")]
    head, body = mod.main(clickhouse=lambda sql: rows, now=NOW)
    assert head.startswith("ok science-facts") and "sources=2 rows=15" in head, head
    assert body["sources"]["spend"] == {"rows": 12, "last_at": "2026-08-27 14:50:00"}
    assert body["backend_errors"] == {}

    # FAIL: the backend answers, and holds no science row: the writer path is dead, and the head says which attribute.
    head, body = mod.main(clickhouse=lambda sql: [], now=NOW)
    assert head.startswith("FAIL science-facts") and "sources=0" in head and "science.source" in head, head

    # BLIND: the backend cannot be queried. Never ok, never FAIL.
    def down(sql):
        raise ConnectionError("signoz-clickhouse:8123 refused")

    head, body = mod.main(clickhouse=down, now=NOW)
    assert head.startswith("BLIND science-facts"), head
    assert "refused" in body["backend_errors"]["logs"]


def test_incident_crew516_query_is_the_backend_not_a_file():
    mod = _collector()
    q = mod.QUERY
    assert "signoz_logs.distributed_logs_v2" in q and "attributes_string['science.source']" in q, q
    assert "GROUP BY source" in q


def test_incident_crew516_receipt_is_wired_end_to_end():
    docs = [d for d in yaml.safe_load_all(MANIFEST.read_text()) if d]
    cron = next(d for d in docs if d["kind"] == "CronJob")
    args = cron["spec"]["jobTemplate"]["spec"]["template"]["spec"]["containers"][0]["args"][0]
    assert "--name science/facts" in args and "estate-drill-receipts" in args
    # the Secret is a file mount, never an env var (Kyverno)
    c = cron["spec"]["jobTemplate"]["spec"]["template"]["spec"]["containers"][0]
    assert not any(e["name"].lower().endswith("password") for e in c.get("env", []))
    assert any(v["mountPath"] == "/secrets" for v in c["volumeMounts"])
    flux = [d for d in yaml.safe_load_all((ROOT / "clusters/oke/platform.yaml").read_text()) if d]
    row = next(d for d in flux if d["metadata"]["name"] == "science")
    assert row["spec"]["path"] == "./platform/science"
    assert {"name": "observability"} in row["spec"]["dependsOn"]
    kust = yaml.safe_load((ROOT / "platform/science/kustomization.yaml").read_text())
    assert kust["namespace"] == "observability" and "science-facts.yaml" in kust["resources"]
    wf = yaml.safe_load((ROOT / ".github/workflows/oke-check.yml").read_text())
    job = wf["jobs"]["science-facts"]
    assert any("bin/idp-science-facts" in (s.get("run") or "") for s in job["steps"])
    reader = (ROOT / "bin/idp-science-facts").read_text()
    assert "--name science/facts" in reader and 'kv.get("sources", 0)) == 0' in reader
