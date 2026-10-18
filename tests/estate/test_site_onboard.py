"""site-onboard derives every declaration one public site needs, and its gate can say no.

The four fixes meridian needed after its application was already written (#6503 listener, #6511
cert-manager egress, #6513 edge egress, #6518 cert-manager ingress_from) were each a missing
declaration in a *different* shared file. So the tests here are about two things and nothing else:

  * the generator writes declarations that its own verifier accepts -- a generator whose output
    fails its gate is a generator nobody can use twice;
  * the verifier fails when one of those declarations is removed, one at a time. A gate that only
    reads the files the generator just wrote cannot fail on the defect it exists to prevent.

The shared-file edits are textual on purpose (a YAML round-trip would delete the comments that
record which outage produced each line), so the tests pin the comments surviving, and pin the two
shapes that broke the first version against the real 700-line allowances.yaml: a comment inside a
flow list that mentions `]`, and a later `patches:` key whose `- target:` rows look like resources.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
import yaml

SCRIPT = Path(__file__).resolve().parents[2] / "platform/estate/libexec/site-onboard.py"
spec = importlib.util.spec_from_file_location("site_onboard", SCRIPT)
so = importlib.util.module_from_spec(spec)
spec.loader.exec_module(so)

GATEWAY = """\
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: prospector-edge
  namespace: prospector
spec:
  gatewayClassName: traefik
  listeners:
    - name: http
      port: 80
      protocol: HTTP
    # Every HTTPS listener terminates with the one certificate, so a new hostname is a re-issue
    # rather than a second certificate.
    - name: https-apex
      hostname: ${ESTATE_ZONE}
      port: 8443
      protocol: HTTPS
      allowedRoutes:
        namespaces:
          from: Selector
          selector:
            matchLabels:
              idp.estate/edge-attach: "true"
      tls:
        mode: Terminate
        certificateRefs:
          - group: ""
            kind: Secret
            name: prospector-edge-tls
"""

ALLOWANCES = """\
# The input data for bin/idp-ns-fence-gen. Change a number here and re-run the generator.
sizing:
  headroom:
    cpu: 3.0
flows:
  custodian:
    ingress_from: [edge]
  edge:
    egress: [custodian, identity,
             # cert-manager declares `ingress_from: [edge]` to match this side -- so this comment
             # holds a closing bracket, and a scanner that trusts the first one it sees puts the
             # next namespace inside this sentence.
             cert-manager]
    ingress_public: [8000, 8443]
    ingress_from: [monitoring, identity]
"""

CLUSTER_ROWS = """\
# Every *.yaml beside this file MUST be listed below: an unlisted file is silently not applied
# and, with prune, its objects are deleted from the cluster.
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - flux-system
  - estate-config.yaml
  - custodian.yaml
patches:
  - target:
      group: kustomize.toolkit.fluxcd.io
      kind: Kustomization
    patch: |-
      apiVersion: kustomize.toolkit.fluxcd.io/v1
      kind: Kustomization
      metadata:
        name: estate-reconcile-interval
"""

CATALOGUE = """\
apiVersion: backstage.io/v1alpha1
kind: Component
metadata:
  name: custodian
spec:
  type: service
"""

FENCE_GEN = """\
#!/usr/bin/env python3
import sys
from pathlib import Path
import yaml
root = Path(__file__).resolve().parents[1]
flows = yaml.safe_load((root / "platform/ns-fences/allowances.yaml").read_text())["flows"]
out = root / "platform/ns-fences/network"
out.mkdir(parents=True, exist_ok=True)
for ns in flows:
    (out / f"{ns}.yaml").write_text(
        "apiVersion: networking.k8s.io/v1\\nkind: NetworkPolicy\\n"
        f"metadata:\\n  name: allow-declared-ingress\\n  namespace: {ns}\\n"
    )
print(f"regenerated {len(flows)} fences")
"""


def put(repo: Path, rel: str, text: str) -> Path:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    """A checkout with the real shape of the files site-onboard edits."""
    put(
        tmp_path,
        "clusters/oke/estate-config.yaml",
        "apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: estate-config\n"
        "  namespace: flux-system\ndata:\n  ESTATE_ZONE: mumchimp.com\n",
    )
    put(tmp_path, "clusters/oke/kustomization.yaml", CLUSTER_ROWS)
    put(
        tmp_path, "clusters/oke/custodian.yaml", "kind: Kustomization\napiVersion: v1\n"
    )
    put(
        tmp_path,
        "platform/image-automation/kustomization.yaml",
        "apiVersion: kustomize.config.k8s.io/v1beta1\nkind: Kustomization\nresources:\n"
        "  - custodian.yaml\n",
    )
    put(tmp_path, "platform/edge/prospector-gateway.yaml", GATEWAY)
    put(tmp_path, "platform/ns-fences/allowances.yaml", ALLOWANCES)
    put(tmp_path, "platform/ns-fences/network/custodian.yaml", "kind: NetworkPolicy\n")
    put(tmp_path, "backstage/platform/catalog-info.yaml", CATALOGUE)
    put(tmp_path, "platform/estate/intents/.keep", "")
    fence = put(tmp_path, "bin/idp-ns-fence-gen", FENCE_GEN)
    fence.chmod(0o755)
    return tmp_path


def cli(*argv: str) -> int:
    return so.main(list(argv))


def site(
    repo: Path, name: str = "pulsera", hostname: str = "pulsera", *extra: str
) -> list:
    return ["--name", name, "--hostname", hostname, "--repo", str(repo), *extra]


def build(
    repo: Path, name: str = "pulsera", hostname: str = "pulsera", *extra: str
) -> None:
    assert cli("write", *site(repo, name, hostname, *extra)) == 0


def load(path: Path) -> dict:
    return yaml.safe_load(path.read_text())


# --- the generator and its own gate agree -------------------------------------------------------


def test_plan_writes_nothing(repo: Path, capsys) -> None:
    assert cli("plan", *site(repo)) == 0
    out = capsys.readouterr().out
    assert not (repo / "platform/pulsera").exists()
    assert "WOULD CREATE platform/pulsera/public-door.yaml" in out
    assert "Nothing was written" in out


def test_what_it_writes_its_gate_accepts(repo: Path, capsys) -> None:
    build(repo)
    capsys.readouterr()
    assert cli("verify", "--name", "pulsera", "--repo", str(repo)) == 0
    out = capsys.readouterr().out
    assert "VERIFIED pulsera" in out
    assert "FAIL" not in out


def test_written_files_are_valid_and_complete(repo: Path) -> None:
    build(repo)
    door = load(repo / "platform/pulsera/public-door.yaml")
    # A token, never a literal: bin/estate-zone-gate refuses the literal, and the zone moves.
    assert door["spec"]["hostnames"] == ["pulsera.${ESTATE_ZONE}"]
    assert door["spec"]["parentRefs"][0]["sectionName"] == "https-pulsera"
    docs = {
        d["kind"]: d
        for d in yaml.safe_load_all(
            (repo / "platform/pulsera/deployment.yaml").read_text()
        )
    }
    assert docs["Deployment"]["spec"]["replicas"] == 2
    assert docs["Deployment"]["spec"]["template"]["spec"]["imagePullSecrets"] == [
        {"name": "ghcr-pull"}
    ]
    assert (
        docs["Service"]["metadata"]["labels"]["backstage.io/kubernetes-id"] == "pulsera"
    )
    ns = load(repo / "platform/pulsera/namespace.yaml")
    assert ns["metadata"]["labels"]["idp.estate/edge-attach"] == "true"
    assert (
        ns["metadata"]["annotations"]["kustomize.toolkit.fluxcd.io/prune"] == "disabled"
    )


def test_image_tag_is_owned_by_flux_not_typed(repo: Path) -> None:
    build(repo)
    text = (repo / "platform/pulsera/kustomization.yaml").read_text()
    assert '{"$imagepolicy": "flux-system:pulsera:tag"}' in text
    assert "newTag: main-0-bootstrap" in text


# --- the shared-file edits: precise, comment-preserving, valid -----------------------------------


def test_allowances_get_both_halves_and_keep_their_comments(repo: Path) -> None:
    build(repo)
    text = (repo / "platform/ns-fences/allowances.yaml").read_text()
    flows = load(repo / "platform/ns-fences/allowances.yaml")["flows"]
    assert flows["edge"]["egress"] == [
        "custodian",
        "identity",
        "cert-manager",
        "pulsera",
    ]
    assert flows["pulsera"]["ingress_from"] == ["edge"]
    # The comment that mentions a bracket is still a comment, in its place, and so is the file's
    # own header. A round-trip through a YAML dumper would have deleted both.
    assert "# cert-manager declares `ingress_from: [edge]` to match this side" in text
    assert text.startswith("# The input data for bin/idp-ns-fence-gen")
    assert "ingress_public: [8000, 8443]" in text


def test_gateway_gains_one_listener_and_keeps_its_comments(repo: Path) -> None:
    build(repo)
    text = (repo / "platform/edge/prospector-gateway.yaml").read_text()
    listeners = load(repo / "platform/edge/prospector-gateway.yaml")["spec"][
        "listeners"
    ]
    assert [l["name"] for l in listeners] == ["http", "https-pulsera", "https-apex"]
    assert "# Every HTTPS listener terminates with the one certificate" in text
    assert listeners[1]["tls"]["certificateRefs"][0]["name"] == "prospector-edge-tls"


def test_lane_row_lands_in_resources_not_in_the_patches_block(repo: Path) -> None:
    build(repo)
    doc = load(repo / "clusters/oke/kustomization.yaml")
    assert "pulsera.yaml" in doc["resources"]
    assert doc["patches"][0]["target"]["kind"] == "Kustomization"
    assert (
        "pulsera.yaml"
        in load(repo / "platform/image-automation/kustomization.yaml")["resources"]
    )
    assert (
        "name: pulsera" in (repo / "backstage/platform/catalog-info.yaml").read_text()
    )


def test_second_run_with_force_adds_nothing_twice(repo: Path) -> None:
    build(repo)
    build(repo, "pulsera", "pulsera", "--force", "true")
    gateway = (repo / "platform/edge/prospector-gateway.yaml").read_text()
    allowances = (repo / "platform/ns-fences/allowances.yaml").read_text()
    rows = (repo / "clusters/oke/kustomization.yaml").read_text()
    assert gateway.count("name: https-pulsera") == 1
    assert allowances.count("  pulsera:\n") == 1
    assert allowances.count("pulsera]") == 1
    assert rows.count("  - pulsera.yaml") == 1


def test_an_existing_site_is_not_silently_overwritten(repo: Path, capsys) -> None:
    build(repo)
    assert cli("write", *site(repo)) == 2
    assert "already exists" in capsys.readouterr().err


def test_a_duplicate_key_is_refused_rather_than_silently_kept(
    repo: Path, capsys
) -> None:
    put(
        repo,
        "platform/ns-fences/allowances.yaml",
        ALLOWANCES + "  edge:\n    egress: [x]\n",
    )
    assert cli("plan", *site(repo)) == 2
    assert "duplicate key" in capsys.readouterr().err


# --- the gate can fail, one declaration at a time ------------------------------------------------


def test_gate_fails_when_the_namespace_does_not_admit_edge(repo: Path, capsys) -> None:
    build(repo)
    path = repo / "platform/ns-fences/allowances.yaml"
    doc = load(path)
    doc["flows"]["pulsera"] = {}
    path.write_text(yaml.safe_dump(doc, sort_keys=False))
    assert cli("verify", "--name", "pulsera", "--repo", str(repo)) == 1
    assert "does not admit edge" in capsys.readouterr().out


def test_gate_fails_when_the_listener_is_gone(repo: Path, capsys) -> None:
    build(repo)
    path = repo / "platform/edge/prospector-gateway.yaml"
    doc = load(path)
    doc["spec"]["listeners"] = [
        l for l in doc["spec"]["listeners"] if l["name"] != "https-pulsera"
    ]
    path.write_text(yaml.safe_dump(doc, sort_keys=False))
    assert cli("verify", "--name", "pulsera", "--repo", str(repo)) == 1
    assert "route attaches to a declared listener" in capsys.readouterr().out


def test_gate_fails_when_the_lane_row_is_missing(repo: Path, capsys) -> None:
    build(repo)
    path = repo / "clusters/oke/kustomization.yaml"
    path.write_text(path.read_text().replace("  - pulsera.yaml\n", ""))
    assert cli("verify", "--name", "pulsera", "--repo", str(repo)) == 1
    assert "flux row is listed" in capsys.readouterr().out


def test_gate_fails_when_the_namespace_is_unfenced(repo: Path, capsys) -> None:
    build(repo)
    path = repo / "platform/ns-fences/allowances.yaml"
    doc = load(path)
    del doc["flows"]["pulsera"]
    path.write_text(yaml.safe_dump(doc, sort_keys=False))
    (repo / "platform/ns-fences/network/pulsera.yaml").unlink()
    assert cli("verify", "--name", "pulsera", "--repo", str(repo)) == 1
    out = capsys.readouterr().out
    assert "namespace is fenced from the one input file" in out
    # Unfenced is not the same finding as cut: nothing denies the namespace, so edge reaches it.
    assert "ok   the site admits edge back" in out


def test_gate_fails_when_a_hostname_is_written_literally(repo: Path, capsys) -> None:
    build(repo)
    path = repo / "platform/pulsera/public-door.yaml"
    path.write_text(path.read_text().replace("${ESTATE_ZONE}", "mumchimp.com"))
    assert cli("verify", "--name", "pulsera", "--repo", str(repo)) == 1
    assert "no literal mumchimp.com" in capsys.readouterr().out


def test_gate_writes_nothing(repo: Path) -> None:
    build(repo)
    before = {p: p.read_bytes() for p in repo.rglob("*") if p.is_file()}
    assert cli("verify", "--name", "pulsera", "--repo", str(repo)) == 0
    after = {p: p.read_bytes() for p in repo.rglob("*") if p.is_file()}
    assert before == after


# --- the two shapes that are not a public site ---------------------------------------------------


def test_a_site_with_no_hostname_touches_no_edge_declaration(repo: Path) -> None:
    gateway_before = (repo / "platform/edge/prospector-gateway.yaml").read_text()
    allowances_before = (repo / "platform/ns-fences/allowances.yaml").read_text()
    build(repo, "vibehub", "")
    assert not (repo / "platform/vibehub/public-door.yaml").exists()
    assert (
        repo / "platform/edge/prospector-gateway.yaml"
    ).read_text() == gateway_before
    assert (
        repo / "platform/ns-fences/allowances.yaml"
    ).read_text() == allowances_before
    ns = load(repo / "platform/vibehub/namespace.yaml")
    assert "idp.estate/edge-attach" not in ns["metadata"]["labels"]


def test_a_vault_entry_is_opt_in_and_mounted_optionally(repo: Path) -> None:
    build(repo, "vibehub", "")
    assert not (repo / "platform/vibehub/vault-secret.yaml").exists()
    build(repo, "pulsera", "pulsera", "--secret-entry", "pulsera")
    secret = load(repo / "platform/pulsera/vault-secret.yaml")
    assert secret["spec"]["dataFrom"] == [{"extract": {"key": "pulsera"}}]
    spec = [
        d
        for d in yaml.safe_load_all(
            (repo / "platform/pulsera/deployment.yaml").read_text()
        )
        if d["kind"] == "Deployment"
    ][0]["spec"]["template"]["spec"]
    volumes = {v["name"]: v for v in spec["volumes"]}
    assert volumes["secrets"]["secret"] == {"secretName": "pulsera", "optional": True}
