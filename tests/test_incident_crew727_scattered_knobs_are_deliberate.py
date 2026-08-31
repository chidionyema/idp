"""crew#727 CP2: every scattered per-file knob is the estate default or a named exception.

Follow-on from the interval wave, same founder directive (2026-08-31): a number nobody
decided is not a configuration, it is a guess. Measured before this wave: HelmRelease and
Kustomization timeouts in 7 spellings (including a 10s and a 15s helm upgrade timeout —
impossible values), ExternalSecret refreshInterval 1h on 39 of 45 entries while the
rotation strategy (crew#722, docs/policy/secrets-rotation.md) promises vault-to-pod in 25
minutes, one stray remediation retries=5, one stray actions/checkout pin.

The rule these tests hold: the default is one constant here; anything else is a row in an
exceptions table with the value pinned and a reason. Drift in either direction — a new
guess, or an exception silently changing — is red CI. Edits were raise-never-lower, so no
running upgrade got a shorter deadline than it had.
"""

import glob
import pathlib
import re

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_TIMEOUT = "10m"
DEFAULT_REFRESH = (
    "10m"  # rotation SLO is 25m vault-to-pod; an hourly refresh cannot honour it
)
DEFAULT_RETRIES = 3

# (kind, name) -> pinned value. Reason per group:
# - 15m/20m rows are CRD-heavy or migration-running stacks (monitoring, observability,
#   temporal, commerce) sized above default before this wave; lower only with a measured
#   upgrade run showing it fits.
TIMEOUT_EXCEPTIONS = {
    ("Kustomization", "commerce"): "15m",
    ("Kustomization", "spire"): "15m",
    ("Kustomization", "keda"): "15m",
    ("Kustomization", "hindsight"): "15m",
    ("Kustomization", "healing"): "15m",
    ("Kustomization", "robusta"): "15m",
    ("Kustomization", "observability"): "20m",
    ("Kustomization", "temporal"): "20m",
    ("Kustomization", "monitoring"): "20m",
    ("HelmRelease", "lago"): "15m",
    ("HelmRelease", "hindsight"): "15m",
    ("HelmRelease", "kube-prometheus-stack"): "15m",
    ("HelmRelease", "langfuse"): "15m",
    ("HelmRelease", "signoz"): "15m",
    ("HelmRelease", "robusta"): "15m",
    ("HelmRelease", "temporal"): "15m",
}

# hermes-agent-a2a: the agent card is written once at bootstrap and never rotated by the
# vault; refreshing it is a deliberate no ("0"), not a missed default.
REFRESH_EXCEPTIONS = {"hermes-agent-a2a": "0"}


def flux_docs():
    files = glob.glob(
        str(ROOT / "clusters" / "**" / "*.yaml"), recursive=True
    ) + glob.glob(str(ROOT / "platform" / "**" / "*.yaml"), recursive=True)
    for f in sorted(set(files)):
        if "flux-system/" in f:
            continue
        for d in yaml.safe_load_all(pathlib.Path(f).read_text()):
            if isinstance(d, dict):
                yield f, d


def test_every_flux_timeout_is_the_default_or_a_named_exception():
    bad, seen = [], set()
    for f, d in flux_docs():
        kind = d.get("kind")
        if kind not in ("Kustomization", "HelmRelease"):
            continue
        tv = (d.get("spec") or {}).get("timeout")
        if tv is None:
            continue
        name = d["metadata"].get("name")
        key = (kind, name)
        if key in TIMEOUT_EXCEPTIONS:
            seen.add(key)
            if str(tv) != TIMEOUT_EXCEPTIONS[key]:
                bad.append(
                    f"{f}: {kind}/{name} exception drifted {tv} != {TIMEOUT_EXCEPTIONS[key]}"
                )
        elif str(tv) != DEFAULT_TIMEOUT:
            bad.append(
                f"{f}: {kind}/{name} timeout={tv} is a new guess (default {DEFAULT_TIMEOUT})"
            )
    stale = set(TIMEOUT_EXCEPTIONS) - seen
    assert not bad and not stale, (
        "timeouts (founder 2026-08-31: deliberate, never a guess):\n"
        + "\n".join(bad)
        + (f"\nstale exception rows (object gone): {sorted(stale)}" if stale else "")
    )


def test_every_remediation_retry_count_is_the_one_value():
    bad = []
    for f, d in flux_docs():
        if d.get("kind") != "HelmRelease":
            continue
        for phase in ("install", "upgrade"):
            r = (((d.get("spec") or {}).get(phase) or {}).get("remediation") or {}).get(
                "retries"
            )
            if r is not None and r != DEFAULT_RETRIES:
                bad.append(f"{f}: {d['metadata'].get('name')} {phase}.retries={r}")
    assert not bad, f"remediation retries != {DEFAULT_RETRIES}:\n" + "\n".join(bad)


def test_every_externalsecret_refresh_honours_the_rotation_slo():
    """crew#722 promises vault-to-pod in 25 minutes; the refresh interval is the first leg.
    39 ExternalSecrets at 1h made that promise arithmetic-impossible before this wave."""
    bad, seen = [], set()
    for f, d in flux_docs():
        if d.get("kind") != "ExternalSecret":
            continue
        name = d["metadata"].get("name")
        rv = str((d.get("spec") or {}).get("refreshInterval"))
        if name in REFRESH_EXCEPTIONS:
            seen.add(name)
            if rv != REFRESH_EXCEPTIONS[name]:
                bad.append(f"{f}: {name} exception drifted {rv}")
        elif rv != DEFAULT_REFRESH:
            bad.append(f"{f}: {name} refreshInterval={rv} (default {DEFAULT_REFRESH})")
    stale = set(REFRESH_EXCEPTIONS) - seen
    assert not bad and not stale, (
        "refreshInterval:\n" + "\n".join(bad) + f"\nstale exceptions: {sorted(stale)}"
        if stale
        else "refreshInterval:\n" + "\n".join(bad)
    )


def test_one_checkout_pin_across_every_workflow():
    pins = {}
    for f in glob.glob(str(ROOT / ".github" / "workflows" / "*.yml")):
        for m in re.finditer(
            r"uses:\s*actions/checkout@(\S+)", pathlib.Path(f).read_text()
        ):
            pins.setdefault(m.group(1), []).append(pathlib.Path(f).name)
    assert len(pins) == 1, (
        "every workflow checks out with the same pinned action SHA; strays: "
        + str({k: v for k, v in pins.items()})
    )
