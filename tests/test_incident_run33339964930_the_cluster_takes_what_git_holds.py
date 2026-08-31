"""Incident run 33339964930 (2026-08-30): git was green and the cluster refused it, twice over.

1. Kustomization flux-system/hermes-agent and flux-system/mcp: the GithubAccessToken generators
   were written `appID: "${githubAppID}"`, but kustomize build re-emits every scalar plain (the
   quotes are syntax, not data), Flux envsubst then substitutes a bare numeral, the re-parse types
   it int, and the API server refuses the typed patch: `.spec.appID: expected string, got 4740261`.
   The only quoting that survives the pipeline is quoting carried IN the substituted value, so the
   flux-system/github-app Secret templates *Quoted keys and the generators substitute those.

2. HelmRelease tailscale/tailscale-operator sat `Failed` blocking guacamole: helm-controller
   spends its remediation retries once and then waits forever for a spec change. Founder blueprint
   (~/.claude/docs/founder/2026-08-30T2252Z-also-o-eliminate-this-exact-class-of-failures-501c10b6.md):
   a wedged release is not left for a person to untangle. Every HelmRelease declares bounded
   install and upgrade remediation.

   The strategy that shipped with it, `uninstall`, was taken back out on 2026-08-31. Founder,
   2026-08-30 (~/.claude/docs/founder/2026-08-30T2332Z-yes-and-the-pattern-is-sound-but-two
   -c08d08d9.md): "Uninstalling a wedged HelmRelease turns a degraded service into a deleted one
   -- PVCs, PDBs, Secrets created by the release, gone ... More importantly, both destroy the
   evidence. You cannot convert an incident into a permanent control if your first move erases the
   state that tells you which invariant was violated. Keep the ability to repave -- but as a manual
   break-glass after capture, never as automated remediation." The retries stay, the default
   rollback strategy stays, and the repave is `bin/idp-oke-break-glass helm-retry`, by a hand.
"""

from pathlib import Path

import subprocess
import yaml

ROOT = Path(__file__).resolve().parents[1]


def _docs(path: str):
    return [d for d in yaml.safe_load_all((ROOT / path).read_text()) if d]


def test_the_generators_substitute_the_quoted_keys() -> None:
    for path in (
        "platform/hermes-agent/gateway.yaml",
        "platform/mcp/external-secret.yaml",
    ):
        gen = next(d for d in _docs(path) if d.get("kind") == "GithubAccessToken")
        assert gen["spec"]["appID"] == "${githubAppIDQuoted}", path
        assert gen["spec"]["installID"] == "${githubAppInstallationIDQuoted}", path


def test_the_secret_template_carries_the_quotes_in_the_value() -> None:
    es = next(
        d
        for d in _docs("platform/alerts-github/github-app.yaml")
        if d.get("kind") == "ExternalSecret" and d["metadata"]["name"] == "github-app"
    )
    data = es["spec"]["target"]["template"]["data"]
    assert data["githubAppIDQuoted"] == "{{ .app_id | quote }}"
    assert data["githubAppInstallationIDQuoted"] == "{{ .installation_id | quote }}"


def test_a_quoted_value_survives_the_pipeline_as_a_string_and_a_bare_one_does_not() -> (
    None
):
    """Pin the mechanism itself: text-level substitution into a plain scalar (what Flux does
    after kustomize has stripped the syntax quotes) types a bare numeral and keeps a quoted one."""
    assert yaml.safe_load("appID: " + "4740261") == {"appID": 4740261}
    assert yaml.safe_load("appID: " + '"4740261"') == {"appID": "4740261"}


def test_every_helmrelease_remediates_a_wedged_install_and_upgrade() -> None:
    files = subprocess.run(
        ["git", "grep", "-l", "kind: HelmRelease", "--", "platform", "clusters"],
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=True,
    ).stdout.split()
    bare, destructive = [], []
    for f in files:
        for d in _docs(f):
            if d.get("kind") != "HelmRelease":
                continue
            spec = d["spec"]
            for phase in ("install", "upgrade"):
                remediation = spec.get(phase, {}).get("remediation", {})
                if remediation.get("retries", 0) < 1:
                    bare.append((f, d["metadata"]["name"], phase))
                if remediation.get("strategy") == "uninstall":
                    destructive.append((f, d["metadata"]["name"], phase))
    assert not bare, f"HelmRelease rows a wedge would freeze forever: {bare}"
    assert not destructive, (
        "these rows uninstall themselves when they fail, which deletes what the release made and "
        "erases the state that says which invariant was violated -- the one thing an incident is "
        f"read from. Repaving is a hand, `bin/idp-oke-break-glass helm-retry`: {destructive}"
    )
