"""The Greenlane's GitHub backend: git in the checkout, `gh api` for the rest, the estate App's
installation token for both (a push made with it starts workflows; GITHUB_TOKEN's does not).

Where things live on GitHub:
  refs/heads/lane/<name>, refs/heads/flux/image-updates   the lanes agents and the controller push
  refs/heads/queue/<batch>                                  one candidate under test at a time
  refs/greenlane/state                                      the engine's State, one JSON file
  commit status `greenlane` on each lane head                the verdict the lane's agent reads

Every write here is idempotent, because a tick can be re-run at any moment: a second push of
the same sha is a no-op, a second PR for the same head branch is found and reused, and a
second fast-forward of main to the same sha is a no-op.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Optional

from .engine import CONFLICT, LANDED, RED, TESTING

BOT_LANE = "flux/image-updates"
STATE_REF = "refs/greenlane/state"
MARKER = "Greenlane-Batch:"
GREEN_CONCLUSIONS = {"success", "skipped", "neutral"}
RED_CONCLUSIONS = {
    "failure",
    "cancelled",
    "timed_out",
    "action_required",
    "startup_failure",
    "stale",
}


def _run(*args: str, check: bool = True, input: Optional[str] = None) -> str:
    p = subprocess.run(args, capture_output=True, text=True, input=input)
    if check and p.returncode != 0:
        raise RuntimeError(
            f"{' '.join(args[:3])}: rc={p.returncode} {p.stderr.strip()[:400]}"
        )
    return p.stdout.strip()


class GitHubBackend:
    def __init__(
        self,
        repo: str,
        required: list[str],
        app_login: str = "estate-agents[bot]",
        run_url: str = "",
        image_only_diff: Optional[Path] = None,
    ):
        self.repo, self.required, self.app_login, self.run_url = (
            repo,
            required,
            app_login,
            run_url,
        )
        self.image_only_diff = image_only_diff
        self.owner = repo.split("/")[0]
        self.refused: dict[str, str] = {}  # lane -> why it is not a lane this tick

    # -- plumbing ----------------------------------------------------------------------------
    def git(self, *args: str, check: bool = True) -> str:
        return _run("git", *args, check=check)

    def gh(self, path: str, method: str = "GET", fields: Optional[dict] = None):
        cmd = ["gh", "api", f"repos/{self.repo}/{path}", "-X", method]
        if fields:
            out = _run(*cmd, "--input", "-", input=json.dumps(fields))
        else:
            out = _run(*cmd)
        return json.loads(out) if out else None

    def fetch(self) -> None:
        self.git(
            "fetch", "-q", "--prune", "origin", "+refs/heads/*:refs/remotes/origin/*"
        )
        self.git("fetch", "-q", "origin", f"+{STATE_REF}:{STATE_REF}", check=False)

    # -- state ---------------------------------------------------------------------------------
    def load_state_text(self) -> str:
        return self.git("show", f"{STATE_REF}:state.json", check=False)

    def save_state_text(self, text: str) -> None:
        blob = _run("git", "hash-object", "-w", "--stdin", input=text)
        tree = _run("git", "mktree", input=f"100644 blob {blob}\tstate.json\n")
        commit = _run("git", "commit-tree", tree, "-m", "greenlane state")
        self.git("update-ref", STATE_REF, commit)
        self.git("push", "-q", "-f", "origin", f"{commit}:{STATE_REF}")

    # -- Backend protocol ----------------------------------------------------------------------
    def now(self) -> float:
        return time.time() / 60.0

    def main(self) -> str:
        return self.git("rev-parse", "origin/main")

    def lanes(self) -> dict[str, str]:
        out: dict[str, str] = {}
        main = self.main()
        for line in self.git(
            "ls-remote",
            "--heads",
            "origin",
            "refs/heads/lane/*",
            f"refs/heads/{BOT_LANE}",
        ).splitlines():
            sha, ref = line.split()
            name = ref[len("refs/heads/") :]
            if (
                subprocess.run(
                    ["git", "merge-base", "--is-ancestor", sha, main],
                    capture_output=True,
                ).returncode
                == 0
            ):
                # already in main: nothing left to prove; the branch is a leftover, not work
                if name != BOT_LANE:
                    self.git("push", "-q", "origin", f":refs/heads/{name}", check=False)
                continue
            if (
                name == BOT_LANE
                and self.image_only_diff is not None
                and not self._image_only(sha, main)
            ):
                self.refused[name] = (
                    "not a plain image bump: bin/idp-image-only-diff refused it"
                )
                self.report(name, sha, RED, self.refused[name])
                continue
            out[name] = sha
        return out

    def _image_only(self, sha: str, main: str) -> bool:
        with tempfile.NamedTemporaryFile("w", suffix=".diff", delete=False) as f:
            f.write(self.git("diff", f"{main}...{sha}"))
        try:
            return (
                subprocess.run([str(self.image_only_diff), "--diff", f.name]).returncode
                == 0
            )
        finally:
            os.unlink(f.name)

    def rebase(self, head: str, onto: str) -> Optional[str]:
        """One squashed commit of the lane's work on top of `onto`, or None when it does not apply."""
        mb = self.git("merge-base", onto, head)
        wt = tempfile.mkdtemp(prefix="greenlane-")
        try:
            self.git("worktree", "add", "-q", "--detach", wt, onto)
            pick = subprocess.run(
                [
                    "git",
                    "-C",
                    wt,
                    "cherry-pick",
                    "--no-commit",
                    "--allow-empty",
                    f"{mb}..{head}",
                ],
                capture_output=True,
                text=True,
            )
            if pick.returncode != 0:
                return None
            if _run("git", "-C", wt, "status", "--porcelain") == "":
                return None  # nothing to land
            subject = self.git("log", "-1", "--format=%s", head)
            author = self.git("log", "-1", "--format=%an <%ae>", head)
            body = self.git("log", "--reverse", "--format=%h %s", f"{mb}..{head}")
            msg = f"{subject}\n\nGreenlane-Head: {head}\n\n{body}\n"
            _run(
                "git",
                "-C",
                wt,
                "commit",
                "-q",
                "--author",
                author,
                "-F",
                "-",
                input=msg,
            )
            return _run("git", "-C", wt, "rev-parse", "HEAD")
        finally:
            subprocess.run(
                ["git", "worktree", "remove", "--force", wt], capture_output=True
            )
            shutil.rmtree(wt, ignore_errors=True)

    def push_candidate(self, batch_id: str, tip: str) -> None:
        self.git("push", "-q", "-f", "origin", f"{tip}:refs/heads/queue/{batch_id}")

    def checks(self, tip: str) -> tuple[str, str]:
        # filter=latest: one run per check name, the newest, so a re-run supersedes its predecessor
        page = self.gh(f"commits/{tip}/check-runs?per_page=100&filter=latest") or {}
        runs = page.get("check_runs", [])
        latest: dict[str, dict] = {}
        for r in runs:
            name = r.get("name", "")
            if name not in latest or (r.get("id") or 0) > (latest[name].get("id") or 0):
                latest[name] = r
        pending, red = [], []
        for ctx in self.required:
            r = latest.get(ctx)
            if r is None or r.get("status") != "completed":
                pending.append(ctx)
            elif r.get("conclusion") in GREEN_CONCLUSIONS:
                continue
            else:
                red.append(f"{ctx} {r.get('conclusion')} {r.get('html_url', '')}")
        if red:
            return "red", "; ".join(red)
        if pending:
            return "pending", "waiting on " + ", ".join(pending)
        return "green", ""

    def land(self, members: list[tuple[str, str, str]], tip: str) -> None:
        for lane, head, rebased in members:
            self.git("push", "-q", "-f", "origin", f"{rebased}:refs/heads/{lane}")
            self._ensure_pr(lane, head, rebased, tip)
        self.git(
            "push", "-q", "origin", f"{tip}:refs/heads/main"
        )  # fast-forward, or refused
        for lane, _, _ in members:
            self.git("push", "-q", "origin", f":refs/heads/{lane}", check=False)

    def _ensure_pr(self, lane: str, head: str, rebased: str, tip: str) -> None:
        existing = (
            self.gh(f"pulls?state=open&head={self.owner}:{lane}&per_page=5") or []
        )
        if existing:
            return
        subject = self.git("log", "-1", "--format=%s", rebased)
        body = (
            f"Landed by the Greenlane: this lane was proven green on top of main at exactly this sha "
            f"before this pull request existed, and main fast-forwards to the same tested commit.\n\n"
            f"{MARKER} candidate {tip}\nGreenlane-Head: {head}\nGreenlane-Run: {self.run_url}\n\n"
            f"BDD-PROOF\nhead: {rebased}\nrequired checks green on candidate {tip}: "
            f"{', '.join(self.required)}\nEND-BDD-PROOF\n"
        )
        self.gh(
            "pulls",
            "POST",
            {"title": subject, "head": lane, "base": "main", "body": body},
        )

    def report(self, lane: str, head: str, status: str, reason: str) -> None:
        state = {
            TESTING: "pending",
            LANDED: "success",
            RED: "failure",
            CONFLICT: "failure",
        }.get(status, "pending")
        fields = {
            "state": state,
            "context": "greenlane",
            "description": (reason or status)[:140],
        }
        if self.run_url:
            fields["target_url"] = self.run_url
        try:
            self.gh(f"statuses/{head}", "POST", fields)
        except RuntimeError:
            pass  # a status is a courtesy to the lane's agent; the verdict lives in the state

    def foreign_prs(self) -> list[dict]:
        prs = self.gh("pulls?state=open&per_page=100") or []
        out = []
        for pr in prs:
            if pr.get("user", {}).get("login") == self.app_login and MARKER in (
                pr.get("body") or ""
            ):
                continue
            out.append(
                {
                    "number": pr["number"],
                    "lane": pr["head"]["ref"],
                    "head": pr["head"]["sha"],
                    "user": pr.get("user", {}).get("login"),
                }
            )
        return out

    def relane(self, pr: dict) -> None:
        branch, sha, n = pr["lane"], pr["head"], pr["number"]
        lane = (
            branch
            if branch.startswith("lane/") or branch == BOT_LANE
            else f"lane/{branch}"
        )
        if lane != branch:
            self.git("push", "-q", "origin", f"{sha}:refs/heads/{lane}", check=False)
        self.gh(
            f"issues/{n}/comments",
            "POST",
            {
                "body": (
                    f"Refused by the Greenlane: pull requests are not raised by hand on this repository. "
                    f"Your branch is untouched and is now the lane `{lane}`; the lane proves it on top of "
                    f"main and raises the pull request itself when it is green. Read the verdict with "
                    f"`gh api repos/{self.repo}/commits/{sha}/status` (context `greenlane`)."
                )
            },
        )
        self.gh(f"pulls/{n}", "PATCH", {"state": "closed"})
