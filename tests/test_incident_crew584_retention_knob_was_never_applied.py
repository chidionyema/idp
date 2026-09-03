"""crew#584 CP-I: the registry promised `logs-metrics-store/enterprise knobs: retention_days: 7`
and nothing on the cluster applied it; SigNoz kept whatever the UI was last hand-set to.

platform/observability/signoz-retention.yaml is the applier: a daily Job logs in with the
mounted signoz-root secret and sets the SigNoz TTL of traces, metrics and logs to the knob.
These tests pin the knob in the ConfigMap to the registry value, keep the secret a mounted
file (Kyverno), and run the script's plan/apply against a fake API."""

import pathlib
import types

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "platform" / "observability" / "signoz-retention.yaml"
DOCS = {
    (d["kind"], d["metadata"]["name"]): d
    for d in yaml.safe_load_all(MANIFEST.read_text())
    if d
}


def _registry_knob():
    reg = yaml.safe_load((ROOT / "platform" / "features" / "features.yaml").read_text())
    feat = next(f for f in reg["features"] if f["name"] == "logs-metrics-store")
    tier = next(t for t in feat["tiers"] if t["name"] == "enterprise")
    return tier["knobs"]["retention_days"]


def _script():
    mod = types.ModuleType("apply")
    exec(
        DOCS[("ConfigMap", "signoz-retention-apply")]["data"]["apply.py"], mod.__dict__
    )
    return mod


def test_the_configmap_knob_is_the_registry_knob():
    assert (
        int(DOCS[("ConfigMap", "signoz-retention")]["data"]["retention_days"])
        == _registry_knob()
    )


def test_the_cronjob_mounts_the_root_secret_as_files_and_reads_the_knob():
    pod = DOCS[("CronJob", "signoz-retention")]["spec"]["jobTemplate"]["spec"][
        "template"
    ]["spec"]
    c = pod["containers"][0]
    assert all("valueFrom" not in e for e in c.get("env", []))
    vols = {v["name"]: v for v in pod["volumes"]}
    assert vols["signoz-root"]["secret"]["secretName"] == "signoz-root"
    assert vols["knob"]["configMap"]["name"] == "signoz-retention"
    mounts = {m["name"]: m["mountPath"] for m in c["volumeMounts"]}
    assert mounts["signoz-root"] == "/secrets" and mounts["knob"] == "/config"
    assert (
        pod["priorityClassName"] == "platform-batch"
    )  # the radio-room class is strictly the six
    assert pod["automountServiceAccountToken"] is False
    assert c["securityContext"]["readOnlyRootFilesystem"] is True
    kust = yaml.safe_load(
        (ROOT / "platform" / "observability" / "kustomization.yaml").read_text()
    )
    assert "signoz-retention.yaml" in kust["resources"]


class _Fake:
    def __init__(self, current):
        self.current, self.calls = current, []

    def __call__(self, method, path, body=None, token=None, params=None):
        self.calls.append((method, path, body, token, params))
        if path == "/api/v2/sessions/context":
            return 200, {"data": {"orgs": [{"id": "org-1"}]}}
        if path == "/api/v2/sessions/email_password":
            assert body == {"email": "root@example", "password": "pw", "orgId": "org-1"}
            return 200, {"data": {"accessToken": "jwt"}}
        assert token == "jwt"
        if method == "GET":
            sig = params["type"]
            return 200, {
                f"{sig}_ttl_duration_hrs": self.current[sig],
                "status": "success",
            }
        self.current[params["type"]] = int(params["duration"].rstrip("h"))
        return 200, {"message": "ok"}


def test_plan_sets_only_the_signals_that_differ_and_uses_hours():
    m = _script()
    fake = _Fake({"traces": 168, "metrics": 720, "logs": 72})
    token = m.login(fake, "root@example", "pw")
    todo = m.plan(fake, token, 7)
    assert todo == [("metrics", 720), ("logs", 72)]
    assert m.apply(fake, token, 7, todo) == []
    posts = [c for c in fake.calls if c[0] == "POST" and c[1] == "/api/v1/settings/ttl"]
    assert [(c[4]["type"], c[4]["duration"]) for c in posts] == [
        ("metrics", "168h"),
        ("logs", "168h"),
    ]
    assert fake.current == {"traces": 168, "metrics": 168, "logs": 168}
