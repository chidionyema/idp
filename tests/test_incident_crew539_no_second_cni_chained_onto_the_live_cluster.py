"""2026-08-27T23:47Z, crew#539 CP12 (idp#505): Cilium 1.20.1 chained after OKE's flannel
(generic-veth) took the pod network down — cilium-operator lost leader election 8 times,
coredns restarted 4 times, every webhook (ESO, Kyverno) answered EOF, 36 Flux objects went
not-ready and catalogue/langfuse crash-looped for over an hour (oke-check 33128360819).
The CNI is the cluster's (platform/oci cni_type); a second one is never a Flux row."""
import pathlib, re
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
CNI = re.compile(r"^(cilium|calico|flannel|weave|antrea|kube-ovn)$", re.I)


def _helm_charts():
    for p in list((ROOT / "platform").rglob("*.yaml")) + list((ROOT / "clusters").rglob("*.yaml")):
        if p.parts[len(ROOT.parts)] == "platform" and p.parts[len(ROOT.parts) + 1] == "oci":
            continue
        try:
            docs = list(yaml.safe_load_all(p.read_text()))
        except yaml.YAMLError:
            continue
        for d in docs:
            if isinstance(d, dict) and d.get("kind") == "HelmRelease":
                chart = (((d.get("spec") or {}).get("chart") or {}).get("spec") or {}).get("chart", "")
                yield p.relative_to(ROOT).as_posix(), chart


def test_no_cni_chart_is_a_flux_row():
    offenders = [(f, c) for f, c in _helm_charts() if CNI.match(str(c))]
    assert offenders == [], f"a CNI is the cluster's, never a Flux row (idp#505 outage): {offenders}"


def test_the_guard_sees_a_cni_chart(tmp_path, monkeypatch):
    (tmp_path / "platform" / "x").mkdir(parents=True)
    (tmp_path / "clusters").mkdir()
    (tmp_path / "platform" / "x" / "c.yaml").write_text(
        "apiVersion: helm.toolkit.fluxcd.io/v2\nkind: HelmRelease\nspec:\n  chart:\n    spec:\n      chart: cilium\n")
    monkeypatch.setattr(__import__(__name__), "ROOT", tmp_path)
    assert [c for _, c in _helm_charts()] == ["cilium"]
