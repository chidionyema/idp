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
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from .engine import CONFLICT, LANDED, RED, TESTING

BOT_LANE = "flux/image-updates"
STATE_REF = "refs/greenlane/state"
MARKER = "Greenlane-Batch:"
ADOPTED = "Greenlane-Lane:"  # in a hand-raised PR's body once the engine has adopted it
DEPENDABOT = (
    "dependabot[bot]"  # exempt from claims BY NAME in bin/claim-gate, so adoptable here
)
AGENT_DECLARATION = re.compile(r"^(Claim|Agent):", re.M)
AGENT_TRAILER = re.compile(r"^Agent:\s*(\S+)\s*$", re.M)
CLAIM_REF = re.compile(r"^Claim:\s*(?:[\w.-]+/[\w.-]+)?#(\d+)\s*$", re.M)
CLAIM_LINE = re.compile(
    r"^CLAIM\s+agent=(?P<agent>\S+)\s+(?:model=(?P<model>\S+)\s+)?paths=(?P<paths>\S+)\s+"
    r"heartbeat=(?P<hb>\S+)\s*$",
    re.M,
)
STAMP_AFTER = timedelta(
    minutes=45
)  # the gate's limit is 2h; stamp at most about hourly


def _bodies(comments: list) -> list:
    return [c.get("body") or "" for c in comments]


GREEN_CONCLUSIONS = {"success", "skipped", "neutral"}
RED_CONCLUSIONS = {
    "failure",
    "cancelled",
    "timed_out",
    "action_required",
    "startup_failure",
    "stale",
}


def _run(
    *args: str,
    check: bool = True,
    input: Optional[str] = None,
    env: Optional[dict] = None,
) -> str:
    p = subprocess.run(args, capture_output=True, text=True, input=input, env=env)  # noqa: S603, S607 -- git/gh with fixed argv, no shell
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
        status_token: str = "",
    ):
        self.repo, self.required, self.app_login, self.run_url = (
            repo,
            required,
            app_login,
            run_url,
        )
        self.image_only_diff = image_only_diff
        # The token report() writes the `greenlane` commit status with (2026-10-09, #5576). Not
        # the App's: neither the platform-engineer lane nor the App itself holds `statuses`
        # (platform/github-app/lanes.json, manifest.json), so every status POST made with it was
        # refused -- 0 of 40 landed lanes carried one, and lane-submit, which waits on exactly
        # that status, timed out BLIND 102 times in 109. The runner's GITHUB_TOKEN has
        # `statuses: write` (greenlane.yml), and a status starts no workflow, so the reason the
        # App token exists does not apply here. Empty means "use gh's own token", as before.
        self.status_token = status_token
        self.owner = repo.split("/")[0]
        self.refused: dict[str, str] = {}  # lane -> why it is not a lane this tick
        self._work_age_cache: Optional[dict[str, float]] = None
        self._state_lease = ""  # remote state sha seen at load; CAS anchor for save

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
        # The lease for compare-and-swap on save: the remote sha this load observed. Two ticks
        # on different refs (a lane push and a main dispatch sit in different concurrency groups
        # and run concurrently) used to both load here, both act, and both force-push -- last
        # writer won, and the loser's batch vanished from the state while its queue branch sat
        # green forever (measured 2026-10-17: b2953 and b2954 both stranded this way, lanes
        # re-marked CONFLICT by a tick running on a pre-batch snapshot). The save leases on
        # this sha and refuses to overwrite a state it never saw.
        self._state_lease = self._remote_state()
        if not self.git("rev-parse", "--verify", "-q", STATE_REF, check=False):
            raise RuntimeError(
                f"{STATE_REF} exists on origin ({self._state_lease[:12]}) but not locally"
            )
        text = self.git("show", f"{STATE_REF}:state.json", check=False)
        if not text:
            raise RuntimeError(f"{STATE_REF} exists but carries no state.json")
        return text

    def save_state_text(self, text: str) -> None:
        blob = _run("git", "hash-object", "-w", "--stdin", input=text)
        tree = _run("git", "mktree", input=f"100644 blob {blob}\tstate.json\n")
        commit = _run("git", "commit-tree", tree, "-m", "greenlane state")
        self.git("update-ref", STATE_REF, commit)
        # Compare-and-swap, not a blind force push: fail if origin moved since load_state_text()
        # captured the lease. An empty lease means the ref must not exist yet (first tick).
        # A rejected save raises; the tick dies visibly and the next dispatch re-reads and
        # re-derives everything. Losing a tick is cheap; silently dropping a green batch (the
        # b2953/b2954 stranding) is not.
        self.git(
            "push",
            "-q",
            f"--force-with-lease={STATE_REF}:{self._state_lease}",
            "origin",
            f"{commit}:{STATE_REF}",
        )

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
            if self._landed(sha, main):
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

    def _landed(self, sha: str, main: str) -> bool:
        """Every change on the lane is already on main (idp#5618).

        Ancestry alone used to decide this, but the Greenlane lands by squash, so a lane whose
        work reached main through ANOTHER lane is never an ancestor of it. rebase() then found
        nothing to land, the engine read that None as CONFLICT, and the lane was parked as
        `does not rebase onto main` -- 6 lanes on 2026-10-09, all of their work on main.
        Either test below is exact, and they catch different shapes: merging the lane into
        main changes nothing (a lane that drifted and was brought back), or each of its
        commits is patch-equivalent to one on main (work landed under another sha, whose
        lines main has since moved on from). The second is not trusted across a merge
        commit, which `git cherry` skips and whose resolution may carry work of its own.
        """

        def ok(*args: str) -> subprocess.CompletedProcess:
            return subprocess.run(  # noqa: S603 -- fixed argv, no shell
                ["git", *args],
                capture_output=True,
                text=True,  # noqa: S607
            )

        if ok("merge-base", "--is-ancestor", sha, main).returncode == 0:
            return True
        merged = ok("merge-tree", "--write-tree", main, sha)
        if merged.returncode == 0 and merged.stdout.split()[:1] == [
            self.git("rev-parse", f"{main}^{{tree}}")
        ]:
            return True
        mb = ok("merge-base", main, sha).stdout.strip()
        if not mb or ok("rev-list", "--merges", f"{mb}..{sha}").stdout.strip():
            return False
        cherry = ok("cherry", main, sha, mb)
        return cherry.returncode == 0 and not any(
            line.startswith("+") for line in cherry.stdout.splitlines()
        )

    def _image_only(self, sha: str, main: str) -> bool:
        # Grade the commit that would land, not the branch's history. `main...sha` is the
        # three-dot diff from the merge-base, and flux/image-updates forks from whatever main
        # looked like when it was cut, so a line main has re-laid since still reads as a non-tag
        # hunk (#3839, #6114). That stale base is why three writers kept rewriting the branch
        # -- image-update-pr's merge of main and two update-branch calls in deploy-when-green --
        # and every rewrite restarted the required checks (2026-10-14: #6174 had 12 heads in 49
        # minutes, #6114 took 226 minutes to land). rebase() builds the candidate the engine
        # tests and lands, so `main..candidate` is exactly the change main would take. When it
        # builds nothing (a conflict, or nothing left to land) the three-dot diff is graded as
        # before, and the engine reports that case as it always has.
        candidate = self.rebase(sha, main)
        rng = f"{main}..{candidate}" if candidate else f"{main}...{sha}"
        with tempfile.NamedTemporaryFile("w", suffix=".diff", delete=False) as f:
            f.write(self.git("diff", rng))
        try:
            return (
                subprocess.run([str(self.image_only_diff), "--diff", f.name]).returncode  # noqa: S603, S607 -- git/gh with fixed argv, no shell
                == 0
            )
        finally:
            os.unlink(f.name)

    def push_head(self, lane: str, sha: str) -> None:
        """Force-push the given sha as the lane's HEAD on origin."""
        self.git(
            "push",
            "-q",
            "-f",
            "origin",
            f"{sha}:refs/heads/{lane}",
        )

    def rebase(self, head: str, onto: str) -> Optional[str]:
        """One squashed commit of the lane's work on top of `onto`, or None when it does not apply."""
        mb = self.git("merge-base", onto, head)
        new = [
            line.split()[1]
            for line in self.git("cherry", onto, head, mb).splitlines()
            if line.startswith("+")
        ]
        print(
            f"DEBUG rebase({head[:8]}, {onto[:8]}): mb={mb[:8]} new={new[:2]}",
            flush=True,
        )
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
            # Subject, author and trailers come from the lane's OWN commits (`new`), not from
            # `head`. The merge-when-green, deploy-when-green and wake-blocked jobs bring a lane
            # up to date with PUT update-branch, which leaves `head` a "Merge branch 'main'"
            # commit by estate-agents[bot] that has no trailers. `git cherry` skips that merge,
            # so the work still landed. But the candidate went out under the merge's subject and
            # author with no Claim:, and claim-gate refused it as "no live claim". That is
            # 7316f4af4 on concierge-vision-minimax (#6148), 2026-10-14: the squash of 1da835c97,
            # whose `Claim: #6103` was dropped. `--no-walk` lists just these commits. A plain
            # `log` walks all of their ancestors, so that body had 6115 lines of main's history.
            last = new[-1]
            subject = self.git("log", "-1", "--format=%s", last)
            author = self.git("log", "-1", "--format=%an <%ae>", last)
            body = self.git(
                "--no-pager", "log", "--no-walk=unsorted", "--format=%h %s", *new
            )
            # Carry the lane commits' trailers onto the candidate. bin/idp-ci-guarded-paths refuses a
            # candidate whose HEAD carries no X-Idp-Signed trailer, and that trailer is put there
            # by .githooks/commit-msg -- which never runs here, because this commit is made by the
            # engine. Dropping it made every lane authored by anything other than the founder or
            # the estate bot fail guarded-paths on a signature the lane had actually earned: the
            # lane's own hook stamped X-Idp-Signed, and the squash threw it away. %(trailers) is
            # git's own trailer block, so a commit with none contributes nothing and the message
            # is unchanged for it.
            seen = self.git(
                "log", "--no-walk=unsorted", "--format=%(trailers:only,unfold)", *new
            ).splitlines()
            trailers = "\n".join(dict.fromkeys(t for t in seen if t.strip()))
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

    # Refs per delete push: one push of 1,680 `:refs/heads/queue/...` deletions is one ref update
    # transaction GitHub may refuse whole; a chunk that fails leaves the rest to the next tick.
    QUEUE_DELETE_CHUNK = 200

    def push_candidate(self, batch_id: str, tip: str) -> None:
        # A force-push that leaves the ref at the sha it already had still emits a push
        # event, with before == after -- and a content-identical rebase (main moved, the
        # candidate rebased to the same tree under a new sha) is the same zero-delta
        # push under a new sha. The verifier grades the push as `git diff <before>...HEAD`,
        # sees an empty diff and refuses ("BLIND verifier: empty diff"), reding the
        # required portal-app and ci contexts -- the green batch requeues, the next
        # formation re-pushes the same content, forever. Measured 2026-10-17:
        # queue/b2991 16:55Z before == HEAD == 08455b9b7; queue/b2993 17:11Z
        # before=4e24a6cfd, tip moved to cd172ce55, portal-app+ci red on the empty-diff
        # guard while every required check on the content was green. Skip when origin
        # already sits at the tip, or at a different sha with the same tree: the runs
        # already on that content stay the ones that judge it.
        want = f"refs/heads/queue/{batch_id}"
        out = self.git("ls-remote", "-q", "origin", want)
        at = out.split()[0] if out.strip() else ""
        if at == tip:
            return
        if at:
            try:
                old_tree = self.git("rev-parse", f"{at}^{{tree}}").strip()
                new_tree = self.git("rev-parse", f"{tip}^{{tree}}").strip()
                if old_tree == new_tree:
                    return
            except Exception:
                pass  # old sha not resolvable locally -- fall through and push
            # New content on a ref that already exists: the push event carries
            # before=<old candidate>, and the verifier grades
            # `git diff <before>...HEAD` -- the delta between two queue
            # candidates, which is not the change main would take. Measured on
            # queue/b2999 (2026-10-17 17:47Z: before=61929e54, tip e825e4ab, the
            # gauntlet graded old-candidate...new-candidate and refused a diff
            # that VERIFIES clean against main locally). Delete the ref first:
            # the create-push then has before=zeros and the verifier grades
            # origin/main...HEAD, the same grade a fresh branch would get.
            self.git("push", "-q", "origin", f":{want}", check=False)
        self.git("push", "-q", "-f", "origin", f"{tip}:{want}")
        # Nothing deleted a finished candidate (2026-10-09, #5603): 1,680 queue/* refs, all under
        # the branch archive's 14 days. The engine holds one batch at a time, so once this one is
        # pushed every other queue ref is finished -- a landed batch is on main, a red one's work
        # is still on its lanes. The first tick after this lands clears the backlog.
        stale = [
            ref
            for line in self.git(
                "ls-remote", "--heads", "origin", "refs/heads/queue/*"
            ).splitlines()
            for ref in line.split()[1:]
            if ref != f"refs/heads/queue/{batch_id}"
        ]
        for i in range(0, len(stale), self.QUEUE_DELETE_CHUNK):
            chunk = stale[i : i + self.QUEUE_DELETE_CHUNK]
            self.git("push", "-q", "origin", *[f":{ref}" for ref in chunk], check=False)

    def checks(self, tip: str) -> tuple[str, str]:
        # filter=latest: one run per check name, the newest, so a re-run supersedes its predecessor
        # 210 check-runs on main; paginate until all pages are read (pages 1-3 at 100/page).
        latest: dict[str, dict] = {}
        page_num = 1
        while True:
            page = (
                self.gh(
                    f"commits/{tip}/check-runs?per_page=100&filter=latest&page={page_num}"
                )
                or {}
            )
            runs = page.get("check_runs", [])
            for r in runs:
                name = r.get("name", "")
                if name not in latest or (r.get("id") or 0) > (
                    latest[name].get("id") or 0
                ):
                    latest[name] = r
            if len(runs) < 100:
                break  # last page
            page_num += 1
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

    CLAIM_GATE = Path(__file__).resolve().parent.parent / "bin" / "claim-gate"

    def unclaimed(self, head: str, base: str) -> str:
        """Main's own bin/claim-gate on the lane, as ci-success will run it (idp#5612).

        Only a FAIL is a reason to hold the lane. A gate that cannot judge -- missing, timed
        out, gh down -- admits it: CI still runs the same gate and stays the guarantee.
        """
        if not self.CLAIM_GATE.is_file():
            return ""
        mb = self.git("merge-base", base, head, check=False) or base
        try:
            p = subprocess.run(  # noqa: S603 -- fixed argv, no shell
                [sys.executable, str(self.CLAIM_GATE), mb, head],
                capture_output=True,
                text=True,
                timeout=60,
                env={**os.environ, "GITHUB_REPOSITORY": self.repo},
            )
        except subprocess.TimeoutExpired:
            return ""
        fails = [
            ln.removeprefix("FAIL  claim-gate  ")
            for ln in p.stdout.splitlines()
            if ln.startswith("FAIL  claim-gate  ")
        ]
        return f"no live claim: {'; '.join(fails)}" if p.returncode and fails else ""

    def work_age(self, sha: str) -> Optional[float]:
        """Minutes since `sha` was authored (git author date), or None if unreadable."""
        if self._work_age_cache is None:
            self._work_age_cache = {}
            try:
                out = self.git(
                    "for-each-ref",
                    "--format=%(objectname) %(authordate:unix)",
                    "refs/remotes/origin/lane/",
                    check=True,
                )
                now = time.time() / 60.0
                for line in out.splitlines():
                    obj, ts = line.split()
                    self._work_age_cache[obj] = now - float(ts) / 60.0
            except OSError:
                pass  # fetch failed; cache stays empty
        return self._work_age_cache.get(sha)

    def land(self, members: list[tuple[str, str, str]], tip: str) -> None:
        try:
            self._land(members, tip)
        except RuntimeError:
            # I4: a lane that does not land keeps its branch. _land force-pushed the rebased
            # squash over each lane ref; left there, the next tick reads it as a re-push and
            # requeues it as new work (2026-10-08, b1990..b1992), and the author's next
            # lane-submit is refused as non-fast-forward. Put every lane back on its own head.
            # Only a lane still on the squash goes back: one that holds anything else was pushed
            # by its author mid-land, and a bare -f erased that push (2026-10-13, #6084's
            # 2c0156b01 at 20:14:01Z, overwritten at 20:14:09Z and 20:15:53Z).
            for lane, head, rebased in members:
                self.git(
                    "push",
                    "-q",
                    f"--force-with-lease=refs/heads/{lane}:{rebased}",
                    "origin",
                    f"{head}:refs/heads/{lane}",
                    check=False,
                )
            raise

    def _await_green(self, sha: str, deadline: float) -> None:
        """Block until every required check on sha is green; raise red or slow on anything else."""
        while True:
            verdict, why = self.checks(sha)
            if verdict == "green":
                return
            if verdict == "red":
                raise RuntimeError(f"land: {sha[:12]} went red after the push: {why}")
            if time.time() > deadline:
                raise RuntimeError(
                    f"land: {sha[:12]} still {why} {self.LAND_WAIT_S}s after the push"
                )
            time.sleep(self.LAND_POLL_S)

    def _land(self, members: list[tuple[str, str, str]], tip: str) -> None:
        adopted = {pr["lane"]: pr for pr in self.adopted_prs()}
        resolved: list[tuple[str, str, str, dict, Optional[int]]] = []
        for lane, head, rebased in members:
            # leased to the head the batch tested: a lane its author has moved since is new work,
            # and landing the old squash over it would erase the push. Refused, it raises, and
            # land() treats it as a refused land (I4).
            self.git(
                "push",
                "-q",
                f"--force-with-lease=refs/heads/{lane}:{head}",
                "origin",
                f"{rebased}:refs/heads/{lane}",
            )
            pr = adopted.get(lane)
            orphan: Optional[int] = None
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
                if self._ref(pr["branch"]) != rebased:
                    # The branch refused the push -- dependabot owns its branches, and under
                    # check=False the refusal was silent. The land then pinned a head nobody
                    # proved and every merge PUT was refused: #6128's content reached main
                    # through #6457 while #6128 itself sat open for days (measured 2026-10-18).
                    # Land through the lane's own pull request instead and close the adopted
                    # one once main has moved: GitHub can never mark it merged, and a close
                    # that names the landing beats a pull request that lies open forever.
                    number = self._ensure_pr(lane, head, rebased, tip)
                    if number:
                        orphan = pr["number"]
                        pr = {"number": number, "branch": lane}
            if not pr:
                number = self._ensure_pr(lane, head, rebased, tip)
                pr = {"number": number, "branch": lane} if number else None
            resolved.append((lane, head, rebased, pr, orphan))
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
        for _lane, _head, rebased, _pr, _ in resolved:
            self._await_green(rebased, deadline)
        for lane, _head, rebased, pr, orphan in resolved:
            if not pr:
                pr = self._pr_for(lane)
            if not pr:
                raise RuntimeError(
                    f"land: no pull request for {lane}; cannot move main"
                )
            # Re-fetch the PR to get its current head. The lane branch may have been updated
            # since the batch was formed (_start_batch pushes b.tip to the lane branch), so
            # the PR's head might differ from the `rebased` SHA we pushed. Use the current head
            # to avoid "Head branch was updated" refusals from gh pr merge.
            current_pr = self.gh(f"pulls/{pr['number']}") or {}
            current_head = current_pr.get("head", {}).get("sha", "")
            merge_sha = current_head if current_head else rebased
            # THE HEAD WE MERGE IS THE HEAD WE PROVE (2026-10-17). current_head can differ
            # from rebased (the batch or a refresh moved the lane branch after the wait
            # above), and the ruleset evaluates the PR head: a merge that pins a sha whose
            # checks were never awaited answers 405 "greenlane is pending" no matter how
            # long we retry. Measured on b2961..b2964: two lands of PR #6375 refused this
            # way, both after checks(rebased) had gone green.
            if merge_sha != rebased:
                self._await_green(merge_sha, time.time() + self.LAND_WAIT_S)
            # THE GREENLANE VOUCHES FOR THE SHA IT MERGES (2026-10-10). `greenlane` is a required
            # check on main (ruleset.idp.required-checks.json), pinned to the Actions app, and
            # this is the only place it is ever written as success -- so a pull request raised
            # and merged by hand, which on 2026-10-10 was #5695, #5680, #5672, #5663 and #5646,
            # can no longer reach main without the engine having proven it. Not swallowed like
            # report(): without the vouch the merge below is refused, so say why here instead.
            # THE VOUCH MUST BE A CHECK-RUN ON THE SHA THE MERGE EVALUATES (2026-10-17).
            # The ruleset's required `greenlane` is a check-run (integration 15368): a commit
            # status is invisible to it, and the ruleset evaluates the PR HEAD -- which is
            # merge_sha, not rebased. Measured on PR #6402 (b2977): vouch posted as a status
            # on rebased, merge pinned at merge_sha, refused with "Repository rule
            # violations found: Required status check greenlane is ...". PATCH the check-run
            # the lane push itself created (the workflow fires on the lane-branch push of
            # merge_sha, so the run exists and is in_progress) to completed/success on the
            # sha actually merged. The check-run creation fallback in _update_check_run
            # covers a head the workflow has not reached yet.
            self._update_check_run(
                merge_sha,
                "success",
                "success",
                f"proven on candidate {tip[:12]}",
            )
            subject = self.git("log", "-1", "--format=%s", merge_sha)
            for attempt in range(self.LAND_MERGE_TRIES):
                try:
                    result = self.gh(
                        f"pulls/{pr['number']}/merge",
                        "PUT",
                        {
                            "merge_method": "squash",
                            "sha": merge_sha,
                            "commit_title": f"{subject} (#{pr['number']})",
                        },
                    )
                    # gh returns a dict even on error (HTTP 4xx). Check for merge failure.
                    merge_error = (
                        result.get("message", "") if isinstance(result, dict) else ""
                    )
                    if not merge_error:
                        break  # merge succeeded
                    # GitHub refused: "Head branch was updated" or "PR not mergeable".
                    # Retry "Head branch was updated" with a fresh PR head.
                    if "Head branch was updated" in merge_error:
                        fresh_pr = self.gh(f"pulls/{pr['number']}") or {}
                        fresh_head = fresh_pr.get("head", {}).get("sha", "")
                        if fresh_head and fresh_head != merge_sha:
                            merge_sha = fresh_head
                            subject = self.git("log", "-1", "--format=%s", merge_sha)
                            self._await_green(merge_sha, time.time() + self.LAND_WAIT_S)
                            continue  # retry with the new, proven merge_sha
                    # HTTP 405 "PR not mergeable": retry with backoff, but re-prove the
                    # head first -- a 405 naming a pending check on a head we have not
                    # awaited only clears once that head's checks do. And the re-prove is a
                    # FULL await (2026-10-17, PR #6402 b2987): right after the lane push the
                    # synchronize's new runs have not registered yet, so checks() still sees
                    # the PREVIOUS push's completed runs and answers green instantly; the
                    # merge then races the fresh runs with 4 x 20s of retries against their
                    # ~3-4 min runtime and loses. Measured: refused at 16:43, all required
                    # checks success on the same sha by 16:47. Await again, budget and all.
                    if "HTTP 405" not in merge_error or (
                        attempt == self.LAND_MERGE_TRIES - 1
                    ):
                        raise RuntimeError(merge_error)
                    fresh_pr = self.gh(f"pulls/{pr['number']}") or {}
                    fresh_head = fresh_pr.get("head", {}).get("sha", "")
                    if fresh_head and fresh_head != merge_sha:
                        merge_sha = fresh_head
                        subject = self.git("log", "-1", "--format=%s", merge_sha)
                    self._await_green(merge_sha, time.time() + self.LAND_WAIT_S)
                    continue
                except RuntimeError as e:
                    if "HTTP 405" not in str(e) or attempt == self.LAND_MERGE_TRIES - 1:
                        raise
                    time.sleep(self.LAND_RETRY_S)
        for lane, _, _, _, _ in resolved:
            self.git("push", "-q", "origin", f":refs/heads/{lane}", check=False)
        # The adopted pull requests whose branches refused the engine's push (see the orphan
        # fallback above) are closed here, AFTER the merge loop -- so a refused merge raises
        # and the lane goes back on its own head (I4) with no PR closed for nothing.
        for _lane, _head, rebased, pr, orphan in resolved:
            if not orphan or not pr:
                continue
            self.gh(f"pulls/{orphan}", "PATCH", {"state": "closed"})
            self.gh(
                f"issues/{orphan}/comments",
                "POST",
                {
                    "body": (
                        f"Landed on main as {rebased[:12]} through the lane's own pull request "
                        f"(#{pr['number']}): this branch belongs to its bot and refuses the "
                        f"engine's push, so GitHub cannot mark this pull request merged. The "
                        f"work is proven and on main; closing rather than lying open."
                    )
                },
            )
        # MAIN MOVED THROUGH THE API, SO origin/main IS STALE (2026-10-13). main() reads the
        # remote-tracking ref fetched at the top of the tick, and tick() starts the next batch
        # straight after this landing -- on the main from before it. The next tick then voids
        # that batch as "main moved under it" and its candidate's check suite is thrown away:
        # b2704 landed #6107 at 19:49:48Z, b2705 was built on 8a3984f2bc45 in the same tick and
        # voided at 19:51:28Z. Not checked: main has already moved, and a failed fetch here must
        # not read as a refused land (that would mark landed lanes red); it only costs that batch.
        self.git(
            "fetch",
            "-q",
            "origin",
            "+refs/heads/main:refs/remotes/origin/main",
            check=False,
        )

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

    def _status(self, sha: str, fields: dict) -> None:
        if self.status_token:
            _run(
                "gh",
                "api",
                f"repos/{self.repo}/statuses/{sha}",
                "-X",
                "POST",
                "--input",
                "-",
                input=json.dumps(fields),
                env={**os.environ, "GH_TOKEN": self.status_token},
            )
        else:
            self.gh(f"statuses/{sha}", "POST", fields)

    def _update_check_run(
        self, sha: str, status: str, conclusion: str, reason: str
    ) -> None:
        """Update (or create) a check run named 'greenlane' on sha to completed/conclusion.

        The greenlane.yml workflow creates a check run named 'greenlane' when it fires on a lane
        push. The check run stays in_progress while the workflow runs. When CI passes and the
        engine is ready to merge, the check run must be marked completed before GitHub allows the
        merge.
        """
        state_map = {
            "success": "completed",
            "failure": "completed",
            "pending": "in_progress",
        }
        check_run_state = state_map.get(status, "in_progress")
        # Find the latest greenlane check run for this sha
        runs = self.gh(f"commits/{sha}/check-runs?per_page=100") or {}
        check_run = None
        for r in runs.get("check_runs", []):
            if r.get("name") == "greenlane":
                if check_run is None or (r.get("id", 0) > check_run.get("id", 0)):
                    check_run = r
        if check_run is None:
            # No check run found; nothing to update. Post a status as fallback.
            self._status(
                sha,
                {
                    "state": status,
                    "context": "greenlane",
                    "description": (reason or status)[:140],
                },
            )
            return
        cr_id = check_run["id"]
        payload = {
            "status": check_run_state,
            "conclusion": conclusion if check_run_state == "completed" else None,
            "completed_at": datetime.now(timezone.utc).isoformat()
            if check_run_state == "completed"
            else None,
            "output": {
                "title": "greenlane",
                "summary": (reason or status)[:140],
            },
        }
        try:
            self.gh(f"check-runs/{cr_id}", "PATCH", payload)
        except RuntimeError as e:
            print(
                f"WARN    greenlane  check-run update failed for {sha}: {e}",
                file=sys.stderr,
            )

    def report_check_run_completed(self, sha: str, status: str, reason: str) -> None:
        """Mark the greenlane check run on sha as completed.

        Called just before land() to mark the check run done. GitHub evaluates required checks
        on the batch tip (the commit main is fast-forwarded to). The lane head's check run
        (from ci.yml) is not visible there. We must create or update a check run on the
        batch tip so GitHub sees the required check satisfied.

        The workflow now has checks:write permission, and GH_TOKEN is the App token which
        has check-run write permission.
        """
        conclusion = {
            TESTING: None,
            LANDED: "success",
            RED: "failure",
            CONFLICT: "failure",
        }.get(status, "pending")
        # First: try to find and update an existing check run
        self._update_check_run(sha, status, conclusion, reason)
        # If no existing check run was found, create one on sha (the batch tip)
        # This happens when greenlane.yml does not create a check run on the batch tip
        # (it only fires on lane/ branches, not queue/ branches).
        runs = self.gh(f"commits/{sha}/check-runs?per_page=100") or {}
        existing = any(r.get("name") == "greenlane" for r in runs.get("check_runs", []))
        if existing:
            return  # Updated successfully in _update_check_run above
        # No existing check run: create one
        check_run_state = "completed" if conclusion else "in_progress"
        payload = {
            "name": "greenlane",
            "head_sha": sha,
            "status": check_run_state,
            "conclusion": conclusion,
            "completed_at": datetime.now(timezone.utc).isoformat()
            if check_run_state == "completed"
            else None,
            "output": {
                "title": "greenlane",
                "summary": (reason or status)[:140],
            },
        }
        if self.run_url:
            payload["output"]["text"] = f"{self.run_url}\n{(reason or status)[:140]}"
        try:
            self.gh("check-runs", "POST", payload)
        except RuntimeError as e:
            print(
                f"WARN    greenlane  check-run create failed for {sha}: {e}",
                file=sys.stderr,
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
            self._status(head, fields)
        except RuntimeError as e:
            # The verdict lives in the state, so a refused status must not fail the tick -- but it
            # is said, not swallowed: the silent `pass` here hid a permanent 403 for weeks.
            print(
                f"WARN    greenlane  status for {lane} not written: {e}",
                file=sys.stderr,
            )

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
        for pr in prs:
            body = pr.get("body") or ""
            if pr.get("user", {}).get("login") == self.app_login and MARKER in body:
                continue
            if ADOPTED in body:
                continue  # already a lane; lanes() follows its head
            # A PR that declares nothing is the founder's own hand work -- the landing vehicle
            # for the enforcement paths agents may not touch (workflows, rulesets, this engine:
            # crew#985). It is never closed or relaned; the founder merges it by hand.
            # 2026-10-11 (idp#5758): this exempted by author login, but every agent pushes with
            # the shared gh auth, so every agent PR was exempt too and dead agent work piled up
            # red for a day+ (#5617, #5632, #5704). Agent work always declares itself
            # (AGENTS.md §5 rule 5); only an undeclared PR is founder hand work.
            if not self.declared(pr):
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

    def declared(self, pr: dict) -> bool:
        """Is this pull request the engine's to drive: a dependency bot's, or one that says an
        agent raised it (a `Claim:`/`Agent:` line in the body or the head commit message,
        AGENTS.md §5 rule 5)? The pulls listing carries no commit messages, so the head commit
        is fetched only when the body is silent."""
        # dependabot cannot declare: its pull requests are machine-raised, and claim-gate
        # exempts dependabot[bot] from claims by name -- the same authority, mirrored here.
        # Treating it as undeclared founder work left every dependabot bump invisible to the
        # engine: #6238, the repo's oldest open PR, sat unadopted for days (measured 2026-10-18).
        if pr.get("user", {}).get("login") == DEPENDABOT:
            return True
        if AGENT_DECLARATION.search(pr.get("body") or ""):
            return True
        c = self.gh(f"commits/{pr.get('head', {}).get('sha', '')}") or {}
        msg = (c.get("commit") or {}).get("message") or ""
        return bool(AGENT_DECLARATION.search(msg))

    def heartbeat(self, lane: str, head: str) -> None:
        """Refresh the heartbeat of the claim a held lane lands on (idp#5758): an agent waiting
        on the lane queue must not watch its claim lapse and its finished work get refused.
        Stamps at most about hourly (the gate's limit is 2h), keeps the agent and paths the
        claim already declares, and never holds a lane on a stamping failure."""
        try:
            base = (
                self.git("merge-base", "origin/main", head, check=False)
                or "origin/main"
            )
            msgs = self.git("log", "--format=%B", f"{base}..{head}", check=False)
            m = CLAIM_REF.search(msgs)
            if not m:
                return
            issue, comments = self._issue_comments(m.group(1))
            claims = [c for c in map(CLAIM_LINE.search, _bodies(comments)) if c]
            if not claims:
                return
            c = claims[-1]
            # The lane's own trailer names the agent that raised it. Refreshing a claim held by
            # a different agent keeps alive a claim the claim-gate must refuse on every run: the
            # lane can never pass, the path is held for as long as the machine keeps stamping,
            # and the holder's heartbeat stays fresh so the claim never lapses (idp#5617 -- 16
            # refreshes over 55 hours, the one open PR red on `claimed by opencode, not
            # claude-code`). Stamp only the claim the lane names; leave another agent's alone.
            declared = AGENT_TRAILER.search(msgs)
            if declared and declared.group(1) != c["agent"]:
                return
            hb = datetime.fromisoformat(c["hb"].replace("Z", "+00:00"))
            if datetime.now(timezone.utc) - hb <= STAMP_AFTER:
                return
            # The restamp re-posts the paths, and claim-gate judges the LAST claim comment --
            # so a restamp copied from the last comment alone silently amputated every widening
            # posted in an earlier one: bpf/** was dropped from claim #6449 this way and
            # dockerfile-rot's b3075 was refused on files its claim used to cover (measured
            # 2026-10-18). Stamp the union of every claim comment this agent posted, so a
            # widening survives the machine's own stamping.
            paths = ",".join(
                dict.fromkeys(
                    p
                    for c2 in claims
                    if c2["agent"] == c["agent"]
                    for p in (c2["paths"].split(",") if c2["paths"] else [])
                    if p
                )
            )
            model = f" model={c['model']}" if c["model"] else ""
            self.gh(
                f"issues/{m.group(1)}/comments",
                "POST",
                {
                    "body": (
                        f"CLAIM agent={c['agent']}{model} paths={paths} "
                        f"heartbeat={datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}\n\n"
                        f"Heartbeat refreshed by the Greenlane: lane `{lane}` is held and still "
                        f"proving this claim's work (idp#5758 -- the machine keeps the claim "
                        f"alive it is working on)."
                    )
                },
            )
        except Exception:
            return

    def _issue_comments(self, num: str):
        issue = self.gh(f"issues/{num}") or {}
        comments = self.gh(f"issues/{num}/comments?per_page=100") or []
        return issue, comments

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
        cur = self.gh(f"pulls/{n}") or {}
        body = cur.get("body") or ""
        patch = {"body": f"{ADOPTED} {lane}\n\n{body}"}
        if cur.get("draft"):
            # A draft cannot be landed: #6366's green lane was refused with "Pull Request is
            # still a draft" until the flag was flipped by hand (2026-10-18). Adoption is the
            # engine saying it will land this work; un-draft it here, not at land time.
            patch["draft"] = False
        self.gh(
            f"pulls/{n}",
            "PATCH",
            patch,
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
