#!/usr/bin/env python3
"""bin/estate-showcase: property + incident tests (crew#474).

Rungs, per ~/AGENTS.md "How to test":
  property  for random synthetic catalogues: every entity is on the page exactly once, a
            grade is never ELITE when the deciding annotation is absent, every GAP row is
            printed before the first ELITE row, and rendering twice gives the same bytes.
  incident  named for crew#474 "expose ourselves before the market exposes us": a job whose
            last run failed is a GAP row on the page, and --check fails on a stale page and
            passes after a render, both ways in one run.

Run: python3 tests/test_estate_showcase.py (needs pyyaml). Exit 0 pass, 1 fail.
"""
import pathlib
import importlib.machinery
import importlib.util
import random
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
BIN = ROOT / "bin" / "estate-showcase"
spec = importlib.util.spec_from_loader("estate_showcase", importlib.machinery.SourceFileLoader("estate_showcase", str(BIN)))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def synth(rng: random.Random) -> list:
    docs = []
    for i in range(rng.randint(1, 8)):
        ann = {}
        if rng.random() < 0.8:
            ann["estate/last-status"] = rng.choice(["clean", "PASS", "FAIL", "NEVER RUN", "signal 1"])
        docs.append({"kind": "Resource", "metadata": {"name": f"job-{i}", "annotations": ann},
                     "spec": {"type": rng.choice(["scheduled-job", "guard"])}})
    for i in range(rng.randint(0, 4)):
        md = {"name": f"repo-{i}", "annotations": {"estate/dirty": str(rng.choice([0, 0, 3])), "estate/offsite": "True"}}
        if rng.random() < 0.7:
            md["description"] = "a repository"
        docs.append({"kind": "Component", "metadata": md, "spec": {"type": "service"}})
    for i in range(rng.randint(0, 3)):
        ann = {"estate/stale": rng.choice(["True", "False"]), "estate/age-h": "3"} if rng.random() < 0.8 else {}
        docs.append({"kind": "Resource", "metadata": {"name": f"drill-{i}", "annotations": ann}, "spec": {"type": "drill"}})
    return docs


def test_properties() -> None:
    for seed in range(200):
        rng = random.Random(seed)
        docs = synth(rng)
        page = mod.render("t", docs, [], None, Path("/x/STANDARDS.md"), Path("/x/S.md"))
        assert page == mod.render("t", docs, [], None, Path("/x/STANDARDS.md"), Path("/x/S.md")), seed
        for d in docs:
            assert page.count(f"`{d['metadata']['name']}`") == 1, (seed, d["metadata"]["name"])
            g, _ = mod.grade(d)
            ann = d["metadata"].get("annotations", {})
            typ = d["spec"]["type"]
            if typ in ("scheduled-job", "guard") and "estate/last-status" not in ann:
                assert g == mod.BLIND, (seed, d)
            if typ == "drill" and "estate/stale" not in ann:
                assert g == mod.BLIND, (seed, d)
        lines = page.splitlines()
        elite_at = lines.index("## Elite")
        assert not any("| GAP |" in l for l in lines[elite_at:]), seed
        assert all("| GAP |" in l or "| BLIND |" in l or not l.startswith("| ") or l.startswith("| Grade") or l.startswith("| —")
                   for l in lines[lines.index("## Gaps, loudest first"):lines.index("## Standards not yet live")]), seed


def test_incident_crew474_a_failed_job_is_a_gap_row_and_check_is_proved_both_ways() -> None:
    with tempfile.TemporaryDirectory() as td:
        cat = Path(td) / "catalog-info.yaml"
        out = Path(td) / "SHOWCASE.md"
        docs = [{"apiVersion": "backstage.io/v1alpha1", "kind": "Resource",
                 "metadata": {"name": "nightly-backup", "annotations": {"estate/last-status": "FAIL"}},
                 "spec": {"type": "scheduled-job"}}]
        cat.write_text("# inventory taken: 2026-08-27T00:00:00Z\n" + yaml.safe_dump_all(docs))
        args = [sys.executable, str(BIN), "--catalog", str(cat), "--out", str(out),
                "--standards", str(Path(td) / "none.md"), "--science", str(Path(td) / "none2.md")]
        assert subprocess.run(args + ["--check"], capture_output=True).returncode == 1, "no page: --check must fail"
        assert subprocess.run(args, capture_output=True).returncode == 0
        page = out.read_text()
        assert "| GAP | scheduled-job | `nightly-backup` | estate/last-status=FAIL |" in page, page
        assert "no table at" in page, "missing standards table must be BLIND on the page, not omitted"
        assert subprocess.run(args + ["--check"], capture_output=True).returncode == 0, "fresh page: --check must pass"
        out.write_text(page + "hand edit\n")
        assert subprocess.run(args + ["--check"], capture_output=True).returncode == 1, "drifted page: --check must fail"


if __name__ == "__main__":
    test_properties()
    test_incident_crew474_a_failed_job_is_a_gap_row_and_check_is_proved_both_ways()
    print("ok    test_estate_showcase: 2 passed")


def test_incident_crew474_guards_and_groups_are_graded_not_blind():
    """46 guards and the Domain/System/Group entities were BLIND on the first render: the
    guards because nothing carried hook-outcomes into the catalogue, the groups because the
    grader had no rule. Both ways: a guard seen clean is ELITE, one never seen stays BLIND,
    a described Domain is ELITE and an undescribed one is a GAP."""
    import importlib.util
    from importlib.machinery import SourceFileLoader
    p = pathlib.Path(__file__).resolve().parents[1] / "bin" / "estate-showcase"
    spec = importlib.util.spec_from_file_location("es_t", p, loader=SourceFileLoader("es_t", str(p)))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    guard = {"kind": "Resource", "spec": {"type": "guard"}, "metadata": {"annotations": {"estate/last-status": "clean"}}}
    assert m.grade(guard)[0] == m.ELITE
    assert m.grade({"kind": "Resource", "spec": {"type": "guard"}, "metadata": {}})[0] == m.BLIND
    assert m.grade({"kind": "Domain", "metadata": {"description": "the platform"}})[0] == m.ELITE
    assert m.grade({"kind": "Domain", "metadata": {}})[0] == m.GAP
