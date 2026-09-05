## RESUME HERE
- crew#593 delivered: crew#594 (report + roles/founder.md, aa07e50), Telegram msg 18294. Waits founder read.
- crew#584 CP3 ticked with evidence (comment 5456333895); CP4 stays with idp#628 owner.
- Switching to: LAW 8 fix in claude-guards — auto-objective/estate_board `startswith("BLOCKED:")` misses a reply that opens with a markdown backtick, so a validated BLOCKED: is refused 4x. Worktree scratchpad/wt-guards, branch fix/blocked-escape-backtick.

## RESUME HERE — f3f21d6e audit lane, 2026-08-28 ~19:05Z
Task: crew#593 depth-psychology audit + crew#596 road to 9D. All written, pushed (crew PR #594 @ 7ad8273), Telegram 18294/18304-18306, crew#596 pinned, memory union-road-to-9d.md.
Next: founder reads #594 → merge → `git -C ~/dev/code/crew worktree remove --force <scratchpad>/wt-593`. claude-guards#201 merged 31e8197. Nothing else open on this lane.

## RESUME HERE — f3f21d6e audit lane, 2026-08-28 ~19:15Z
crew#594 MERGED d4a6e0c (audit + ROAD-TO-9D + roles/founder.md); crew#596 pinned; Telegram pins 18305/18306; cg#204 R48-zero-friction MERGED acc4191; cg#203 = Stage 1.1 ticket; cg#201 merged 31e8197.
Open: idp#631 (portal nav "Union"), rebased onto main after #626/#628; merge on green: `gh pr merge 631 -R chidionyema/idp --squash --delete-branch`, then `git -C ~/dev/code/idp worktree remove --force <scratchpad>/wt-idp-union`.

## f3f21d6e · audit · 2026-08-28T19:40Z
- idp#631 MERGED b1ea0bd (portal nav). idp#633 open (estate-founder `## The goal` + `--telegram`; wt scratchpad/wt-goal). crew#597 open (law-vocab, ruff fixed daf9d61; wt-595). crew#600 open (DECISION-RIGHTS; wt-16).
- Telegram GOAL pin 18328 live; crew#596 labelled `goal`.
- Next: Stage 1.8 `union stage 1` row in crew scripts/estate-snapshot; merge the three PRs on green + REVIEW:.

## f3f21d6e · audit · 2026-08-28T20:05Z
- Founder, furious: "we lost track of what founder is trying to accomplish, his dream healthy setup". Goal sentence written at the top of crew#596 (read by the founder page and the GOAL pin). Snapshot row (Stage 1.8) DROPPED, worktree removed. Board burn NOT done (5 closes/19 demotions listed in this session; wait for his word).
- Tailscale OAuth = other session's lane (idp#606 / ortal-polish), not this one.

## f3f21d6e · audit · 2026-08-28T20:35Z
- crew#562 (iPhone→Mac remote desk): Tailscale RUNNING 100.93.240.113, Sunshine service up :47990, creds user founder, password ONLY in ~/.estate/sunshine-founder.pass (0600); vault put BLIND (OCI session expired, crew#345). Telegram 18349 (had the password) DELETED, password rotated. Pin 18351 = founder's phone step (Moonlight PIN pairing).
- Founder: "we dont send password here" -> R49-no-secrets-in-chat, claude-guards#205 (merge on green).
- Board burn NOT done; Stage 1.8 row DROPPED; crew#600 open.

## RESUME HERE — session a7b41022 (verification-plane), 2026-08-29 17:2xZ
- crew#631: idp#831/#833/#836/#842 merged; CP3 proven (run 33264660281); CP9 waits for the catalogue image rollout (hourly :43 run).
- idp#835 (Langfuse one core) merged 17:09Z; login drill 33265030124 red only on Langfuse (OAuthCallback, old pod). Watcher bin9jj3ev waits for the cluster runs then reruns login-drill.yml.
- Founder 2026-08-29: "be ruthless and disable them" — drill-heartbeat, portability-drill, trace-drill, verify-drill disabled on GitHub (gh workflow disable). login-drill stays (Backstage is the portal). Next: PR that removes their schedule blocks and catalogue rows (branch chore/founder-disable-duplicate-drills, worktree $S/wtdrills), then crew item: staging namespace first, login drill as a Kuberhealthy check.
- Lean flip branch feat/crew584-run-lean parked until logins green.

## RESUME HERE — session 80471694, 2026-08-29 21:10Z
- crew#66 Tailscale road 2: DONE in inventory terms; idp#860 merged 7aab3311; apply run 33271070020 step 18 `ok mint`; receipt on crew#66.
- Now: crew#561 Otto parity. Finding: Tailscale GUI build cannot run Tailscale SSH (kb/1193: open-source tailscaled only); tagging the Mac breaks the founder's phone route (policy header). Road chosen: ACL `tag:k8s -> ${FOUNDER_TAILNET_USER}:22` + macOS Remote Login (already on) + CI-minted ed25519 key in vault `hermes-mac-run`; hermes-v2 image needs openssh-client + netcat-openbsd.
- Worktrees: ~/dev/code/.wt-otto (idp feat/crew561-otto-mac-run), ~/dev/code/.wt-hermes-ssh (hermes-v2 feat/crew561-ssh-client).
- Doctor run 33272111128 (architect-doctor) in flight for CP4/CP5 state.
- Founder words this hour: "prove this all works from scratch, product dept will demand this"; "recall we automate infra"; "personal agents have a commercial angle for the estate"; Windmill/staging captured on crew#646.

### session 80471694 — 2026-08-29 21:4x (RESUME HERE, supersedes the section above)
- Measured: the Mac IS tagged `tag:founder-mac` (tailscale status --self). Branch policy rewritten to name the tag (commit 0efffa80 in ~/dev/code/.wt-otto, branch feat/crew561-otto-mac-run). 56 tests green.
- af09b539: remote-desk README ticks measured items; Brewfile drops `cask tailscale`; `bin/idp-mac-adopt-otto --shortcut-key`.
- Push of the branch in flight (pre-push rungs, ~10 min). Then `gh pr create --body-file $S/pr-otto.md`, `bin/pr-evidence.py attach --no-push`, push. FREEZE: no merge, no apply.
- Founder hands left (measured): Privacy grants, Tailscale Run at Login (OFF), DeskPad display, Sunshine encoder, Moonlight pairing (0 clients), Shortcut.

## RESUME HERE — session 41fd24d8 (code-ad), 2026-08-29 22:2xZ
Founder: "lets prep for the crew migration to cloud" (crew#654; disaster recovery crew#300; portability crew#309).
Freeze still on: local prep only, no push/merge/dispatch. Worktree ~/dev/code/.wt-crew654 on
feat/crew654-cloud-session-bootstrap (from origin/main): bin/idp-session-bootstrap + .claude/settings.json
SessionStart hook + tests/test_crew654_session_bootstrap_installs_the_guards_on_a_clean_machine.py.
Clean-home drill ($S/clean-home-drill.sh): 31/32 Mac hooks exit 0 in a fresh clone of claude-estate; only
prompt-ledger fails closed on the empty payload. Next: commit locally, post the plan + result on crew#654.

## Session 80471694 (.wt-otto) — 2026-08-29T23:42Z
## RESUME HERE
- crew#561 Otto: idp#876 MERGED 0b433471; idp#883 (policy comment) MERGED 4fab9c52; apply run 33280827503 = `ok tailscale-policy applied` + key line; `bin/idp-mac-adopt-otto` on the Mac = ok (key from run 33280827503 authorized, sshd listens).
- otto-parity run 33281170001 FAIL: hermes gateway CrashLoopBackOff, log `entrypoint: /data/bin/hermes is not executable after the copy` (diagnose run 33281380053). Root cause: hermes-v2 1005760b (#50) dropped --no-preserve=mode, but cp keeps an EXISTING destination's mode and the PVC already holds bin/hermes at 0644 → test -x refuses every boot. Fix in flight: hermes-v2 branch fix/crew561-exec-bits-existing-volume (worktree $S/hv2): `cp -R --no-preserve=ownership --preserve=mode` + pinned test; then image-automation bumps the tag; rerun otto-parity.
- idp#885 (adopter reads any dispatched run; IDP_APPLY_RUN) body fixed (backticked Verify, Optimised shape, four LAW bullets), pushed; CI red earlier on tests/test_incident_founder_laws_guards_page_is_generated.py (passes locally) — recheck.
- crew#562 Jump Desktop: idp#882 MERGED a7a43969; posted on crew#562. Sunshine retirement after founder's first tap.
- Not mine, reported on crew#561 5465432154: iam-policy live statement, vault tenancy limit (crew#577), minimax key shape (crew#579), catalogue-drift, telemetry-coverage.

## RESUME HERE (session 80471694, lane .wt-otto, 2026-08-30 ~03:5xZ)
- crew#561 Otto: PROVEN, otto-parity PASS run 33285885139, receipt comment 5466026582; DONE needs the founder's Telegram reply.
- idp#904 rego review: pushed bb4addc1 (bin/policy-test runs conftest verify); watcher bml1ne7ur; merge on green (rule-guard refuses while checks run).
- crew#686 brainstorm: both research runs back (scratchpad research-product.md + capability list in this session); next = write docs/product/BRAINSTORM-2026-08-30.md in crew worktree .wt-brain686, PR, merge, comment crew#686 + crew#609.
- crew#681 asset register, crew#283 metrics ruling, crew#102 broadcast 5465986878 all posted.

## RESUME HERE (2026-08-30T02:45Z, session 80471694)
crew#561: hermes-v2#56 merged 577cf23f, image main-47, Flux bumped idp newTag; otto-parity run watching (bgk2kwnup). Next: idp PR adding gh-version, gh-auth and founder-mac-skill steps to the otto-parity playbook in bin/idp-oke-break-glass; then founder Telegram round trip.

## RESUME HERE (2026-08-30T03:1xZ, session 80471694)
kini: founder says what was built is not what he spec'd; suspending clusters/oke/platform.yaml temporal row in .wt-kini-suspend; then back to crew#561 Telegram round trip.

## RESUME HERE (2026-08-30 04:2xZ, session 80471694, .wt-macrun)
- crew#561: otto-parity run 33291368505 FAIL mac-run-hostname: `cp: cannot create regular file '/tmp/mac-run.id_ed25519': Permission denied` — gateway is readOnlyRootFilesystem and /tmp has no volume; fix mac-run.yaml to copy the key under $HERMES_HOME (/data, the PVC) plus a test.
- idp#923 (temporal suspend) watcher w923.sh; merge on green.

## RESUME HERE — .wt-macrun (session 80471694) 2026-08-30T06:1xZ
crew#561: idp#940 (main fix + Otto docs) 2f542e08, idp#923 (temporal suspend) 27980b6a, idp#955 (Reloader rolls the pod on mac-run change) 4a743bd3 all MERGED. Science lane's idp#949 (mac-run reads mounted key) is the Otto->Mac fix.
Next: otto-parity must read `ok mac-run-hostname` (loop running, up to 3 dispatches); then post on crew#561 and the founder's Telegram `mac-run hostname` is the DONE receipt. Branch fix/crew561-mac-run-configmap-reloads-the-pod is merged; worktree can be detached to origin/main.
