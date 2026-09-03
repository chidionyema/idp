"""crew#584 / idp#631, 2026-08-28 (run 33201855349, job 98953001837): a docs-only PR (mkdocs.yml)
went red on `helm template signoz signoz --repo https://charts.signoz.io --version 0.138.0` with a
bare CalledProcessError and no reason -- bin/idp-kyverno-render ran helm with stderr=DEVNULL
(LAW 28). The chart exists (index grep = 1) and the same render passed 7 minutes earlier on #628:
eight dirs render at once (IDP_RENDER_JOBS) and three bdd tests under `-n auto` each render
again, all writing helm's ONE shared repository cache (index.yaml + chart .tgz) at the same time.
Founder: "why the fuck we always fucking up" / "why cant anything get done".

Rule: every `helm template` runs with its own cache under the judge's scratch dir, and a failing
helm's stderr reaches the judge's output verbatim. The block under test is lifted from the script
itself; `helm` is a stub on PATH; no network."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin" / "idp-kyverno-render"

STUB = """#!/bin/sh
# records the cache helm was given, then behaves as $HELM_STUB_MODE says
printf '%s\\n' "${HELM_REPOSITORY_CACHE:-DEFAULT}" >> "$HELM_STUB_LOG"
case "$HELM_STUB_MODE" in
  fail) echo "Error: no cached repo found. (try 'helm repo update'): open index-cache.yaml: no such file" >&2; exit 1 ;;
  *) printf 'apiVersion: v1\\nkind: ConfigMap\\nmetadata:\\n  name: %s\\n' "$2" ;;
esac
"""


def _helm_block() -> str:
    """The python heredoc that renders HelmReleases, exactly as the script runs it."""
    lines = SCRIPT.read_text().splitlines()
    start = next(
        i
        for i, l in enumerate(lines)
        if l.startswith('  python3 - "$S" "$S/kz-$slug.yaml" <<\'PY\'')
    )
    end = next(i for i in range(start + 1, len(lines)) if lines[i] == "PY")
    return "\n".join(lines[start + 1 : end]) + "\n"


def _kz(tmp: Path, releases: list[str]) -> Path:
    docs = [
        {
            "apiVersion": "source.toolkit.fluxcd.io/v1",
            "kind": "HelmRepository",
            "metadata": {"name": "repo"},
            "spec": {"url": "https://charts.example.test"},
        }
    ]
    for r in releases:
        docs.append(
            {
                "apiVersion": "helm.toolkit.fluxcd.io/v2",
                "kind": "HelmRelease",
                "metadata": {"name": r, "namespace": "observability"},
                "spec": {
                    "chart": {
                        "spec": {
                            "chart": r,
                            "version": "0.138.0",
                            "sourceRef": {"kind": "HelmRepository", "name": "repo"},
                        }
                    }
                },
            }
        )
    p = tmp / "kz.yaml"
    p.write_text(yaml.safe_dump_all(docs))
    return p


def _run(
    tmp: Path, releases: list[str], mode: str
) -> tuple[subprocess.CompletedProcess, list[str], Path]:
    fake = tmp / "bin"
    fake.mkdir()
    (fake / "helm").write_text(STUB)
    (fake / "helm").chmod(0o755)
    log = tmp / "helm.log"
    s = tmp / "S"
    s.mkdir()
    env = {
        **os.environ,
        "PATH": f"{fake}:{os.environ['PATH']}",
        "HELM_STUB_LOG": str(log),
        "HELM_STUB_MODE": mode,
    }
    env.pop("HELM_REPOSITORY_CACHE", None)
    out = subprocess.run(
        ["python3", "-", str(s), str(_kz(tmp, releases))],
        input=_helm_block(),
        env=env,
        capture_output=True,
        text=True,
    )
    caches = log.read_text().split() if log.exists() else []
    return out, caches, s


def test_every_helm_template_gets_its_own_cache_under_the_scratch_dir(tmp_path):
    out, caches, s = _run(tmp_path, ["signoz", "langfuse"], "ok")
    assert out.returncode == 0, out.stderr
    assert len(caches) == 2 and len(set(caches)) == 2, caches
    for c in caches:
        assert c != "DEFAULT" and Path(c).is_relative_to(s) and Path(c).is_dir(), (c, s)


def test_a_failing_helm_says_why_in_the_judges_output(tmp_path):
    out, _, _ = _run(tmp_path, ["signoz"], "fail")
    assert out.returncode != 0
    assert (
        "helm template signoz (signoz 0.138.0 from https://charts.example.test) exited 1"
        in out.stderr
    ), out.stderr
    assert "no cached repo found" in out.stderr, out.stderr
    assert "Traceback" not in out.stderr, out.stderr
