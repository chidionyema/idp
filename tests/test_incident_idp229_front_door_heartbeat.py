"""Incident idp#229 / crew#307 (2026-08-27): login-drill.yml carried a */5 cron and oke-check FAILed
whenever the newest run was over 20 minutes old. Measured over the last 30 runs: 3 came from the cron,
17 from pushes, 10 from dispatches, gaps up to 68 minutes. GitHub drops high-frequency schedules, so
the heartbeat graded GitHub's clock. Rules (rung 2 properties over the manifests, rung 4 for the drift):
  1. the five-minute pulse is a CronJob on the estate's cluster, restricted-PSA, pinned to the image
     the chaos receipt already uses, and it writes the object the reader names;
  2. the GitHub heartbeat threshold is the catalogue's max_age_hours, never tighter than GitHub honours;
  3. drills/catalogue.yaml names the workflow file that exists and copies its cron verbatim (the
     catalogue promised a quietly unscheduled drill shows up as a diff; the login-drill row had drifted
     to oke-check.yml / "17 6 * * *" while the workflow said login-drill.yml / "*/5")."""
import pathlib
import re
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _docs(rel):
    return [d for d in yaml.safe_load_all((ROOT / rel).read_text()) if d]


def test_pulse_is_a_restricted_cronjob_writing_the_object_the_reader_reads():
    cj = [d for d in _docs("platform/identity/front-door-heartbeat.yaml") if d["kind"] == "CronJob"][0]
    assert cj["spec"]["schedule"] == "*/5 * * * *" and cj["spec"]["concurrencyPolicy"] == "Forbid"
    pod = cj["spec"]["jobTemplate"]["spec"]["template"]["spec"]
    assert pod["securityContext"]["runAsNonRoot"] is True and pod["automountServiceAccountToken"] is False
    c = pod["containers"][0]
    sc = c["securityContext"]
    assert sc["readOnlyRootFilesystem"] and sc["capabilities"] == {"drop": ["ALL"]} and not sc["allowPrivilegeEscalation"]
    chaos = (ROOT / "platform/chaos/backstage-pod-kill.yaml").read_text()
    assert c["image"] in chaos, "one pinned oci-cli image for every receipt writer"
    script = c["args"][0]
    obj = re.search(r"--name (drills/\S+)", script).group(1)
    assert obj == "drills/front-door-heartbeat"
    reader = (ROOT / "bin/idp-door-heartbeat").read_text()
    assert 'NAME=front-door-heartbeat' in reader and '"drills/$NAME"' in reader
    env = {e["name"]: e["value"] for e in c["env"]}
    assert env["DOOR_URL"] == "https://catalogue.${ESTATE_ZONE}/" and env["IDENTITY_URL"] == "${ESTATE_OIDC_DOMAIN_URL}"
    assert "front-door-heartbeat.yaml" in (ROOT / "platform/identity/kustomization.yaml").read_text()


def test_github_heartbeat_threshold_is_the_catalogue_age():
    cat = {d["name"]: d for d in yaml.safe_load((ROOT / "drills/catalogue.yaml").read_text())["drills"]}
    rebuild = (ROOT / "bin/idp-oke-rebuild").read_text()
    m = re.search(r'idp-drill-heartbeat" login-drill\.yml (\d+)', rebuild)
    assert m and int(m.group(1)) == cat["login-drill"]["max_age_hours"] * 60
    assert 'step door-heartbeat "$IDP/bin/idp-door-heartbeat"' in rebuild


def test_incident_idp229_catalogue_names_the_workflow_and_its_cron_verbatim():
    for d in yaml.safe_load((ROOT / "drills/catalogue.yaml").read_text())["drills"]:
        if d.get("pending"):
            continue
        wf = ROOT / ".github/workflows" / d["workflow"]
        assert wf.is_file(), (d["name"], d["workflow"])
        crons = [s["cron"] for s in (yaml.safe_load(wf.read_text()).get(True) or yaml.safe_load(wf.read_text()).get("on"))["schedule"]]
        assert d["schedule"] in crons, (d["name"], d["schedule"], crons)
