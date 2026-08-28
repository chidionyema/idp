"""crew#539 DoD item 2: failing langfuse-web pages the founder within 5 minutes, as a Chaos Mesh
drill with a receipt graded from outside the cluster.

Each check is one way the drill could go silent: the Schedule stops selecting langfuse-web, the
namespace stops admitting chaos, the receipt task stops asking Alertmanager for the right alert,
the grader stops being run, or the catalogue forgets the row. No test opens a socket.
"""
import pathlib
import re

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
CHAOS = ROOT / "platform/chaos"
SCHEDULE = yaml.safe_load((CHAOS / "langfuse-alert-drill.yaml").read_text())
TEMPLATES = {t["name"]: t for t in SCHEDULE["spec"]["workflow"]["templates"]}


def test_schedule_fails_every_langfuse_web_pod_long_enough_for_the_5m_for():
    assert SCHEDULE["kind"] == "Schedule" and SCHEDULE["metadata"]["namespace"] == "observability"
    assert SCHEDULE["spec"]["type"] == "Workflow" and SCHEDULE["spec"]["concurrencyPolicy"] == "Forbid"
    pc = TEMPLATES["fail-web"]["podChaos"]
    assert pc["action"] == "pod-failure" and pc["mode"] == "all"
    assert pc["selector"]["namespaces"] == ["observability"]
    # the langfuse chart 2.0.2 Deployment langfuse-web selector, rendered in the PR (helm template)
    assert pc["selector"]["labelSelectors"] == {"app.kubernetes.io/name": "langfuse", "app": "web"}
    minutes = int(pc["duration"].rstrip("m"))
    assert minutes >= 8, "FounderSurfaceDown has for: 5m plus scrape and group_wait; 8m is the floor"
    assert TEMPLATES["experiment"]["templateType"] == "Parallel"
    assert set(TEMPLATES["experiment"]["children"]) == {"fail-web", "receipt"}


def test_the_alert_the_drill_waits_for_is_the_one_the_probe_rule_raises():
    rules = yaml.safe_load((ROOT / "platform/monitoring/rules/estate.yaml").read_text())
    names = {r["alert"] for g in rules["spec"]["groups"] for r in g["rules"] if "alert" in r}
    assert "FounderSurfaceDown" in names
    args = TEMPLATES["receipt"]["task"]["container"]["args"][0]
    assert 'alertname="FounderSurfaceDown"' in args
    assert '"langfuse" in a["labels"].get("instance", "")' in args
    assert 'alertmanager_notifications_total{integration="telegram"}' in args
    assert "kps-alertmanager.monitoring.svc:9093" in args and "kps-prometheus.monitoring.svc:9090" in args
    assert "--auth instance_principal" in args and "--name chaos/langfuse-alert-drill" in args
    assert re.search(r"^\s*line = f\"FAIL langfuse-alert-drill", args, re.M), "no receipt is written on silence"


def test_receipt_task_is_restricted_pss():
    c = TEMPLATES["receipt"]["task"]["container"]
    sc = c["securityContext"]
    assert sc["runAsNonRoot"] is True and sc["allowPrivilegeEscalation"] is False
    assert sc["readOnlyRootFilesystem"] is True and sc["capabilities"] == {"drop": ["ALL"]}
    assert sc["seccompProfile"] == {"type": "RuntimeDefault"}
    assert "limits" in c["resources"]


def test_namespace_admits_chaos_and_the_flux_row_waits_for_monitoring():
    ns = yaml.safe_load((ROOT / "platform/observability/namespace.yaml").read_text())
    assert ns["metadata"]["labels"]["chaos-mesh.org/inject"] == "enabled"
    rows = [d for d in yaml.safe_load_all((ROOT / "clusters/oke/platform.yaml").read_text()) if d]
    chaos = next(d for d in rows if d["metadata"]["name"] == "chaos")
    assert {"name": "monitoring"} in chaos["spec"]["dependsOn"]
    kust = yaml.safe_load((CHAOS / "kustomization.yaml").read_text())
    assert "langfuse-alert-drill.yaml" in kust["resources"]
    assert "langfuse-alert-drill-first-run.yaml" in kust["resources"]


def test_grader_is_parametrised_and_run_by_oke_check_under_the_catalogue_row():
    grader = (ROOT / "bin/idp-chaos-drill").read_text()
    assert 'NAME="${1:-backstage-pod-kill}"' in grader and 'ROW="${2:-chaos-drill}"' in grader
    body = grader.split("set -uo pipefail", 1)[1]
    assert "chaos-drill  " not in body, "a literal row label would mislabel the alert-drill receipt"
    wf = yaml.safe_load((ROOT / ".github/workflows/oke-check.yml").read_text())
    job = wf["jobs"]["alert-drill"]
    runs = [s.get("run", "") for s in job["steps"]]
    assert "bin/idp-chaos-drill langfuse-alert-drill alert-drill" in runs
    cat = yaml.safe_load((ROOT / "drills/catalogue.yaml").read_text())
    row = next(d for d in cat["drills"] if d["name"] == "alert-drill")
    assert row["workflow"] == "oke-check.yml" and row["job"] == "alert-drill"
    doc = (ROOT / "docs/onboarding/monitoring.md").read_text()
    assert "bin/idp-chaos-drill langfuse-alert-drill alert-drill" in doc
