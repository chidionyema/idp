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
ADOPTED = "Greenlane-Lane:"  # in a hand-raised PR's body once the engine has adopted it
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
    p = subprocess.run(args, capture_output=True, text=True, input=input)  # noqa: S603, S607 -- git/gh with fixed argv, no shell
    if check and p.returncode != 0:
        raise RuntimeError(
            f"{' '.join(args[:3])}: rc={p.returncode} {p.stderr.strip()[:400]}"
        )
    return p.stdout.strip()


class GitHubBackend:
    # land(): how long the required re-runs a lane-head push starts may take before the merge.
    # The tick job's timeout-minutes is 15 (.github/workflows/greenlane.yml); these fit inside it.
    LAND_SETTLE_S = (
        20  # for GitHub to register the re-runs, so checks() does not read the old ones
    )
    LAND_WAIT_S = 600
    LAND_POLL_S = 15
    LAND_MERGE_TRIES = 4
    LAND_RETRY_S = 20

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
        # A failed state fetch used to be swallowed (check=False), which left refs/greenlane/state
        # at whatever the checkout already had. load_state_text() then read a *stale* ref and
        # returned it as current: on 2026-10-03 that made a landed batch look like it had never
        # been saved, and sent a diagnosis chasing a save_state_text() bug that did not exist.
        #
        # Only one failure is benign: the ref does not exist yet, which is the engine's very
        # first tick. Every other failure (unreachable origin, corrupt remote) must be fatal --
        # a state ref that cannot be refreshed is not a state ref, and must never be reported as
        # current. So the absence is probed for explicitly rather than inferred from an empty
        # stdout, which is also what a failed fetch returns.
        if not self._remote_state():
            # Origin has no state ref. That is the engine's first tick -- but it is only a fresh
            # start if the local checkout agrees. A checkout that carries a local ref origin does
            # not have (a re-pointed remote, a rolled-back state ref) would otherwise keep serving
            # that ref as current, which is the same stale-read defect one layer down. Drop it.
            self.git("update-ref", "-d", STATE_REF, check=False)
            return
        self.git("fetch", "-q", "origin", f"+{STATE_REF}:{STATE_REF}")

    # -- state ---------------------------------------------------------------------------------
    def _remote_state(self) -> str:
        """The sha origin has at refs/greenlane/state, or "" when the ref does not exist yet.

        ls-remote with check=False cannot tell "the remote ref is absent" from "origin is not
        there". Distinguish them by exit status: a reached remote with no matching ref exits 0
        and prints nothing, while an unreachable/failing remote exits non-zero. Conflating the
        two is the whole defect this method guards, on a smaller scale.
        """
        p = subprocess.run(  # noqa: S603, S607 -- git with fixed argv, no shell
            ["git", "ls-remote", "--refs", "origin", STATE_REF],
            capture_output=True,
            text=True,
        )
        if p.returncode != 0:
            raise RuntimeError(
                f"git ls-remote {STATE_REF}: rc={p.returncode} {p.stderr.strip()[:400]}"
            )
        return p.stdout.split()[0] if p.stdout.strip() else ""

    def load_state_text(self) -> str:
        # No state ref at all is a real, expected case (the very first tick): the engine starts
        # from State(). Anything else -- a missing state.json inside an existing ref -- is
        # corruption, and returning "" would silently start the engine from scratch on top of a
        # live trunk. Distinguish the two.
        if not self.git("rev-parse", "--verify", "-q", STATE_REF, check=False):
            return ""
        text = self.git("show", f"{STATE_REF}:state.json", check=False)
        if not text:
            raise RuntimeError(f"{STATE_REF} exists but carries no state.json")
        return text

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
        # An adopted pull request keeps moving: the agent pushes fixes to its branch, and the
        # lane ref follows the PR head, so a red verdict is answered by a push, not a new PR.
        for pr in self.adopted_prs():
            lane, head = pr["lane"], pr["head"]
            if self._ref(lane) != head:
                self.git(
                    "push",
                    "-q",
                    "-f",
                    "origin",
                    f"{head}:refs/heads/{lane}",
                    check=False,
                )
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
                subprocess.run(  # noqa: S603 -- fixed argv, no shell
                    ["git", "merge-base", "--is-ancestor", sha, main],  # noqa: S607
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
                subprocess.run([str(self.image_only_diff), "--diff", f.name]).returncode  # noqa: S603, S607 -- git/gh with fixed argv, no shell
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
            # Apply only the lane's commits that are NOT already on `onto`.
            #
            # The lane rewrites shas on every landing, so a lane that has been landed once
            # keeps its old commits AND gains no new ones -- and `merge-base..head` then
            # re-applies work that is already on main. Re-applying an already-landed commit
            # that ADDS a file conflicts (add/add), `cherry-pick` exits non-zero, this returns
            # None, and the lane is reported CONFLICT forever. Measured 2026-10-04: 14 of 25
            # lanes were stuck this way and `candidate=none` on every tick, so nothing could
            # land at all -- including the fix for the condition. A lane whose only commits are
            # already upstream must instead report "nothing to land" (the `return None` below),
            # which is true, rather than "does not rebase", which is a lie about a clean branch.
            #
            # `git cherry` is the right oracle: it compares patch-ids, so an already-upstream
            # commit is excluded even though its sha differs, and a commit that genuinely is new
            # is kept. `-` lines are applied upstream, `+` lines are not.
            new = [
                line.split()[1]
                for line in self.git("cherry", onto, head, mb).splitlines()
                if line.startswith("+")
            ]
            if not new:
                return None  # nothing to land
            pick = subprocess.run(  # noqa: S603 -- fixed argv, no shell
                [  # noqa: S607
                    "git",
                    "-C",
                    wt,
                    "cherry-pick",
                    "--no-commit",
                    "--allow-empty",
                    *new,
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
            body = self.git("--no-pager", "log", "--reverse", "--format=%h %s", *new)
            # Carry the lane head's trailers onto the candidate. bin/idp-ci-guarded-paths refuses a
            # candidate whose HEAD carries no X-Idp-Signed trailer, and that trailer is put there
            # by .githooks/commit-msg -- which never runs here, because this commit is made by the
            # engine. Dropping it made every lane authored by anything other than the founder or
            # the estate bot fail guarded-paths on a signature the lane had actually earned: the
            # lane's own hook stamped X-Idp-Signed, and the squash threw it away. %(trailers) is
            # git's own trailer block, so a commit with none contributes nothing and the message
            # is unchanged for it.
            trailers = self.git("log", "-1", "--format=%(trailers)", head).strip()
            msg = f"{subject}\n\nGreenlane-Head: {head}\n\n{body}\n"
            if trailers:
                msg = f"{msg}\n{trailers}\n"
            # Build the candidate WITHOUT the repository's project hooks.
            #
            # This commit is made in a throwaway worktree, on the engine's behalf, to produce a
            # candidate the lane then tests in CI. The .githooks/pre-commit revision runs
            # `tsc --noEmit` over the whole backstage project and ruff over the staged tree --
            # and in the temp worktree there is no backstage/node_modules, so tsc reports BLIND
            # and the hook exits non-zero. That turned EVERY lane into `does not rebase`:
            # rebase() raised on the commit, so no candidate was ever built. Measured 2026-10-04
            # against main 1b5fe300c03a: 14 of 25 lanes conflict, candidate=none on every tick.
            #
            # The trailer `commit-msg` would add is not lost: the lane head was authored under
            # the same hooks and already carries X-Idp-Signed, and the `%(trailers)` read above
            # copies it onto this commit. guarded-paths therefore still sees a signed candidate --
            # the signature is carried, not manufactured here. What is skipped is the project-wide
            # tsc/ruff probe, which is the candidate's OWN CI job (guarded-paths, fast-gate) and
            # must not also run, blind, in the engine.
            _run(  # noqa: S603, S607 -- git/gh with fixed argv, no shell
                "git",
                "-C",
                wt,
                "-c",
                "core.hooksPath=/dev/null",
                "commit",
                "-q",
                "--no-verify",
                "--author",
                author,
                "-F",
                "-",
                input=msg,
            )
            return _run("git", "-C", wt, "rev-parse", "HEAD")
        finally:
            subprocess.run(  # noqa: S603 -- fixed argv, no shell
                ["git", "worktree", "remove", "--force", wt],  # noqa: S607
                capture_output=True,
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

    def main_red(self, sha: str) -> bool:
        return self.checks(sha)[0] == "red"

    def land(self, members: list[tuple[str, str, str]], tip: str) -> None:
        adopted = {pr["lane"]: pr for pr in self.adopted_prs()}
        resolved: list[tuple[str, str, str, dict]] = []
        for lane, head, rebased in members:
            self.git("push", "-q", "-f", "origin", f"{rebased}:refs/heads/{lane}")
            pr = adopted.get(lane)
            if pr and pr["branch"] != lane:
                # the PR's own branch takes the landed sha, so GitHub marks the PR merged
                # when main fast-forwards over it; the branch's old commits stay reachable
                # through the Greenlane-Head trailer on the squash
                self.git(
                    "push",
                    "-q",
                    "-f",
                    "origin",
                    f"{rebased}:refs/heads/{pr['branch']}",
                    check=False,
                )
            if not pr:
                number = self._ensure_pr(lane, head, rebased, tip)
                pr = {"number": number, "branch": lane} if number else None
            resolved.append((lane, head, rebased, pr))
        # MAIN MOVES THROUGH THE PULL REQUEST, NOT BY A DIRECT PUSH (2026-10-06).
        #
        # This used to be `git push tip:refs/heads/main`. On 2026-10-06 that was refused:
        #
        #   remote: error: GH013: Repository rule violations found for refs/heads/main.
        #   remote: - Required status check "no-harness-folders" is expected.
        #
        # and every batch failed at exactly this line, so nothing landed. The ruleset on main
        # requires EIGHT status checks and carries a `pull_request` rule. Measured on main HEAD
        # 2c3b3c63a, seven of the eight are absent (only `test` is present) -- because each of
        # those workflows runs on `push`/`pull_request` against the BRANCH being pushed, and a
        # direct push to main arrives before any of them has run against `main`. The requirement
        # is therefore not late, it is unsatisfiable: the retry loop below was written for a lag
        # of ~30 s and no amount of waiting can conjure a check-run that has never been created.
        #
        # A lane that is green is not the same fact as a commit whose required checks have passed
        # on the protected ref, and only the second one may move main (I1). The merge API is the
        # door that satisfies both: it lands the SAME tested sha, and it is how #5445 and #5440
        # reached main today (mergedBy=app/estate-agents). The PR is already opened above -- this
        # stops ignoring it and uses it.
        #
        # `merge_method: "squash"` IS WHAT THE RULESET PERMITS, MEASURED. `merge` is refused --
        # "Merge commits are not allowed on this repository" -- and `rebase` too, while the API
        # reports allow_squash_merge=true. The live proof is #5445, the last commit to reach main:
        # head 9bd3f068f, base cf35fb207, merge commit 2c3b3c63a, and its head carried
        # bdd, ci-success, executes-gate, fast-gate, feature-request-plan and no-harness-folders,
        # all success. That is the shape this reproduces.
        #
        # WHAT THIS GIVES UP, HONESTLY. I1 says main moves to a sha whose required checks passed
        # at that exact sha; a squash mints a NEW sha, so what is proven is the PR's head and what
        # lands is its squash. The gap is closed the only way the platform allows: the PR head is
        # the rebased tip itself (pushed above), so the merge applies that exact tree onto main,
        # and GitHub's own required-check evaluation is what authorises the move -- the same
        # authority that authorised #5445. `sha` pins the merge to the commit that was judged --
        # the rebased commit just pushed as the lane head, which is what GitHub will squash -- so a
        # lane that moves under us fails the call instead of landing unproven work.
        #
        # THE PUSH ABOVE RESTARTS THE REQUIRED CHECKS (2026-10-07). Force-pushing the rebased sha
        # onto the PR's head branch is a `synchronize`: GitHub queues every required workflow
        # again on that same sha, and until those re-runs finish it answers the merge with
        # HTTP 405 "Pull Request is not mergeable". Merging straight after the push lost that
        # race every time: #5461 went b1893..b1897, every candidate green, every land a 405,
        # every next tick "member changed under test; requeued" because the lane head was now
        # the sha this method had pushed. Measured on b1896 (2b211e835): push at 18:10:04Z,
        # seven required re-runs started 18:10:06Z, all green by 18:11Z, tick already dead.
        # So: wait for the re-runs on the sha being landed, then merge, and retry the 405
        # GitHub keeps returning for a few seconds while it recomputes mergeability.
        time.sleep(self.LAND_SETTLE_S)
        deadline = time.time() + self.LAND_WAIT_S
        for _lane, _head, rebased, _pr in resolved:
            while True:
                verdict, why = self.checks(rebased)
                if verdict == "green":
                    break
                if verdict == "red":
                    raise RuntimeError(
                        f"land: {rebased[:12]} went red after the push: {why}"
                    )
                if time.time() > deadline:
                    raise RuntimeError(
                        f"land: {rebased[:12]} still {why} {self.LAND_WAIT_S}s after the push"
                    )
                time.sleep(self.LAND_POLL_S)
        for lane, _head, rebased, pr in resolved:
            if not pr:
                pr = self._pr_for(lane)
            if not pr:
                raise RuntimeError(
                    f"land: no pull request for {lane}; cannot move main"
                )
            subject = self.git("log", "-1", "--format=%s", rebased)
            for attempt in range(self.LAND_MERGE_TRIES):
                try:
                    self.gh(
                        f"pulls/{pr['number']}/merge",
                        "PUT",
                        {
                            "merge_method": "squash",
                            "sha": rebased,
                            "commit_title": f"{subject} (#{pr['number']})",
                        },
                    )
                    break
                except RuntimeError as e:
                    if "HTTP 405" not in str(e) or attempt == self.LAND_MERGE_TRIES - 1:
                        raise
                    time.sleep(self.LAND_RETRY_S)
        for lane, _, _, _ in resolved:
            self.git("push", "-q", "origin", f":refs/heads/{lane}", check=False)

    def _pr_for(self, lane: str) -> Optional[dict]:
        """The open pull request whose head is `lane`, or None."""
        found = self.gh(f"pulls?state=open&head={self.owner}:{lane}&per_page=5") or []
        return found[0] if found else None

    def _ensure_pr(self, lane: str, head: str, rebased: str, tip: str) -> Optional[int]:
        existing = (
            self.gh(f"pulls?state=open&head={self.owner}:{lane}&per_page=5") or []
        )
        if existing:
            return existing[0]["number"]
        subject = self.git("log", "-1", "--format=%s", rebased)
        body = (
            f"Landed by the Greenlane: this lane was proven green on top of main at exactly this sha "
            f"before this pull request existed, and main fast-forwards to the same tested commit.\n\n"
            f"{MARKER} candidate {tip}\nGreenlane-Head: {head}\nGreenlane-Run: {self.run_url}\n\n"
            f"BDD-PROOF\nhead: {rebased}\nrequired checks green on candidate {tip}: "
            f"{', '.join(self.required)}\nEND-BDD-PROOF\n"
        )
        created = self.gh(
            "pulls",
            "POST",
            {"title": subject, "head": lane, "base": "main", "body": body},
        )
        # The merge that follows needs the number. Re-reading it from the API would work but
        # costs a round trip and races with GitHub's own listing lag; the POST already carries
        # it. `None` still means "no PR" and the caller refuses rather than guessing.
        return (created or {}).get("number")

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

    def adopted_prs(self) -> list[dict]:
        """Open pull requests the engine adopted: (number, branch, lane, head)."""
        out = []
        for pr in self.gh("pulls?state=open&per_page=100") or []:
            body = pr.get("body") or ""
            if ADOPTED not in body:
                continue
            lane = body.split(ADOPTED, 1)[1].split()[0]
            out.append(
                {
                    "number": pr["number"],
                    "branch": pr["head"]["ref"],
                    "lane": lane,
                    "head": pr["head"]["sha"],
                }
            )
        return out

    def _ref(self, name: str) -> str:
        line = self.git(
            "ls-remote", "--heads", "origin", f"refs/heads/{name}", check=False
        )
        return line.split()[0] if line.strip() else ""

    def foreign_prs(self) -> list[dict]:
        prs = self.gh("pulls?state=open&per_page=100") or []
        out = []
        owner = self.repo.split("/")[0]
        for pr in prs:
            body = pr.get("body") or ""
            if pr.get("user", {}).get("login") == self.app_login and MARKER in body:
                continue
            if ADOPTED in body:
                continue  # already a lane; lanes() follows its head
            # The repository owner's own pull request is the founder's landing vehicle for
            # the enforcement paths agents may not touch (workflows, rulesets, this engine:
            # crew#985). It is never closed or relaned; the founder merges it by hand.
            if pr.get("user", {}).get("login") == owner:
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
        """Adopt a hand-raised pull request: its branch becomes the lane, the PR stays open and
        carries the lane's verdict, and it is marked merged when the lane lands. Nothing is
        closed and nobody has to chase it (founder 2026-09-29: "I don't just discard stuff")."""
        branch, sha, n = pr["lane"], pr["head"], pr["number"]
        lane = (
            branch
            if branch.startswith("lane/") or branch == BOT_LANE
            else f"lane/{branch}"
        )
        if lane != branch:
            self.git(
                "push", "-q", "-f", "origin", f"{sha}:refs/heads/{lane}", check=False
            )
        body = (self.gh(f"pulls/{n}") or {}).get("body") or ""
        self.gh(
            f"pulls/{n}",
            "PATCH",
            {"body": f"{ADOPTED} {lane}\n\n{body}"},
        )
        self.gh(
            f"issues/{n}/comments",
            "POST",
            {
                "body": (
                    f"Adopted by the Greenlane as lane `{lane}`. This pull request stays open: the lane "
                    f"proves your branch on top of main, and this PR is marked merged the moment it lands. "
                    f"A red or conflicting verdict appears as the `greenlane` status on your head commit "
                    f"with its reason; push the fix to `{branch}` and the lane follows. Nothing here is "
                    f"closed or discarded."
                )
            },
        )
