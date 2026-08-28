"""crew#524, 2026-08-27: every oke-check receipt since hindsight landed graded
`HelmRepository hindsight/hindsight: no Ready condition yet` (since null) and the cluster-state
row went FAIL on it. An OCI HelmRepository (`spec.type: oci`) is static: source-controller never
reconciles it and it carries no status conditions, so "not Ready" is not a state it can leave.
A guard that refuses correct work is an outage (LAW 38). Rule: an OCI HelmRepository with no Ready
condition is graded ready with a message saying why; an OCI one that does carry Ready=False, and
a non-OCI one with no condition, stay not-ready. Rung 4, incident test, the collector run end to
end against a stubbed API server."""
import json
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "platform/state/cluster-state.yaml"

REPOS = [
    {"metadata": {"name": "hindsight", "namespace": "hindsight"}, "spec": {"type": "oci", "url": "oci://x"}},
    {"metadata": {"name": "broken-oci", "namespace": "a"}, "spec": {"type": "oci", "url": "oci://y"},
     "status": {"conditions": [{"type": "Ready", "status": "False", "message": "pull denied"}]}},
    {"metadata": {"name": "plain", "namespace": "b"}, "spec": {"url": "https://charts.example"}},
]

PREAMBLE = r'''
import io, json as _j, ssl as _ssl, urllib.request as _u
_ssl.create_default_context = lambda **k: None
class _R(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self, *a): return False
def _open(req, context=None, timeout=None):
    path = req.full_url.split("kubernetes.default.svc", 1)[1]
    body = {"items": REPOS} if "helmrepositories" in path else {"items": []}
    return _R(_j.dumps(body).encode())
_u.urlopen = _open
REPOS = %s
'''


def _run(tmp_path: Path) -> dict:
    docs = [d for d in yaml.safe_load_all(MANIFEST.read_text()) if d]
    collect = next(d for d in docs if d["kind"] == "ConfigMap")["data"]["collect.py"]
    sa = tmp_path / "sa"
    sa.mkdir()
    (sa / "token").write_text("t")
    (sa / "ca.crt").write_text("")
    src = collect.replace('SA = "/var/run/secrets/kubernetes.io/serviceaccount"', f'SA = "{sa}"', 1)
    assert src != collect, "SA constant found"
    r = subprocess.run([sys.executable, "-c", PREAMBLE % json.dumps(REPOS) + src], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr[-2000:]
    return json.loads(r.stdout.strip().splitlines()[-1])


def test_oci_repo_without_a_condition_is_ready_and_says_why(tmp_path):
    body = _run(tmp_path)
    rows = {(r["ns"], r["name"]): r for r in body["flux"] if r["kind"] == "HelmRepository"}
    assert rows[("hindsight", "hindsight")]["ready"] is True
    assert "no Ready condition" in rows[("hindsight", "hindsight")]["message"]
    assert not any(r["kind"] == "HelmRepository" and r["name"] == "hindsight" for r in body["flux_not_ready"])


def test_a_failing_oci_repo_and_a_plain_repo_without_a_condition_stay_not_ready(tmp_path):
    body = _run(tmp_path)
    rows = {(r["ns"], r["name"]): r for r in body["flux"] if r["kind"] == "HelmRepository"}
    assert rows[("a", "broken-oci")]["ready"] is False and "pull denied" in rows[("a", "broken-oci")]["message"]
    assert rows[("b", "plain")]["ready"] is False and rows[("b", "plain")]["message"] == "no Ready condition yet"
