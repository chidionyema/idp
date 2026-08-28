"""Incident crew#325, 2026-08-26: the https-llm and https-langfuse listeners sat unpublished on
the cluster for ~90 minutes and no session could read why, because a runner has no kube path
and Flux's only alert channel was Telegram. The rule: every flux-system Kustomization event
reaches a place a session can read (a repository_dispatch on idp, printed by a workflow)."""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
ALERTS = ROOT / "platform" / "alerts-github"   # crew#406: the ledger has its own Kustomization


def _docs(path: Path) -> list[dict]:
    return [d for d in yaml.safe_load_all(path.read_text()) if d]


def test_every_flux_kustomization_event_reaches_a_readable_ledger() -> None:
    providers = {d["metadata"]["name"]: d for p in ALERTS.glob("provider*.yaml") for d in _docs(p) if d["kind"] == "Provider"}
    alerts = [d for d in _docs(ALERTS / "alert.yaml") if d["kind"] == "Alert"]
    readable = [
        a for a in alerts
        if providers.get(a["spec"]["providerRef"]["name"], {}).get("spec", {}).get("type") == "githubdispatch"
        and a["spec"].get("eventSeverity") == "info"
        and {"kind": "Kustomization", "name": "*", "namespace": "flux-system"} in a["spec"]["eventSources"]
    ]
    assert readable, "no info-severity Alert forwards every flux-system Kustomization to a githubdispatch Provider"
    provider = providers[readable[0]["spec"]["providerRef"]["name"]]
    # The dispatch signs in as the App that already writes to idp; a second credential is stitching.
    assert provider["spec"]["secretRef"] == {"name": "github-app"}
    wired = yaml.safe_load((ALERTS / "kustomization.yaml").read_text())["resources"]
    assert all(p.name in wired for p in ALERTS.glob("provider*.yaml")), wired


def test_the_dispatch_has_a_workflow_that_prints_it() -> None:
    wf = yaml.safe_load((ROOT / ".github" / "workflows" / "flux-events.yml").read_text())
    # PyYAML reads the bare key `on` as boolean True.
    triggers = wf.get("on", wf.get(True))
    assert "repository_dispatch" in triggers, triggers
    # crew#307, 2026-08-28: this workflow was a ledger -- it printed the reconcile and exited 0,
    # so a red cluster produced a green run. Flux reported `Deployment/backstage/catalogue
    # status: 'Failed'` every ten minutes from 2026-08-27 16:05 and nothing read it, and the
    # founder's portal served a stale pod for seventeen hours. It is now an alarm: a red event
    # opens a P0 issue and fails the run. An alarm that cannot open the issue is the ledger
    # again, so `issues: write` is the job, not a surface. The scope is still the smallest that
    # does it -- this asserts equality, so `actions: write`, `contents: write` or
    # `pull-requests: write` still fail here.
    assert wf["permissions"] == {"contents": "read", "issues": "write"}, (
        "the alarm opens a P0 and nothing else: contents:read + issues:write exactly")
