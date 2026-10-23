"""Every intent names a repo that exists, and a refusal is reported as a refusal.

2026-10-22: `pr-list` had never worked, and each defect hid the next one.

  1. its default repo was `chidioniema/idp` -- the org is `chidionyema`, one letter short -- so
     every call died with "Could not resolve to a Repository";
  2. `2>/dev/null` threw that message away, so the only trace was a `JSONDecodeError` on an empty
     stdin, which is what the Face showed the founder for weeks;
  3. the `|` threw away gh's exit status, and the state/repo values were interpolated into a python
     f-string by the shell, so `repo=chidionyema/idp` was a SyntaxError even when gh answered.

A gate that cannot fail is not a gate, so this one does not read the YAML and agree with itself:
the pr-list tests run the rendered step against a stub `gh` that refuses, and against one that
answers, and assert the difference in what the caller sees.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
INTENTS = sorted((REPO_ROOT / "platform/estate/intents").glob("*.yaml"))

# The estate's GitHub org. Every image the pipeline publishes is ghcr.io/chidionyema/<name>
# (AGENTS.md section 2); a second spelling in a repo position is a typo, not a mirror.
EXPECTED_ORG = "chidionyema"


def _render(cmd: str, args: dict) -> str:
    for name, val in args.items():
        rendered = str(val)
        cmd = cmd.replace("{{" + name + "}}", shlex.quote(rendered))
        cmd = cmd.replace("<<" + name + ">>", rendered)
    return cmd


def _defaults(intent: dict) -> dict:
    return {
        k: (v or {}).get("default", "x") if isinstance(v, dict) else v
        for k, v in (intent.get("args") or {}).items()
    }


def _step_cmd(intent: dict) -> str:
    for step in intent.get("steps") or []:
        if "cmd" in step:
            return _render(step["cmd"], _defaults(intent))
    raise AssertionError("no cmd step")


@pytest.mark.parametrize("path", INTENTS, ids=lambda p: p.stem)
def test_no_intent_names_a_repo_that_does_not_exist(path):
    """A repo position must carry the real org. One letter off is a dead door, not a redirect."""
    text = path.read_text()
    assert "chidioniema" not in text, (
        f"{path.name}: names chidioniema, which GitHub cannot resolve (the org is {EXPECTED_ORG})"
    )
    # a concrete repo position: `--repo owner/name` or `repos/owner/name`. A `{{placeholder}}`
    # cannot match the owner pattern, so a parameterised repo is left alone.
    concrete = re.compile(
        r"(?:--repo |repos/)([A-Za-z0-9][A-Za-z0-9-]*)/[A-Za-z0-9._-]+"
    )
    for line in text.splitlines():
        if line.strip().startswith("#"):
            continue
        for owner in concrete.findall(line):
            assert owner == EXPECTED_ORG, (
                f"{path.name}: repo owner {owner!r} is not {EXPECTED_ORG}: {line.strip()}"
            )


@pytest.mark.parametrize("path", INTENTS, ids=lambda p: p.stem)
def test_a_read_door_does_not_throw_away_why_its_tool_refused(path):
    """`2>/dev/null` on a gh call is how a real reason became a JSONDecodeError."""
    offenders = [
        line.strip()
        for line in path.read_text().splitlines()
        if "gh " in line and "2>/dev/null" in line and not line.strip().startswith("#")
    ]
    assert not offenders, f"{path.name}: discards gh's own reason: {offenders}"


def _stub_gh(tmp_path: Path, body: str) -> Path:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    stub = bin_dir / "gh"
    stub.write_text("#!/bin/sh\n" + body)
    stub.chmod(0o755)
    return bin_dir


def test_lane_answers_from_any_working_directory(tmp_path):
    """`gh repo view` with no `--repo` only answers inside a checkout.

    2026-10-23: asked from the home directory -- where the executor runs and where the Face's call
    lands -- the `lane` step halted with `JSONDecodeError: Expecting value: line 1 column 1`, because
    gh wrote its refusal to stderr and the step piped the empty stdout into json.load. The step must
    name the repo it is asking about; GH_REPO is how idp-greenlane takes that name.
    """
    intent = yaml.safe_load(
        (REPO_ROOT / "platform/estate/intents/lane.yaml").read_text()
    )
    cmd = _step_cmd(intent)
    assert re.search(r"GH_REPO=(?:\$\{GH_REPO:-)?chidionyema/idp", cmd), (
        f"lane does not name the repo it asks gh about, so it fails outside a checkout: {cmd}"
    )


def _run_pr_list(tmp_path: Path, gh_body: str) -> subprocess.CompletedProcess:
    intent = yaml.safe_load(
        (REPO_ROOT / "platform/estate/intents/pr-list.yaml").read_text()
    )
    cmd = _step_cmd(intent)
    bin_dir = _stub_gh(tmp_path, gh_body)
    env = dict(os.environ, PATH=f"{bin_dir}:/usr/bin:/bin:/usr/sbin:/sbin")
    return subprocess.run(
        ["/bin/sh", "-c", cmd],
        cwd=str(tmp_path),
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_pr_list_shows_gh_refusal_instead_of_a_json_traceback(tmp_path):
    reason = "GraphQL: Could not resolve to a Repository with the name 'nope/nope'."
    result = _run_pr_list(tmp_path, f'echo "{reason}" >&2\nexit 1\n')
    seen = result.stdout + result.stderr
    assert result.returncode == 1, (
        f"a refusal must fail the step, got {result.returncode}"
    )
    assert reason in seen, f"gh's own reason was lost; the caller saw: {seen!r}"
    assert "JSONDecodeError" not in seen, (
        f"still reporting a parser error, not the reason: {seen!r}"
    )


def test_pr_list_lists_the_prs_when_gh_answers(tmp_path):
    payload = [
        {
            "number": 6880,
            "title": "fleetview-backend: the image builds again",
            "headRefName": "lane/x",
            "baseRefName": "main",
            "isDraft": False,
            "additions": 1,
            "deletions": 2,
            "changedFiles": 3,
            "updatedAt": "2026-10-22T20:00:00Z",
        }
    ]
    result = _run_pr_list(tmp_path, f"cat <<'JSON'\n{json.dumps(payload)}\nJSON\n")
    assert result.returncode == 0, result.stderr
    assert "PRs (1, state=open, repo=chidionyema/idp):" in result.stdout, result.stdout
    assert "#6880" in result.stdout, result.stdout
