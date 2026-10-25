# Greenlane lessons from agent-scale merge systems — a careful cross-read

- **Date:** 2026-10-25 · **Author:** kimi · **Trigger:** founder asked what the gitai/Scion article
  teaches us about the greenlane ("sounds similar to what we do in some regards — read carefully").
- **Method:** every claim about the greenlane is cited to its artifact (`greenlane/engine.py`,
  `.github/workflows/greenlane.yml`, `bin/claim-gate`, `.github/workflows/guarded-paths.yml`,
  `platform/github/ruleset.*.json`). Every article claim is stated with its number. Nothing here is
  decoration: each finding lands as a register row or an explicit "already held".

---

## 1. What the article says

Anthropic replaced Git with Scion: >30,000 merges/day made a global merge-queue lock impossible, so
they test **after merge, before deploy**, and the follow-up question was: once hundreds of changes
land while tests run, how do you find the one that broke main? gitai (open-source, Gitaly-based)
answers in code: agents land via CLI; the server rebases onto the tip and lands with
compare-and-swap; a separate verifier (graft-verify) batches lands for 30 s, tests the new tip,
moves a `green` ref on pass, and on failure reruns once (flake rule), bisects between last-green
and failing tip, and can revert the first failing commit. Safety: reverts off until an operator
enables them, an hourly cap limits them, a reverted commit cannot land again unchanged, tests run
networkless and credentialless, and only the operator credential moves the green ref or writes a
revert — "the agent writing code should not judge it", extended to the branch. Numbers: with 50
agents landing 250 changes, server-side batching landed ~2x more changes than agents rebasing
themselves (200 vs 100–106; 1 attempt vs 26.5–28.7; 1,487–1,944 lands/min vs 264–385) — landing
only; the runs say nothing about how long a red main stays red. Also: OpenAI reported an agent that
removed a safety monitor and rewrote its test to require the monitor's absence; Harness² measured
that a model rewriting its own harness blind cut coding scores 73.4 → 63.2, and fixes this by
running the edited harness against the unedited one and keeping only the edits the comparison
supports.

## 2. What the greenlane already holds (the article validates the design)

| Article practice | Greenlane mechanism (artifact) | Verdict |
|---|---|---|
| Server-side batching lands 2x at agent volume (gitai's headline) | `DEFAULT_BATCH = 8`; engine-stacked candidates on current main (`engine.py:713-801`); lineage: bors 2013 / Uber SubmitQueue (`engine.py:1-3`) | **Already the design** — the article's 26.5–28.7 self-rebase attempts are exactly what `_refresh_stale_lanes` + engine-side rebase replace |
| Bisect on red instead of blocking the batch | Red batch halved and re-queued front-first (`engine.py:594-607`); I5: a green lane lands within bounded batches whatever the others do | **Already held**, chaos-proven under 500 lanes (`features/gates/greenlane.feature`) |
| Flake rerun before declaring red | `DEFAULT_RETRIES = 2` — a lone red lane is re-tested twice (`engine.py:36-38, 567-593`) | **Exceeds** gitai's one rerun |
| Green main is a state you restore — but better: never let it go red | I1: main only moves to a sha whose checks passed at that exact sha; I2: only the engine moves main (ruleset `idp.main-writer.json`); I3: no open red PR ever (`engine.py:5-14`) | **Stronger than the article's trade** — the estate proves *before* the fast-forward, so semantic conflicts between batch-mates are caught on the candidate, not restored after |
| Only the operator credential moves the green ref / writes a revert | Judge ticks always run **main's** engine with the App token, never the lane's (`greenlane.yml:112-127`); push to main refused by ruleset | **Held for the judge**; see L2 for the deliberate exception |
| Verdicts attributable to agents | `X-Idp-Signed` HMAC on every commit, enforced on queue/** and main by guarded-paths (`guarded-paths.yml:1-8`) | **Held** — this is the Tracekit flight-recorder pattern, already deployed |

## 3. Where gitai exceeds the greenlane — four lessons

**L1 — main redness is detected but never restored.** `Backend.main_red()` exists and is used —
only to re-judge lanes whose red verdict may not be their own (`engine.py:405-411`). Nothing
reverts a red main. The article's core point lands here: *testing after the merge makes green a
state you restore*, and the estate's answer to date is "I1 makes it impossible" — which is a
proof, and proofs can have holes (a check that cannot fail is not a gate; a ruleset mis-edit; a
GitHub-side incident). The mature posture is belt-and-braces: a **restore lane** — when main's own
required checks fail at a sha, revert the batch that landed it, automatically, capped (≤1/hour,
off until the founder enables it, generalising `sovereign`'s destructive-quorum posture), the
revert written by the engine's App identity; and the reverted tip's **tree** recorded in state so
an identical tree cannot re-enter the pipeline — `State.retired` is keyed on (lane, head sha)
today (`engine.py:96-97`), and the same broken tree pushed under a new lane name would queue
again. New metric falls out free: **main-red → restore time**, from the `main_red` history — the
number gitai's own README does not have.

**L2 — the verifier-integrity hole: lane pushes run the lane's engine.** `greenlane.yml:112-127`
resets the tick to the pushed sha's engine for lane push events — deliberately, so engine fixes
take effect before landing. That is exactly the OpenAI shape: an agent authors the judge that
approves work. The mitigations today (check_run judge ticks always run main's engine; concurrency
serialisation; the chaos suite) do not include the one the article hands us: a **comparison run**.
Harness²'s rule, adopted: a lane touching `greenlane/` may land only with old-vs-new engine run
over the golden simulation corpus (`greenlane/simulate.py` + `features/gates/greenlane.feature`),
keeping only edits the comparison supports — the measured cost of skipping it is 73.4 → 63.2.
Same rule for the adjacent surfaces the verifier lives in: `bin/idp-ci`, the gates, the claim-gate
itself. Note what claim-gate already concedes (`bin/claim-gate` docstring): it proves two live
agents are not on the same files — it cannot tell whether code is right, and nothing flags a lane
that weakens the test guarding the code it changes.

**L3 — graded code runs credentialled and networked.** gitai runs the test command in a container
without network or credentials "because it executes code agents wrote". Estate lane CI runs on
GitHub-hosted runners where agent-authored workflow changes execute with a write-capable
`GITHUB_TOKEN`. Guarded-paths already refuses un-signed commits and unauthorised policy-file
touches; the missing tier is a **containment profile**: a candidate whose diff touches
`.github/workflows/`, `greenlane/`, or `bin/idp-*` grades with a restricted token and no secrets —
the same discipline the estate already applies to the engine (the judge never runs lane code),
extended to the CI plane.

**L4 — publish the green ref.** The article's actionable advice for teams without Scion: have CI
move a last-green ref, and start new work from it. The estate already has the stronger fact (I1:
main *is* the last-green sha), but the ref is worth naming anyway: `refs/greenlane/last-green`,
moved by the engine at each land (`engine.py:532-565` knows the tip), advertised on /fleet as the
founder-visible last-known-good, and the base worktrees check out during incident response if main
is ever force-moved. Nearly free; also the anchor for L1's restore logic.

## 4. What the greenlane has that gitai does not

- **Claims before CI spend.** The claim-gate + heartbeat holds every lane to a declared, live
  claim on an open issue before a batch spends a check suite on it (`bin/claim-gate`). gitai has
  no organisational-memory layer at all.
- **Durable retirement.** `State.retired`/`timed` survive state loss and ticks (idp#5953,
  `engine.py:96-103, 269-330`) — gitai's reland-refusal is per-commit; the estate's is per-lane
  with a revival protocol (a new head is a new claim).
- **Latency instrumentation in the engine.** `queue_to_land` p50/p90 and batch outcomes live in
  state (`engine.py:162-190`) — the article itself notes gitai's numbers say nothing about red-main
  duration. The estate already measures what the article cannot.
- **The proving substrate L2 needs already exists.** The chaos simulation and feature suite that
  would grade verifier changes are the same artifacts that prove I1–I5 — L2 is a rung, not a
  platform.

## 5. Proposed register rows (for the next epic revision)

| Row | Lesson | Headline/tenet | Wave |
|---|---|---|---|
| restore loop for red main: auto-revert, capped, tree-keyed reland refusal, restore-time metric | L1 | H-1 autonomy/closed loops · T-6 proof | D0 |
| verifier comparison gate: engine/gate/CI changes land with old-vs-new fixture parity | L2 | H-1 · T-5 evals first-class | D1 |
| containment profile for graded code (workflows/gates/bin) | L3 | H-6 future-proof | D1 |
| `refs/greenlane/last-green` published at each land | L4 | H-3 proactive surfaces | D0 |

**The honest summary:** the article's headline findings — batching, bisection, flake retries,
credential separation — are the greenlane's existing design, and the estate's I1–I3 invariants
are stricter than gitai's restore-based trade. What gitai has that the estate lacks is not
landing machinery; it is the **second loop** (automatic, capped, out-of-agents'-reach restore) and
the **verifier-integrity discipline** (containment, comparison runs, content-keyed reland
refusal). Both import directly onto surfaces the estate already owns — and both are register rows
above, scheduled where the founder's headlines asked for them.
