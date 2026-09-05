"""crew#488 CP2: the same Flux tree is rehearsed on a second provider and a second distribution in
the same run — a k3s node on the GitHub-hosted (Azure) runner, no docker, no OCI — graded against the
same floor, with the wall-clock and the cost printed. Both jobs run one hydration script, so
"the drill" has one definition (LAW 19: portability outranks detection; LAW 23: the smaller road)."""
import os
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / ".github/workflows/portability-drill.yml"


def _jobs():
    return yaml.safe_load(WF.read_text())["jobs"]


def test_k3s_job_is_a_second_distribution_on_the_runner_vm_not_docker() -> None:
    jobs = _jobs()
    assert set(jobs) >= {"hydrate", "k3s"}
    k3s = jobs["k3s"]
    assert k3s["runs-on"] == "ubuntu-latest"
    install = next(s for s in k3s["steps"] if "k3s on the runner VM" in s.get("name", ""))
    assert re.fullmatch(r"v\d+\.\d+\.\d+\+k3s\d+", install["env"]["INSTALL_K3S_VERSION"]), "k3s version must be pinned"
    assert "--disable traefik" in install["env"]["INSTALL_K3S_EXEC"], "the estate's traefik comes from the Flux tree"
    assert "get.k3s.io" in install["run"] and "k3d" not in install["run"]
    assert "docker" not in yaml.dump(k3s), "CP2 is a second distribution, not k3d under another name"


def test_both_providers_run_the_one_hydration_script_at_the_same_commit() -> None:
    jobs = _jobs()
    for name in ("hydrate", "k3s"):
        step = next(s for s in jobs[name]["steps"] if s.get("run") == "bin/idp-hydrate")
        assert step["env"]["SHA"] == "${{ github.event.pull_request.head.sha || github.sha }}", name
        assert step["env"]["REF"] == "${{ github.head_ref || github.ref_name }}", name
    script = ROOT / "bin/idp-hydrate"
    assert os.access(script, os.X_OK)
    body = script.read_text()
    assert "flux install" in body and "flux create source git" in body and '--commit="$SHA"' in body
    assert "clusters/oke/estate-config.yaml" in body and 'clusters/oke/*.yaml' in body
    assert "bin/idp-hydrate" in yaml.safe_load(WF.read_text())[True]["pull_request"]["paths"]


def test_k3s_job_grades_the_same_floor_and_prints_wall_clock_and_cost() -> None:
    k3s = _jobs()["k3s"]
    grade = next(s for s in k3s["steps"] if "wall-clock" in s.get("name", ""))
    assert "bin/idp-portability-drill receipt/kustomizations.json" in grade["run"]
    assert "wall_clock=${secs}s" in grade["run"] and "cost=${cost}" in grade["run"]
    assert grade["env"]["PRIVATE"] == "${{ github.event.repository.private }}", "cost is read from the repository, never assumed"
    assert "ok      portability-k3s" in grade["run"]


def test_catalogue_row_grades_the_k3s_job_on_the_same_schedule() -> None:
    rows = {r["name"]: r for r in yaml.safe_load((ROOT / "drills/catalogue.yaml").read_text())["drills"]}
    a, b = rows["portability"], rows["portability-k3s"]
    assert b["workflow"] == a["workflow"] == "portability-drill.yml"
    assert b["job"] == "k3s" and a["job"] == "hydrate"
    assert b["schedule"] == a["schedule"] and b["max_age_hours"] == a["max_age_hours"]
    assert "cost" in b["proves"] and "k3s" in b["proves"]
