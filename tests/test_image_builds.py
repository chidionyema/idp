"""bin/idp-image-builds: the light that reads a red post-merge image build (EPIC-IDP-090).

The estate was green on 2026-10-22 while production ran a fleetview-backend image from before every
voice change the estate had landed: the lane's ci grades the change and never builds an image, the
merge is green because the change landed, bin/idp-deploy-lag is green because the tag that exists
reached main, and the pod is Ready because it is serving the old build. The one fact none of them
read is that the image build on main FAILED. These tests pin that fact down, and the three ways it
can be read wrongly: a repair that is not newer, a repair that is only half the matrix, and a
missing measurement reported as a pass.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "bin" / "idp-image-builds"


def _load():
    # The file has no .py suffix: spec_from_file_location returns None for it, so the loader is
    # named explicitly.
    loader = importlib.machinery.SourceFileLoader("idp_image_builds", str(SCRIPT))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[loader.name] = mod
    loader.exec_module(mod)
    return mod


ib = _load()


def run(rid, sha="a" * 40, conclusion="failure"):
    return {
        "id": rid,
        "head_sha": sha,
        "conclusion": conclusion,
        "html_url": f"https://example.test/runs/{rid}",
    }


def job(name, conclusion="success", steps=None):
    return {
        "name": name,
        "conclusion": conclusion,
        "steps": steps
        or [
            {"name": "Set up job", "conclusion": "success"},
            {"name": "Build and push", "conclusion": conclusion},
        ],
    }


def build(image, conclusion="success", arch="linux/amd64"):
    return job(
        f"build ({image}, {image}.Dockerfile, ., {arch})",
        conclusion,
        steps=[
            {"name": "Set up job", "conclusion": "success"},
            {"name": "Scan image for vulnerabilities", "conclusion": conclusion},
        ],
    )


def test_a_red_image_build_that_nothing_rebuilt_is_reported():
    runs = [run(2, "b" * 40), run(1, "a" * 40)]
    jobs = {
        2: [job("fast-gate / fast-gate"), build("factory")],
        1: [job("fast-gate / fast-gate"), build("fleetview-backend", "failure")],
    }
    rows = ib.unrepaired(runs, lambda r: jobs[r["id"]])
    assert [r["image"] for r in rows] == ["fleetview-backend"]
    assert rows[0]["run"] == 1
    assert rows[0]["step"] == "Scan image for vulnerabilities"
    assert rows[0]["state"] == "FAIL"


def test_a_later_green_build_of_the_same_image_repairs_it():
    runs = [run(2, "b" * 40, "success"), run(1, "a" * 40)]
    jobs = {
        2: [build("fleetview-backend")],
        1: [build("fleetview-backend", "failure")],
    }
    assert ib.unrepaired(runs, lambda r: jobs[r["id"]]) == []


def test_a_green_arm_in_the_same_run_does_not_repair_the_red_one():
    # both architectures and the merge must succeed before a tag exists
    runs = [run(1)]
    jobs = {
        1: [
            build("fleetview-backend", "success", "linux/amd64"),
            build("fleetview-backend", "failure", "linux/arm64"),
        ]
    }
    rows = ib.unrepaired(runs, lambda r: jobs[r["id"]])
    assert [r["image"] for r in rows] == ["fleetview-backend"]


def test_a_cancelled_newest_build_stands_because_nothing_was_published():
    runs = [run(1)]
    jobs = {1: [build("fleetview-backend", "cancelled")]}
    rows = ib.unrepaired(runs, lambda r: jobs[r["id"]])
    assert [r["image"] for r in rows] == ["fleetview-backend"]
    assert rows[0]["conclusion"] == "cancelled"


def test_the_merge_and_gate_jobs_are_not_images():
    assert ib.image_of("merge (backstage, backstage/Dockerfile, backstage)") is None
    assert ib.image_of("fast-gate / fast-gate") is None
    assert ib.image_of("discover") is None
    assert ib.image_of("build (factory, factory.Dockerfile, ., linux/amd64)") == "factory"


def test_a_missing_measurement_is_blind_not_green(monkeypatch, capsys):
    monkeypatch.setattr(ib, "gh_api", lambda path: {"workflow_runs": []})
    rc = ib.main(["--repo", "chidionyema/idp"])
    out = capsys.readouterr().out
    assert rc == 2, out
    assert "BLIND" in out


def test_a_red_build_makes_the_row_exit_non_zero(monkeypatch, capsys):
    def fake(path):
        if "/runs?" in path:
            return {"workflow_runs": [run(1)]}
        return {"jobs": [build("fleetview-backend", "failure")]}

    monkeypatch.setattr(ib, "gh_api", fake)
    rc = ib.main(["--repo", "chidionyema/idp"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "FAIL    image-builds  fleetview-backend" in out


def test_a_repaired_build_is_green(monkeypatch, capsys):
    def fake(path):
        if "/runs?" in path:
            return {"workflow_runs": [run(2, "b" * 40, "success"), run(1)]}
        return {"jobs": [build("fleetview-backend", "success")]}

    monkeypatch.setattr(ib, "gh_api", fake)
    rc = ib.main(["--repo", "chidionyema/idp"])
    out = capsys.readouterr().out
    assert rc == 0, out
    assert "ok      image-builds" in out
