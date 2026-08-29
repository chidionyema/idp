"""Incident, 2026-08-29: catalog-render run 33224632189 died at `pip install -q -r
.github/requirements/catalog-render.txt` — "No such file or directory". #662 added the
line to a workflow whose idp checkout lives under `path: idp`, so every relative path in a
step without `working-directory: idp` resolves against the empty workspace root.

Guard: in every workflow that checks this repo out under a `path:`, a requirements file
named by `pip install -r` or `cache-dependency-path` in a step that has no
working-directory must carry that path prefix and exist in the tree.
"""
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = sorted((ROOT / ".github" / "workflows").glob("*.yml"))
REQ = re.compile(r"(?:-r\s+|cache-dependency-path:\s*\|?\s*)?([\w./-]*requirements/[\w./-]+)")


def _checkout_path(steps):
    for s in steps:
        uses = str(s.get("uses", ""))
        if uses.startswith("actions/checkout") and "repository" not in (s.get("with") or {}):
            return (s.get("with") or {}).get("path")
    return None


def _misses(wf_path: Path):
    doc = yaml.safe_load(wf_path.read_text())
    out = []
    for job in (doc.get("jobs") or {}).values():
        steps = job.get("steps") or []
        prefix = _checkout_path(steps)
        if not prefix:
            continue
        for s in steps:
            wd = s.get("working-directory") or (job.get("defaults") or {}).get("run", {}).get("working-directory")
            text = "\n".join([str(s.get("run", "")), yaml.safe_dump(s.get("with") or {})])
            for ref in REQ.findall(text):
                rel = ref if wd else ref
                base = ROOT if (wd == prefix) else None
                if base is None:
                    if not ref.startswith(prefix + "/"):
                        out.append(f"{wf_path.name}: step {s.get('name', s.get('uses'))!r} names {ref} outside the {prefix}/ checkout")
                        continue
                    rel = ref[len(prefix) + 1:]
                if not (ROOT / rel).exists():
                    out.append(f"{wf_path.name}: {ref} does not exist in the tree")
    return out


def test_every_requirements_path_resolves_inside_the_checkout():
    misses = [m for wf in WORKFLOWS for m in _misses(wf)]
    assert not misses, "\n".join(misses)


def test_the_incident_shape_is_refused(tmp_path):
    bad = tmp_path / "x.yml"
    bad.write_text(
        "jobs:\n  r:\n    steps:\n      - uses: actions/checkout@v7\n        with: {path: idp}\n"
        "      - run: pip install -r .github/requirements/catalog-render.txt\n"
    )
    assert _misses(bad), "the 00:48Z shape must be named"
