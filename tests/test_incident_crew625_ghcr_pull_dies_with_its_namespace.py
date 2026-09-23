"""2026-08-29 (crew#625): temporal/ghcr-pull and mcp/ghcr-pull read `could not get secret data from
provider` and the temporal chart's Job could not pull. The source they mirror is the Kubernetes
Secret backstage/ghcr-pull, written from a laptop by bin/idp-flux-bootstrap and owned by nothing
on the cluster; the backstage namespace was pruned and recreated that morning (idp#648) and the
Secret went with it. This file pins the repair (`ghcr-pull-restore`: copy from a namespace that
still holds it, value through a file, never argv or stdout) and the fence (the namespace a
ClusterSecretStore reads from is never prunable).
"""

import os
import stat
import subprocess
from pathlib import Path

import yaml

IDP = Path(__file__).resolve().parents[1]
PLAYBOOK = IDP / "bin" / "idp-oke-break-glass"
PAYLOAD = "eyJhdXRocyI6e319"  # base64 of {"auths":{}}


def _run(tmp_path: Path) -> tuple[subprocess.CompletedProcess, list[str]]:
    log = tmp_path / "calls.log"
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    # kubectl stub: flux-system no longer holds the secret, prospector does
    (bin_dir / "kubectl").write_text(
        "#!/bin/sh\n"
        f'printf \'%s\\n\' "kubectl $*" >> "{log}"\n'
        'case "$*" in\n'
        "  *'get secret ghcr-pull -n flux-system'*) exit 1 ;;\n"
        f"  *'get secret ghcr-pull -n prospector -o jsonpath'*) printf '%s' {PAYLOAD} ;;\n"
        "  *) echo ok ;;\n"
        "esac\n"
    )
    (bin_dir / "flux").write_text(
        f'#!/bin/sh\nprintf \'%s\\n\' "flux $*" >> "{log}"\necho ok\n'
    )
    for f in (bin_dir / "kubectl", bin_dir / "flux"):
        f.chmod(f.stat().st_mode | stat.S_IEXEC)
    env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}"}
    p = subprocess.run(
        [str(PLAYBOOK), "ghcr-pull-restore"],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    return p, (log.read_text().splitlines() if log.exists() else [])


def test_ghcr_pull_restore_is_a_named_playbook():
    out = subprocess.run(
        [str(PLAYBOOK), "--list"], capture_output=True, text=True, check=True
    ).stdout
    assert "ghcr-pull-restore" in out.split()
    wf = (IDP / ".github" / "workflows" / "oke-check.yml").read_text()
    assert "ghcr-pull-restore" in wf, "the playbook is not dispatchable from Actions"


def test_it_copies_from_a_surviving_namespace_into_backstage_and_resyncs(tmp_path):
    p, calls = _run(tmp_path)
    assert "prospector" in p.stdout.split("--- source")[1].splitlines()[1], p.stdout
    assert any(
        "create secret generic ghcr-pull -n backstage" in c and "--from-file=" in c
        for c in calls
    ), calls
    assert any("apply -f -" in c for c in calls), calls
    for ns in ("temporal", "mcp"):
        assert any(
            f"annotate externalsecret ghcr-pull -n {ns} force-sync=" in c for c in calls
        ), calls
    assert any("reconcile helmrelease temporal -n temporal" in c for c in calls), calls


def test_the_secret_value_never_reaches_argv_or_stdout(tmp_path):
    p, calls = _run(tmp_path)
    assert PAYLOAD not in p.stdout + p.stderr
    for c in calls:
        assert "--from-literal" not in c, c
        assert PAYLOAD not in c, c
        assert '{"auths"' not in c, c


def test_the_namespace_a_cluster_secret_store_reads_from_is_never_prunable():
    stores = []
    for f in (IDP / "platform").rglob("*.yaml"):
        for doc in yaml.safe_load_all(f.read_text()):
            if isinstance(doc, dict) and doc.get("kind") == "ClusterSecretStore":
                ns = (
                    doc.get("spec", {}).get("provider", {}).get("kubernetes") or {}
                ).get("remoteNamespace")
                if ns:
                    stores.append((f.relative_to(IDP), ns))
    assert stores, "no kubernetes-provider ClusterSecretStore found"
    for f, ns in stores:
        found = False
        for nf in (IDP / "platform").rglob("*.yaml"):
            for doc in yaml.safe_load_all(nf.read_text()):
                if (
                    isinstance(doc, dict)
                    and doc.get("kind") == "Namespace"
                    and doc["metadata"]["name"] == ns
                ):
                    found = True
                    labels = doc["metadata"].get("labels") or {}
                    assert (
                        labels.get("kustomize.toolkit.fluxcd.io/prune") == "disabled"
                    ), (
                        f"{f}: reads {ns}, but {nf.relative_to(IDP)} lets Flux prune it (idp#648 class)"
                    )
        assert found, f"{f}: reads namespace {ns} that no platform/ manifest declares"
