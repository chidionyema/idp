#!/usr/bin/env python3
"""Materialize Uber SubmitQueue's *entire speculative path* for unprivileged CI.

Uber's githubactions BuildRunner dispatches four sq_* inputs. Testing only
sq_head_uris silently certifies the wrong future; this builder applies
sq_base_uris followed by sq_head_uris to trusted main, refusing missing or
moved refs. No PR source code executes until credentials have been dropped.
The candidate is provisional: production proof must still match the SHA
the protected-main promoter actually evaluates.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from dataclasses import dataclass
from urllib.parse import urlsplit

SHA = re.compile(r"^[0-9a-f]{40}$")
NAME = re.compile(r"^[A-Za-z0-9_.-]+$")


@dataclass(frozen=True)
class Change:
    owner: str
    repo: str
    number: int
    sha: str


def parse_uri(uri: str, expected_repo: str) -> Change:
    parsed = urlsplit(uri)
    parts = parsed.path.strip("/").split("/")
    if (
        parsed.scheme != "github"
        or parsed.hostname != "github.com"
        or parsed.username
        or parsed.password
        or parsed.port
        or parsed.query
        or parsed.fragment
        or len(parts) != 5
        or parts[2] != "pull"
        or not NAME.fullmatch(parts[0])
        or not NAME.fullmatch(parts[1])
        or f"{parts[0]}/{parts[1]}" != expected_repo
        or not re.fullmatch(r"[1-9][0-9]*", parts[3])
        or not SHA.fullmatch(parts[4])
    ):
        raise ValueError("untrusted/noncanonical GitHub change URI")
    return Change(parts[0], parts[1], int(parts[3]), parts[4])


def parse_input(value: str, expected_repo: str, allow_empty: bool) -> list[Change]:
    values = json.loads(value)
    if (
        not isinstance(values, list)
        or len(values) > 32
        or (not allow_empty and not values)
    ):
        raise ValueError("invalid speculative build path length")
    if not all(isinstance(v, str) for v in values):
        raise ValueError("change URI must be a string")
    parsed = [parse_uri(v, expected_repo) for v in values]
    if len({v.number for v in parsed}) != len(parsed):
        raise ValueError("duplicate PR in one path")
    return parsed


def parse_path(base_json: str, head_json: str, repo: str) -> list[Change]:
    bases = parse_input(base_json, repo, True)
    heads = parse_input(head_json, repo, False)
    all_changes = bases + heads
    if len({v.number for v in all_changes}) != len(all_changes):
        raise ValueError("PR appears both as dependency and batch head")
    return all_changes


def git(*args: str, authenticated: bool = False) -> str:
    env = dict(os.environ)
    if authenticated:
        token = env.pop("GH_TOKEN", "")
        if not token:
            raise RuntimeError("GH_TOKEN absent; cannot verify private PR refs")
        env.update(
            {
                "GIT_CONFIG_COUNT": "1",
                "GIT_CONFIG_KEY_0": "http.https://github.com/.extraheader",
                "GIT_CONFIG_VALUE_0": f"AUTHORIZATION: bearer {token}",
            }
        )
    else:
        env.pop("GH_TOKEN", None)
    proc = subprocess.run(
        ["git", *args], env=env, text=True, capture_output=True, timeout=90, check=False
    )
    if proc.returncode:
        # Never include environment/token in an exception.
        raise RuntimeError(
            f"git {args[0]} failed ({proc.returncode}): {proc.stderr[:200]}"
        )
    return proc.stdout.strip()


def materialize(changes: list[Change]) -> dict:
    if git("status", "--porcelain"):
        raise RuntimeError("worktree must be clean before source materialization")
    # This is a read-only build worktree; any GitHub token is used only for
    # verified fetches and removed from child environments for test execution.
    base = git("rev-parse", "HEAD")
    if not SHA.fullmatch(base):
        raise RuntimeError("checkout has no trusted full HEAD")
    applied = []
    for change in changes:
        ref = f"refs/remotes/origin/sq-verified-{change.number}"
        git(
            "fetch",
            "--no-tags",
            "origin",
            f"+refs/pull/{change.number}/head:{ref}",
            authenticated=True,
        )
        got = git("rev-parse", ref)
        if got != change.sha:
            raise RuntimeError(
                f"PR #{change.number} moved: expected {change.sha}, got {got}"
            )
        git("merge", "--squash", "--no-commit", got)
        if not git("diff", "--cached", "--name-only"):
            raise RuntimeError(f"PR #{change.number} contributed no staged diff")
        git(
            "-c",
            "user.name=submitqueue-verifier",
            "-c",
            "user.email=submitqueue-verifier@users.noreply.github.com",
            "commit",
            "-m",
            f"sq-verify PR #{change.number} ({got[:12]})",
        )
        applied.append({"pr": change.number, "head": got})
    return {
        "base_sha": base,
        "candidate_sha": git("rev-parse", "HEAD"),
        "applied": applied,
        "materialization": "speculative-not-release-certification",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--bases", required=True)
    parser.add_argument("--heads", required=True)
    parser.add_argument("--plan", action="store_true")
    args = parser.parse_args()
    if args.repo != os.environ.get("GITHUB_REPOSITORY", args.repo):
        parser.error("repository mismatch")
    try:
        path = parse_path(args.bases, args.heads, args.repo)
        result = (
            {"path": [vars(x) for x in path], "state": "PLAN_ONLY"}
            if args.plan
            else materialize(path)
        )
        print(json.dumps(result, sort_keys=True))
        return 0
    except (ValueError, RuntimeError, json.JSONDecodeError) as e:
        print(json.dumps({"state": "REFUSED", "cause": str(e)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
