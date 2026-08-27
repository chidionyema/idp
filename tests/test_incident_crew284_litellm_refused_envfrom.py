"""Incident 2026-08-26 (crew#284): the llm Kustomization stayed Ready=False for a day with
`Deployment/llm/litellm dry-run failed: admission webhook "validate.kyverno.svc-fail" denied`
(secrets-not-from-env-vars, no-optional-secret-references) and llm.mumchimp.com never got a
record. The class: a plain workload under platform/ that CI never judged, because
bin/idp-kyverno-render and bin/idp-ci step 9 covered HelmReleases only. Rule (rung 4): every
platform dir that ships a plain workload is in the idp-ci kyverno dir list, and litellm carries
no envFrom and no optional secret."""
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
KINDS = re.compile(r"^kind: (Deployment|StatefulSet|DaemonSet|Job|CronJob)$", re.M)


def test_ci_judges_every_plain_workload_dir() -> None:
    ci = (ROOT / "bin" / "idp-ci").read_text()
    assert "Deployment|StatefulSet|DaemonSet|Job|CronJob" in ci, "idp-ci step 9 lists HelmRelease dirs only"
    tool = (ROOT / "bin" / "idp-kyverno-render").read_text()
    assert 'kinds = {"Deployment", "StatefulSet", "DaemonSet", "Job", "CronJob", "Pod"}' in tool


def test_litellm_takes_no_secret_from_env() -> None:
    docs = [d for d in yaml.safe_load_all((ROOT / "platform/llm/litellm.yaml").read_text()) if isinstance(d, dict)]
    dep = next(d for d in docs if d["kind"] == "Deployment")
    for c in dep["spec"]["template"]["spec"]["containers"]:
        assert "envFrom" not in c
        for e in c.get("env", []):
            assert "secretKeyRef" not in (e.get("valueFrom") or {})
    for v in dep["spec"]["template"]["spec"]["volumes"]:
        if "secret" in v:
            assert not v["secret"].get("optional"), f"volume {v['name']} is optional"
