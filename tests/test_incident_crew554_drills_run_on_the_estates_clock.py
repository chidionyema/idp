"""Incident crew#554 (2026-08-28 02:38Z): every hourly cron on the GitHub account fired 1-3 times in
24h (verify-drill 1/24, trace-drill 2/24, login-drill 2/24, stale 1/24). The catalogue's green ages
came from push runs; nothing was scheduling the drills. platform/drills/drill-dispatcher.yaml runs
them on the estate's clock as the GitHub App. Rules (rung 2 over the manifests, rung 4 for drift):
  1. the dispatcher is a restricted CronJob on the pinned image every estate CronJob uses, hourly,
     Forbid, authenticating as the App Secret Flux's githubdispatch Provider already reads;
  2. WORKFLOWS is exactly the catalogue's hourly, non-pending workflows -- a drill added to the
     catalogue without the dispatcher, or the reverse, is a diff;
  3. the repo slug comes from estate-config (LAW 46), never a literal in platform/;
  4. the embedded dispatcher compiles, and its plan() skips a workflow that already ran this hour
     (GitHub's own schedule, or a push) and dispatches one that did not."""
from __future__ import annotations

import pathlib
import re
from datetime import datetime, timezone

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "platform/drills/drill-dispatcher.yaml"


def _cronjob() -> dict:
    return [d for d in yaml.safe_load_all(MANIFEST.read_text()) if d and d["kind"] == "CronJob"][0]


def _container() -> dict:
    return _cronjob()["spec"]["jobTemplate"]["spec"]["template"]["spec"]["containers"][0]


def _script() -> str:
    args = _container()["args"][0]
    return args[args.index("<<'PY'\n") + len("<<'PY'\n"):args.rindex("\nPY")]


def _hourly_workflows() -> set[str]:
    out = set()
    for d in yaml.safe_load((ROOT / "drills/catalogue.yaml").read_text())["drills"]:
        if d.get("pending"):
            continue
        minute, hour, *_ = d["schedule"].split()
        if hour == "*" and re.fullmatch(r"\d+", minute):
            out.add(d["workflow"])
    return out


def test_dispatcher_is_a_restricted_hourly_cronjob_on_the_pinned_image() -> None:
    cj = _cronjob()
    assert cj["metadata"]["namespace"] == "flux-system", "the github-app Secret lives in flux-system"
    minute, hour, *_ = cj["spec"]["schedule"].split()
    assert hour == "*" and minute.isdigit() and cj["spec"]["concurrencyPolicy"] == "Forbid"
    pod = cj["spec"]["jobTemplate"]["spec"]["template"]["spec"]
    assert pod["securityContext"]["runAsNonRoot"] is True and pod["automountServiceAccountToken"] is False
    psc = pod["securityContext"]
    assert psc.get("runAsUser", 0) != 0 and psc.get("fsGroup") == psc["runAsUser"], "the 0400 Secret is readable only when the pod group owns it (REWORK 9b57aef)"
    c = _container()
    sc = c["securityContext"]
    assert sc["readOnlyRootFilesystem"] and sc["capabilities"] == {"drop": ["ALL"]} and not sc["allowPrivilegeEscalation"]
    assert c["image"] in (ROOT / "platform/chaos/backstage-pod-kill.yaml").read_text(), "one pinned image for every estate CronJob"
    assert not any("valueFrom" in e for e in c["env"]), "kyverno secrets-not-from-env-vars: the App identity is files, never env"
    vols = {v["secret"]["secretName"] for v in pod["volumes"] if "secret" in v}
    assert vols == {"github-app"}
    env = {e["name"]: e["value"] for e in c["env"]}
    assert env["GITHUB_APP_DIR"] in {vm["mountPath"] for vm in c["volumeMounts"] if vm["name"] == "github-app"}
    es = [d for d in yaml.safe_load_all((ROOT / "platform/alerts-github/github-app.yaml").read_text()) if d][0]
    assert es["spec"]["target"]["name"] == "github-app" and es["metadata"]["namespace"] == "flux-system"
    assert "drill-dispatcher.yaml" in (ROOT / "platform/drills/kustomization.yaml").read_text()


def test_workflows_are_exactly_the_catalogues_hourly_drills() -> None:
    env = {e["name"]: e.get("value") for e in _container()["env"]}
    assert set(env["WORKFLOWS"].split()) == _hourly_workflows()
    for wf in env["WORKFLOWS"].split():
        text = (ROOT / ".github/workflows" / wf).read_text()
        assert "workflow_dispatch" in text, f"{wf} cannot be dispatched"


def test_repo_slug_is_estate_config_not_a_literal() -> None:
    env = {e["name"]: e.get("value") for e in _container()["env"]}
    assert env["GITHUB_REPO"] == "${ESTATE_GITHUB_REPO}"
    cfg = yaml.safe_load((ROOT / "clusters/oke/estate-config.yaml").read_text())
    assert re.fullmatch(r"[\w.-]+/[\w.-]+", cfg["data"]["ESTATE_GITHUB_REPO"])
    assert "github.com/" not in MANIFEST.read_text().split("PY\n", 1)[0].replace("api.github.com", "")
    flux = (ROOT / "clusters/oke/platform.yaml").read_text()
    assert "path: ./platform/drills" in flux and "name: estate-config" in flux


def test_plan_skips_a_workflow_that_already_ran_this_hour_and_dispatches_one_that_did_not() -> None:
    ns: dict = {"__name__": "test"}
    exec(compile(_script(), str(MANIFEST), "exec"), ns)  # noqa: S102 - the manifest's own program, main() not called
    now = datetime(2026, 8, 28, 3, 3, tzinfo=timezone.utc)
    assert ns["plan"]([], now) == "dispatch"
    assert ns["plan"]([{"created_at": "2026-08-28T02:23:07Z", "event": "schedule", "id": 1}], now) == "dispatch"
    got = ns["plan"]([{"created_at": "2026-08-28T03:00:41Z", "event": "push", "id": 7}], now)
    assert got.startswith("skipped: push run 7")
    assert ns["PERMISSIONS"] == {"actions": "write", "metadata": "read"}
