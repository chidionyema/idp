"""cni-resync is a real break-glass playbook: listed, dispatchable, restarts calico on every node
and proves cross-node reach per node (incident 2026-09-09, OKE re-rolled flannel on both nodes)."""

import pathlib, re, subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
BG = ROOT / "bin" / "idp-oke-break-glass"
WF = ROOT / ".github" / "workflows" / "oke-check.yml"


def _body(name):
    lines = BG.read_text().splitlines()
    start = next(i for i, ln in enumerate(lines) if ln.startswith(f"{name}() {{"))
    end = next(i for i in range(start, len(lines)) if lines[i] == "}")
    return lines[start:end]


def test_cni_resync_is_listed_and_dispatchable():
    out = subprocess.run(["bash", str(BG), "--list"], capture_output=True, text=True)
    assert out.returncode == 0 and "cni-resync" in out.stdout.split()
    assert "  cni-resync) pb_cni_resync ;;" in BG.read_text().splitlines()


def test_cni_resync_restarts_calico_on_every_node_and_waits():
    body = _body("pb_cni_resync")
    assert any("rollout restart ds calico-node" in ln for ln in body)
    assert any(
        "rollout status ds calico-node" in ln and "--timeout" in ln for ln in body
    )


def test_cni_resync_probes_cross_node_from_each_node():
    body = _body("pb_cni_resync")
    assert any("spec.nodeName!=" in ln for ln in body)
    assert any("tcp_probe " in ln for ln in body)
    assert any(ln.strip().startswith("dns_probe ") for ln in body)


def test_cni_resync_is_a_workflow_choice():
    opts = re.search(r"playbook:.*?options: \[(.*?)\]", WF.read_text(), re.S).group(1)
    assert "cni-resync" in [o.strip() for o in opts.split(",")]
