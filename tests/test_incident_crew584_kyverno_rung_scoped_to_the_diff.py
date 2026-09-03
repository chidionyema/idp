"""crew#584 zero-bottleneck law (founder 2026-08-28: "zero bottleneck law optinise ruthlessly").

Run 33198380701 spent 160 of bin/idp-ci's 422 s judging every platform dir against Kyverno on a PR
that changed one shell script; #625's parallel render bought 12 s of that on the hosted runner. The
rung now judges only the dirs the PR's diff touches, and every dir when the judge, a policy, a
fixture or the cluster wiring moved. Two ways this can rot, both graded here by executing the
block lifted from bin/idp-ci against a throwaway git repo, never by reading comments:

  * a changed dir is dropped -> a render that would be refused at admission merges (crew#539)
  * the judge changes and the scope stays narrow -> every unchanged dir's verdict goes unchecked
"""

import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CI = ROOT / "bin" / "idp-ci"


def _scope_block() -> str:
    src = CI.read_text()
    start = src.index('  kyv_scope="every dir"')
    end = src.index('  [ "$dirs" = skip ] ||', start)
    return src[start:end]


def _repo(tmp_path: Path) -> Path:
    r = tmp_path / "repo"
    r.mkdir(parents=True)
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@t",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@t",
    }

    def git(*a: str) -> None:
        subprocess.run(["git", *a], cwd=r, check=True, capture_output=True, env=env)

    git("init", "-q", "-b", "main")
    for d in ("platform/a", "platform/b"):
        (r / d).mkdir(parents=True)
        (r / d / "kustomization.yaml").write_text("resources: []\n")
    git("add", ".")
    git("commit", "-q", "-m", "main")
    git("checkout", "-q", "-b", "pr")
    return r


def _run(repo: Path, changed: str, base: str = "main") -> dict:
    (repo / changed).parent.mkdir(parents=True, exist_ok=True)
    (repo / changed).write_text("x\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=t",
            "-c",
            "user.email=t@t",
            "commit",
            "-q",
            "-m",
            "pr",
        ],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    script = (
        'IDP="$PWD"; say() { printf "%s\\n" "$*"; }\ndirs="platform/a\nplatform/b"\n'
        + _scope_block()
        + 'printf "DIRS=%s\\nSCOPE=%s\\n" "$(printf "%s" "$dirs" | tr "\\n" " ")" "$kyv_scope"\n'
    )
    r = subprocess.run(
        ["bash", "-c", script],
        cwd=repo,
        capture_output=True,
        text=True,
        env={**os.environ, "IDP_CI_BASE": base},
    )
    assert r.returncode == 0, r.stderr
    return dict(re.findall(r"^(DIRS|SCOPE)=(.*)$", r.stdout, re.M)) | {"out": r.stdout}


def test_a_changed_dir_is_judged_and_an_untouched_one_is_not(tmp_path: Path) -> None:
    out = _run(_repo(tmp_path), "platform/a/values.yaml")
    assert out["DIRS"].split() == ["platform/a"], out
    assert out["SCOPE"].startswith("1 of 2 dirs changed against main"), out


def test_a_pr_touching_no_platform_dir_skips_with_a_verdict_that_says_so(
    tmp_path: Path,
) -> None:
    out = _run(_repo(tmp_path), "docs/x.md")
    assert out["DIRS"] == "skip", out
    assert "ok    kyverno  no platform dir changed against main" in out["out"], out


def test_the_judge_a_policy_or_the_cluster_wiring_changing_widens_to_every_dir(
    tmp_path: Path,
) -> None:
    for path in (
        "bin/idp-kyverno-render",
        "tests/fixtures/kyverno/must-fail/x.yaml",
        "clusters/oke/flux.yaml",
        "bin/idp-ci",
    ):
        out = _run(_repo(tmp_path / path.replace("/", "_")), path)
        assert out["DIRS"].split() == ["platform/a", "platform/b"], (path, out)
        assert out["SCOPE"].startswith("every dir:"), (path, out)


def test_no_base_ref_means_every_dir(tmp_path: Path) -> None:
    out = _run(_repo(tmp_path), "docs/x.md", base="")
    assert out["DIRS"].split() == ["platform/a", "platform/b"], out
    assert out["SCOPE"] == "every dir", out
