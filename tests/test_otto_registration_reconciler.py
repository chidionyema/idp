"""Registration reconciler (build order step 6, docs/specs/otto-platform-v1/
EVENT-GATEWAY-TENANCY.md, receipt layer 3 "vendor registration"): a scheduled job in
platform/otto-golden/ calls Telegram's own getWebhookInfo with the vault-mounted token
(the SAME Secret telegram-secret.yaml already renders, never a second vault entry, never a
literal token anywhere in the manifest) and reports two metrics per tenant/channel:
channel_registration_ok (0/1) and channel_pending_updates (a count).

Rung 2 properties over the checkout (no network, no cluster): the manifest parses, the
schedule and retry shape are sane, the token never appears as a literal, the metric names
match the spec exactly, and the reconciler's own script never prints the token it reads.
"""

import pathlib
import re

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "platform" / "otto-golden" / "registration-reconciler.yaml"
KUSTOMIZATION = ROOT / "platform" / "otto-golden" / "kustomization.yaml"

# The estate's own live-shaped Telegram bot token pattern (see telegram-secret.yaml's docstring
# and GHSA-3vpc-7q5r-276h): a real token is digits, a colon, then 35 base64url-ish characters.
LIVE_TOKEN_RE = re.compile(r"\b\d{6,12}:[A-Za-z0-9_-]{30,}\b")


def _docs():
    return [d for d in yaml.safe_load_all(MANIFEST.read_text()) if d]


def _configmap():
    return next(d for d in _docs() if d["kind"] == "ConfigMap")


def _script():
    return _configmap()["data"]["check.py"]


def _cronjob():
    return next(d for d in _docs() if d["kind"] == "CronJob")


def _container():
    return _cronjob()["spec"]["jobTemplate"]["spec"]["template"]["spec"]["containers"][
        0
    ]


def test_manifest_parses_as_a_configmap_and_a_cronjob():
    kinds = {d["kind"] for d in _docs()}
    assert kinds == {"ConfigMap", "CronJob"}


def test_cronjob_runs_every_five_minutes():
    cj = _cronjob()
    assert cj["metadata"]["namespace"] == "otto-golden"
    assert cj["spec"]["schedule"] == "*/5 * * * *"


def test_cronjob_retry_and_deadline_shape_is_sane():
    """A stuck run must not pile up behind the next one, and a hung getWebhookInfo call must
    not run forever."""
    spec = _cronjob()["spec"]
    assert spec["concurrencyPolicy"] == "Forbid"
    job = spec["jobTemplate"]["spec"]
    assert 0 < job["backoffLimit"] <= 3
    assert 0 < job["activeDeadlineSeconds"] <= 300, (
        "a schedule of 5 minutes needs a deadline well under 5 minutes"
    )
    assert job["ttlSecondsAfterFinished"] <= 3600


def test_the_token_is_mounted_from_the_existing_secret_never_a_second_vault_entry():
    volumes = {
        v["name"]: v
        for v in _cronjob()["spec"]["jobTemplate"]["spec"]["template"]["spec"][
            "volumes"
        ]
    }
    token_vol = volumes["telegram-token"]
    assert token_vol["secret"]["secretName"] == "otto-staging-telegram", (
        "must reuse the same Secret telegram-secret.yaml already renders from vault, "
        "never a second, hand-minted entry"
    )
    container = _container()
    mount = next(m for m in container["volumeMounts"] if m["name"] == "telegram-token")
    assert mount["readOnly"] is True
    assert mount["mountPath"] == "/run/secrets/otto-staging-telegram"


def test_no_literal_secret_anywhere_in_the_manifest():
    raw = MANIFEST.read_text()
    assert not LIVE_TOKEN_RE.search(raw), "a live-shaped Telegram bot token literal"
    assert "valueFrom" not in raw or "secretKeyRef" not in raw, (
        "Kyverno secrets-not-from-env-vars refuses env.valueFrom.secretKeyRef on a Pod (crew#341)"
    )
    container = _container()
    env_names = {e["name"] for e in container.get("env", [])}
    assert "OTTO_TELEGRAM_BOT_TOKEN" not in env_names, (
        "the token is a mounted file the script reads itself, never a pod env var"
    )


def test_the_script_never_prints_the_token_it_reads():
    script = _script()
    assert "print(token" not in script
    assert 'print(f"{token' not in script
    # the token variable is used only to build the request URL and read the file; it must never
    # be interpolated into anything the script writes to stdout.
    print_lines = [ln for ln in script.splitlines() if "print(" in ln]
    for ln in print_lines:
        assert "token" not in ln, f"a print statement names the token variable: {ln!r}"


def test_metric_names_match_the_spec_exactly():
    script = _script()
    assert '"channel_registration_ok"' in script
    assert '"channel_pending_updates"' in script
    # the spec's two metrics only, no drift to a third name or a renamed one
    metric_literals = set(re.findall(r'_gauge\("([a-z_]+)"', script))
    assert metric_literals == {"channel_registration_ok", "channel_pending_updates"}


def test_metrics_carry_tenant_and_channel_attributes():
    script = _script()
    assert '"key": "tenant_id"' in script
    assert '"key": "channel"' in script


def test_metrics_are_pushed_to_the_estates_one_existing_collector():
    """LAW 43: no second metrics sink. Same endpoint as platform/otto-golden/deployment.yaml's
    OTEL_EXPORTER_OTLP_ENDPOINT."""
    container = _container()
    env = {e["name"]: e["value"] for e in container["env"] if "value" in e}
    assert (
        env["OTEL_EXPORTER_OTLP_ENDPOINT"]
        == "http://signoz-otel-collector.observability.svc:4318"
    )
    script = _script()
    assert "/v1/metrics" in script
    assert "OTEL_EXPORTER_OTLP_ENDPOINT" in script


def test_container_is_locked_down_like_every_other_workload_here():
    container = _container()
    sc = container["securityContext"]
    assert sc["allowPrivilegeEscalation"] is False
    assert sc["readOnlyRootFilesystem"] is True
    assert sc["runAsNonRoot"] is True
    assert sc["capabilities"]["drop"] == ["ALL"]
    pod_sc = _cronjob()["spec"]["jobTemplate"]["spec"]["template"]["spec"][
        "securityContext"
    ]
    assert pod_sc["runAsNonRoot"] is True
    assert (
        _cronjob()["spec"]["jobTemplate"]["spec"]["template"]["spec"][
            "automountServiceAccountToken"
        ]
        is False
    )


def test_resources_fit_the_namespaces_existing_quota_headroom():
    """otto-golden-ceiling (quota.yaml) already reserves requests.cpu=200m/requests.memory=384Mi
    against the two-replica Deployment (50m/256Mi requested, 400m/512Mi limited at most three
    pods during a rollout); this job must fit the remaining headroom without a quota bump, so it
    ships with no increase to a recurring bill.

    crew#584: a job that wakes for one HTTP call every 5 minutes reserves no standing CPU
    (requests.cpu is an honest "0", never an unset field the namespace's LimitRange would
    silently default to 50m). memory keeps requests == limits -- Guaranteed for memory, since an
    OOM here is a false FAIL on a fact-finding check, not a real saving."""
    container = _container()
    req = container["resources"]["requests"]
    lim = container["resources"]["limits"]
    assert req["cpu"] == "0", (
        "no standing CPU reservation for a job idle 299 of every 300 seconds"
    )
    assert req["memory"] == lim["memory"], "Guaranteed QoS for memory"
    cpu_limit_millis = int(str(lim["cpu"]).rstrip("m"))
    mem_mi = int(req["memory"].rstrip("Mi"))
    assert cpu_limit_millis <= 100, (
        "must fit the ~150m of headroom left under requests.cpu"
    )
    assert mem_mi <= 100, "must fit the ~128Mi of headroom left under requests.memory"


def test_kustomization_carries_the_new_resource():
    ks = yaml.safe_load(KUSTOMIZATION.read_text())
    assert "registration-reconciler.yaml" in ks["resources"]


def test_the_reconciler_exits_nonzero_when_registration_is_not_ok():
    """A CronJob's own exit code is the cheapest possible receipt (`kubectl get jobs` reads it
    with no log line, no dashboard): registration_ok=0 must fail the run."""
    script = _script()
    assert "sys.exit(1)" in script
    assert "registration_ok != 1" in script
