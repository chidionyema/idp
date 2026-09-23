"""Prove the shadow state-sync re-shaper (spec W2.1, LAW 3).

The rule under test: 'bin/idp-shadow-sync'. In the shadow dimension a workload's manifests are
cloned down so a change can be proven without touching live production (spec W2.1). Secrets are
NEVER copied: each becomes a same-shape shell under keys of the same names (stamped
shadow.estate/shell=true) so a Deployment mounts and starts, and no live value survives into the
shadow. Everything non-secret passes through unchanged.

These tests prove both directions on real fixture manifests: a live Secret value must not survive
re-shaping (and --check refuses a verbatim secret), while a Deployment passes through byte-for-key
unchanged. Spinning the vcluster is the live seam this deterministic tool deliberately does not
need.
"""

import os
import subprocess
import tempfile

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "bin", "idp-shadow-sync")
SRC = os.path.join(ROOT, "tests", "fixtures", "shadow-sync", "src")
LIVE = "live-token-value-abc123-that-must-never-survive"


def _reshaped(out_dir):
    r = subprocess.run(
        [
            "python3",
            BIN,
            os.path.join(SRC, "deployment.yaml"),
            os.path.join(SRC, "secret.yaml"),
            "--out",
            out_dir,
        ],
        capture_output=True,
        text=True,
    )
    return r


def test_binary_exists():
    assert os.path.exists(BIN)


def test_live_secret_value_never_survives_into_shadow():
    with tempfile.TemporaryDirectory() as d:
        r = _reshaped(d)
        assert r.returncode == 0, r.stdout
        out = os.path.join(d, "secret-worker-creds.yaml")
        assert os.path.exists(out)
        doc = yaml.safe_load(open(out, encoding="utf-8"))
        # the live plaintext is gone; keys survive as same-shape shells
        assert doc["metadata"]["annotations"]["shadow.estate/shell"] == "true"
        assert "hunter2" not in open(out, encoding="utf-8").read()
        assert (
            "CYRUS_GITHUB_TOKEN" in doc["stringData"]
            and "DB_PASSWORD" in doc["stringData"]
        )
        assert all("shadow-" in v for v in doc["stringData"].values())


def test_deployment_passes_through_unchanged():
    with tempfile.TemporaryDirectory() as d:
        r = _reshaped(d)
        assert r.returncode == 0
        doc = yaml.safe_load(
            open(os.path.join(d, "deployment-worker.yaml"), encoding="utf-8")
        )
        assert doc == yaml.safe_load(
            open(os.path.join(SRC, "deployment.yaml"), encoding="utf-8")
        )


def test_check_refuses_a_verbatim_secret_and_accepts_shells():
    # a non-shell secret dir must FAIL --check; the reshaped out dir must pass
    with tempfile.TemporaryDirectory() as verbatim:
        v = os.path.join(verbatim, "s.yaml")
        with open(v, "w", encoding="utf-8") as fh:
            yaml.safe_dump(
                {
                    "apiVersion": "v1",
                    "kind": "Secret",
                    "metadata": {"name": "x"},
                    "stringData": {"K": LIVE},
                },
                fh,
            )
        bad = subprocess.run(
            ["python3", BIN, "--check", verbatim], capture_output=True, text=True
        )
        assert bad.returncode == 1, bad.stdout
    with tempfile.TemporaryDirectory() as d:
        _reshaped(d)
        good = subprocess.run(
            ["python3", BIN, "--check", d], capture_output=True, text=True
        )
        assert good.returncode == 0, good.stdout
