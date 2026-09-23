"""crew#684 CP2: the open-reds table reads the Alertmanager the cluster actually runs.

The mistake class this guards is fix-proved-on-the-wrong-surface: a page that names a
Service by hand, proven only on a mocked proxy, and the real Service is called something
else or the service account may not proxy to it. So the hook's constants are checked
against the HelmRelease that makes the Service, and the RBAC that lets the portal reach it.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "backstage/packages/app/src/modules/home/useOpenReds.ts"
RBAC = ROOT / "platform/backstage/base/rbac.yaml"
KPS = ROOT / "platform/monitoring/kube-prometheus-stack.yaml"
OPS = ROOT / "backstage/packages/app/src/modules/home/Ops.tsx"


def _const(name: str) -> str:
    m = re.search(rf"export const {name} = '([^']+)'", HOOK.read_text())
    assert m, f"{HOOK.name} must export {name} as a string literal"
    return m.group(1)


def _helm_release() -> dict:
    docs = [d for d in yaml.safe_load_all(KPS.read_text()) if d]
    rels = [d for d in docs if d.get("kind") == "HelmRelease"]
    assert len(rels) == 1, "one kube-prometheus-stack HelmRelease"
    return rels[0]


def test_the_alertmanager_service_the_hook_names_is_the_one_the_chart_makes():
    rel = _helm_release()
    release = rel["spec"].get("releaseName") or rel["metadata"]["name"]
    assert rel["spec"]["values"]["alertmanager"]["enabled"] is True
    # charts/kube-prometheus-stack/templates/alertmanager/service.yaml:
    #   name: {{ template "kube-prometheus-stack.fullname" . }}-alertmanager
    assert len(release) <= 26, "the chart truncates fullname to 26 characters"
    assert _const("ALERTMANAGER_SERVICE") == f"{release}-alertmanager"
    assert _const("ALERTMANAGER_NAMESPACE") == rel["metadata"]["namespace"]


def test_the_portal_service_account_may_proxy_to_a_service():
    docs = [d for d in yaml.safe_load_all(RBAC.read_text()) if d]
    roles = [d for d in docs if d.get("kind") == "ClusterRole"]
    assert roles, "the portal has a ClusterRole"
    rules = [r for role in roles for r in role["rules"]]
    proxy = [r for r in rules if "services/proxy" in r.get("resources", [])]
    assert proxy, "rbac.yaml must grant services/proxy, or Alertmanager answers 403"
    assert all(set(r["verbs"]) <= {"get"} for r in proxy), "read only"


def test_a_source_that_cannot_be_read_is_said_never_counted_as_zero():
    ops = OPS.read_text()
    assert "ops-reds-unread" in ops
    hook = HOOK.read_text()
    assert "Promise.allSettled" in hook, "one source down must not hide the other"
    assert "unread" in hook
