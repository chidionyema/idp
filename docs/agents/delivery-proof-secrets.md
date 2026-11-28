<!-- estate:routed-from AGENTS.md -- current law, not history. It is loaded on demand through the AGENTS.md route table instead of at Turn 1 (idp#8636). Moved verbatim. -->

## 2. Never hand-apply. Merge, and let Flux converge.

`kubectl apply` by hand is forbidden. PR merges to `main` → `build-multiarch.yml` builds amd64 +
arm64, Trivy, cosign → tag `ghcr.io/chidionyema/<name>:main-<run>-<sha>` → Flux image-reflector
polls → `image-automation` writes `flux/image-updates` → `deploy-when-green` merges on green.
`bin/build-image` enforces R24. Do not bypass it.

**An agent never raises a pull request and never pushes main** (founder 2026-09-29: "a PR that
can fail should never be allowed to be raised", "main must never go red, never"). Work reaches
main through the Greenlane only: push the branch to `lane/<name>` (`estate-execute lane-submit`),
then operationalise what can safely run from that exact pushed SHA. The lane
(`greenlane/engine.py`, `.github/workflows/greenlane.yml`) proves it green on
top of the current main, raises the pull request itself and fast-forwards main to the tested
commit; a red or conflicting lane keeps its branch and carries the reason on its head's
`greenlane` commit status. A hand-raised pull request is closed and relaned; a push to main is
refused by the ruleset. Flux deploys what lands — a real production log line is the only "done."
Runbook: `docs/runbooks/greenlane.md`. If the local `gh` CLI (HTTPS) stalls or the pre-push gate
hangs, that is a flaky network path to report and a missing door to add — not a reason to drag the
founder through manual re-runs. `git` over SSH and `curl` to the GitHub API keep working; use those,
or add a governed capability, but never convert a pipeline the estate already runs into a
founder-manned procedure.

**Pushing without the git hook (any agent, any model).** A push made through the GitHub API (blobs,
trees, commits, refs) runs no `.githooks/pre-push`, so none of the pre-CI rules would run on it
(2026-11-28: 29 of 32 Greenlane verdicts were red, most on rules the pusher could have run in
seconds). Use `bin/lane-push-api --lane lane/<name> --claim <owner/repo#N> --agent <name>
--message-file MSG PATH...` instead of calling those endpoints by hand: it runs the pinned
`ruff format`, `bin/language-gate` and the merge trial first, stamps your claim heartbeat just
before it authors the commit, and pushes without force. A refusal names the file and the exact
`Language-Exception: <path> -- <reason>` line to add; `BLIND` means a rule could not be judged and
nothing was written. `git push` of a lane runs the same rules through `bin/lane-preflight`, before
the disk floor.

### 2a. Yield before ceremony

Founder, 2026-11-10: once work is pushed, anything that can be operationalised immediately without
waiting for the Greenlane MUST be. Greenlane is convergence, not a waiting room. A local runtime,
preview, diagnostics path, registry refresh, or cloud-side capability that can safely run from the
exact pushed SHA is activated in the same turn, with its receipt, rollback and owner recorded.

This does not authorise direct pushes to `main`, skipping a gate, or deploying an unverified or
unpushed tree. Where production promotion depends on `main`, ship the safe operational path now
and let Greenlane perform the protected promotion. "Pushed" is the condition for immediate
operationalisation; "merged" is not.

---

## 3. Proof, not assertion

Never declare something WORKING from a synthetic probe, a green CI gate, or an HTTP 200. Prove it
with a real production log line. **"Built" and "operating" are different facts** — say which one
you mean. A gate that cannot fail is not a gate; a test that executes nothing is not a test.

This is two rules kept as one because they are one: **narrating instead of proving** and **asserting
instead of proving** are the same defect, an agent producing words where a measurement belongs.

**Operational** means *used*: the thing is doing its job in production, for its real caller, and
the founder can watch it doing that job live on /fleet (the primary work surface; a new page when it
needs one). A safeguard is operational only when /fleet shows it deciding (pass / refuse) on real
agent actions as they happen. A router lane is operational when /fleet shows real calls through it.

**Done = operational.** Merged, deployed, green CI, a healthy pod, an HTTP 200, a passing test: none
of these is done. Each is a step on the way, never the finish.

**Report only two things: done, or seriously blocked.** A merged PR, an opened PR, a pushed commit,
a green check is not news; do not announce it. A claim of "blocked" carries its evidence: the intent
that was run (`estate-execute <intent>` or `estate_invoke`), its exit status, and the line it
printed. A blocker without an intent run behind it is a guess, and is not reported.

---

## 4. Secrets — by name only, from the vault

Keys arrive through `estate-secrets` (SOPS + age) or the Bitwarden human-vault bridge:

```bash
gh workflow run vault-seed.yml -f entry=laptop
git -C ~/Documents/code/estate-secrets pull
source ~/Documents/code/estate-secrets/scripts/secret-load
```

Never paste a key into a file, an env var in code, a commit, a message, a journal entry, or a graph
node. Reference it by env var name. Never print a secret value. Never ask the founder to carry one
between surfaces.

---

