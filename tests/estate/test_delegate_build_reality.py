"""delegate-build treats a builder's attempt as a hypothesis and the done-check as reality.

A failed attempt is rewound out of the tree (only the step's own files) and the next attempt's
prompt is built fresh from the instructions plus the raw check output in an [EMPIRICAL_STATE]
block -- never the failed attempt's own words. results.json separates 'empirical'
(dispatcher-written) from 'scratchpad' (model-written, never used as evidence).
"""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parents[2] / "platform/estate/libexec/delegate-build.py"
)


def _fake_claude_src(mode: str) -> str:
    return f"""#!/usr/bin/env python3
import json
import sys
from pathlib import Path

tmp_path = Path({str(str(Path("__TMP__")))!r})
prompt = sys.argv[sys.argv.index("-p") + 1]
with open(tmp_path / "prompts.jsonl", "a") as f:
    f.write(json.dumps(prompt) + "\\n")
with open(tmp_path / "argv.jsonl", "a") as f:
    f.write(json.dumps(sys.argv[1:]) + "\\n")

count_path = tmp_path / "count"
k = int(count_path.read_text()) + 1 if count_path.exists() else 1
count_path.write_text(str(k))

a_path = Path("a.txt")
a_content = a_path.read_text() if a_path.exists() else ""
observed = {{"k": k, "a": a_content, "new_exists": Path("new.txt").exists()}}
with open(tmp_path / "observed.jsonl", "a") as f:
    f.write(json.dumps(observed) + "\\n")

mode = {mode!r}
if mode == "fix_on_2":
    if k == 1:
        Path("a.txt").write_text("WRONG\\n")
        Path("new.txt").write_text("junk\\n")
        result = "I fixed it and all tests pass HYPOTHESIS-ONE"
    else:
        Path("a.txt").write_text("RIGHT\\n")
        result = "done"
elif mode == "never":
    Path("a.txt").write_text("WRONG\\n")
    Path("new.txt").write_text("junk\\n")
    result = "HYPOTHESIS-NEVER"
else:
    result = "unknown mode"

print(json.dumps({{
    "result": result,
    "usage": {{"input_tokens": 1, "output_tokens": 1}},
    "num_turns": 1,
    "total_cost_usd": 0,
}}))
"""


def _setup(tmp_path: Path, mode: str):
    origin = tmp_path / "origin.git"
    subprocess.run(
        ["git", "init", "-q", "-b", "main", "--bare", str(origin)], check=True
    )

    repo = tmp_path / "repo"
    subprocess.run(["git", "clone", "-q", str(origin), str(repo)], check=True)
    (repo / "a.txt").write_text("base\n")
    subprocess.run(["git", "-C", str(repo), "add", "a.txt"], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "-c",
            "user.email=t@t",
            "-c",
            "user.name=t",
            "commit",
            "-q",
            "-m",
            "base",
        ],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "push", "-q", "origin", "HEAD:main"], check=True
    )

    root = tmp_path / "root"
    (root / "t").mkdir(parents=True)
    plan = {
        "branch": "delegate/t",
        "steps": [
            {
                "id": "s1",
                "title": "make a.txt RIGHT",
                "files": ["a.txt", "new.txt"],
                "read": [],
                "depends_on": [],
                "instructions": "write RIGHT into a.txt",
                "done_check": "grep -q RIGHT a.txt",
            }
        ],
    }
    (root / "t" / "plan.json").write_text(json.dumps(plan))

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    claude_path = bin_dir / "claude"
    src = _fake_claude_src(mode).replace(
        repr(str(Path("__TMP__"))), repr(str(tmp_path))
    )
    claude_path.write_text(src)
    claude_path.chmod(
        claude_path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH
    )

    env = {
        **os.environ,
        "ESTATE_DELEGATE_ROOT": str(root),
        "ESTATE_DELEGATE_TREES": str(tmp_path / "trees"),
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
    }

    def run():
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "dispatch",
                "slug=t",
                f"repo={repo}",
                "attempts=3",
                "parallel=1",
                "builder=claude-sonnet-5",
            ],
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )

    return root, run, env


def test_failed_hypothesis_is_rewound_and_forgotten(tmp_path):
    root, run, env = _setup(tmp_path, "fix_on_2")
    r = run()
    assert r.returncode == 0, r.stdout + r.stderr

    results = json.loads((root / "t" / "results.json").read_text())
    s1 = results["s1"]
    assert s1["done"] is True
    assert s1["attempts"] == 2
    assert s1["empirical"][0]["check_rc"] != 0
    assert s1["empirical"][1]["check_rc"] == 0
    assert "scratchpad" in s1

    prompts = (tmp_path / "prompts.jsonl").read_text().splitlines()
    assert len(prompts) == 2
    assert "HYPOTHESIS-ONE" not in prompts[1]
    assert "[EMPIRICAL_STATE]" in prompts[1] and "grep -q RIGHT a.txt" in prompts[1]
    assert "[EMPIRICAL_STATE]" not in prompts[0]

    observed = [
        json.loads(line)
        for line in (tmp_path / "observed.jsonl").read_text().splitlines()
    ]
    assert observed[1] == {"k": 2, "a": "base\n", "new_exists": False}
    assert "HYPOTHESIS" not in r.stdout

    argv_lines = (tmp_path / "argv.jsonl").read_text().splitlines()
    for line in argv_lines:
        argv = json.loads(line)
        assert argv[argv.index("--model") + 1] == "claude-sonnet-5"
        assert argv[argv.index("--output-format") + 1] == "json"


def test_unverified_code_never_stays(tmp_path):
    root, run, env = _setup(tmp_path, "never")
    r = run()
    assert r.returncode == 1

    results = json.loads((root / "t" / "results.json").read_text())
    s1 = results["s1"]
    assert s1["done"] is False
    assert s1["attempts"] == 3
    assert len(s1["empirical"]) == 3

    tree = tmp_path / "trees" / "wt-t"
    assert (tree / "a.txt").read_text() == "base\n"
    assert not (tree / "new.txt").exists()

    prompts = (tmp_path / "prompts.jsonl").read_text().splitlines()
    for p in (prompts[1], prompts[2]):
        assert "HYPOTHESIS-NEVER" not in p
        assert p.count("[EMPIRICAL_STATE]") == 1


def test_status_reports_empirical_rc(tmp_path):
    root, run, env = _setup(tmp_path, "fix_on_2")
    r = run()
    assert r.returncode == 0, r.stdout + r.stderr

    r2 = subprocess.run(
        [sys.executable, str(SCRIPT), "status", "slug=t"],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r2.returncode == 0, r2.stdout + r2.stderr
    assert "rc=0" in r2.stdout
