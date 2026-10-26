"""Every object Flux applies for this repo names its namespace (the #7231 class).

The estate already knows this failure mode twice -- crew#503 (2026-08-27, the backstage
catalog ConfigMap) and 2026-09-06 (the sandbox sweeper) -- and both times the fix was one
line in one kustomization.yaml, followed by the same silence: no guard, so the next one
was missed as well. On 2026-10-26 it was the catalog's schema ConfigMap, and the cost was
not a red pod: Flux refused the whole Kustomization, so the cluster kept an older revision
of the estate and every check that reads the live estate graded a revision that was no
longer there (idp#7231).

The guard is the rendered output, not the yaml. A kustomization may set `namespace:` at the
top, set it per generator, set it per object, or inherit it from a base -- only
`kustomize build` (the build Flux runs) knows what was actually produced. So this renders
every path this repo's own Flux Kustomizations point at and asserts that no namespaced
object came out without a namespace, and that the one path whose ConfigMap is mounted by a
CronJob mounts the GENERATED (hashed) name in the SAME namespace, because a ConfigMap in
another namespace is not mounted at all.

Cluster-scoped kinds are exempt: they have no namespace to name.
"""

import glob
import pathlib
import subprocess

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]

# Kinds that live outside a namespace. Listing them is the honest way to say "this object
# is not namespaced", rather than "the object forgot to say so".
CLUSTER_SCOPED = {
    "APIService",
    "CSIDriver",
    "CSINode",
    "ClusterIssuer",
    "ClusterPolicy",
    "ClusterRole",
    "ClusterRoleBinding",
    "ClusterSecretStore",
    "CustomResourceDefinition",
    "MutatingWebhookConfiguration",
    "Namespace",
    "Node",
    "PersistentVolume",
    "PriorityClass",
    "RuntimeClass",
    "StorageClass",
    "ValidatingWebhookConfiguration",
    "VolumeSnapshotClass",
}


def render(path):
    """What Flux will apply: kustomize build, parsed into documents."""
    proc = subprocess.run(
        ["kustomize", "build", str(path)],
        capture_output=True,
        text=True,
        check=True,
        timeout=120,
    )
    return [d for d in yaml.safe_load_all(proc.stdout) if d]


def _docs(path):
    """The yaml documents in a file, or none at all if it does not parse.

    A cluster file that does not parse is not this test's business, but it is also not a
    reason to stop reading the other files: the guard is about what Flux renders, and one
    unreadable row does not make the readable ones safe.
    """
    try:
        return [d for d in yaml.safe_load_all(path.read_text()) if d]
    except yaml.YAMLError:
        return []


def flux_paths():
    """Every path in this repo that this repo's own Flux Kustomizations reconcile.

    Only rows whose source is this repo's GitRepository (flux-system): a row that points at
    another source (the gateway-api CRDs come from the upstream repo) reconciles a path
    that is not in this tree, and is not this test's business.
    """
    paths = set()
    for f in glob.glob(str(ROOT / "clusters/**/*.yaml"), recursive=True):
        for d in _docs(pathlib.Path(f)):
            if not isinstance(d, dict):
                continue
            if d.get("kind") != "Kustomization":
                continue
            if not str(d.get("apiVersion", "")).startswith(
                "kustomize.toolkit.fluxcd.io"
            ):
                continue
            spec = d.get("spec") or {}
            src = spec.get("sourceRef") or {}
            if src.get("kind") != "GitRepository" or src.get("name") != "flux-system":
                continue
            path = spec.get("path")
            if path and path.startswith("./"):
                paths.add(path[2:])
    return sorted(paths)


def test_there_are_flux_paths_to_check():
    """A guard that checks nothing is not a guard."""
    paths = flux_paths()
    assert len(paths) >= 20, f"expected the estate's Flux paths, found {len(paths)}"
    assert "platform/catalog" in paths, "the catalog path is the one #7231 was about"


def test_no_flux_path_renders_an_object_without_a_namespace():
    """The class of #7231: an object with no namespace makes Flux refuse the whole row."""
    offenders = []
    for path in flux_paths():
        rendered = render(ROOT / path)
        for d in rendered:
            if not isinstance(d, dict):
                continue
            kind = d.get("kind")
            if kind in CLUSTER_SCOPED:
                continue
            meta = d.get("metadata") or {}
            if not meta.get("namespace"):
                offenders.append(f"{path}: {kind}/{meta.get('name')}")
    assert not offenders, "objects rendered without a namespace: " + "; ".join(
        offenders
    )


def test_catalog_cronjob_mounts_the_generated_configmap_in_the_same_namespace():
    """The CronJob mounts a generated ConfigMap: the name carries a hash and the namespace must match.

    Two bugs hide behind one symptom. The generator without a namespace produces an object
    Flux refuses; and a ConfigMap in another namespace than its CronJob is not mounted at
    all, so the reference is never rewritten to the hashed name and the pod waits for a
    ConfigMap that does not exist.
    """
    rendered = render(ROOT / "platform/catalog")
    configmaps = [
        d
        for d in rendered
        if d.get("kind") == "ConfigMap"
        and str(d["metadata"]["name"]).startswith("catalog-schema")
    ]
    assert len(configmaps) == 1, (
        f"expected one generated catalog schema ConfigMap, got {len(configmaps)}"
    )
    cm = configmaps[0]
    assert cm["metadata"].get("namespace") == "estate-db", (
        "the catalog schema ConfigMap must live where the CronJob that mounts it lives, "
        f"not {cm['metadata'].get('namespace')!r} (#7231)"
    )

    cronjobs = [
        d
        for d in rendered
        if d.get("kind") == "CronJob" and d["metadata"]["name"] == "catalog-schema"
    ]
    assert len(cronjobs) == 1, (
        f"expected one catalog-schema CronJob, got {len(cronjobs)}"
    )
    cronjob = cronjobs[0]
    assert cronjob["metadata"].get("namespace") == "estate-db"

    mounted = []
    for volume in cronjob["spec"]["jobTemplate"]["spec"]["template"]["spec"]["volumes"]:
        if "configMap" in volume:
            mounted.append(volume["configMap"]["name"])
    assert mounted == [cm["metadata"]["name"]], (
        f"the CronJob mounts {mounted}, but the generated ConfigMap is "
        f"{cm['metadata']['name']!r}: a stale or unhashed reference never resolves (#7231)"
    )
