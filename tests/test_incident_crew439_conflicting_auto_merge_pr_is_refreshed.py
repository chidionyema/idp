"""crew#439: idp#298 (flux/image-updates -> main, auto-merge armed) went CONFLICTING when #296
merged the same newTag line by another path. For two hours every controller push re-ran
image-update-pr, which printed "ok auto-merge armed", and nothing merged; the sovereign-worker fix
sat unrolled. Rule: bin/idp-image-update-pr never prints ok for a pull request that is not
MERGEABLE; a CONFLICTING one gets main merged into it (the branch's lines win), pushed, and ci
pushed with the writer key so ci runs on the branch; anything else exits 1. Rung 4, incident test, proved both ways against a
fake gh and a real temporary origin."""
import os
import stat
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin" / "idp-image-update-pr"


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
                          cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def make_repos(tmp_path: Path) -> tuple[Path, Path]:
    """origin has main and flux/image-updates diverged on the newTag line of k.yaml, and main
    also changed a line three lines away (a separate hunk, as #296 did); work is a
    clone on flux/image-updates."""
    origin = tmp_path / "origin.git"
    seed = tmp_path / "seed"
    git(tmp_path, "init", "-q", "--bare", str(origin))
    git(tmp_path, "init", "-q", "-b", "main", str(seed))
    (seed / "k.yaml").write_text("newTag: main-700\n#\n#\n#\nother: 1\n")
    git(seed, "add", "k.yaml")
    git(seed, "commit", "-q", "-m", "base")
    git(seed, "checkout", "-q", "-b", "flux/image-updates")
    (seed / "k.yaml").write_text("newTag: main-783\n#\n#\n#\nother: 1\n")
    git(seed, "commit", "-q", "-am", "controller: main-783")
    git(seed, "checkout", "-q", "main")
    (seed / "k.yaml").write_text("newTag: main-775\n#\n#\n#\nother: 2\n")
    git(seed, "commit", "-q", "-am", "by another path: main-775, other 2")
    git(seed, "push", "-q", str(origin), "main", "flux/image-updates")
    work = tmp_path / "work"
    git(tmp_path, "clone", "-q", "-b", "flux/image-updates", str(origin), str(work))
    return origin, work


def fake_gh(tmp_path: Path, mergeable: str) -> tuple[Path, Path]:
    log = tmp_path / "gh.log"
    d = tmp_path / "bin"
    d.mkdir(exist_ok=True)
    gh = d / "gh"
    gh.write_text(f"""#!/bin/sh
echo "$*" >> {log}
case "$1 $2" in
  "pr list") echo 5 ;;
  "pr view") case "$*" in *body*) echo "Optimised: 1 -> 1 steps, 1 -> 1 round trips; cut: nothing" ;; *) echo {mergeable} ;; esac ;;
esac
""")
    gh.chmod(gh.stat().st_mode | stat.S_IEXEC)
    return d, log


def run(work: Path, bindir: Path) -> subprocess.CompletedProcess:
    env = {**os.environ, "PATH": f"{bindir}:{os.environ['PATH']}", "MERGEABLE_WAIT": "0"}
    return subprocess.run([str(SCRIPT)], cwd=work, env=env, capture_output=True, text=True)


def test_a_conflicting_pr_gets_main_merged_and_pushed_before_it_is_armed(tmp_path):
    origin, work = make_repos(tmp_path)
    bindir, log = fake_gh(tmp_path, "CONFLICTING")
    r = run(work, bindir)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "was CONFLICTING, merged main" in r.stdout and "pushed with the writer key" in r.stdout
    assert r.stdout.strip().endswith("auto-merge armed")
    pushed = git(tmp_path, "--git-dir", str(origin), "show", "flux/image-updates:k.yaml")
    assert pushed == "newTag: main-783\n#\n#\n#\nother: 2", pushed  # the controller's line won, main's change came along
    calls = log.read_text()
    assert "workflow run" not in calls  # a GITHUB_TOKEN dispatch is not the path; the writer-key push fires ci
    assert calls.strip().endswith("pr merge 5 --auto --squash")


def test_a_mergeable_pr_is_armed_and_nothing_is_pushed(tmp_path):
    origin, work = make_repos(tmp_path)
    before = git(tmp_path, "--git-dir", str(origin), "rev-parse", "flux/image-updates")
    bindir, log = fake_gh(tmp_path, "MERGEABLE")
    r = run(work, bindir)
    assert r.returncode == 0 and r.stdout.strip() == "ok      image-update-pr #5 auto-merge armed", r.stdout + r.stderr
    assert git(tmp_path, "--git-dir", str(origin), "rev-parse", "flux/image-updates") == before
    assert "workflow run" not in log.read_text()


def test_an_unknown_mergeable_state_is_never_reported_ok(tmp_path):
    _origin, work = make_repos(tmp_path)
    bindir, log = fake_gh(tmp_path, "UNKNOWN")
    r = run(work, bindir)
    assert r.returncode == 1 and r.stdout.startswith("FAIL    image-update-pr #5 mergeable=UNKNOWN")
    assert "pr merge" not in log.read_text()


def test_the_workflow_runs_the_script_and_the_refresh_push_fires_ci():
    wf = (ROOT / ".github/workflows/image-update-pr.yml").read_text()
    assert "bin/idp-image-update-pr" in wf and "fetch-depth: 0" in wf
    # A GITHUB_TOKEN push fires no run, and a workflow_dispatch on ci.yml is a founder button
    # (crew#401 rule 3), so the refresh pushes with the flux-writer deploy key like kini-finish.yml.
    assert "SEED_FLUX_WRITER_IDENTITY_B64" in wf and 'PUSH_URL="git@github.com:' in wf
    assert "workflow_dispatch" not in (ROOT / ".github/workflows/ci.yml").read_text()
    assert os.access(SCRIPT, os.X_OK)


def test_the_oke_check_row_fails_on_a_stuck_armed_pr_and_is_ok_when_none_is(tmp_path):
    """crew#439 row 1, both ways: the row grades the exact shape gh pr list returns."""
    row = ROOT / "bin" / "idp-automerge-stuck"
    stuck = tmp_path / "stuck.json"
    stuck.write_text('[{"number": 298, "autoMergeRequest": {"enabledAt": "t"}, "mergeable": "CONFLICTING"},'
                     ' {"number": 300, "autoMergeRequest": null, "mergeable": "CONFLICTING"},'
                     ' {"number": 301, "autoMergeRequest": {"enabledAt": "t"}, "mergeable": "MERGEABLE"}]')
    r = subprocess.run([str(row), "--input", str(stuck)], capture_output=True, text=True)
    assert r.returncode == 1 and r.stdout.strip() == "FAIL    automerge-stuck  1 stuck: #298 CONFLICTING", r.stdout
    clean = tmp_path / "clean.json"
    clean.write_text('[{"number": 301, "autoMergeRequest": {"enabledAt": "t"}, "mergeable": "MERGEABLE"},'
                     ' {"number": 300, "autoMergeRequest": null, "mergeable": "CONFLICTING"}]')
    r = subprocess.run([str(row), "--input", str(clean)], capture_output=True, text=True)
    assert r.returncode == 0 and r.stdout.strip() == "ok      automerge-stuck  0 stuck of 1 armed", r.stdout
    assert "run: bin/idp-automerge-stuck" in (ROOT / ".github/workflows/oke-check.yml").read_text()


if __name__ == "__main__":
    sys.exit(subprocess.call([sys.executable, "-m", "pytest", "-q", __file__]))
